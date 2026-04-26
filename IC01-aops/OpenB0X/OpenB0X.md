# OpenB0X

## Identificação institucional

| Campo | Informação |
|---|---|
| Instituição | UniCEUB |
| Curso | Ciência da Computação |
| Disciplina | Introdução à Computação |
| Autor | Alcides Olivo Pollazzon Soterio |
| Docente/Tutor | Fabrício Ofugi |
| Data de consolidação | 2026-04-26 |
| Fonte canônica | `OpenB0X.md` |

## Sumário executivo

O presente documento consolida o deliverable técnico do workspace `IC01-aops`. Seu objeto não
é tratar o `MXQ Pro 4K` como um caso ordinário de consumo, mas analisá-lo como artefato de risco,
combinando estudo de caso em segurança, rastreabilidade documental e evidência operacional com
base no relatório Claude importado [LOC-01] e no research do retarget `RK3229` [LOC-02].

O projeto final tem 3 pilares:

- `ADV7ia`, como camada de automação, controle e memória operacional.
- `Obsidian meta-vault`, como camada de organização, indexação e evidência.
- `ADV7Sec (IPS_IDS)`, como camada de detecção local para workstation.

`OpenBox0.1v/ADV7Box` figura apenas como antecessor histórico e metodológico: ele demonstra a
disciplina documental que tornou possível este formato consolidado [LOC-03] [LOC-04], mas não
constitui o argumento final do presente artefato.

## 1. Método e limites do conjunto probatório

Este artefato adota um critério probatório conservador. Não encontrei, em fonte governamental
brasileira, uma contagem oficial específica de consumidores do modelo `MXQ Pro 4K`.
Por isso, o documento separa a análise em três camadas complementares:

- fontes oficiais brasileiras para dimensionar o mercado de TV boxes piratas e o risco regulatório [BR-01] [BR-05] [BR-07];
- fontes técnicas externas para descrever campanhas, famílias de malware e vetores de comprometimento documentados [INT-01] [INT-02] [INT-04];
- artefatos locais do workspace para contextualizar o caso `MXQ Pro 4K` / `RK3229` sem extrapolar além da evidência disponível [LOC-01] [LOC-02].

Esse recorte evita inventar estatística por modelo onde ela não foi publicada e também evita
afirmar, sem imagem forense do aparelho, que toda unidade `RK3229` chega infectada. O que o
documento sustenta é algo mais preciso: o `MXQ Pro 4K` pertence a uma classe de dispositivos com
histórico documentado de firmware adulterado, malware de cadeia de suprimento e exposição massiva
no Brasil [BR-01] [BR-05] [BR-07] [INT-01] [LOC-02].

### 1.1 Critérios de seleção das fontes governamentais brasileiras

A seleção das fontes governamentais brasileiras foi organizada em uma subseção própria para separar
referência institucional, uso probatório e limite interpretativo. O objetivo não é produzir uma
estatística por modelo, mas construir um panorama oficial confiável para enquadrar o `MXQ Pro 4K`
como exemplar de uma classe de risco.

| Critério | Aplicação no documento | Limite metodológico |
|---|---|---|
| Origem institucional primária | Priorizar páginas e comunicados em domínios oficiais do Governo Federal, especialmente Receita Federal, Anatel e Ministério das Comunicações. | Não usar republicações, matérias sem órgão emissor claro ou resumos sem rastreabilidade. |
| Pertinência temática | Selecionar fontes que tratem diretamente de TV boxes piratas, homologação, malware, retirada de mercado, BadBox 2.0 ou IPTV clandestina. | Não transferir automaticamente dados gerais do mercado pirata para o modelo `MXQ Pro 4K`. |
| Valor probatório | Usar números oficiais para dimensionar fiscalização, exposição residencial, contaminação conhecida e base usuária. | Não inferir que uma unidade específica esteja infectada sem imagem forense, hash de firmware ou laudo técnico. |
| Rastreabilidade temporal | Preservar órgão, data e evento para sustentar a linha do tempo externa de risco. | Não misturar eventos regulatórios com evidências locais do workspace sem explicitar a camada de análise. |
| Separação de métricas | Manter apreensão, retirada de mercado, lares expostos, dispositivos infectados e usuários estimados em eixos distintos. | Evitar gráficos ou leituras que comparem categorias heterogêneas como se fossem a mesma métrica. |

Com esse método, as fontes [BR-01] a [BR-07] são tratadas como base oficial para caracterizar o
ambiente brasileiro de risco, não como prova individual contra uma unidade específica do aparelho.
A conclusão operacional permanece conservadora: o `MXQ Pro 4K` deve ser analisado como dispositivo
potencialmente comprometido até que haja wipe completo, substituição de firmware e verificação
pós-flash com evidência técnica própria.

## 2. Linha do tempo consolidada

A linha do tempo a seguir separa, de forma deliberada, os marcos internos do projeto e os eventos
externos que sustentam a leitura de risco do caso. Essa divisão evita misturar evolução do
artefato acadêmico com fatos regulatórios, policiais e técnicos pertencentes ao ecossistema de
TV boxes não homologados.

### 2.1 Linha do tempo interna do projeto

| Data | Marco | Evidência local |
|---|---|---|
| 2026-04-18 | Entrega-base `AV01_OpenBox_Audit_Report` | `OpenBox0.1v/deliverables/AV01_OpenBox_Audit_Report.ms` e `.pdf` |
| 2026-04-23 | Consolidação do `ADV7Sec` com auditoria e tuning | `IPS_IDS/ADV7Sec_1.0_AUDIT.md` e `IPS_IDS/PHASE2_TUNING.md` |
| 2026-04-24 | Evidência estável do `ADV7ia` | `ADV7ia/evidence/*.log` |
| 2026-04-25 | Retarget do OpenBox para `RK3229 / R29_5G_LP3` | `OpenBox0.1v/CHANGELOG.md` e `OpenB0X/sources/rk3229_threat_research.md` |
| 2026-04-26 | Consolidação do `OpenB0X` com integração do legado `ADV7Box` | `OpenBox0.1v/ADV7Box/ADV7Box.pdf` e este artefato |

### 2.2 Linha do tempo externa de risco

| Data | Marco | Leitura para o caso |
|---|---|---|
| 2021-05-06 | Receita destrói mais de 97 mil TV boxes piratas | mostra o volume histórico do problema no Brasil [BR-01] |
| 2021-12-22 | Anatel confirma malware em TV boxes não homologados | introduz o eixo segurança, não só pirataria [BR-02] |
| 2022-12-22 | Anatel constata novas vulnerabilidades | confirma que o risco persiste e evolui [BR-03] |
| 2023-03-15 | Anatel publica página de TV boxes homologados | dá referência regulatória ao consumidor [BR-04] |
| 2023-09-06 | Doctor Web descreve Android.Pandora | explica persistência e abuso em TV boxes Android [INT-04] |
| 2025-06-05 | FBI publica PSA I-060525-PSA | formaliza o vetor de cadeia de suprimento e o risco de ativação no primeiro boot [INT-01] |
| 2025-08-12 | Anatel alerta sobre BadBox 2.0 | Brasil aparece como país mais afetado no alerta [BR-05] |
| 2025-11-04/05 | Anatel e MCom consolidam o White Paper e o balanço de 8 milhões | sinaliza escala sistêmica [BR-06] |
| 2026-01-15 | MCom estima 4-6 milhões de usuários recorrentes e 7-8 milhões com eventuais | dimensiona a base de consumo pirata [BR-07] |

## 3. Infográfico dos 3 pilares

```text
OpenBox / ADV7Box (antecedente)
        |
        v
OpenB0X
  +-------------------+   +----------------------+   +----------------------+
  | ADV7ia            |   | Obsidian meta-vault  |   | ADV7Sec (IPS_IDS)    |
  | automação, mesh,  |   | indexação, evidência |   | detecção local       |
  | sessões, controle |   | e rastreabilidade    |   | e baseline host      |
  +-------------------+   +----------------------+   +----------------------+
                    \            |            /
                     \           |           /
                      +----------+----------+
                                 |
                                 v
                               OpenB0X
```

## 4. Estudo de caso de segurança

### 4.1 Panorama brasileiro

Os dados oficiais brasileiros não sustentam uma contagem por modelo `MXQ Pro 4K`; contudo,
sustentam, com grau suficiente de consistência, o pano de fundo regulatório e operacional
necessário para enquadrar o caso:

- a Receita Federal destruiu mais de 97 mil aparelhos em 2021 e a ABTA estimou 4,5 milhões de lares expostos [BR-01];
- a Anatel confirmou malware em TV boxes não homologados em 2021 [BR-02];
- em 2022, a Anatel confirmou novas vulnerabilidades e citou 3,8 milhões de produtos retirados do mercado em dois anos [BR-03];
- em 2025, a Anatel afirmou que o Brasil concentrava 1,8 milhão de dispositivos infectados por BadBox 2.0 [BR-05];
- em 2026, o MCom afirmou que entre 4 e 6 milhões de usuários usam IPTV pirata de forma recorrente, chegando a 7-8 milhões quando se soma consumo eventual e compartilhamento [BR-07].

Em termos metodológicos, esse conjunto de dados não autoriza inferência estatística por modelo,
mas autoriza tratar o `MXQ Pro 4K` como exemplar técnico de uma classe mais ampla de risco.

### 4.2 MXQ Pro 4K e vulnerabilidades correlatas

O relatório Claude local em `OpenB0X/sources/compass_mxq_pro_5g.md` [LOC-01] e o research de
ameaça em `OpenB0X/sources/rk3229_threat_research.md` [LOC-02] convergem em quatro pontos:

- o aparelho é apresentado como uma variante genérica da família Rockchip RK3229 / RK3228A [LOC-01];
- o firmware pode carregar backdoor de cadeia de suprimento, com persistência fora do fluxo normal de "factory reset" [LOC-01] [LOC-02];
- o ecossistema Android TV box foi associado a Android.Pandora e BADBOX 2.0 [INT-04] [INT-01] [INT-02];
- o risco não é apenas violação de direitos autorais, mas também exfiltração, proxy residencial e ataque lateral na rede doméstica.

### 4.3 Análise aprofundada do vetor de backdoor no ecossistema RK3229

No caso `RK3229`, o termo "backdoor" descreve dois planos distintos de risco, que não devem ser
confundidos: o plano físico, vinculado ao `Maskrom` embutido na `BootROM` do SoC, e o plano
lógico, associado ao firmware de cadeia de suprimento e ao carregamento de componentes maliciosos
no primeiro boot [INT-01] [LOC-02].

| Camada | O que a evidência sustenta | Leitura de risco |
|---|---|---|
| Física (`BootROM` / `Maskrom`) | o `RK3229` mantém um modo de recuperação em silício, anterior ao sistema operacional, que permite regravação com acesso físico [LOC-02] | não prova infecção prévia, mas reduz a barreira para adulteração pós-posse |
| Firmware / cadeia de suprimento | o dispositivo pode sair de fábrica com payload pré-instalado ou baixar componente malicioso no primeiro boot [INT-01] [LOC-02] | explica persistência fora do fluxo normal de uso e a limitação de um simples "factory reset" |
| Aplicação / ecossistema | sideloading e lojas paralelas reforçam a infecção em boxes piratas [INT-01] [INT-02] | amplia a superfície de comprometimento mesmo sem ataque dirigido |

Em outras palavras, o problema central não é um "exploit manual" acionado pelo usuário, mas um
modelo de comprometimento embutido na cadeia de fornecimento e reforçado por um hardware que
facilita regravação quando há acesso físico. Essa distinção é relevante: `Maskrom` é uma interface
de recuperação em silício, não uma prova de malware; ainda assim, combinado com firmware opaco e
boxes genéricas, ele amplia o risco operacional do aparelho [LOC-02].

### 4.4 Leitura do material público do FBI

O PSA `I-060525-PSA`, publicado pelo FBI, não nomeia o `RK3229` nem o `MXQ Pro 4K`
individualmente. Ainda assim, é central para este estudo porque descreve, com clareza, o padrão de
comprometimento observado na classe de dispositivos em que o aparelho se insere:
comprometimento pré-venda, ativação no primeiro boot e monetização do dispositivo para atividade
criminosa em background [INT-01].

O documento do FBI permite três leituras úteis para este artefato:

- confirma o vetor de cadeia de suprimento como risco primário, e não acessório [INT-01];
- reforça que parte do comprometimento pode ocorrer antes de qualquer ação do usuário [INT-01];
- não prova, por si só, que esta unidade específica estava infectada antes da aquisição, o que
  preserva o rigor metodológico do estudo [INT-01] [LOC-02].

Portanto, a evidência do FBI deve ser utilizada aqui como suporte de classe, e não como laudo
pericial de unidade. A conclusão operacional permanece a mesma: tratar o `MXQ Pro 4K` como
potencialmente comprometido até o wipe completo, a troca de firmware e a verificação pós-flash
[INT-01] [LOC-02].

### 4.5 Correlação entre risco, firmware e rede

| Eixo | O que o caso mostra | Impacto prático |
|---|---|---|
| Firmware | atualização/boot podem carregar código malicioso | o dispositivo não deve entrar na rede antes de wipe completo |
| Rede | TV box pode atuar como proxy residencial ou pivot | o tráfego deve ser isolado por VLAN ou rede segregada |
| Usuário | o dono não percebe a infecção em uso normal | a defesa precisa ser preventiva, não reativa |
| Mercado | o problema é massivo no Brasil | o caso individual representa uma classe de exposição |

### 4.6 Desagregação analítica do panorama brasileiro

Em substituição ao gráfico único, este documento passa a organizar os indicadores em três eixos
temáticos. A mudança é metodologicamente necessária: apreensões, lares expostos, dispositivos
infectados e estimativas de uso pertencem a categorias distintas e, quando exibidos em um único
eixo, induzem comparação inadequada.

#### 4.6.1 Fiscalização e retirada de mercado

| Indicador | Valor | Leitura |
|---|---|---|
| TV boxes piratas destruídas | 97 mil | dado direto da Receita Federal / ABTA [BR-01] |
| Produtos não homologados retirados em 2 anos | 3,8 milhões | balanço da Anatel em 2022 [BR-03] |
| TV boxes entre os produtos retirados | 1,1 milhão | subconjunto citado pela Anatel [BR-03] |
| Produtos retirados desde 2018 até out/2025 | 8 milhões | balanço Anatel / MCom [BR-06] |

Esse primeiro eixo mede capacidade de repressão, apreensão e retirada de mercado. Ele não informa,
por si só, quantos consumidores efetivamente utilizam cada modelo, mas quantifica a escala da
resposta estatal ao problema.

#### 4.6.2 Exposição residencial e contaminação

| Indicador | Valor | Leitura |
|---|---|---|
| Lares com aparelhos ilegais | 4,5 milhões | estimativa da ABTA com base em IBGE e Anatel [BR-01] |
| Dispositivos infectados por BadBox 2.0 no Brasil | 1,8 milhão | alerta da Anatel de 2025 [BR-05] |

O segundo eixo aproxima exposição doméstica e contaminação conhecida. Embora as métricas não sejam
equivalentes, sua leitura conjunta é útil para demonstrar que o problema não é residual nem
circunscrito a apreensões pontuais.

#### 4.6.3 Estimativa de base usuária

| Indicador | Valor | Leitura |
|---|---|---|
| Usuários recorrentes de IPTV pirata | 4-6 milhões | estimativa oficial do Governo do Brasil [BR-07] |
| Usuários recorrentes + eventuais | 7-8 milhões | faixa ampliada pelo MCom [BR-07] |

O terceiro eixo desloca a análise do mercado físico para a base usuária. Trata-se da camada mais
próxima do impacto social do fenômeno, ainda que continue sem granularidade por modelo.

## 5. Logs, reports e tests

### 5.1 OpenBox

- `OpenBox0.1v/deliverables/AV01_OpenBox_Audit_Report.ms`
- `OpenBox0.1v/deliverables/AV01_OpenBox_Audit_Report.pdf`
- `OpenBox0.1v/tests/validate-stack.sh`
- `OpenBox0.1v/tests/validate-obsidian-vault.sh`
- `OpenBox0.1v/tests/phase-b-vault-tool.sh`
- `OpenBox0.1v/tests/ci-syntax-check.sh`

### 5.2 IPS_IDS / ADV7Sec

- `IPS_IDS/ADV7Sec_1.0_AUDIT.md`
- `IPS_IDS/PHASE2_TUNING.md`
- `IPS_IDS/tests/ci-syntax-check.sh`
- `IPS_IDS/tests/test_adv7sec_cli.py`
- `IPS_IDS/tests/test_adv7sec_install.py`
- `IPS_IDS/tests/test_adv7sec_apply_contract.py`

### 5.3 ADV7ia

- `ADV7ia/evidence/ai-stack-status.stable.2026-04-24-153505.log`
- `ADV7ia/evidence/audit-local-ai-stack.final.2026-04-24-041947.log`
- `ADV7ia/evidence/audit-local-ai-stack.known-good.2026-04-24-045236.log`
- `ADV7ia/tests/validate-project-layout.sh`
- `ADV7ia/tests/validate-obsidian-vault.sh`
- `ADV7ia/tests/validate-control-mesh.sh`

## 6. Referências

### Oficiais brasileiras

- [BR-01] Receita Federal e ABTA, 06/05/2021, https://www.gov.br/receitafederal/pt-br/assuntos/noticias/2021/maio/receita-federal-e-associacao-brasileira-de-televisao-por-assinatura-destroem-mais-de-97-mil-aparelhos-de-tv-box-piratas-no-rio-de-janeiro
- [BR-02] Anatel, 22/12/2021, https://www.gov.br/anatel/pt-br/assuntos/noticias/anatel-constata-presenca-de-malware-em-aparelhos-de-tv-box-nao-homologados
- [BR-03] Anatel, 22/12/2022, https://www.gov.br/anatel/pt-br/assuntos/noticias/anatel-constata-novas-vulnerabilidades-em-tv-box-nao-homologados
- [BR-04] Anatel, 15/03/2023, https://www.gov.br/anatel/pt-br/assuntos/noticias/anatel-lanca-pagina-com-tv-boxes-homologados
- [BR-05] Anatel, 12/08/2025, https://www.gov.br/anatel/pt-br/assuntos/noticias/anatel-emite-alerta-sobre-malware-bad-box-2-0-em-tv-boxes-piratas
- [BR-06] Anatel / MCom, 04/11/2025 e 05/11/2025, https://www.gov.br/anatel/pt-br/assuntos/noticias/anatel-lanca-white-paper-e-reforca-compromisso-com-a-seguranca-dos-usuarios e https://www.gov.br/mcom/pt-br/noticias/2025/novembro/anatel-retira-de-circulacao-mais-de-8-milhoes-de-produtos-de-telecomunicacoes-por-falta-de-homologacao-correspondendo-a-r-833-6-milhoes
- [BR-07] Ministério das Comunicações, 15/01/2026, https://www.gov.br/mcom/pt-br/noticias/2026/janeiro/brasil-intensifica-combate-a-pirataria-digital-em-2025-com-apreensao-milionaria-e-mapeamento-de-ate-8-milhoes-de-usuarios-clandestinos

### Técnicas externas

- [INT-01] FBI, PSA I-060525-PSA, 05/06/2025, https://www.fbi.gov/investigate/cyber/alerts/psa/home-internet-connected-devices-facilitate-criminal-activity
- [INT-02] HUMAN Security, BADBOX 2.0, 05/03/2025, https://www.humansecurity.com/newsroom/human-exposes-badbox-2-0-scheme/
- [INT-03] Google Security Blog, ação legal contra BadBox 2.0, https://blog.google/innovation-and-ai/technology/safety-security/google-taking-legal-action-against-the-badbox-20-botnet/
- [INT-04] Doctor Web, Android.Pandora, 06/09/2023, https://news.drweb.com/show/?i=14743

### Locais

- [LOC-01] `OpenB0X/sources/compass_mxq_pro_5g.md`
- [LOC-02] `OpenB0X/sources/rk3229_threat_research.md`
- [LOC-03] `OpenBox0.1v/CHANGELOG.md`
- [LOC-04] `OpenBox0.1v/ADV7Box/ADV7Box.pdf`
- [LOC-05] `ADV7ia/evidence/*.log`
- [LOC-06] `IPS_IDS/ADV7Sec_1.0_AUDIT.md`
- [LOC-07] `IPS_IDS/PHASE2_TUNING.md`

## 7. Conclusão

Em síntese, OpenB0X organiza, em um único artefato, três dimensões complementares: memória
operacional (`ADV7ia`), rastreabilidade documental (`Obsidian meta-vault`) e visibilidade
defensiva (`ADV7Sec`). O caso `MXQ Pro 4K`, por sua vez, cumpre papel analítico preciso: não
serve como curiosidade de mercado, mas como exemplo tecnicamente defensável de risco de cadeia de
suprimento, opacidade de firmware e exposição ampliada no contexto brasileiro.
