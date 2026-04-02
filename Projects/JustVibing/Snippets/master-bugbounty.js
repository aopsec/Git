// Master BugBounty client-side recon snippet (high precision)
(function() {

    const VERSION = '1.0.3';
    const defaultConfig = {
        scriptConcurrency: 8,
        maxScriptsToScan: 500,
        scriptTimeoutMs: 12000,
        includeTrackers: false,
        logToConsole: true,
        maxConsoleItemsPerSection: 20,
        hiddenObserver: false,
        hiddenObserverDebounceMs: 1000,
        ignoreBlockedResources: true,
        retryFailedRequests: true,
        maxRetries: 3,
        corsMode: 'cors',
        verbose: true,
        detectBlockedByClient: true,
        usePerformanceAPI: true,
        requireInScope: false,
        inScopeHosts: [],
        maskSensitiveOutput: true,
        maxResponseChars: 2000000
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
        config: normalizeConfig(defaultConfig),
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

    function nowMs() {
        if (typeof performance !== 'undefined' && performance && typeof performance.now === 'function') {
            return performance.now();
        }
        return Date.now();
    }

    function clampInt(value, fallback, min, max) {
        const n = Number(value);
        if (!Number.isFinite(n)) return fallback;
        const i = Math.floor(n);
        if (i < min) return min;
        if (i > max) return max;
        return i;
    }

    function clampBool(value, fallback) {
        return typeof value === 'boolean' ? value : fallback;
    }

    function normalizeCorsMode(mode, fallback = 'cors') {
        const allowed = new Set(['cors', 'no-cors', 'same-origin']);
        const text = String(mode || '').toLowerCase();
        return allowed.has(text) ? text : fallback;
    }

    function isIpLikeHost(hostname) {
        return /^\d{1,3}(?:\.\d{1,3}){3}$/.test(String(hostname || ''));
    }

    function isLikelyHost(hostname) {
        const host = normalizeHost(hostname);
        if (!host) return false;
        if (host === 'localhost') return true;
        if (isIpLikeHost(host)) return true;
        return isLikelyDomain(host);
    }

    function normalizeScopeHosts(scopeHosts) {
        if (!Array.isArray(scopeHosts)) return [];
        const uniq = new Set();
        scopeHosts.forEach(item => {
            const host = normalizeHost(item);
            if (!host) return;
            if (!isLikelyHost(host)) return;
            uniq.add(host);
        });
        return Array.from(uniq).sort((a, b) => a.localeCompare(b));
    }

    function normalizeConfig(inputConfig) {
        const cfg = { ...defaultConfig, ...(inputConfig || {}) };
        const normalized = {
            ...cfg,
            scriptConcurrency: clampInt(cfg.scriptConcurrency, defaultConfig.scriptConcurrency, 1, 32),
            maxScriptsToScan: clampInt(cfg.maxScriptsToScan, defaultConfig.maxScriptsToScan, 1, 5000),
            scriptTimeoutMs: clampInt(cfg.scriptTimeoutMs, defaultConfig.scriptTimeoutMs, 1000, 60000),
            maxConsoleItemsPerSection: clampInt(cfg.maxConsoleItemsPerSection, defaultConfig.maxConsoleItemsPerSection, 1, 200),
            hiddenObserverDebounceMs: clampInt(cfg.hiddenObserverDebounceMs, defaultConfig.hiddenObserverDebounceMs, 100, 30000),
            maxRetries: clampInt(cfg.maxRetries, defaultConfig.maxRetries, 0, 5),
            maxResponseChars: clampInt(cfg.maxResponseChars, defaultConfig.maxResponseChars, 10000, 5000000),
            includeTrackers: clampBool(cfg.includeTrackers, defaultConfig.includeTrackers),
            logToConsole: clampBool(cfg.logToConsole, defaultConfig.logToConsole),
            hiddenObserver: clampBool(cfg.hiddenObserver, defaultConfig.hiddenObserver),
            ignoreBlockedResources: clampBool(cfg.ignoreBlockedResources, defaultConfig.ignoreBlockedResources),
            retryFailedRequests: clampBool(cfg.retryFailedRequests, defaultConfig.retryFailedRequests),
            verbose: clampBool(cfg.verbose, defaultConfig.verbose),
            detectBlockedByClient: clampBool(cfg.detectBlockedByClient, defaultConfig.detectBlockedByClient),
            usePerformanceAPI: clampBool(cfg.usePerformanceAPI, defaultConfig.usePerformanceAPI),
            requireInScope: clampBool(cfg.requireInScope, defaultConfig.requireInScope),
            maskSensitiveOutput: clampBool(cfg.maskSensitiveOutput, defaultConfig.maskSensitiveOutput),
            corsMode: normalizeCorsMode(cfg.corsMode, defaultConfig.corsMode),
            inScopeHosts: normalizeScopeHosts(cfg.inScopeHosts)
        };

        if (normalized.requireInScope && normalized.inScopeHosts.length === 0) {
            normalized.requireInScope = false;
        }

        return normalized;
    }

    function safePreview(value, maxLen) {
        let text = '';
        try {
            if (value == null) {
                text = String(value);
            } else if (typeof value === 'string') {
                text = value;
            } else if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint') {
                text = String(value);
            } else if (typeof value === 'function') {
                text = '[function]';
            } else if (Array.isArray(value)) {
                const sampleTypes = value.slice(0, 5).map(item => typeof item).join(',');
                text = `[array len=${value.length} sampleTypes=${sampleTypes || 'empty'}]`;
            } else if (typeof value === 'object') {
                const keys = Object.keys(value);
                const sampleKeys = keys.slice(0, 8).join(',');
                text = `{object keys=${sampleKeys || 'none'}${keys.length > 8 ? ',...' : ''}}`;
            } else {
                text = String(value);
            }
        } catch (_err) {
            text = `[${typeof value} - nao serializavel]`;
        }
        return text.length > maxLen ? `${text.slice(0, maxLen - 3)}...` : text;
    }

    function safeGlobalValuePreview(key, value, category) {
        const sensitiveCategories = new Set(['credentials', 'privateKeys', 'oauth', 'apiKeys', 'database', 'paymentServices']);
        const preview = safePreview(value, 160);
        const shouldMask = state.config.maskSensitiveOutput && (sensitiveCategories.has(category) || isSensitiveText(key) || isSensitiveText(preview));
        if (shouldMask) return redactValue(preview);
        return preview;
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

    function isUrlInScope(urlValue, config) {
        if (!config.requireInScope) return true;
        const parsed = parseUrlSafe(urlValue, window.location ? window.location.href : undefined);
        if (!parsed || !parsed.hostname) return false;
        const host = normalizeHost(parsed.hostname);
        return (config.inScopeHosts || []).some(scopeHost => host === scopeHost || host.endsWith(`.${scopeHost}`));
    }

    function stableDigest(input) {
        const text = String(input || '');
        let hash = 5381;
        for (let i = 0; i < text.length; i++) {
            hash = ((hash << 5) + hash + text.charCodeAt(i)) >>> 0;
        }
        return hash.toString(16).padStart(8, '0');
    }

    function redactValue(value) {
        const text = String(value == null ? '' : value);
        return `[REDACTED len=${text.length} digest=${stableDigest(text)}]`;
    }

    function isSensitiveText(text) {
        const source = String(text || '').toLowerCase();
        if (!source) return false;
        return ['token', 'secret', 'password', 'passwd', 'auth', 'session', 'csrf', 'private_key', 'apikey', 'api_key', 'bearer', 'jwt']
            .some(word => source.includes(word));
    }

    function maskIfSensitive(value, contextHint, enabled) {
        if (!enabled) return String(value == null ? '' : value);
        const raw = String(value == null ? '' : value);
        if (!raw) return raw;
        if (!isSensitiveText(`${contextHint || ''} ${raw}`)) return raw;
        return redactValue(raw);
    }

    function sortedStrings(values) {
        return Array.from(values || []).sort((a, b) => String(a).localeCompare(String(b)));
    }

    function sortErrorItems(items) {
        return Array.from(items || []).sort((a, b) => {
            const ak = `${a.url || ''}|${a.reason || ''}|${a.duration || ''}|${a.details || ''}`;
            const bk = `${b.url || ''}|${b.reason || ''}|${b.duration || ''}|${b.details || ''}`;
            return ak.localeCompare(bk);
        });
    }

    function logDebug() {
        const fn = (typeof console !== 'undefined' && typeof console.debug === 'function')
            ? console.debug
            : (typeof console !== 'undefined' && typeof console.log === 'function' ? console.log : null);
        if (!fn) return;
        fn.apply(console, arguments);
    }

    function logInfo() {
        const fn = (typeof console !== 'undefined' && typeof console.info === 'function')
            ? console.info
            : (typeof console !== 'undefined' && typeof console.log === 'function' ? console.log : null);
        if (!fn) return;
        fn.apply(console, arguments);
    }

    function isBlockedByClient(url) {
        const blockedPatterns = ['analytics', 'gtag', 'tracking', 'ads', 'doubleclick', 'clarity', 'stats-collector', 'adsbygoogle'];
        return blockedPatterns.some(p => url.toLowerCase().includes(p));
    }

    async function fetchWithTimeout(url, timeoutMs, retries = 0, config = {}) {
        const controller = new AbortController();
        const startTime = nowMs();
        let timer = null;
        const blockedByClientHint = config.detectBlockedByClient && isBlockedByClient(url);
        
        try {
            if (config.verbose) logDebug(`[FETCH-INIT] ${url.substring(0, 60)}... timeout=${timeoutMs}ms retry=${retries}`);

            // Usar timeout com Promise.race para evitar travamentos
            timer = setTimeout(() => {
                if (config.verbose) logDebug(`[FETCH-TIMEOUT] Aborting ${url.substring(0, 60)}...`);
                controller.abort();
            }, timeoutMs);
            
            if (config.verbose) logDebug(`[FETCH-CALLING] fetch() para ${url.substring(0, 60)}...`);
            const response = await fetch(url, { 
                credentials: 'omit', 
                signal: controller.signal,
                mode: config.corsMode || 'cors',
                redirect: 'follow'
            });
            
            clearTimeout(timer);
            const duration = nowMs() - startTime;
            
            if (config.verbose) {
                logDebug(`[FETCH-OK] ${url.substring(0, 60)}... status=${response.status} duration=${duration.toFixed(0)}ms`);
            }
            
            return response;
        } catch (err) {
            if (timer) clearTimeout(timer);
            const duration = nowMs() - startTime;
            const errObj = (err && typeof err === 'object') ? err : {};
            const errName = String(errObj.name || '');
            const errMessage = String(errObj.message || '');
            const blockedByClient = Boolean(
                config.detectBlockedByClient &&
                (
                    /ERR_BLOCKED_BY_CLIENT/i.test(errMessage) ||
                    (blockedByClientHint && errName === 'TypeError' && errMessage.includes('Failed to fetch'))
                )
            );
            const isCorsError = !blockedByClient && (errMessage.includes('CORS') || errMessage.includes('Failed to fetch'));
            const isNetworkError = errName === 'AbortError' || /network/i.test(errMessage) || duration >= timeoutMs;
            
            if (config.verbose) {
                logDebug(`[FETCH-FAIL] ${url.substring(0, 60)}... err=${errName}/${errMessage} dur=${duration.toFixed(0)}ms cors=${isCorsError} netErr=${isNetworkError} blocked=${blockedByClient}`);
            }
            
            if (config.retryFailedRequests && retries < (config.maxRetries || 3) && !isCorsError && !blockedByClient) {
                const delay = 300 * Math.pow(2, retries);
                await new Promise(resolve => setTimeout(resolve, delay));
                return fetchWithTimeout(url, timeoutMs, retries + 1, config);
            }
            throw {
                ...errObj,
                name: errName || 'Error',
                message: errMessage || 'Unknown error',
                corsError: isCorsError,
                networkError: isNetworkError,
                blockedByClient,
                url,
                duration
            };
        }
    }

    function collectScriptCandidates(config) {
        const candidates = [];
        const seen = new Set();
        const stats = {
            rawTotal: 0,
            skippedDuplicates: 0,
            skippedNonFetchable: 0,
            skippedTrackers: 0,
            skippedInvalid: 0,
            skippedOutOfScope: 0,
            skippedByLimit: 0,
            fromDOM: 0,
            fromPerformance: 0
        };

        function tryAdd(rawUrl, source = 'unknown') {
            const parsed = parseUrlSafe(rawUrl, window.location ? window.location.href : undefined);
            if (!parsed) { stats.skippedInvalid++; return; }
            if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') { stats.skippedNonFetchable++; return; }
            const normalized = parsed.href;
            if (!isUrlInScope(normalized, config)) { stats.skippedOutOfScope++; return; }
            if (seen.has(normalized)) { stats.skippedDuplicates++; return; }
            if (!config.includeTrackers && isTrackerHost(parsed.hostname)) { stats.skippedTrackers++; return; }
            seen.add(normalized);
            candidates.push(normalized);
            if (source === 'dom') stats.fromDOM++;
            if (source === 'perf') stats.fromPerformance++;
        }

        const scriptNodes = Array.from(document.querySelectorAll('script[src]'));
        stats.rawTotal = scriptNodes.length;
        scriptNodes.forEach(node => tryAdd(node.src, 'dom'));

        if (config.usePerformanceAPI && window.performance && typeof window.performance.getEntriesByType === 'function') {
            (window.performance.getEntriesByType('resource') || [])
                .filter(entry => entry && entry.initiatorType === 'script' && entry.name)
                .forEach(entry => tryAdd(entry.name, 'perf'));
        }

        if (candidates.length > config.maxScriptsToScan) {
            stats.skippedByLimit = candidates.length - config.maxScriptsToScan;
            candidates.length = config.maxScriptsToScan;
        }

        return { candidates, stats };
    }

    async function scanScripts(config) {
        const { candidates, stats } = collectScriptCandidates(config);
        if (config.verbose) {
            console.log(`[SCAN-SCRIPTS] Found ${stats.rawTotal} total. DOM: ${stats.fromDOM}, Perf: ${stats.fromPerformance}. After filtering: ${candidates.length} candidates`);
        }

        function isValidIp(ipStr) {
            const parts = String(ipStr || '').split('.');
            if (parts.length !== 4) return false;
            return parts.every(p => {
                const n = parseInt(p, 10);
                return !isNaN(n) && n >= 0 && n <= 255;
            });
        }

        const out = {
            urls: new Set(),
            apis: new Set(),
            secrets: new Map(),
            emails: new Set(),
            ips: new Set(),
            domains: new Set(),
            scriptErrors: [],
            corsErrors: [],
            scripts: {
                rawTotal: stats.rawTotal,
                total: candidates.length,
                success: 0,
                failed: 0,
                corsBlocked: 0,
                blockedByClient: 0,
                timeout: 0,
                skipped: stats.skippedDuplicates + stats.skippedNonFetchable + stats.skippedTrackers + stats.skippedInvalid + stats.skippedOutOfScope + stats.skippedByLimit,
                skippedDuplicates: stats.skippedDuplicates,
                skippedNonFetchable: stats.skippedNonFetchable,
                skippedTrackers: stats.skippedTrackers,
                skippedInvalid: stats.skippedInvalid,
                skippedOutOfScope: stats.skippedOutOfScope,
                skippedByLimit: stats.skippedByLimit,
                fromDOM: stats.fromDOM,
                fromPerformance: stats.fromPerformance
            }
        };

        const rx = {
            urls: /https?:\/\/[a-zA-Z0-9._~:/?#@!$&'()*+,;=%-]+/gi,
            apis: /\/api\/(?:v\d+\/)?[a-zA-Z0-9_\/-{}:]+/gi,
            secrets: /(?:api[_-]?key|api[_-]?secret|aws[_-]?secret|client[_-]?secret|access[_-]?token|bearer|password|private[_-]?key)\s*[:=]\s*["']?([A-Za-z0-9._~\-\/=+]{16,})["']?/gi,
            emails: /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/gi,
            ips: /\b(?:\d{1,3}\.){3}\d{1,3}\b/g
        };

        let cursor = 0;
        async function worker() {
            while (true) {
                const idx = cursor++;
                if (idx >= candidates.length) {
                    if (config.verbose && idx === 0) console.log(`[WORKER] Nenhum candidato encontrado para processar (candidates.length=${candidates.length})`);
                    return;
                }
                const url = candidates[idx];
                if (config.verbose) console.log(`[WORKER-${idx}] Iniciando fetch: ${url.substring(0, 80)}...`);
                
                const workerStartTime = nowMs();
                try {
                    if (config.verbose) logDebug(`[WORKER-${idx}] START fetchWithTimeout`);
                    const response = await fetchWithTimeout(url, config.scriptTimeoutMs, 0, config);
                    if (config.verbose) logDebug(`[WORKER-${idx}] GOT response status=${response.status} ok=${response.ok}`);
                    
                    if (!response.ok && response.status !== 0) {
                        if (config.verbose) logDebug(`[WORKER-${idx}] HTTP error: ${response.status}`);
                        throw new Error(`HTTP ${response.status}`);
                    }
                    
                    let text = '';
                    try {
                        if (config.verbose) logDebug(`[WORKER-${idx}] START response.text()`);
                        text = await response.text();
                        if (text.length > config.maxResponseChars) text = text.slice(0, config.maxResponseChars);
                        if (config.verbose) logDebug(`[WORKER-${idx}] GOT text length=${text ? text.length : 0}`);
                    } catch (e) {
                        if (config.verbose) logDebug(`[WORKER-${idx}] response.text() FAILED: ${e.message}`);
                        text = '';
                    }

                    if (!text || text.length === 0) {
                        if (config.verbose) logDebug(`[WORKER-${idx}] Empty response - corsBlocked++`);
                        if (config.ignoreBlockedResources) {
                            out.scripts.corsBlocked++;
                            out.scripts.success++;
                            continue;
                        }
                    }

                    if (config.verbose) logDebug(`[WORKER-${idx}] Processing ${text.length} bytes`);
                    const urlMatches = (text.match(rx.urls) || []).filter(item => {
                        const parsed = parseUrlSafe(item);
                        return parsed && (config.includeTrackers || !isTrackerHost(parsed.hostname)) && isLikelyDomain(parsed.hostname);
                    });
                    addSetValues(out.urls, urlMatches);
                    addSetValues(out.apis, text.match(rx.apis));
                    addSetValues(out.emails, text.match(rx.emails));
                    addSetValues(out.ips, (text.match(rx.ips) || []).filter(isValidIp));

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
                        const safeValue = maskIfSensitive(value, key, config.maskSensitiveOutput);
                        const formatted = `${key.toLowerCase()}="${safeValue}"`;
                        out.secrets.set(formatted, (out.secrets.get(formatted) || 0) + 1);
                    }

                    const workerDuration = nowMs() - workerStartTime;
                    out.scripts.success++;
                    if (config.verbose) logDebug(`[WORKER-${idx}] SUCCESS (${workerDuration.toFixed(0)}ms)`);
                } catch (err) {
                    const workerDuration = nowMs() - workerStartTime;
                    out.scripts.failed++;
                    let reason = 'Network Error';
                    if (err.name === 'AbortError') reason = 'Timeout';
                    else if (err.blockedByClient) reason = 'Blocked by Ad-blocker/Extension';
                    else if (err.corsError) reason = 'CORS Error';
                    
                    const errorInfo = {
                        url,
                        reason: reason,
                        details: err.message || 'Unknown error',
                        duration: err.duration ? `${err.duration.toFixed(0)}ms` : `${workerDuration.toFixed(0)}ms`
                    };
                    
                    if (err.blockedByClient) {
                        out.scripts.blockedByClient++;
                    } else if (err.corsError) {
                        out.scripts.corsBlocked++;
                        out.corsErrors.push(errorInfo);
                    } else if (err.name === 'AbortError') {
                        out.scripts.timeout++;
                    }
                    
                    out.scriptErrors.push(errorInfo);
                    if (config.verbose) logInfo(`[${reason}] ${url.substring(0, 80)}... duration=${workerDuration.toFixed(0)}ms`);
                }
            }
        }

        const workers = Math.min(config.scriptConcurrency, Math.max(1, candidates.length));
        if (config.verbose) console.log(`[SCANSCRIPTS-WORKERS] Criando ${workers} workers para ${candidates.length} candidatos`);
        await Promise.all(Array.from({ length: workers }, () => worker()));
        if (config.verbose) console.log(`[SCANSCRIPTS-DONE] Processamento de scripts concluido. Success: ${out.scripts.success}, Failed: ${out.scripts.failed}`);

        const sortedSecrets = Array.from(out.secrets.entries()).sort((a, b) => a[0].localeCompare(b[0]));
        return {
            ...out,
            urls: sortedStrings(out.urls),
            apis: sortedStrings(out.apis),
            emails: sortedStrings(out.emails),
            ips: sortedStrings(out.ips),
            domains: sortedStrings(out.domains),
            scriptErrors: sortErrorItems(out.scriptErrors),
            corsErrors: sortErrorItems(out.corsErrors),
            secrets: Object.fromEntries(sortedSecrets)
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

            out[category].push({ key, type: typeof value, value: safeGlobalValuePreview(key, value, category) });
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
        const selector = [
            'input[type="hidden"]',
            'input[type="password"]',
            '[hidden]',
            '[aria-hidden="true"]',
            '[data-hidden]',
            '.hidden',
            '[style*="display:none"]',
            '[style*="display: none"]',
            '[style*="visibility:hidden"]',
            '[style*="visibility: hidden"]',
            '[style*="opacity:0"]',
            '[style*="opacity: 0"]'
        ].join(',');
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
                Valor: maskIfSensitive(value, `${el.name || ''} ${el.id || ''}`, state.config.maskSensitiveOutput),
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
            else if (item.category === 'apis') {
                const apiPath = String(item.key || '').toLowerCase();
                const highSignalApi = ['auth', 'oauth', 'payment', 'withdraw', 'admin', 'identity', 'token'].some(token => apiPath.includes(token));
                if (highSignalApi) out.high.push(item);
                else out.medium.push(item);
            }
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

    function analyzeFindings(flat, report) {
        const analysis = {
            totalFindings: flat.globals.length + flat.scripts.length + flat.hidden.length,
            byCategory: {},
            byModule: { globals: 0, scripts: 0, hidden: 0 },
            topFinding: { category: '', count: 0 },
            suspicious: [],
            summary: ''
        };

        flat.globals.forEach(item => {
            analysis.byCategory[item.category] = (analysis.byCategory[item.category] || 0) + 1;
            analysis.byModule.globals++;
        });

        flat.scripts.forEach(item => {
            analysis.byCategory[item.category] = (analysis.byCategory[item.category] || 0) + 1;
            analysis.byModule.scripts++;
        });

        flat.hidden.forEach(item => {
            analysis.byCategory[item.category] = (analysis.byCategory[item.category] || 0) + 1;
            analysis.byModule.hidden++;
        });

        Object.keys(analysis.byCategory).forEach(cat => {
            if (analysis.byCategory[cat] > analysis.topFinding.count) {
                analysis.topFinding.category = cat;
                analysis.topFinding.count = analysis.byCategory[cat];
            }
        });

        const severity = report.severity || {};
        analysis.suspicious = [
            { level: 'CRITICO', count: (severity.critical || []).length },
            { level: 'ALTO', count: (severity.high || []).length },
            { level: 'MEDIO', count: (severity.medium || []).length },
            { level: 'BAIXO', count: (severity.low || []).length }
        ];

        const criticalCount = (severity.critical || []).length;
        const highCount = (severity.high || []).length;
        if (criticalCount > 0) analysis.summary += `ALERTA: ${criticalCount} achado(s) critico(s) detectado(s). `;
        if (highCount > 0) analysis.summary += `${highCount} achado(s) de alto risco. `;
        analysis.summary += `Total: ${analysis.totalFindings} achados em ${Object.keys(analysis.byCategory).length} categoria(s).`;

        return analysis;
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
        if (typeof setTimeout === 'function') setTimeout(() => URL.revokeObjectURL(url), 150);
        else URL.revokeObjectURL(url);
    }

    function printReport(report) {
        if (!state.config.logToConsole) return;
        const max = state.config.maxConsoleItemsPerSection;
        const analysis = analyzeFindings(state.flat, report);

        console.log('\n');
        console.log('%c===============================================================%c', 'color: cyan;', '');
        console.log('%c[+] BUG BOUNTY MASTER REPORT v' + report.version + '%c', 'color: cyan; font-weight: bold;', '');
        console.log('%c===============================================================%c', 'color: cyan;', '');

        // Severidade
        const severity = report.severity || {};
        if ((severity.critical || []).length > 0) {
            console.group('%c[!] CRITICO - ' + severity.critical.length + ' achado(s)%c', 'color: red; font-weight: bold;', '');
            severity.critical.slice(0, max).forEach(item => console.log(item));
            if (severity.critical.length > max) console.log(`... e ${severity.critical.length - max} mais`);
            console.groupEnd();
        }

        if ((severity.high || []).length > 0) {
            console.group('%c[!] ALTO RISCO - ' + severity.high.length + ' achado(s)%c', 'color: orange; font-weight: bold;', '');
            severity.high.slice(0, 5).forEach(item => console.log(item));
            if (severity.high.length > 5) console.log(`... e ${severity.high.length - 5} mais`);
            console.groupEnd();
        }

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
        console.log('%c[+] ANALISE DE FINDINGS:%c', 'color: cyan; font-weight: bold;', '');
        analysis.suspicious.forEach(s => console.log(`   ${s.level}: ${s.count}`));
        console.log(`   ${analysis.summary}`);
        console.log('');
        console.log('%c[+] SUMMARY:%c', 'color: cyan; font-weight: bold;', '');
        console.log(`   Globals suspeitos: ${report.summary.globalsFindings}`);
        console.log(`   Scripts processados: ${report.summary.scriptsSuccess}/${report.summary.scriptsTotal}`);
        console.log(`   Scripts com erro: ${report.summary.scriptsFailed}`);
        console.log(`   Scripts bloqueados por CORS: ${report.summary.corsBlocked || 0}`);
        console.log(`   Scripts bloqueados por Ad-blocker: ${report.summary.blockedByClient || 0}`);
        console.log(`   Scripts com timeout: ${report.summary.timeout || 0}`);
        console.log(`   Scripts pulados: ${report.summary.scriptsSkipped}`);
        console.log(`   Scripts fora de escopo pulados: ${report.summary.scriptsSkippedOutOfScope || 0}`);
        console.log(`   Scripts pulados por limite (maxScriptsToScan): ${report.summary.scriptsSkippedByLimit || 0}`);
        console.log(`   Hidden fields: ${report.summary.hiddenFindings}`);
        console.log(`   Hidden ruido filtrado: ${report.summary.hiddenSkippedNoise || 0}`);
        console.log(`   Total consolidado: ${report.summary.totalFindings}`);
        console.log(`   Scripts encontrados (DOM): ${report.scripts.scripts.fromDOM || 0}`);
        console.log(`   Scripts encontrados (Performance API): ${report.scripts.scripts.fromPerformance || 0}`);
        console.log('%c===============================================================%c', 'color: cyan;', '');
    }

    function ensureLast() {
        if (!state.last) throw new Error('Nenhuma analise executada ainda. Use bugBountyMaster.run()');
    }

    function startObserver() {
        if (state.observer) return true;
        if (typeof MutationObserver !== 'function') return false;

        let debounceActive = false;
        state.observer = new MutationObserver(() => {
            if (debounceActive) return;
            debounceActive = true;
            if (state.observerTimer) clearTimeout(state.observerTimer);
            state.observerTimer = setTimeout(() => {
                try {
                    if (!state.last) return;
                    state.last.hidden = scanHiddenElements();
                    state.flat = flatten(state.last);
                    state.last.severity = bySeverity(state.last, state.flat);
                    state.last.summary.hiddenFindings = state.last.hidden.rows.length;
                    state.last.summary.totalFindings = state.last.summary.globalsFindings + state.last.summary.scriptsFindings + state.last.summary.hiddenFindings;
                } finally {
                    debounceActive = false;
                }
            }, state.config.hiddenObserverDebounceMs);
        });

        try {
            state.observer.observe(document.documentElement || document.body, {
                childList: true,
                subtree: true,
                attributes: true,
                attributeFilter: ['style', 'class', 'hidden', 'aria-hidden']
            });
        } catch (_err) {
            if (state.observer) {
                state.observer.disconnect();
                state.observer = null;
            }
            return false;
        }
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
        const config = normalizeConfig({ ...state.config, ...(overrides || {}) });
        const [globals, scripts, hidden] = await Promise.all([scanGlobals(), scanScripts(config), scanHiddenElements()]);

        const report = {
            version: VERSION,
            generatedAt: new Date().toISOString(),
            config,
            globals,
            scripts,
            hidden,
            scriptErrors: scripts.scriptErrors || [],
            corsErrors: scripts.corsErrors || [],
            summary: {
                globalsFindings: globals.total,
                scriptsFindings: Object.keys(scripts.secrets).length + scripts.apis.length + scripts.urls.length + scripts.emails.length + scripts.ips.length + scripts.domains.length,
                hiddenFindings: hidden.rows.length,
                scriptsTotal: scripts.scripts.total,
                scriptsSuccess: scripts.scripts.success,
                scriptsFailed: scripts.scripts.failed,
                scriptsSkipped: scripts.scripts.skipped,
                scriptsSkippedOutOfScope: scripts.scripts.skippedOutOfScope || 0,
                scriptsSkippedByLimit: scripts.scripts.skippedByLimit || 0,
                corsBlocked: scripts.scripts.corsBlocked || 0,
                timeout: scripts.scripts.timeout || 0,
                hiddenSkippedNoise: hidden.skippedNoise || 0,
                totalFindings: 0
            }
        };

        report.summary.totalFindings = report.summary.globalsFindings + report.summary.scriptsFindings + report.summary.hiddenFindings;
        report.summary.corsBlocked = scripts.scripts.corsBlocked || 0;
        report.summary.blockedByClient = scripts.scripts.blockedByClient || 0;
        report.summary.timeout = scripts.scripts.timeout || 0;
        
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
            const analysis = analyzeFindings(state.flat, state.last);
            const payload = {
                version: state.last.version,
                generatedAt: state.last.generatedAt,
                config: state.last.config,
                summary: state.last.summary,
                analysis: analysis,
                globals: state.last.globals,
                scripts: state.last.scripts,
                hidden: state.last.hidden,
                severity: state.last.severity,
                scriptErrors: state.last.scriptErrors || state.last.scripts.scriptErrors || [],
                corsErrors: state.last.corsErrors || []
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

        analyze: () => {
            ensureLast();
            return analyzeFindings(state.flat, state.last);
        },

        getCorsErrors: () => {
            ensureLast();
            return state.last.corsErrors || [];
        },

        getStatistics: () => {
            ensureLast();
            const analysis = analyzeFindings(state.flat, state.last);
            return {
                timestamp: state.last.generatedAt,
                totalFindings: analysis.totalFindings,
                bySeverity: analysis.suspicious,
                byModule: analysis.byModule,
                byCategory: analysis.byCategory,
                corsBlockedCount: state.last.summary.corsBlocked,
                blockedByClientCount: state.last.summary.blockedByClient,
                timeoutCount: state.last.summary.timeout,
                summary: analysis.summary
            };
        },

        getDetailedErrors: () => {
            ensureLast();
            const scriptErrors = state.last.scriptErrors || state.last.scripts.scriptErrors || [];
            return {
                scriptErrors: scriptErrors,
                corsErrors: state.last.corsErrors || [],
                totalErrors: scriptErrors.length
            };
        },

        getScriptCandidates: () => {
            ensureLast();
            const { candidates, stats } = collectScriptCandidates(state.config);
            return {
                candidatesFound: candidates.length,
                stats: stats,
                candidates: candidates
            };
        },

        startObserver: () => startObserver(),
        stopObserver: () => { stopObserver(); return true; },
        config: () => ({ ...state.config }),
        setConfig: (cfg = {}) => {
            state.config = normalizeConfig({ ...state.config, ...(cfg || {}) });
            return { ...state.config };
        }
    };

    window.bugBountyMaster = api;
    api.ready = api.run();

    if (state.config.logToConsole) {
        console.log('%c[i] bugBountyMaster v' + VERSION + ' inicializado%c', 'color: blue; font-weight: bold;', '');
        console.log("   Metodos: .ready | .run() | .getAll() | .export('json'|'csv') | .download() | .filter() | .bySeverity()");
        console.log("   Analise: .analyze() | .getStatistics() | .getCorsErrors() | .getDetailedErrors() | .getScriptCandidates()");
        console.log("   Configuracao: .config() | .setConfig({ignoreBlockedResources: true, verbose: true, retryFailedRequests: true, scriptTimeoutMs: 12000})");
    }
})();
