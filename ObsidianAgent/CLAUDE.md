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
```

```bash
# Verificar notas stale (somente leitura)
python3 "${AOPS_OBSIDIAN_AGENT_CLI:-$HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py}" --check --repo .

# Regenerar notas sob Vault/Generated/
python3 "${AOPS_OBSIDIAN_AGENT_CLI:-$HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py}" --sync --repo .

# Saúde geral do stack (Codex+Claude+Obsidian) — não destrutivo
bash tests/validate-collab-stack.sh

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

## Skills esperados

Os skills Claude `preserve`, `compress`, `resume`, `collab` devem estar em
`~/.claude/commands/` (um `.md` por skill). `validate-collab-stack.sh` falha se
algum estiver ausente. `/compress` é o único que escreve em `SessionLogs/<project>/`.

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
├── Projects/                # Projetos aninhados. Apenas OpenBox0.1v tem .aops-vault.toml
│   │                        #   (logo, único em Project Manifests). IPS_IDS/README.md entra
│   │                        #   em Project Overviews; codDESPERTAR não tem README e fica fora.
│   ├── codDESPERTAR/         # Sem .aops-vault.toml (Roteiros/, Videos_Ref/)
│   ├── IPS_IDS/              # Sem .aops-vault.toml. Tem CLAUDE.md próprio (instalador
│   │                         #   IPS/IDS Arch, fase 1 detection-only). README entra no
│   │                         #   catálogo Project Overviews do meta-vault.
│   └── OpenBox0.1v/          # Fixture de prova (referência canônica) e projeto real
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
├── SessionLogs/              # Logs de sessão (saída do skill /compress)
│   └── <project>/            # Criado pelo /compress; dir 700, arquivos 600
└── tests/
    └── validate-collab-stack.sh  # Health check do stack completo
```

## CLAUDE.md aninhados

- `Projects/IPS_IDS/CLAUDE.md` — cobre apenas o instalador IPS/IDS (Arch, Bash+Python
  parity, sensores auditd/Falco/Kunai/Suricata/Zeek). Não repete aqui: contrato de
  vault do meta-repo. Escopo complementar, não sobreposto.

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
  `projects/cod_despertar:`). Não inventar prefixos novos fora desse esquema.
- Saída determinística obrigatória: o mesmo estado de repo deve produzir arquivos idênticos.
- Redação de segredos em session logs: obrigatória via `~/plugins/aops-agent/cpr/redact.py`.

## Gotchas

- O CLI (`obsidian_agent_cli.py`) NÃO está neste repo. Se `$AOPS_OBSIDIAN_AGENT_CLI`
  não estiver definido e `$HOME/plugins/aops-agent/obsidian-agent/` não existir,
  todos os comandos sync/check falharão.
- `validate-collab-stack.sh` exige que os skills Claude (`preserve`, `compress`,
  `resume`, `collab`) estejam em `~/.claude/commands/`. Skills ausentes → FAIL.
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
