# Obsidian Vault — OpenBox

O repositório `OpenBox0.1v` pode ser aberto diretamente como um vault do Obsidian.

## O que foi integrado

- Configuração mínima em `.obsidian/` para templates, daily notes e navegação básica.
- Notas manuais em `vault/` para dashboards, backlog, roadmap e pesquisa.
- Notas geradas em `vault/Generated/` a partir de `install.d/`, `systemd/`, `usr/local/sbin/`, `tests/` e `etc/`.
- Contrato do vault em `.aops-vault.toml`.
- Diretório universal padrão do Obsidian agent em `~/plugins/aops-agent/obsidian-agent/`.
- Wrapper compatível em `tools/sync_obsidian_vault.py`.
- Wrapper repo-local em `tools/aops_vault_cli.py`.

## Como usar

```bash
cd /caminho/para/OpenBox0.1v
python3 tools/sync_obsidian_vault.py --check
python3 tools/sync_obsidian_vault.py --sync
```

Para outro repositório opt-in:

```bash
python3 "${AOPS_OBSIDIAN_AGENT_CLI:-$HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py}" --init --repo /caminho/para/outro-repo
python3 "${AOPS_OBSIDIAN_AGENT_CLI:-$HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py}" --check --repo /caminho/para/outro-repo
python3 "${AOPS_OBSIDIAN_AGENT_CLI:-$HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py}" --sync --repo /caminho/para/outro-repo
```

Depois disso:

1. Abra a pasta raiz do projeto no Obsidian.
2. Use `vault/Dashboards/OpenBox Vault Home.md` como ponto de entrada.
3. Edite notas manuais em `vault/`.
4. Não edite notas geradas em `vault/Generated/` manualmente; regenere.

## Validacao

```bash
bash tests/validate-obsidian-vault.sh
bash tests/phase-b-vault-tool.sh
```

O primeiro teste recompila o tooling Python e falha se os arquivos gerados estiverem desatualizados.
O segundo prova o contrato Phase B e o gate principal de Phase C: `--init`, `--check`, `--sync`, check-first por padrão, stale detection determinística, fixture repo-neutral e compatibilidade com `OpenBox0.1v`.
