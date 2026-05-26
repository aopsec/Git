# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Propósito

Meta-vault que orquestra a geração de notas Obsidian em múltiplos repos de projeto AOPS.
Não é uma aplicação standalone. Função central: executar `obsidian_agent_cli.py` contra
arquivos `.aops-vault.toml` para produzir notas determinísticas em `Vault/Generated/`
e, dentro de cada projeto aninhado, em seu próprio vault root.

O CLI externo **não está neste repo**:
`$HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py`
Substituível via `$AOPS_OBSIDIAN_AGENT_CLI` (check/sync) ou `$AOPS_OBSIDIAN_AGENT_HOME`
(wrapper scripts dentro de `Projects/`).

`AGENTS.md` na raiz é o sibling Codex-side com guidance substancialmente
sobreposto (comandos, layout, regra de determinismo). Ao alterar este CLAUDE.md
verifique se `AGENTS.md` precisa do mesmo update — divergência entre os dois
quebra parity Claude↔Codex.

## Stack

| Camada | Tecnologia |
|---|---|
| CLI principal | Python 3 (externo, não vendorizado aqui) |
| Testes / validação | Bash 5.x |
| Contrato de vault | TOML (`.aops-vault.toml`) |
| Notas geradas | Markdown para Obsidian |
| Redação de segredos | `~/plugins/aops-agent/cpr/redact.py` |

## Comandos

Rodar a partir da raiz do repo, salvo indicação.

Bootstrap recomendado para a sessão (evita repetir o path em cada comando):

```bash
export AOPS_OBSIDIAN_AGENT_CLI="${AOPS_OBSIDIAN_AGENT_CLI:-$HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py}"
export LC_ALL=C.UTF-8 LANG=C.UTF-8   # ordenação determinística de globs no --sync
test -f "$AOPS_OBSIDIAN_AGENT_CLI" || echo "MISSING: external CLI not reachable"
```

Se o smoke-test acima reportar MISSING, **não** rode `--check`/`--sync` — corrija o
path primeiro (`$AOPS_OBSIDIAN_AGENT_CLI` ou clone do repo `aops-agent`).

O CLI não tem bit `+x` no filesystem de plugin (read-only). Sempre invocar via
`python3 "$AOPS_OBSIDIAN_AGENT_CLI"` — nunca `"$AOPS_OBSIDIAN_AGENT_CLI"` direto.

```bash
# Atalho: smoke driver (check + pytest + cyber-dry-run)
bash .claude/skills/run-obsidian-agent/smoke.sh all

# Verificar notas stale (somente leitura)
python3 "${AOPS_OBSIDIAN_AGENT_CLI:-$HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py}" --check --repo .

# Regenerar notas sob Vault/Generated/
python3 "${AOPS_OBSIDIAN_AGENT_CLI:-$HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py}" --sync --repo .

# Saúde geral do stack (Codex+Claude+Obsidian) — não destrutivo
bash tests/validate-collab-stack.sh

# Regenerar o vault de referência CyberPDF (cyber-only, copyright-bounded)
python3 tools/extract_cyber_pdf_reference.py \
  --pdf-list tools/cyber_pdf_ref/b00ks_sources.txt --repo . --copy-pdfs --replace

# Dry-run: classifica PDFs sem escrever nada (safe para auditoria)
python3 tools/extract_cyber_pdf_reference.py \
  --pdf-list tools/cyber_pdf_ref/b00ks_sources.txt --repo . --dry-run

# Teste Python do extractor CyberPDF
pytest -q tests/test_cyber_pdf_ref.py

# Testes da fixture OpenBox
bash Projects/OpenBox0.1v/tests/phase-b-vault-tool.sh    # prova vault repo-neutral
bash Projects/OpenBox0.1v/tests/validate-obsidian-vault.sh
bash Projects/OpenBox0.1v/tests/ci-syntax-check.sh       # bash -n + shellcheck + nft + python
bash Projects/OpenBox0.1v/tests/validate-stack.sh        # 10 checks acumulados (não aborta na 1ª falha)
```

Fluxo padrão após qualquer mudança de vault: `--check` → `--sync` → `--check`.
Após `--sync`, o segundo `--check` DEVE sair sem stale entries; divergência = bug de
gerador ou source não rastreado.

Rodando um teste isolado: cada `.sh` em `Projects/OpenBox0.1v/tests/` é executável
diretamente via `bash <path>`. Não há runner agregador além de `validate-stack.sh`
(que só acumula PASS/FAIL — ver Gotchas) e `tests/validate-collab-stack.sh` na raiz.
Os testes Python da raiz (`tests/test_*.py`) cobrem o pipeline CyberPDF e rodam
via `pytest -q tests/`.

## Skills esperados

Os skills Claude `preserve`, `compress`, `resume`, `collab` devem estar em
`~/.claude/commands/` (um `.md` por skill). `validate-collab-stack.sh` falha se
algum estiver ausente. `/compress` é o único que escreve em `SessionLogs/<project>/`.

Outros skills do harness (`simplify`, `update-config`, `keybindings-help`,
`fewer-permission-prompts`, `loop`, `schedule`, `init`, `review`, `security-review`)
podem estar disponíveis no ambiente mas são opcionais — não validados pelo stack.

Skill dual-ecossistema: `cyberref` em `~/.codex/skills/cyberref/SKILL.md` (Codex) e `~/.claude/commands/cyberref.md` (Claude); opt-in para trabalho cyber/offensive-security com vault CyberPDF certificado e gate `objective_complete=100%`.

Skill projeto-local: `.claude/skills/run-obsidian-agent/` — driver de smoke para o
ObsidianAgent (check + pytest + cyber-dry-run). Exposto ao harness como skill
`run-obsidian-agent`; o entry-point é `smoke.sh` com subcomandos
`check|sync|test|cyber-dry|all`.

## Arquitetura

```
ObsidianAgent/
├── .aops-vault.toml          # Contrato meta-vault (Project Manifests, Overviews,
│                             #   Session Logs, Daily Notes)
├── AGENTS.md                 # Diretrizes para agentes IA neste repo
├── README.md                 # Propósito e CLI padrão
├── Vault/
│   ├── Vault Home.md         # Nota manual de entrada
│   ├── Journal/Daily/        # Daily notes (manuais, 600)
│   └── Generated/            # GERADO PELA MÁQUINA — nunca editar à mão
│       ├── Repository Map.md
│       ├── Project Manifest Index.md
│       ├── Project Overview Index.md
│       ├── Session Log Index.md
│       ├── Daily Note Index.md
│       ├── Project Manifests/
│       ├── Project Overviews/
│       ├── Daily Notes/
│       └── Session Logs/
├── Projects/                # Projetos aninhados. Quem tem .aops-vault.toml entra em
│   │                        #   Project Manifests; quem tem README.md entra em Project
│   │                        #   Overviews. ADV7ia, OpenBox0.1v e bbWebScan têm ambos →
│   │                        #   dupla entrada. IPS_IDS e adv7YT só têm README → só Overviews.
│   ├── ADV7ia/               # Python project. Tem .aops-vault.toml + README.md → manifest E overview.
│   ├── ADV7_0f_Sec_Tools/    # Offensive security tooling (bash scripts; sem .aops-vault.toml
│   │   │                     #   → não entra nos catálogos do meta-vault).
│   │   ├── adv7FUZZ0.1.5v.sh    # Fuzzer HTTP (versão ativa)
│   │   ├── adv7SQLMap0.0.7v.sh  # SQLi automation + evasion (versão ativa)
│   │   ├── adv7WebClone.sh   # Clone de site para análise offline
│   │   └── bbWebScan/        # Python project ativo (v0.5.10, CHANGELOG.md, coverage gate
│   │                         #   98%). Orquestrador de recon de bug bounty. Tem
│   │                         #   .aops-vault.toml + README.md + CLAUDE.md próprio → dupla
│   │                         #   entrada nos catálogos. Cyberref debt: Scrapy stage shipped
│   │                         #   com `cyberref: PENDING` marker (promover quando vault
│   │                         #   citation existir).
│   ├── adv7YT/               # C# .NET 8 WPF app (Windows desktop, YouTube downloader +
│   │                         #   converter). Sem .aops-vault.toml → só entra em Project
│   │                         #   Overviews. Tem README.md + CLAUDE.md próprio. Binários
│   │                         #   bundled (yt-dlp.exe, ffmpeg.exe) não estão no git — devem
│   │                         #   ser adicionados em src/adv7YT/Assets/ antes do build.
│   │                         #   Stack: WPF-UI 4.0.3, CommunityToolkit.Mvvm 8.3.2.
│   ├── IC01-aops/            # Umbrella com sub-projetos (ADV7ia, AVAL01-IC, IPS_IDS, OpenB0X,
│   │                         #   OpenBox0.1v). Sem TOML/README na raiz → fora dos catálogos do
│   │                         #   meta-vault. Possui CLAUDE.md aninhados (ver seção abaixo).
│   ├── IPS_IDS/              # Sem .aops-vault.toml. Tem CLAUDE.md próprio (instalador
│   │                         #   IPS/IDS Arch, fase 1 detection-only). README entra no
│   │                         #   catálogo Project Overviews do meta-vault.
│   ├── OpenBox0.1v/          # Fixture de prova (referência canônica) e projeto real
│       ├── .aops-vault.toml  # Contrato de vault do projeto
│       ├── install.sh        # Instalador faseado (Debian/Raspbian, requer root)
│       ├── install.d/        # Fases 00–09 (base, sysctl, nft, wg, dns, tor, stremio,
│       │                     #   monitoring, watchdogs, validate)
│       ├── etc/              # Configs de sistema (nftables, ssh, tor, wireguard, monit,
│       │                     #   caddy, fail2ban, dnscrypt-proxy, sysctl)
│       ├── usr/local/sbin/   # Scripts operacionais (ntfy, wg-watchdog, killswitch,
│       │                     #   dnsleak-check, tor-check, tune)
│       ├── systemd/          # Units e timers (.service, .timer)
│       ├── tools/            # Wrappers Python do CLI externo (aops_vault_cli.py,
│       │                     #   sync_obsidian_vault.py, _agent_path.py) + build_av01_pdf.sh
│       ├── vault/            # Vault root do projeto (Generated/ dentro)
│       ├── tests/            # Suite de testes shell (phase-b, validate-obsidian-vault,
│       │                     #   ci-syntax-check, validate-stack)
│       ├── CHANGELOG.md, VERSION, LICENSE
│       └── docs/, deliverables/  # Documentação de release e artefatos (não afetam vault contract)
│   └── topology-c-dedicated-kvm-whonix.md   # Markdown solto na raiz de Projects/. Não é
│                              #   projeto e não casa com nenhum source_pattern do meta-vault
│                              #   (catalogs esperam Projects/*/.aops-vault.toml ou
│                              #   Projects/*/README.md). Manter em mente ao auditar drift.
├── SessionLogs/              # Logs de sessão (saída do skill /compress)
│   └── <project>/            # Criado pelo /compress; dir 700, arquivos 600
├── tools/
│   ├── extract_cyber_pdf_reference.py   # Builder do vault CyberPDF
│   └── cyber_pdf_ref/        # Módulos do extractor (cli, extractor, render,
│                             #   patterns, sections, source_note, ...)
├── Vault/References/CyberPDFs/  # Vault de referência cyber-only (copyright-bounded,
│   ├── B00Ks/                   #   Mirror repo-local dos PDFs fonte (PT_books/,
│   │                            #   My-CyberSecurity-Store/, R3DH47/, 1Sem/).
│   │                            #   Substituiu dependência de mount externo [REF-CYBERPDF-04].
│   └── Sources/                 #   Notas geradas por tools/extract_cyber_pdf_reference.py
└── tests/
    ├── validate-collab-stack.sh   # Health check do stack completo
    └── test_cyber_pdf_ref.py      # Testes pytest do extractor CyberPDF
```

## CyberPDF Extractor — Classificação de PDFs

O extractor (`tools/cyber_pdf_ref/extractor.py`) produz um de quatro status por PDF:

| Status | Critério |
|---|---|
| `cyber-active` | ≥ 3 hits em `STRONG_CYBER_KEYWORDS`, ou ≥ 1 strong + (hits ≥ 6 ou título marcado em `CYBER_TITLE_MARKERS`) |
| `cyber-adjacent` | ≥ 1 strong hit, ou título marcado + ≥ 3 broad hits |
| `non-cyber` | Path contém parte em `NON_CYBER_PATH_PARTS` **ou** título/conteúdo bate `GENERAL_PROGRAMMING_TITLE_MARKERS` ou `NON_CYBER_MARKERS` |
| `duplicate` | SHA256 já visto num PDF anterior |

`NON_CYBER_PATH_PARTS` (em `patterns.py`) filtra automaticamente prateleiras
misturadas: `1sem`, `finance books`, `learn programming`, `self help books`.
O `B00Ks/` mirror pode conter essas prateleiras — elas não entram nos índices
CyberPDF mesmo que passem pelo `b00ks_sources.txt`.

`[REF-CYBERPDF-06]` — keyword matching usa word-boundary regex para evitar falsos
positivos como `tor` em `investor`.

Ao adicionar novos PDFs a `B00Ks/`, rodar `--dry-run` primeiro para verificar o
status antes de fazer `--replace`. Status `cyber-adjacent` não gera nota ativa —
revisar manualmente se deve promover a `cyber-active`.

## CLAUDE.md aninhados

- `Projects/IPS_IDS/CLAUDE.md` — instalador IPS/IDS (Arch, Bash+Python parity,
  sensores auditd/Falco/Kunai/Suricata/Zeek).
- `Projects/IC01-aops/IPS_IDS/CLAUDE.md` — runtime ADV7Sec 1.0 (Python, single
  source of truth `adv7sec_1_0/`, CLI unificado audit/doctor/backend/install).
- `Projects/IC01-aops/AVAL01-IC/CLAUDE.md` — entrega AV01 CEUB; documento derivado
  que reaproveita OpenBox0.1v + IPS_IDS, **não fonte**.
- `Projects/OpenBox0.1v/ADV7Box/CLAUDE.md` — entrega AV01-A consolidada (também
  derivada, referência visual; não editar).
- `Projects/ADV7_0f_Sec_Tools/bbWebScan/CLAUDE.md` — engenharia do bbWebScan
  (convenções de commit, gotchas, gates de qualidade).
- `Projects/adv7YT/CLAUDE.md` — app Windows C#/.NET 8 WPF (YouTube downloader);
  stack, security rules, bundled binaries workflow, commit prefix.

Escopos complementares, não sobrepostos ao contrato de vault do meta-repo.

## Projects/ADV7_0f_Sec_Tools/bbWebScan (Python, ativo)

Projeto Python com `CLAUDE.md` próprio em `Projects/ADV7_0f_Sec_Tools/bbWebScan/CLAUDE.md`
(escopo de engenharia). Contratação de produto continua em `README.md` +
`CHANGELOG.md`. É o projeto Python mais desenvolvido do meta-repo e o que
mais se modifica entre releases.

Como é offensive-security tooling, trabalho de referência externo deve passar
pelo skill `cyberref` (vault-bounded). Não colar prosa upstream em fonte sem
citação no vault — review blocker.

| Camada | Detalhe |
|---|---|
| Versão atual | `0.5.10` (fonte de verdade: `pyproject.toml`) |
| Stack | Python 3.12+, Pydantic v2, PyYAML, Scrapy (safe-default), opcional `publicsuffix2`, opcional `scrapy-playwright` via extra `[js]` |
| Gates obrigatórios | `ruff check .`, `mypy --strict`, `pytest -q`, coverage ≥ 98% (rodar via `bash scripts/verify.sh`) |
| CLI | `bbwebscan {scan,install,doctor,init,history,show,compare}`; smart-default `bbwebscan example.com` |
| Layout | `bbwebscan/` package · `bbwebscan/stages/` (httpx/katana/scrapy/discovery/params/nuclei/amass/kiterunner) · `bbwebscan/data/` (vendored secrets ruleset) · `tests/fixtures/` JSONL · `runs/<UTC>/` artefatos |
| Versionamento | `pyproject.toml` é única fonte de verdade; `__version__` lê via `importlib.metadata`; `tests/test_changelog.py` falha se um bump de versão esquecer de atualizar o CHANGELOG. |

**Cyberref debt (registrado em 2026-05-14):** Scrapy stage shipped com
`cyberref: PENDING attestation` marker. Promover a "certified" quando vault
citation existir para Scrapy. Atualizar quarterly o `bbwebscan/data/secrets_patterns.yml`
(vendored de mazen160/secrets-patterns-db, CC-BY-4.0).

Comandos típicos dentro de `Projects/ADV7_0f_Sec_Tools/bbWebScan/`:

```bash
source .venv/bin/activate
pip install -e '.[dev,cov]'              # ',psl' opcional · ',js' para scrapy-playwright
bash scripts/verify.sh                    # ruff + mypy + pytest --cov (gate único)
bbwebscan --version                       # bbwebscan 0.5.10
bbwebscan doctor                          # readiness do toolchain (httpx/katana/scrapy/...)
bbwebscan history --limit 10              # últimos runs

# Teste isolado (pytest)
pytest tests/test_<module>.py::TestClass::test_name -v
```

Códigos de saída do `scan`: `0` ok, `2` erro de preflight (tool/wordlist
faltando), `3` há findings ≥ `--severity` (gate de CI). DNS preflight via
`--check-dns` é não-fatal — falhas viram nota em `summary.md`, não erro.

Conexão com o meta-vault: `bbWebScan/.aops-vault.toml` declara seus próprios
catálogos (Stages, Profiles) usados apenas dentro do projeto; não interfere
com os catálogos do meta-vault raiz que apenas indexam o `README.md` em
"Project Overviews" e o `.aops-vault.toml` em "Project Manifests".

## Schema .aops-vault.toml

```toml
version = 1
[project]  name, tag
[vault]    root, generated
[render]   generator_ref, regenerate_command, stale_message, summary_fallback
[repository_map]  include, core_documents[], manual_dashboards[]
[related_notes]   defaults[], [related_notes.match] keyword = [linked-docs]
[[catalog]]  label, folder, note_prefix, tag, source_patterns[], title_mode, index_name
```

Valores de `title_mode` em uso: `standard`, `project-parent`, `session-log`, `daily`,
`install-phase`, `config`.

## Convenções

- `Vault/Generated/` é inteiramente gerenciado por máquina — nunca editar manualmente.
- Notas manuais: nomes curtos, title-case, link-friendly (e.g., `Vault Home.md`).
- `Sumary.base` na raiz é um Obsidian Base (view definition); não é nota gerada, deixar intacto.
- Padrões de source em catalogs usam glob relativo à raiz do repo.
- `SessionLogs/<project>/` é populado pelo skill `/compress`; dir=700, arquivos=600.
- Convenção de commits: `vault:`, `tests:`, `projects/openbox:` como prefixos
  observados. Para novos projetos aninhados, seguir o mesmo padrão
  (`projects/<slug>:`, slug em snake_case minúsculo — e.g. `projects/ips_ids:`,
  `projects/adv7ia:`). Não inventar prefixos novos fora desse esquema.
- Saída determinística obrigatória: o mesmo estado de repo deve produzir arquivos idênticos.
- Redação de segredos em session logs: obrigatória via `~/plugins/aops-agent/cpr/redact.py`.

## Gotchas

- O CLI (`obsidian_agent_cli.py`) NÃO está neste repo. Se `$AOPS_OBSIDIAN_AGENT_CLI`
  não estiver definido e `$HOME/plugins/aops-agent/obsidian-agent/` não existir,
  todos os comandos sync/check falharão.
- **`--sync` aborta com orphan files** — contrato two-phase do CLI externo: `scan_drift`
  detecta orphans em `Vault/Generated/` → `run_sync` recusa escrever qualquer coisa
  enquanto houver orphans. Remover o(s) arquivo(s) ou registrá-los no `[[catalog]]`
  do `.aops-vault.toml` antes de rodar `--sync`. Orphan = arquivo com frontmatter
  `project: <name>` + `type: generated-index|source-note` não produzido pelo
  gerador atual.
- `validate-collab-stack.sh` exige que os skills Claude (`preserve`, `compress`,
  `resume`, `collab`) estejam em `~/.claude/commands/`. Skills ausentes → FAIL.
  O script também espera o checkout canônico em `$HOME/ObsidianAgent`; rodando
  fora dele alguns checks de path absoluto podem falhar.
- O `.aops-vault.toml` raiz e o do OpenBox são contratos separados.
  `--repo .` na raiz processa apenas o meta-vault.
- `Projects/OpenBox0.1v/tests/validate-stack.sh` usa `set -uo pipefail` (falta `-e`,
  marcado `[INTENTIONAL]` no script). Não interrompe em falhas de comando individuais —
  comportamento proposital para acumular PASS/FAIL. Não confundir com `tests/validate-collab-stack.sh`
  na raiz, que usa `set -euo pipefail` (aborta na primeira falha).
- OpenBox é alvo Debian/Raspbian (apt), não Arch. Scripts de instalação NÃO rodam
  em Arch sem adaptação.
- Determinismo do `--sync` depende de locale consistente (ordenação de globs).
  Sempre exportar `LC_ALL=C.UTF-8` antes de gerar/comparar — divergência entre
  máquinas com locales distintos pode produzir reordenação de catálogos sem que
  o source tenha mudado.
- `etc/wireguard/wg0.conf.example` e `etc/monit/monitrc.d/openbox.conf` contêm
  placeholders (`REPLACE_WITH_*`) que devem ser substituídos antes do deploy.
