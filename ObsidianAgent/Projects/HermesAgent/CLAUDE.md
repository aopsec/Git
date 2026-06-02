# HermesAgent — Engineering Guide

Hardened, GPU-local deployment of the Nous Research **Hermes Agent**
(`github.com/nousresearch/hermes-agent`) attached to the ObsidianAgent meta-vault.
Scope here is engineering/ops; product framing lives in `README.md` (pt-br), and the
security rationale in `docs/HARDENING.md`. Additive to — not overlapping with — the
meta-vault contract in the root `CLAUDE.md`.

## Stack
- **Hermes Agent** — built locally as `hermes-agent:local` from the upstream Dockerfile
  (Debian + s6-overlay PID 1 `/init`, non-root `hermes` user UID 10000). NOT vendored:
  cloned to `$HOME/plugins/hermes-agent`.
- **Ollama** — serves `hermes3:8b` on the **RTX 4070 Ti** via CDI GPU passthrough.
- **Squid** (`ubuntu/squid`) — egress allowlist proxy.
- **Docker Compose** — 4 services, 2 networks (`internal` no-route + `egress`).

## Architecture / security model
- Posture = Hermes' own *"safest architecture"*: whole-process Docker wrapping
  (`SECURITY.md`) + the documented `internal`/`egress` split with a Squid allowlist
  (`docs/security/network-egress-isolation.md`).
- **Inference is air-gapped**: `ollama` is on `internal` only; prompts never leave the host.
- `gateway` is dual-homed; all outbound HTTP(S) is forced through Squid (`HTTP_PROXY`),
  which denies everything not in `squid/squid-allowlist.conf`.
- `dashboard` is internal-only, published to host **127.0.0.1** only.

## Key Security Rules
1. **Never** restore upstream's `network_mode: host` — it defeats the egress split.
2. **Never** use the `docker` terminal backend or mount `docker.sock` — host-escape risk.
   The whole-process wrap is the only boundary; keep `terminal.backend: local`.
3. Squid default is **deny-all**; add hosts to the allowlist only when a tool needs them,
   narrowest domain first. Re-comment `registry.ollama.ai` after the one-time model pull.
4. Keep `Vault/Generated/` mounted **read-only** (preserves meta-vault determinism).
5. The dashboard runs as the gateway container's OWN s6 service (`HERMES_DASHBOARD=1`),
   NOT a separate container — a second container sharing `/opt/data` fights the s6-log
   lock and crash-loops. It binds `0.0.0.0` *inside* the container with
   `HERMES_DASHBOARD_INSECURE=1` (no OAuth `DashboardAuthProvider` is configured, so
   Hermes fails closed on non-loopback binds); the published port is pinned to host
   `127.0.0.1` only — that loopback-only publish is the compensating control. Never
   publish it on `0.0.0.0` at the host level.

## Commands
```bash
make setup        # nvidia-container-toolkit + CDI + build + pull-model + up (sudo; local box)
make gpu-check    # docker run --rm --gpus all ollama/ollama nvidia-smi
make build        # clone upstream + build hermes-agent:local
make pull-model   # ollama pull hermes3:8b (one time)
make up / down    # start / stop the stack
make verify       # bash -n setup.sh + docker compose config + shellcheck (if present)
```
E2E: `docker exec hermes hermes chat -q "ping"` returns a local-model reply while
`nvidia-smi` shows the `ollama` process using VRAM.

## Gotchas
- `make setup`/`gpu-check` only run on the local Arch box with the GPU; they cannot run
  in the cloud/CI container (no GPU, no `pacman`, no docker daemon).
- **BuildKit/buildx is required** to build the upstream image (its Dockerfile uses
  `COPY --chmod`); the legacy builder fails with *"the --chmod option requires BuildKit"*.
  Install `docker-buildx` (`sudo pacman -S docker-buildx`) or drop the buildx binary into
  `~/.docker/cli-plugins/docker-buildx`. A Docker-Desktop box can leave a **dangling**
  `~/.docker/cli-plugins/docker-buildx` symlink → remove it first. `setup.sh build` hard-
  checks `docker buildx version` and builds via `docker buildx build --load`.
- **Config path (verified on the built image):** `HERMES_HOME=/opt/data`, and Hermes loads
  `{HERMES_HOME}/config.yaml` first, then the project fallback `/opt/hermes/cli-config.yaml`
  — **never** `/opt/data/cli-config.yaml`. So compose mounts our `cli-config.yaml` →
  `/opt/data/config.yaml:ro` (proven: `hermes config show` reflects model + `terminal.cwd`).
  Safe RO: stage2-hook seeds `config.yaml` only when absent and chmod/chowns best-effort.
- **Editing `cli-config.yaml` needs a recreate, not just a save** — it's a *single-file*
  bind mount, so the running container binds the file's inode at creation and an in-place
  rewrite (new inode) leaves it reading the OLD config. After any edit:
  `docker compose up -d --force-recreate gateway` (verified via the `worktree` fix).
- `worktree: false` in `cli-config.yaml` is load-bearing: `/workspace` (the Vault) is not a
  git checkout, and `worktree: true` hard-fails `hermes chat` with "requires being inside a
  git repository".
- Dashboard flags confirmed on the image: `--host` / `--port` (default **9119**) / `--no-open`
  are valid; `HERMES_DASHBOARD_PORT=9119` is correct.
- The smoke test checks **both** `--gpus all` (runtime) and the CDI device
  `nvidia.com/gpu=all` (what compose actually uses). Regenerate `/etc/cdi/nvidia.yaml`
  (`setup.sh gpu`) after any driver update.

## Commit Prefix
`projects/hermes_agent:`
