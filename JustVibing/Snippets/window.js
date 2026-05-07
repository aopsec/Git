// Dumper otimizado de variaveis globais com categorizacao de segredos (modo high precision)
(function() {
    console.clear();

    const PREVIEW_MAX_LEN = 160;
    const IGNORED_PREFIXES = ['webkit', 'moz', '__', 'chrome', 'safari'];
    const IGNORED_EXACT_KEYS = new Set([
        'window',
        'self',
        'frames',
        'parent',
        'top',
        'document',
        'location',
        'history',
        'navigator',
        'navigation',
        'credentialless',
        'indexeddb',
        'performance',
        'screen',
        'caches',
        'localstorage',
        'sessionstorage',
        'cookiestore',
        'visualviewport',
        'origin',
        'name',
        'length',
        'undefined',
        'globalthis',
        'trustedtypes',
        'crypto',
        'crossoriginisolated',
        'issecurecontext'
    ]);

    const CATEGORY_ORDER = [
        'privateKeys',
        'paymentServices',
        'cloudServices',
        'oauth',
        'apiKeys',
        'database',
        'analytics',
        'crypto',
        'credentials'
    ];

    const results = {
        credentials: [],
        apiKeys: [],
        cloudServices: [],
        paymentServices: [],
        oauth: [],
        database: [],
        privateKeys: [],
        analytics: [],
        crypto: [],
        other: [],
        total: 0
    };

    function truncateText(value, maxLen) {
        const text = String(value);
        if (text.length <= maxLen) {
            return text;
        }
        return text.slice(0, maxLen - 3) + '...';
    }

    function buildPreview(value, valueType) {
        try {
            if (valueType === 'string') {
                return truncateText(value, PREVIEW_MAX_LEN);
            }

            if (valueType === 'number' || valueType === 'boolean' || valueType === 'bigint') {
                return truncateText(String(value), PREVIEW_MAX_LEN);
            }

            if (valueType === 'object') {
                const serialized = JSON.stringify(value);
                if (serialized) {
                    return truncateText(serialized, PREVIEW_MAX_LEN);
                }
            }

            return truncateText(String(value), PREVIEW_MAX_LEN);
        } catch (err) {
            return truncateText(`[${valueType} - nao serializavel]`, PREVIEW_MAX_LEN);
        }
    }

    function tokenizeKey(key) {
        return key
            .replace(/([a-z0-9])([A-Z])/g, '$1_$2')
            .replace(/[^a-zA-Z0-9]+/g, '_')
            .split('_')
            .map(token => token.trim().toLowerCase())
            .filter(Boolean);
    }

    function hasAny(tokenSet, candidates) {
        return candidates.some(token => tokenSet.has(token));
    }

    const categoryMatchers = {
        privateKeys: (keyLower, tokenSet) => {
            return (
                keyLower.includes('privatekey') ||
                keyLower.includes('private_key') ||
                hasAny(tokenSet, ['private', 'pem', 'rsa', 'certificate', 'cert', 'tls', 'keystore', 'x509'])
            );
        },

        paymentServices: (_keyLower, tokenSet) => {
            return hasAny(tokenSet, [
                'stripe',
                'paypal',
                'braintree',
                'square',
                'checkout',
                'adyen',
                'payment',
                'pagseguro',
                'mercadopago'
            ]);
        },

        cloudServices: (_keyLower, tokenSet) => {
            return hasAny(tokenSet, [
                'aws',
                'azure',
                'gcp',
                'firebase',
                'supabase',
                'vercel',
                'cloudflare',
                'digitalocean',
                'heroku',
                'netlify'
            ]);
        },

        oauth: (_keyLower, tokenSet) => {
            return (
                hasAny(tokenSet, ['oauth', 'jwt', 'bearer']) ||
                (tokenSet.has('refresh') && tokenSet.has('token')) ||
                (tokenSet.has('access') && tokenSet.has('token')) ||
                (tokenSet.has('client') && tokenSet.has('secret'))
            );
        },

        apiKeys: (keyLower, tokenSet) => {
            return (
                keyLower.includes('apikey') ||
                keyLower.includes('api_key') ||
                keyLower.includes('api-secret') ||
                ((tokenSet.has('api') || keyLower.includes('api')) && hasAny(tokenSet, ['key', 'secret', 'token', 'client'])) ||
                (tokenSet.has('access') && tokenSet.has('key'))
            );
        },

        database: (_keyLower, tokenSet) => {
            return (
                hasAny(tokenSet, ['database', 'postgres', 'postgresql', 'mongodb', 'mongo', 'redis', 'mysql', 'mariadb', 'sqlite', 'sql', 'dsn']) ||
                (tokenSet.has('connection') && hasAny(tokenSet, ['string', 'uri', 'host'])) ||
                (tokenSet.has('db') && hasAny(tokenSet, ['connection', 'conn', 'uri', 'host', 'name']))
            );
        },

        analytics: (_keyLower, tokenSet) => {
            return hasAny(tokenSet, ['analytics', 'tracking', 'segment', 'mixpanel', 'amplitude', 'matomo', 'snowplow', 'heap']);
        },

        crypto: (_keyLower, tokenSet) => {
            return hasAny(tokenSet, ['encrypt', 'encryption', 'decrypt', 'decryption', 'cipher', 'hash', 'hmac', 'nonce', 'salt', 'iv', 'signature']);
        },

        credentials: (_keyLower, tokenSet) => {
            return (
                hasAny(tokenSet, ['password', 'passwd', 'pwd', 'secret', 'credential', 'credentials']) ||
                (hasAny(tokenSet, ['auth', 'session']) && hasAny(tokenSet, ['token', 'secret'])) ||
                (tokenSet.has('token') && hasAny(tokenSet, ['csrf', 'session', 'auth', 'id']))
            );
        }
    };

    function detectCategory(keyLower, tokenSet) {
        for (const category of CATEGORY_ORDER) {
            if (categoryMatchers[category](keyLower, tokenSet)) {
                return category;
            }
        }
        return null;
    }

    console.log('%c[+] Iniciando analise de variaveis globais (high precision)...%c', 'color: darkblue; font-weight: bold;', '');
    console.log('');

    let analyzed = 0;
    let skipped = 0;

    const keys = Object.getOwnPropertyNames(window);

    for (const key of keys) {
        const keyLower = key.toLowerCase();

        if (IGNORED_EXACT_KEYS.has(keyLower) || IGNORED_PREFIXES.some(prefix => keyLower.startsWith(prefix))) {
            skipped++;
            continue;
        }

        let value;
        try {
            value = window[key];
        } catch (err) {
            skipped++;
            continue;
        }

        const typeOf = typeof value;

        if (typeOf === 'function' || value === null || value === undefined) {
            skipped++;
            continue;
        }

        analyzed++;

        const tokenSet = new Set(tokenizeKey(key));
        const category = detectCategory(keyLower, tokenSet);

        if (!category) {
            continue;
        }

        const preview = buildPreview(value, typeOf);
        results[category].push({ key, value: preview, type: typeOf });
        results.total++;
    }

    function printCategory(category, title, style, useWarn) {
        if (results[category].length === 0) {
            return;
        }

        console.group(`%c${title} (${results[category].length})%c`, style, '');
        results[category].forEach(item => {
            const logger = useWarn ? console.warn : console.log;
            logger(`${item.key} (${item.type})`, item.value);
        });
        console.groupEnd();
    }

    console.log('%c===============================================================%c', 'color: cyan;', '');
    console.log('%c[+] RELATORIO DE VARIAVEIS GLOBAIS%c', 'color: cyan; font-weight: bold;', '');
    console.log('%c===============================================================%c', 'color: cyan;', '');
    console.log('');

    printCategory('credentials', '[!] CREDENCIAIS', 'color: red; font-weight: bold;', true);
    printCategory('privateKeys', '[!] CHAVES PRIVADAS', 'color: darkred; font-weight: bold;', true);
    printCategory('apiKeys', '[!] CHAVES DE API', 'color: orange; font-weight: bold;', true);
    printCategory('cloudServices', '[i] SERVICOS NA NUVEM', 'color: purple; font-weight: bold;', false);
    printCategory('paymentServices', '[i] SERVICOS DE PAGAMENTO', 'color: green; font-weight: bold;', false);
    printCategory('oauth', '[!] OAUTH E TOKENS', 'color: blue; font-weight: bold;', true);
    printCategory('database', '[i] BANCO DE DADOS', 'color: brown; font-weight: bold;', false);
    printCategory('crypto', '[i] CRIPTOGRAFIA', 'color: teal; font-weight: bold;', false);
    printCategory('analytics', '[i] ANALYTICS', 'color: navy; font-weight: bold;', false);

    console.log('');
    console.log('%c[+] RESUMO:%c', 'color: cyan; font-weight: bold;', '');
    console.log(`   Total de chaves analisadas: ${analyzed}`);
    console.log(`   Chaves puladas (browser APIs): ${skipped}`);
    console.log(`   Itens suspeitos encontrados: ${results.total}`);
    console.log('');

    window.globalAnalysis = {
        credentials: results.credentials,
        privateKeys: results.privateKeys,
        apiKeys: results.apiKeys,
        cloudServices: results.cloudServices,
        paymentServices: results.paymentServices,
        oauth: results.oauth,
        database: results.database,
        crypto: results.crypto,
        analytics: results.analytics,

        getAll: () => results,

        export: (format = 'json') => {
            const data = {
                timestamp: new Date().toISOString(),
                scanSummary: {
                    analyzed: analyzed,
                    skipped: skipped,
                    suspicious: results.total
                },
                findings: results
            };
            return format === 'json' ? JSON.stringify(data, null, 2) : data;
        },

        download: (format = 'json') => {
            const data = window.globalAnalysis.export(format);
            const blob = new Blob([data], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `global-vars-${Date.now()}.${format}`;
            a.click();
            URL.revokeObjectURL(url);
        },

        filter: (keyword) => {
            const query = String(keyword || '').toLowerCase();
            const filtered = {};
            Object.keys(results).forEach(category => {
                if (!Array.isArray(results[category])) {
                    return;
                }

                filtered[category] = results[category].filter(item => {
                    const keyText = String(item.key || '').toLowerCase();
                    const valueText = String(item.value || '').toLowerCase();
                    return keyText.includes(query) || valueText.includes(query);
                });
            });
            return filtered;
        },

        search: (keyword) => {
            return window.globalAnalysis.filter(keyword);
        },

        bySeverity: () => {
            return {
                critical: [
                    ...results.credentials,
                    ...results.privateKeys,
                    ...results.oauth
                ],
                high: [
                    ...results.apiKeys,
                    ...results.paymentServices,
                    ...results.database
                ],
                medium: [
                    ...results.cloudServices,
                    ...results.crypto
                ],
                low: results.analytics
            };
        }
    };

    console.log('%c[i] Use window.globalAnalysis para acessar os dados:%c', 'color: blue; font-style: italic;', '');
    console.log("   .getAll() | .export() | .download() | .filter('api') | .bySeverity()");
    console.log('%c===============================================================%c', 'color: cyan;', '');
})();
