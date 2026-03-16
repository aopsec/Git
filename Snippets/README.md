# Snippets de BugBounty (High Precision)

Este pacote contem 3 snippets focados em recon client-side com reducao de falso positivo e sem quebra de API publica.

## 0) master-bugbounty.js - Snippet unico automatizado
- Executa em uma unica passada:
  - scan de scripts/client-side artifacts
  - scan de variaveis globais
  - scan de campos/elementos ocultos
- API publica:
  - `window.bugBountyMaster.ready` (Promise da primeira execucao)
  - `window.bugBountyMaster.run(overrides?)`
  - `window.bugBountyMaster.getAll()`
  - `window.bugBountyMaster.export('json'|'csv')`
  - `window.bugBountyMaster.download('json'|'csv')`
  - `window.bugBountyMaster.filter('all'|'scripts'|'globals'|'hidden', query)`
  - `window.bugBountyMaster.bySeverity()`
  - `window.bugBountyMaster.startObserver()` / `.stopObserver()`

Uso rapido no console do navegador:
```js
// cole o conteudo de master-bugbounty.js no console e depois:
await window.bugBountyMaster.ready;
window.bugBountyMaster.getAll();
window.bugBountyMaster.bySeverity();
window.bugBountyMaster.export('json');
```

## 1) window.js - Global Variable Analyzer
- Escaneia apenas chaves proprias de `window` (`Object.getOwnPropertyNames`).
- Faz tokenizacao de chaves (`camelCase`, `snake_case`, `kebab-case`) para match exato.
- Ignora globais nativas comuns (`navigator`, `navigation`, `credentialless`, `indexedDB`, etc.).
- Usa precedencia fixa de categorias:
  - `privateKeys` -> `paymentServices` -> `cloudServices` -> `oauth` -> `apiKeys` -> `database` -> `analytics` -> `crypto` -> `credentials`
- Preview de valor truncado com limite de 160 chars.

API publica mantida:
- `window.globalAnalysis.getAll()`
- `window.globalAnalysis.export('json')`
- `window.globalAnalysis.download('json')`
- `window.globalAnalysis.filter(keyword)`
- `window.globalAnalysis.bySeverity()`

## 2) finder.js - Script Analyzer
- Deduplica URLs de scripts e ignora `data:` / `blob:`.
- Processamento concorrente controlado (5 workers) com timeout de 8000ms por request.
- Segredos em modo high precision:
  - apenas atribuicoes explicitas
  - valores entre aspas
  - tamanho minimo 16
  - supressao de placeholders (`example`, `dummy`, `changeme`, `test`, etc.)
- Dominios extraidos apenas de hosts de URLs validadas, reduzindo ruido de JS minificado.
- Scripts de tracking/analytics comuns sao pulados por padrao para reduzir erro `ERR_BLOCKED_BY_CLIENT` e ruido.
- `filter('secrets', query)` corrigido para iterar o `Map` corretamente.
- Filtros case-insensitive para `secrets`, `urls`, `apis`, `emails`, `ips`, `domains`.

API publica mantida:
- `window.analysisResults.export('json')`
- `window.analysisResults.download('json')`
- `window.analysisResults.filter(type, query)`

## 3) HiddenForms.js - Hidden Form Mapper
- Seletores amplos + decisao final por motivos reais de visibilidade:
  - `input[type=hidden]`, `input[type=password]`, `hidden`, `aria-hidden=true`, `display:none`, `visibility:hidden`, `opacity:0`, etc.
- Dedupe forte por assinatura (`tag + type + name + id + value`).
- Campo `Visibilidade` agora mostra os motivos detectados.
- CSV com escape correto de aspas e quebra de linha.
- Filtro case-insensitive em identificador, valor e classes.
- Supressao de ruido para elementos injetados por extensoes/widgets (ex.: DarkReader, chat widgets).

API publica mantida:
- `window.hiddenFormData.export()`
- `window.hiddenFormData.exportCSV()`
- `window.hiddenFormData.filter(field)`
- `window.hiddenFormData.download(format)`

## Arquivos de teste
- `window-test.html`: valida categorias sensiveis e supressao de falsos positivos de globais nativas.
- `finder-test.html`: inclui exemplos de segredos validos e placeholders para validar supressao.
- `test.html`: valida motivos de visibilidade, export e filtro do hidden mapper.

## Validacao rapida
1. Abrir cada arquivo `*-test.html` no navegador.
2. Pressionar F12.
3. Executar no console:
   - `window.globalAnalysis.bySeverity()`
   - `window.analysisResults.filter('secrets', 'api')`
   - `window.hiddenFormData.filter('token')`

## Runner automatico (1 comando)
- Arquivo: `Snippets/test-runner.js`
- Executar da raiz do repo:
  - `node Snippets/test-runner.js`
- Executar dentro de `Snippets`:
  - `node test-runner.js`

O runner valida:
- parse/syntax dos snippets (`window.js`, `finder.js`, `HiddenForms.js`, `master-bugbounty.js`)
- exposicao das APIs publicas
- comportamento principal de deteccao/supressao de ruido
- wiring dos arquivos `*-test.html`
