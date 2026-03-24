// Analisador otimizado de scripts client-side com deteccao high precision de segredos
(async function() {
    console.clear();

    const MAX_CONCURRENCY = 5;
    const FETCH_TIMEOUT_MS = 8000;

    const rawScripts = Array.from(document.querySelectorAll('script[src]')).map(node => node.src);
    const seenScriptUrls = new Set();
    const scripts = [];

    let skippedNonFetchable = 0;
    let skippedTrackers = 0;

    const patterns = {
        urls: /https?:\/\/[a-zA-Z0-9._~:/?#@!$&'()*+,;=%-]+/gi,
        apiEndpoints: /\/api\/(?:v\d+\/)?[a-zA-Z0-9_\/-{}]+/gi,
        secrets: /["'`]?((?:api[_-]?key|api[_-]?secret|aws[_-]?secret(?:access[_-]?key)?|client[_-]?secret|access[_-]?token|refresh[_-]?token|auth[_-]?token|oauth[_-]?token|jwt[_-]?secret|password|passwd|private[_-]?key))["'`]?\s*[:=]\s*["'`]([A-Za-z0-9._~\-\/=+]{16,})["'`]/gi,
        emails: /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/gi,
        ipAddresses: /\b(?:\d{1,3}\.){3}\d{1,3}\b/g
    };

    const placeholderRegexes = [
        /example/i,
        /dummy/i,
        /changeme/i,
        /placeholder/i,
        /sample/i,
        /\\.\\.\\./,
        /(?:^|[_-])test(?:[_-]|$)/i,
        /^(?:x{8,}|a{8,}|0{8,})$/i
    ];

    const suspiciousTldTokens = new Set([
        'length',
        'display',
        'current',
        'message',
        'params',
        'notify',
        'bind',
        'show',
        'next',
        'value',
        'config',
        'state',
        'status',
        'click',
        'focus',
        'href'
    ]);

    const highConfidenceGtlds = new Set([
        'com', 'org', 'net', 'io', 'co', 'dev', 'app', 'ai', 'me', 'ly', 'xyz',
        'info', 'biz', 'gov', 'edu', 'mil', 'cloud', 'site', 'online', 'store',
        'shop', 'tech', 'media', 'global', 'group', 'systems', 'services',
        'digital', 'solutions', 'agency', 'live', 'world', 'games', 'casino',
        'bet', 'tv', 'cc', 'gg', 'ws', 'fm', 'pro'
    ]);

    const trackerHostTokens = [
        'clarity.ms',
        'googletagmanager.com',
        'google-analytics.com',
        'doubleclick.net',
        'hotjar.com',
        'facebook.net',
        'facebook.com',
        'stats-collector.'
    ];

    function parseUrlSafe(urlValue) {
        const normalized = String(urlValue || '').trim();
        if (!normalized) {
            return null;
        }

        try {
            return new URL(normalized);
        } catch (_err) {
            return null;
        }
    }

    function normalizeHost(hostCandidate) {
        return String(hostCandidate || '')
            .trim()
            .toLowerCase()
            .replace(/^\.+|\.+$/g, '');
    }

    function isTrackerHost(hostname) {
        const host = normalizeHost(hostname);
        if (!host) {
            return false;
        }

        return trackerHostTokens.some(token =>
            host === token || host.endsWith(`.${token}`) || host.includes(token)
        );
    }

    function isLikelyDomain(hostCandidate) {
        const host = normalizeHost(hostCandidate);
        if (!host || host.length > 253) {
            return false;
        }

        if (!host.includes('.') || host.includes('..')) {
            return false;
        }

        if (!/^[a-z0-9.-]+$/.test(host)) {
            return false;
        }

        const labels = host.split('.');
        if (labels.length < 2) {
            return false;
        }

        if (labels.some(label => label.length < 1 || label.length > 63 || label.startsWith('-') || label.endsWith('-'))) {
            return false;
        }

        const tld = labels[labels.length - 1];
        if (!/^[a-z]{2,24}$/.test(tld)) {
            return false;
        }

        if (tld.length > 2 && !highConfidenceGtlds.has(tld)) {
            return false;
        }

        if (suspiciousTldTokens.has(tld)) {
            return false;
        }

        if (labels.every(label => label.length <= 2)) {
            return false;
        }

        return true;
    }

    function isHighConfidenceUrl(urlValue) {
        const parsed = parseUrlSafe(urlValue);
        if (!parsed) {
            return false;
        }

        if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
            return false;
        }

        if (isTrackerHost(parsed.hostname)) {
            return false;
        }

        return isLikelyDomain(parsed.hostname);
    }

    rawScripts.forEach(url => {
        const normalized = String(url || '').trim();
        if (!normalized || normalized.startsWith('data:') || normalized.startsWith('blob:')) {
            skippedNonFetchable++;
            return;
        }

        if (seenScriptUrls.has(normalized)) {
            skippedNonFetchable++;
            return;
        }

        const parsed = parseUrlSafe(normalized);
        const host = parsed ? parsed.hostname : '';
        if (host && isTrackerHost(host)) {
            skippedTrackers++;
            return;
        }

        seenScriptUrls.add(normalized);
        scripts.push(normalized);
    });

    const results = {
        secrets: new Map(),
        urls: new Set(),
        apis: new Set(),
        emails: new Set(),
        ips: new Set(),
        domains: new Set(),
        scripts: {
            success: 0,
            failed: 0,
            total: scripts.length,
            skipped: skippedNonFetchable + skippedTrackers,
            skippedNonFetchable: skippedNonFetchable,
            skippedTrackers: skippedTrackers,
            rawTotal: rawScripts.length
        }
    };

    function shouldSuppressSecret(keyName, secretValue) {
        const value = String(secretValue || '');
        const key = String(keyName || '');
        const valueLower = value.toLowerCase();

        if (value.length < 16) {
            return true;
        }

        if (/^[A-Z0-9_]+$/.test(value) && /(PASSWORD|TOKEN|SECRET|KEY)/.test(value)) {
            return true;
        }

        if (
            valueLower.includes('localhost') ||
            valueLower.includes('127.0.0.1') ||
            valueLower.includes('example.com') ||
            valueLower.includes('example.org') ||
            valueLower.includes('example.net')
        ) {
            return true;
        }

        return placeholderRegexes.some(regex => regex.test(value) || regex.test(key));
    }

    function extractSecrets(scriptText) {
        const found = [];
        patterns.secrets.lastIndex = 0;

        let match;
        while ((match = patterns.secrets.exec(scriptText)) !== null) {
            const keyName = String(match[1] || '').trim();
            const secretValue = String(match[2] || '').trim();

            if (!keyName || !secretValue) {
                continue;
            }

            if (shouldSuppressSecret(keyName, secretValue)) {
                continue;
            }

            found.push(`${keyName.toLowerCase()}="${secretValue}"`);
        }

        return found;
    }

    function extractDomainsFromUrls(urlsInCurrentScript) {
        const domains = new Set();

        urlsInCurrentScript.forEach(urlValue => {
            const parsed = parseUrlSafe(urlValue);
            if (!parsed) {
                return;
            }

            const host = normalizeHost(parsed.hostname);
            if (isLikelyDomain(host)) {
                domains.add(host);
            }
        });

        return domains;
    }

    function addMatchesToSet(targetSet, matches) {
        if (!matches) {
            return;
        }

        matches.forEach(item => {
            if (item) {
                targetSet.add(item);
            }
        });
    }

    async function fetchWithTimeout(url) {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);

        try {
            return await fetch(url, {
                credentials: 'omit',
                signal: controller.signal
            });
        } finally {
            clearTimeout(timer);
        }
    }

    function getFileName(url) {
        const parts = url.split('/');
        return parts[parts.length - 1] || url;
    }

    console.log(`%c[+] Iniciando analise de ${scripts.length} arquivos JS (high precision)...%c`, 'color: blue; font-weight: bold;', '');
    if (results.scripts.skippedNonFetchable > 0) {
        console.log(`%c[i] URLs puladas (duplicadas/blob/data): ${results.scripts.skippedNonFetchable}%c`, 'color: gray;', '');
    }
    if (results.scripts.skippedTrackers > 0) {
        console.log(`%c[i] Scripts tracker pulados: ${results.scripts.skippedTrackers}%c`, 'color: gray;', '');
    }

    let processed = 0;
    let cursor = 0;

    async function processScript(url) {
        try {
            const response = await fetchWithTimeout(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const text = await response.text();

            const secretMatches = extractSecrets(text);
            secretMatches.forEach(secret => {
                const count = results.secrets.get(secret) || 0;
                results.secrets.set(secret, count + 1);
            });

            const urlMatches = (text.match(patterns.urls) || []).filter(isHighConfidenceUrl);
            addMatchesToSet(results.urls, urlMatches);
            addMatchesToSet(results.apis, text.match(patterns.apiEndpoints));
            addMatchesToSet(results.emails, text.match(patterns.emails));
            addMatchesToSet(results.ips, text.match(patterns.ipAddresses));
            const extractedDomains = extractDomainsFromUrls(urlMatches);
            addMatchesToSet(results.domains, Array.from(extractedDomains));

            results.scripts.success++;
            console.log(`%c[+] ${++processed}/${scripts.length}%c ${getFileName(url)}`, 'color: green;', '');
        } catch (err) {
            results.scripts.failed++;
            const reason = err && err.name === 'AbortError' ? 'Timeout' : 'CORS/Network Error';
            console.warn(`%c[-] ${++processed}/${scripts.length}%c ${getFileName(url)} (${reason})`, 'color: orange;', '');
        }
    }

    async function worker() {
        while (true) {
            const current = cursor;
            cursor += 1;

            if (current >= scripts.length) {
                return;
            }

            await processScript(scripts[current]);
        }
    }

    const workerCount = Math.min(MAX_CONCURRENCY, Math.max(1, scripts.length));
    await Promise.all(Array.from({ length: workerCount }, () => worker()));

    console.log('\n');
    console.log('%c===============================================================%c', 'color: cyan;', '');
    console.log('%c[+] RELATORIO DE ANALISE DE SCRIPTS%c', 'color: cyan; font-weight: bold;', '');
    console.log('%c===============================================================%c', 'color: cyan;', '');

    if (results.secrets.size > 0) {
        console.group(`%c[!] SEGREDOS DETECTADOS (${results.secrets.size})%c`, 'color: red; font-weight: bold;', '');
        results.secrets.forEach((count, secret) => {
            console.warn(`${secret} (encontrado ${count}x)`);
        });
        console.groupEnd();
    }

    if (results.apis.size > 0) {
        console.group(`%c[i] ENDPOINTS DE API (${results.apis.size})%c`, 'color: purple; font-weight: bold;', '');
        Array.from(results.apis).sort().forEach(api => console.log(api));
        console.groupEnd();
    }

    if (results.urls.size > 0) {
        console.group(`%c[i] URLs ENCONTRADAS (${results.urls.size})%c`, 'color: blue; font-weight: bold;', '');
        Array.from(results.urls).sort().slice(0, 20).forEach(url => console.log(url));
        if (results.urls.size > 20) {
            console.log(`... e ${results.urls.size - 20} mais`);
        }
        console.groupEnd();
    }

    if (results.emails.size > 0) {
        console.group(`%c[i] EMAILS ENCONTRADOS (${results.emails.size})%c`, 'color: orange; font-weight: bold;', '');
        Array.from(results.emails).sort().forEach(email => console.log(email));
        console.groupEnd();
    }

    if (results.ips.size > 0) {
        console.group(`%c[i] ENDERECOS IP ENCONTRADOS (${results.ips.size})%c`, 'color: darkred; font-weight: bold;', '');
        Array.from(results.ips).sort().forEach(ip => console.log(ip));
        console.groupEnd();
    }

    if (results.domains.size > 0) {
        console.group(`%c[i] DOMINIOS ENCONTRADOS (${results.domains.size})%c`, 'color: brown; font-weight: bold;', '');
        Array.from(results.domains).sort().slice(0, 20).forEach(domain => console.log(domain));
        if (results.domains.size > 20) {
            console.log(`... e ${results.domains.size - 20} mais`);
        }
        console.groupEnd();
    }

    console.log('\n');
    console.log('%c[+] RESUMO:%c', 'color: cyan; font-weight: bold;', '');
    console.log(`   Scripts processados: ${results.scripts.success}/${results.scripts.total}`);
    console.log(`   Scripts com erro: ${results.scripts.failed}`);
    console.log(`   Scripts pulados: ${results.scripts.skipped}`);
    console.log(`   Scripts tracker pulados: ${results.scripts.skippedTrackers}`);
    console.log(`   Total de itens encontrados: ${results.secrets.size + results.apis.size + results.urls.size + results.emails.size + results.ips.size + results.domains.size}`);
    console.log('\n');

    window.analysisResults = {
        secrets: Object.fromEntries(results.secrets),
        urls: Array.from(results.urls),
        apis: Array.from(results.apis),
        emails: Array.from(results.emails),
        ips: Array.from(results.ips),
        domains: Array.from(results.domains),

        export: (format = 'json') => {
            const data = {
                timestamp: new Date().toISOString(),
                secrets: Object.fromEntries(results.secrets),
                urls: Array.from(results.urls),
                apis: Array.from(results.apis),
                emails: Array.from(results.emails),
                ips: Array.from(results.ips),
                domains: Array.from(results.domains),
                summary: results.scripts
            };
            return format === 'json' ? JSON.stringify(data, null, 2) : data;
        },

        download: (format = 'json') => {
            const data = window.analysisResults.export(format);
            const blob = new Blob([data], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `script-analysis-${Date.now()}.${format}`;
            a.click();
            URL.revokeObjectURL(url);
        },

        filter: (type, query = '') => {
            const queryLower = String(query).toLowerCase();
            switch (String(type || '').toLowerCase()) {
                case 'secrets':
                    return Array.from(results.secrets.entries()).filter(([secret]) =>
                        secret.toLowerCase().includes(queryLower)
                    );
                case 'urls':
                    return Array.from(results.urls).filter(url =>
                        url.toLowerCase().includes(queryLower)
                    );
                case 'apis':
                    return Array.from(results.apis).filter(api =>
                        api.toLowerCase().includes(queryLower)
                    );
                case 'emails':
                    return Array.from(results.emails).filter(email =>
                        email.toLowerCase().includes(queryLower)
                    );
                case 'ips':
                    return Array.from(results.ips).filter(ip =>
                        ip.toLowerCase().includes(queryLower)
                    );
                case 'domains':
                    return Array.from(results.domains).filter(domain =>
                        domain.toLowerCase().includes(queryLower)
                    );
                default:
                    return [];
            }
        }
    };

    console.log('%c[i] Use window.analysisResults para acessar os dados:%c', 'color: blue; font-style: italic;', '');
    console.log("   .export('json') | .download('json') | .filter('apis', '/users')");
    console.log('%c===============================================================%c', 'color: cyan;', '');
})();
