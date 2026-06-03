# HermesAgent Vault Home

Manual entry note for the HermesAgent project-local vault.

This project ships a hardened, GPU-local deployment of the Nous Research Hermes Agent
wired into the ObsidianAgent meta-vault. See the generated indexes under `Generated/`
after running the project's own `--sync`, and `docs/HARDENING.md` for the security model.

- **Project Docs** — `docs/*.md` (hardening rationale, cyberref-grounded)
- **Automation** — `setup.sh` (GPU toolkit + build + model pull + bring-up)
- **Configs** — `docker-compose.yml`, `cli-config.yaml`, `squid/*.conf`

> `Generated/` is machine-managed by `obsidian_agent_cli.py` — never edit by hand.
