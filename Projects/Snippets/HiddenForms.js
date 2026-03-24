// Mapeador otimizado de parametros de interface ocultos com motivos explicitos de visibilidade
(function() {
    const candidateSelector = [
        'input[type="hidden"]',
        'input[type="password"]',
        '[hidden]',
        '[aria-hidden="true"]',
        '[data-hidden]',
        '.hidden',
        '[style]'
    ].join(',');

    const candidates = document.querySelectorAll(candidateSelector);
    const seen = new Set();
    const results = [];
    let skippedNoise = 0;

    const injectedNoiseTokens = [
        'darkreader',
        'chat-widget',
        'chatwidget',
        'crisp',
        'intercom',
        'zendesk',
        'tawk',
        'livechat',
        'drift',
        'hubspot-messages',
        'chrome-extension',
        'moz-extension'
    ];

    function getElementValue(el) {
        const tag = el.tagName.toLowerCase();

        if (tag === 'input' || tag === 'textarea' || tag === 'select') {
            return String(el.value || '').trim();
        }

        const dataValue = el.getAttribute('data-value');
        if (dataValue) {
            return String(dataValue).trim();
        }

        return String(el.textContent || '').trim();
    }

    function getVisibilityReasons(el) {
        const reasons = [];
        const tag = el.tagName.toLowerCase();
        const type = String(el.getAttribute('type') || '').toLowerCase();

        if (tag === 'input' && type === 'hidden') {
            reasons.push('input[type=hidden]');
        }

        if (tag === 'input' && type === 'password') {
            reasons.push('input[type=password]');
        }

        if (el.hidden || el.hasAttribute('hidden')) {
            reasons.push('hidden');
        }

        const ariaHidden = String(el.getAttribute('aria-hidden') || '').toLowerCase();
        if (ariaHidden === 'true') {
            reasons.push('aria-hidden=true');
        }

        if (el.classList && el.classList.contains('hidden')) {
            reasons.push('class:hidden');
        }

        if (el.hasAttribute('data-hidden')) {
            reasons.push('data-hidden');
        }

        try {
            const computed = window.getComputedStyle(el);
            if (computed.display === 'none') {
                reasons.push('display:none');
            }
            if (computed.visibility === 'hidden') {
                reasons.push('visibility:hidden');
            }
            if (computed.opacity === '0') {
                reasons.push('opacity:0');
            }
        } catch (_err) {
            // Ignora falha de estilo computado para manter robustez
        }

        return Array.from(new Set(reasons));
    }

    function getDataAttrs(el) {
        const keys = Object.keys(el.dataset || {});
        if (keys.length === 0) {
            return '(Nenhum)';
        }
        return JSON.stringify(el.dataset);
    }

    function buildSignature(el, value) {
        const tag = el.tagName.toLowerCase();
        const type = String(el.getAttribute('type') || '').toLowerCase();
        const name = String(el.name || '');
        const id = String(el.id || '');
        return [tag, type, name, id, value].join('|');
    }

    function shouldSkipAsInjectedNoise(el) {
        const id = String(el.id || '').toLowerCase();
        const className = String(el.className || '').toLowerCase();
        const name = String(el.getAttribute('name') || '').toLowerCase();
        const src = String(el.getAttribute('src') || '').toLowerCase();
        const dataAttrKeys = Object.keys(el.dataset || {}).map(key => key.toLowerCase());

        const haystack = [id, className, name, src, ...dataAttrKeys].join(' ');
        if (injectedNoiseTokens.some(token => haystack.includes(token))) {
            return true;
        }

        if (src.startsWith('chrome-extension:') || src.startsWith('moz-extension:')) {
            return true;
        }

        return false;
    }

    function escapeCsvValue(value) {
        const normalized = String(value == null ? '' : value)
            .replace(/"/g, '""')
            .replace(/\r?\n/g, '\\n');
        return `"${normalized}"`;
    }

    candidates.forEach(el => {
        try {
            const reasons = getVisibilityReasons(el);
            if (reasons.length === 0) {
                return;
            }

            if (shouldSkipAsInjectedNoise(el)) {
                skippedNoise++;
                return;
            }

            const id = el.name || el.id || el.getAttribute('data-field') || '';
            const value = getElementValue(el);
            const signature = buildSignature(el, value);

            if (seen.has(signature)) {
                return;
            }

            seen.add(signature);
            results.push({
                Identificador: id || '(Sem Identificacao)',
                Valor: value,
                Tipo_Elemento: el.tagName,
                Visibilidade: reasons.join(', '),
                Classes: String(el.className || '').trim() || '(Nenhuma)',
                DataAttrs: getDataAttrs(el)
            });
        } catch (err) {
            console.warn('[!] Erro ao processar elemento:', err);
        }
    });

    if (results.length > 0) {
        console.log(`%c[+] ${results.length} parametros ocultos encontrados%c`, 'color: green; font-weight: bold;', '');
        if (skippedNoise > 0) {
            console.log(`%c[i] Elementos injetados/ruido ignorados: ${skippedNoise}%c`, 'color: gray;', '');
        }
        console.table(results);

        window.hiddenFormData = {
            export: () => JSON.stringify(results, null, 2),

            exportCSV: () => {
                if (results.length === 0) {
                    return '';
                }

                const headers = Object.keys(results[0]);
                const lines = results.map(row => headers.map(header => escapeCsvValue(row[header])).join(','));
                return [headers.join(','), ...lines].join('\n');
            },

            filter: (field) => {
                const query = String(field || '').toLowerCase();
                if (!query) {
                    return results.slice();
                }

                return results.filter(row => {
                    return [row.Identificador, row.Valor, row.Classes]
                        .map(value => String(value || '').toLowerCase())
                        .some(value => value.includes(query));
                });
            },

            download: (format = 'json') => {
                const normalizedFormat = String(format || 'json').toLowerCase();
                const data = normalizedFormat === 'csv'
                    ? window.hiddenFormData.exportCSV()
                    : window.hiddenFormData.export();

                const blob = new Blob([data], { type: 'text/plain' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `hidden-params-${Date.now()}.${normalizedFormat}`;
                a.click();
                URL.revokeObjectURL(url);
            }
        };

        console.log('%c[i] Use window.hiddenFormData para acessar: .export(), .exportCSV(), .filter(field), .download(format)%c', 'color: blue; font-style: italic;', '');
    } else {
        if (skippedNoise > 0) {
            console.log(`%c[i] Elementos injetados/ruido ignorados: ${skippedNoise}%c`, 'color: gray;', '');
        }
        console.log('%c[-] Nenhum campo oculto relevante encontrado no DOM atual.%c', 'color: orange;', '');
    }
})();
