// Master BugBounty client-side recon snippet (high precision)
(function() {

    const VERSION = '1.0.0';
    const defaultConfig = {
        scriptConcurrency: 5,
        scriptTimeoutMs: 8000,
        includeTrackers: false,
        logToConsole: true,
        maxConsoleItemsPerSection: 20,
        hiddenObserver: false,
        hiddenObserverDebounceMs: 1000
    };

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

    const highConfidenceGtlds = new Set([
        'com', 'org', 'net', 'io', 'co', 'dev', 'app', 'ai', 'me', 'ly', 'xyz', 'info',
        'biz', 'gov', 'edu', 'mil', 'cloud', 'site', 'online', 'store', 'shop', 'tech',
        'media', 'global', 'group', 'systems', 'services', 'digital', 'solutions', 'agency',
        'live', 'world', 'games', 'casino', 'bet', 'tv', 'cc', 'gg', 'ws', 'fm', 'pro'
    ]);

    const suspiciousTlds = new Set([
        'length', 'display', 'current', 'message', 'params', 'notify', 'bind', 'show',
        'next', 'value', 'config', 'state', 'status', 'click', 'focus', 'href'
    ]);

    const hiddenNoiseTokens = [
        'darkreader', 'chat-widget', 'chatwidget', 'crisp', 'intercom', 'zendesk',
        'tawk', 'livechat', 'drift', 'hubspot-messages', 'chrome-extension', 'moz-extension'
    ];

    const globalIgnoredPrefixes = ['webkit', 'moz', '__', 'chrome', 'safari'];
    const globalIgnoredExact = new Set([
        'window', 'self', 'frames', 'parent', 'top', 'document', 'location', 'history',
        'navigator', 'navigation', 'credentialless', 'indexeddb', 'performance', 'screen',
        'caches', 'localstorage', 'sessionstorage', 'cookiestore', 'visualviewport',
        'origin', 'name', 'length', 'undefined', 'globalthis', 'trustedtypes', 'crypto'
    ]);

    const state = {
        config: { ...defaultConfig },
        inFlight: null,
        last: null,
        flat: null,
        observer: null,
        observerTimer: null
    };

    function parseUrlSafe(urlValue, baseUrl) {
        try {
            return baseUrl ? new URL(String(urlValue || '').trim(), baseUrl) : new URL(String(urlValue || '').trim());
        } catch (_err) {
            return null;
        }
    }

    function normalizeHost(hostValue) {
        return String(hostValue || '').trim().toLowerCase().replace(/^\.+|\.+$/g, '');
    }

    function isTrackerHost(hostname) {
        const host = normalizeHost(hostname);
        return trackerHostTokens.some(token => host === token || host.endsWith(`.${token}`) || host.includes(token));
    }

    function isLikelyDomain(hostname) {
        const host = normalizeHost(hostname);
        if (!host || !host.includes('.') || host.includes('..') || !/^[a-z0-9.-]+$/.test(host)) return false;
        const labels = host.split('.');
        if (labels.length < 2) return false;
        if (labels.some(label => !label || label.length > 63 || label.startsWith('-') || label.endsWith('-'))) return false;
        const tld = labels[labels.length - 1];
        if (!/^[a-z]{2,24}$/.test(tld)) return false;
        if (tld.length > 2 && !highConfidenceGtlds.has(tld)) return false;
        if (suspiciousTlds.has(tld)) return false;
        if (labels.every(label => label.length <= 2)) return false;
        return true;
    }

    function safePreview(value, maxLen) {
        let text = '';
        try {
            text = typeof value === 'string' ? value : JSON.stringify(value);
            if (!text) text = String(value);
        } catch (_err) {
            text = `[${typeof value} - nao serializavel]`;
        }
        return text.length > maxLen ? `${text.slice(0, maxLen - 3)}...` : text;
    }

    function tokenizeKey(input) {
        return String(input || '')
            .replace(/([a-z0-9])([A-Z])/g, '$1_$2')
            .replace(/[^a-zA-Z0-9]+/g, '_')
            .split('_')
            .map(token => token.trim().toLowerCase())
            .filter(Boolean);
    }

    function shouldSuppressSecret(key, value) {
        const keyText = String(key || '');
        const valueText = String(value || '');
        if (!keyText || !valueText || valueText.length < 16) return true;
        if (/^[A-Z0-9_]+$/.test(valueText) && /(PASSWORD|TOKEN|SECRET|KEY)/.test(valueText)) return true;
        return [/example/i, /dummy/i, /changeme/i, /placeholder/i, /sample/i, /(?:^|[_-])test(?:[_-]|$)/i]
            .some(rx => rx.test(keyText) || rx.test(valueText));
    }

    function addSetValues(targetSet, values) {
        (values || []).forEach(value => {
            if (value) targetSet.add(value);
        });
    }

    async function fetchWithTimeout(url, timeoutMs) {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), timeoutMs);
        try {
            return await fetch(url, { credentials: 'omit', signal: controller.signal });
        } finally {
            clearTimeout(timer);
        }
    }

    function collectScriptCandidates(config) {
        const candidates = [];
        const seen = new Set();
        const stats = { rawTotal: 0, skippedDuplicates: 0, skippedNonFetchable: 0, skippedTrackers: 0, skippedInvalid: 0 };

        function tryAdd(rawUrl) {
            const parsed = parseUrlSafe(rawUrl, window.location ? window.location.href : undefined);
            if (!parsed) { stats.skippedInvalid++; return; }
            if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') { stats.skippedNonFetchable++; return; }
            const normalized = parsed.href;
            if (seen.has(normalized)) { stats.skippedDuplicates++; return; }
            if (!config.includeTrackers && isTrackerHost(parsed.hostname)) { stats.skippedTrackers++; return; }
            seen.add(normalized);
            candidates.push(normalized);
        }

        const scriptNodes = Array.from(document.querySelectorAll('script[src]'));
        stats.rawTotal = scriptNodes.length;
        scriptNodes.forEach(node => tryAdd(node.src));

        if (window.performance && typeof window.performance.getEntriesByType === 'function') {
            (window.performance.getEntriesByType('resource') || [])
                .filter(entry => entry && entry.initiatorType === 'script' && entry.name)
                .forEach(entry => tryAdd(entry.name));
        }

        return { candidates, stats };
    }

    async function scanScripts(config) {
        const { candidates, stats } = collectScriptCandidates(config);
        const out = {
            urls: new Set(),
            apis: new Set(),
            secrets: new Map(),
            emails: new Set(),
            ips: new Set(),
            domains: new Set(),
            scriptErrors: [],
            scripts: {
                rawTotal: stats.rawTotal,
                total: candidates.length,
                success: 0,
                failed: 0,
                skipped: stats.skippedDuplicates + stats.skippedNonFetchable + stats.skippedTrackers + stats.skippedInvalid,
                skippedDuplicates: stats.skippedDuplicates,
                skippedNonFetchable: stats.skippedNonFetchable,
                skippedTrackers: stats.skippedTrackers,
                skippedInvalid: stats.skippedInvalid
            }
        };

        const rx = {
            urls: /https?:\/\/[a-zA-Z0-9._~:/?#@!$&'()*+,;=%-]+/gi,
            apis: /\/api\/(?:v\d+\/)?[a-zA-Z0-9_\/-{}:]+/gi,
            secrets: /["'`]?((?:api[_-]?key|api[_-]?secret|aws[_-]?secret(?:access[_-]?key)?|client[_-]?secret|access[_-]?token|refresh[_-]?token|auth[_-]?token|oauth[_-]?token|jwt[_-]?secret|password|passwd|private[_-]?key))["'`]?\s*[:=]\s*["'`]([A-Za-z0-9._~\-\/=+]{16,})["'`]/gi,
            emails: /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/gi,
            ips: /\b(?:\d{1,3}\.){3}\d{1,3}\b/g
        };

        let cursor = 0;
        async function worker() {
            while (true) {
                const idx = cursor++;
                if (idx >= candidates.length) return;
                const url = candidates[idx];
                try {
                    const response = await fetchWithTimeout(url, config.scriptTimeoutMs);
                    if (!response.ok) throw new Error(`HTTP ${response.status}`);
                    const text = await response.text();

                    const urlMatches = (text.match(rx.urls) || []).filter(item => {
                        const parsed = parseUrlSafe(item);
                        return parsed && (config.includeTrackers || !isTrackerHost(parsed.hostname)) && isLikelyDomain(parsed.hostname);
                    });
                    addSetValues(out.urls, urlMatches);
                    addSetValues(out.apis, text.match(rx.apis));
                    addSetValues(out.emails, text.match(rx.emails));
                    addSetValues(out.ips, (text.match(rx.ips) || []).filter(ip => /^\d{1,3}(?:\.\d{1,3}){3}$/.test(ip)));

                    urlMatches.forEach(item => {
                        const parsed = parseUrlSafe(item);
                        if (parsed && isLikelyDomain(parsed.hostname)) out.domains.add(normalizeHost(parsed.hostname));
                    });

                    rx.secrets.lastIndex = 0;
                    let match;
                    while ((match = rx.secrets.exec(text)) !== null) {
                        const key = String(match[1] || '').trim();
                        const value = String(match[2] || '').trim();
                        if (shouldSuppressSecret(key, value)) continue;
                        const formatted = `${key.toLowerCase()}="${value}"`;
                        out.secrets.set(formatted, (out.secrets.get(formatted) || 0) + 1);
                    }

                    out.scripts.success++;
                } catch (err) {
                    out.scripts.failed++;
                    out.scriptErrors.push({ url, reason: err && err.name === 'AbortError' ? 'Timeout' : 'CORS/Network Error' });
                }
            }
        }

        const workers = Math.min(config.scriptConcurrency, Math.max(1, candidates.length));
        await Promise.all(Array.from({ length: workers }, () => worker()));

        return {
            ...out,
            urls: Array.from(out.urls),
            apis: Array.from(out.apis),
            emails: Array.from(out.emails),
            ips: Array.from(out.ips),
            domains: Array.from(out.domains),
            secrets: Object.fromEntries(out.secrets)
        };
    }

    const globalMatchers = {
        privateKeys: (k, t) => k.includes('privatekey') || k.includes('private_key') || ['private', 'pem', 'rsa', 'certificate', 'cert', 'tls'].some(x => t.has(x)),
        paymentServices: (_k, t) => ['stripe', 'paypal', 'braintree', 'square', 'checkout', 'adyen', 'payment'].some(x => t.has(x)),
        cloudServices: (_k, t) => ['aws', 'azure', 'gcp', 'firebase', 'supabase', 'vercel', 'cloudflare'].some(x => t.has(x)),
        oauth: (_k, t) => ['oauth', 'jwt', 'bearer'].some(x => t.has(x)) || (t.has('refresh') && t.has('token')) || (t.has('access') && t.has('token')) || (t.has('client') && t.has('secret')),
        apiKeys: (k, t) => k.includes('apikey') || k.includes('api_key') || k.includes('api-secret') || ((t.has('api') || k.includes('api')) && ['key', 'secret', 'token', 'client'].some(x => t.has(x))),
        database: (_k, t) => ['database', 'postgres', 'postgresql', 'mongodb', 'mongo', 'redis', 'mysql', 'sqlite', 'sql', 'dsn'].some(x => t.has(x)) || (t.has('db') && ['connection', 'conn', 'uri', 'host', 'name'].some(x => t.has(x))),
        analytics: (_k, t) => ['analytics', 'tracking', 'segment', 'mixpanel', 'amplitude', 'matomo'].some(x => t.has(x)),
        crypto: (_k, t) => ['encrypt', 'encryption', 'decrypt', 'decryption', 'cipher', 'hash', 'hmac', 'nonce', 'salt', 'iv'].some(x => t.has(x)),
        credentials: (_k, t) => ['password', 'passwd', 'pwd', 'secret', 'credential', 'credentials'].some(x => t.has(x)) || (['auth', 'session'].some(x => t.has(x)) && ['token', 'secret'].some(x => t.has(x)))
    };

    function detectGlobalCategory(keyLower, tokenSet) {
        const order = ['privateKeys', 'paymentServices', 'cloudServices', 'oauth', 'apiKeys', 'database', 'analytics', 'crypto', 'credentials'];
        for (const category of order) {
            if (globalMatchers[category](keyLower, tokenSet)) return category;
        }
        return null;
    }

    function scanGlobals() {
        const out = {
            credentials: [], apiKeys: [], cloudServices: [], paymentServices: [], oauth: [],
            database: [], privateKeys: [], analytics: [], crypto: [], total: 0, analyzed: 0, skipped: 0
        };

        Object.getOwnPropertyNames(window).forEach(key => {
            const keyLower = key.toLowerCase();
            if (globalIgnoredExact.has(keyLower) || globalIgnoredPrefixes.some(p => keyLower.startsWith(p))) {
                out.skipped++;
                return;
            }

            let value;
            try { value = window[key]; } catch (_err) { out.skipped++; return; }
            if (typeof value === 'function' || value == null) { out.skipped++; return; }

            out.analyzed++;
            const tokenSet = new Set(tokenizeKey(key));
            const category = detectGlobalCategory(keyLower, tokenSet);
            if (!category) return;

            out[category].push({ key, type: typeof value, value: safePreview(value, 160) });
            out.total++;
        });

        return out;
    }

    function getHiddenReasons(el) {
        const reasons = [];
        const tag = String(el.tagName || '').toLowerCase();
        const type = String(el.getAttribute('type') || '').toLowerCase();

        if (tag === 'input' && type === 'hidden') reasons.push('input[type=hidden]');
        if (tag === 'input' && type === 'password') reasons.push('input[type=password]');
        if (el.hidden || el.hasAttribute('hidden')) reasons.push('hidden');
        if (String(el.getAttribute('aria-hidden') || '').toLowerCase() === 'true') reasons.push('aria-hidden=true');
        if (el.classList && typeof el.classList.contains === 'function' && el.classList.contains('hidden')) reasons.push('class:hidden');
        if (el.hasAttribute('data-hidden')) reasons.push('data-hidden');

        try {
            const cs = window.getComputedStyle(el);
            if (cs.display === 'none') reasons.push('display:none');
            if (cs.visibility === 'hidden') reasons.push('visibility:hidden');
            if (cs.opacity === '0') reasons.push('opacity:0');
        } catch (_err) {}

        return Array.from(new Set(reasons));
    }

    function shouldSkipHiddenNoise(el) {
        const id = String(el.id || '').toLowerCase();
        const cls = String(el.className || '').toLowerCase();
        const name = String(el.getAttribute('name') || '').toLowerCase();
        const src = String(el.getAttribute('src') || '').toLowerCase();
        const dataKeys = Object.keys(el.dataset || {}).map(k => k.toLowerCase());
        const hay = [id, cls, name, src, ...dataKeys].join(' ');

        if (hiddenNoiseTokens.some(token => hay.includes(token))) return true;
        return src.startsWith('chrome-extension:') || src.startsWith('moz-extension:');
    }

    function getHiddenValue(el) {
        const tag = String(el.tagName || '').toLowerCase();
        if (tag === 'input' || tag === 'textarea' || tag === 'select') return String(el.value || '').trim();
        const dataValue = el.getAttribute('data-value');
        if (dataValue) return String(dataValue).trim();
        return String(el.textContent || '').trim();
    }

    function scanHiddenElements() {
        const selector = ['input[type="hidden"]', 'input[type="password"]', '[hidden]', '[aria-hidden="true"]', '[data-hidden]', '.hidden', '[style]'].join(',');
        const nodes = document.querySelectorAll(selector);
        const rows = [];
        const seen = new Set();
        let skippedNoise = 0;

        nodes.forEach(el => {
            const reasons = getHiddenReasons(el);
            if (reasons.length === 0) return;
            if (shouldSkipHiddenNoise(el)) { skippedNoise++; return; }

            const value = getHiddenValue(el);
            const signature = [String(el.tagName || '').toLowerCase(), String(el.getAttribute('type') || '').toLowerCase(), String(el.name || ''), String(el.id || ''), value].join('|');
            if (seen.has(signature)) return;
            seen.add(signature);

            rows.push({
                Identificador: el.name || el.id || el.getAttribute('data-field') || '(Sem Identificacao)',
                Valor: value,
                Tipo_Elemento: String(el.tagName || ''),
                Visibilidade: reasons.join(', '),
                Classes: String(el.className || '').trim() || '(Nenhuma)',
                DataAttrs: Object.keys(el.dataset || {}).length ? JSON.stringify(el.dataset) : '(Nenhum)'
            });
        });

        return { rows, skippedNoise };
    }

    function flatten(report) {
        const flat = { globals: [], scripts: [], hidden: [] };

        ['credentials', 'privateKeys', 'apiKeys', 'cloudServices', 'paymentServices', 'oauth', 'database', 'crypto', 'analytics']
            .forEach(category => {
                (report.globals[category] || []).forEach(item => {
                    flat.globals.push({ module: 'globals', category, key: item.key, value: item.value, type: item.type });
                });
            });

        Object.keys(report.scripts.secrets || {}).forEach(key => flat.scripts.push({ module: 'scripts', category: 'secrets', key, count: report.scripts.secrets[key] }));
        (report.scripts.apis || []).forEach(item => flat.scripts.push({ module: 'scripts', category: 'apis', key: item }));
        (report.scripts.urls || []).forEach(item => flat.scripts.push({ module: 'scripts', category: 'urls', key: item }));
        (report.scripts.domains || []).forEach(item => flat.scripts.push({ module: 'scripts', category: 'domains', key: item }));
        (report.scripts.emails || []).forEach(item => flat.scripts.push({ module: 'scripts', category: 'emails', key: item }));
        (report.scripts.ips || []).forEach(item => flat.scripts.push({ module: 'scripts', category: 'ips', key: item }));

        (report.hidden.rows || []).forEach(row => {
            flat.hidden.push({
                module: 'hidden',
                category: 'field',
                key: row.Identificador,
                value: row.Valor,
                visibility: row.Visibilidade,
                type: row.Tipo_Elemento
            });
        });

        return flat;
    }

    function bySeverity(report, flat) {
        const out = { critical: [], high: [], medium: [], low: [] };

        flat.globals.forEach(item => {
            if (['credentials', 'privateKeys', 'oauth'].includes(item.category)) out.critical.push(item);
            else if (['apiKeys', 'paymentServices', 'database'].includes(item.category)) out.high.push(item);
            else if (['cloudServices', 'crypto'].includes(item.category)) out.medium.push(item);
            else out.low.push(item);
        });

        flat.scripts.forEach(item => {
            if (item.category === 'secrets') out.critical.push(item);
            else if (item.category === 'apis') out.high.push(item);
            else if (item.category === 'emails' || item.category === 'ips') out.medium.push(item);
            else out.low.push(item);
        });

        (report.hidden.rows || []).forEach(row => {
            const text = `${row.Identificador} ${row.Valor}`.toLowerCase();
            const payload = { module: 'hidden', category: 'field', key: row.Identificador, value: row.Valor, visibility: row.Visibilidade, type: row.Tipo_Elemento };
            if (['token', 'secret', 'password', 'auth', 'session', 'csrf'].some(k => text.includes(k))) out.high.push(payload);
            else out.medium.push(payload);
        });

        return out;
    }

    function toCsv(flat) {
        const header = ['module', 'category', 'key', 'value', 'type', 'count', 'visibility'];
        const rows = [header.join(',')];
        const all = [...flat.globals, ...flat.scripts, ...flat.hidden];

        function esc(value) {
            return `"${String(value == null ? '' : value).replace(/"/g, '""').replace(/\r?\n/g, '\\n')}"`;
        }

        all.forEach(item => {
            rows.push([
                esc(item.module),
                esc(item.category || ''),
                esc(item.key || ''),
                esc(item.value || ''),
                esc(item.type || ''),
                esc(item.count == null ? '' : item.count),
                esc(item.visibility || '')
            ].join(','));
        });

        return rows.join('\n');
    }

    function downloadText(name, text) {
        const blob = new Blob([text], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = name;
        a.click();
        URL.revokeObjectURL(url);
    }

    function printReport(report) {
        if (!state.config.logToConsole) return;
        const max = state.config.maxConsoleItemsPerSection;

        console.log('\n');
        console.log('%c===============================================================%c', 'color: cyan;', '');
        console.log('%c[+] BUG BOUNTY MASTER REPORT%c', 'color: cyan; font-weight: bold;', '');
        console.log('%c===============================================================%c', 'color: cyan;', '');

        const globals = state.flat.globals;
        const scripts = state.flat.scripts;
        const hidden = state.flat.hidden;

        if (globals.length) {
            console.group(`%c[i] Globals (${globals.length})%c`, 'color: orange; font-weight: bold;', '');
            globals.slice(0, max).forEach(item => console.log(item));
            if (globals.length > max) console.log(`... e ${globals.length - max} mais`);
            console.groupEnd();
        }

        if (scripts.length) {
            console.group(`%c[i] Scripts (${scripts.length})%c`, 'color: purple; font-weight: bold;', '');
            scripts.slice(0, max).forEach(item => console.log(item));
            if (scripts.length > max) console.log(`... e ${scripts.length - max} mais`);
            console.groupEnd();
        }

        if (hidden.length) {
            console.group(`%c[i] Hidden (${hidden.length})%c`, 'color: green; font-weight: bold;', '');
            hidden.slice(0, max).forEach(item => console.log(item));
            if (hidden.length > max) console.log(`... e ${hidden.length - max} mais`);
            console.groupEnd();
        }

        console.log('');
        console.log('%c[+] SUMMARY:%c', 'color: cyan; font-weight: bold;', '');
        console.log(`   Globals suspeitos: ${report.summary.globalsFindings}`);
        console.log(`   Scripts processados: ${report.summary.scriptsSuccess}/${report.summary.scriptsTotal}`);
        console.log(`   Scripts com erro: ${report.summary.scriptsFailed}`);
        console.log(`   Scripts pulados: ${report.summary.scriptsSkipped}`);
        console.log(`   Hidden fields: ${report.summary.hiddenFindings}`);
        console.log(`   Total consolidado: ${report.summary.totalFindings}`);
        console.log('%c===============================================================%c', 'color: cyan;', '');
    }

    function ensureLast() {
        if (!state.last) throw new Error('Nenhuma analise executada ainda. Use bugBountyMaster.run()');
    }

    function startObserver() {
        if (state.observer) return true;
        if (typeof MutationObserver !== 'function') return false;

        state.observer = new MutationObserver(() => {
            if (state.observerTimer) clearTimeout(state.observerTimer);
            state.observerTimer = setTimeout(() => {
                if (!state.last) return;
                state.last.hidden = scanHiddenElements();
                state.flat = flatten(state.last);
                state.last.severity = bySeverity(state.last, state.flat);
                state.last.summary.hiddenFindings = state.last.hidden.rows.length;
                state.last.summary.totalFindings = state.last.summary.globalsFindings + state.last.summary.scriptsFindings + state.last.summary.hiddenFindings;
            }, state.config.hiddenObserverDebounceMs);
        });

        state.observer.observe(document.documentElement || document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['style', 'class', 'hidden', 'aria-hidden']
        });

        return true;
    }

    function stopObserver() {
        if (state.observer) {
            state.observer.disconnect();
            state.observer = null;
        }
        if (state.observerTimer) {
            clearTimeout(state.observerTimer);
            state.observerTimer = null;
        }
    }

    async function runInternal(overrides) {
        const config = { ...state.config, ...(overrides || {}) };
        const [globals, scripts, hidden] = await Promise.all([scanGlobals(), scanScripts(config), scanHiddenElements()]);

        const report = {
            version: VERSION,
            generatedAt: new Date().toISOString(),
            config,
            globals,
            scripts,
            hidden,
            summary: {
                globalsFindings: globals.total,
                scriptsFindings: Object.keys(scripts.secrets).length + scripts.apis.length + scripts.urls.length + scripts.emails.length + scripts.ips.length + scripts.domains.length,
                hiddenFindings: hidden.rows.length,
                scriptsTotal: scripts.scripts.total,
                scriptsSuccess: scripts.scripts.success,
                scriptsFailed: scripts.scripts.failed,
                scriptsSkipped: scripts.scripts.skipped,
                totalFindings: 0
            }
        };

        report.summary.totalFindings = report.summary.globalsFindings + report.summary.scriptsFindings + report.summary.hiddenFindings;
        state.config = config;
        state.last = report;
        state.flat = flatten(report);
        report.severity = bySeverity(report, state.flat);

        if (config.hiddenObserver) startObserver(); else stopObserver();
        printReport(report);

        return report;
    }

    const api = {
        version: VERSION,

        run: async (overrides = {}) => {
            if (state.inFlight) return state.inFlight;
            state.inFlight = runInternal(overrides).finally(() => { state.inFlight = null; });
            return state.inFlight;
        },

        getAll: () => {
            ensureLast();
            return state.last;
        },

        export: (format = 'json') => {
            ensureLast();
            const normalized = String(format || 'json').toLowerCase();
            if (normalized === 'csv') return toCsv(state.flat);
            const payload = {
                version: state.last.version,
                generatedAt: state.last.generatedAt,
                config: state.last.config,
                summary: state.last.summary,
                globals: state.last.globals,
                scripts: state.last.scripts,
                hidden: state.last.hidden,
                severity: state.last.severity
            };
            return normalized === 'json' ? JSON.stringify(payload, null, 2) : payload;
        },

        download: (format = 'json') => {
            const normalized = String(format || 'json').toLowerCase();
            const data = api.export(normalized);
            downloadText(`bugbounty-master-${Date.now()}.${normalized}`, data);
        },

        filter: (scope = 'all', keyword = '') => {
            ensureLast();
            const src = String(scope || 'all').toLowerCase();
            const query = String(keyword || '').toLowerCase();

            let pool = [];
            if (src === 'all' || src === 'globals') pool = pool.concat(state.flat.globals);
            if (src === 'all' || src === 'scripts') pool = pool.concat(state.flat.scripts);
            if (src === 'all' || src === 'hidden') pool = pool.concat(state.flat.hidden);

            if (!query) return pool;
            return pool.filter(item => [item.module, item.category, item.key, item.value, item.type, item.visibility].map(v => String(v || '').toLowerCase()).join(' ').includes(query));
        },

        bySeverity: () => {
            ensureLast();
            return state.last.severity;
        },

        startObserver: () => startObserver(),
        stopObserver: () => { stopObserver(); return true; },
        config: () => ({ ...state.config }),
        setConfig: (cfg = {}) => { state.config = { ...state.config, ...(cfg || {}) }; return { ...state.config }; }
    };

    window.bugBountyMaster = api;
    api.ready = api.run();

    console.log('%c[i] bugBountyMaster inicializado%c', 'color: blue; font-weight: bold;', '');
    console.log("   .ready | .run() | .getAll() | .export('json'|'csv') | .download() | .filter('all','token') | .bySeverity()");
})();
