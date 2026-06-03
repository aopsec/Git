#!/usr/bin/env bash
# HermesAgent bootstrap — RUN ON THE LOCAL RTX 4070 Ti (Arch) BOX, not in CI/cloud.
# Idempotent: safe to re-run. Needs sudo for pacman / CDI write / docker restart.
#
#   bash setup.sh            # full bootstrap (toolkit -> CDI -> build -> pull -> up)
#   bash setup.sh gpu        # just install nvidia-container-toolkit + generate CDI
#   bash setup.sh build      # just clone upstream + build hermes-agent:local
#
# See docs/HARDENING.md for the security rationale behind each step.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
UPSTREAM_DIR="${HERMES_UPSTREAM_DIR:-$HOME/plugins/hermes-agent}"
UPSTREAM_REPO="${HERMES_UPSTREAM_REPO:-https://github.com/nousresearch/hermes-agent.git}"
IMAGE_TAG="hermes-agent:local"
MODEL="${HERMES_MODEL:-hermes3:8b}"
CDI_FILE="/etc/cdi/nvidia.yaml"

log()  { printf '\033[1;34m[hermes]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[hermes]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[hermes]\033[0m %s\n' "$*" >&2; exit 1; }

need() { command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"; }

setup_gpu() {
    need pacman
    need docker
    log "Installing nvidia-container-toolkit (extra repo)..."
    sudo pacman -S --needed --noconfirm nvidia-container-toolkit
    need nvidia-ctk

    log "Generating CDI spec at ${CDI_FILE} (re-run after any driver update)..."
    sudo install -d -m 0755 "$(dirname "$CDI_FILE")"
    sudo nvidia-ctk cdi generate --output="$CDI_FILE"

    log "GPU smoke test inside a container (must list the RTX 4070 Ti)..."
    if ! docker run --rm --gpus all --entrypoint nvidia-smi ollama/ollama:latest; then
        warn "CDI path failed; trying the legacy runtime fallback."
        sudo nvidia-ctk runtime configure --runtime=docker
        sudo systemctl restart docker
        docker run --rm --gpus all --entrypoint nvidia-smi ollama/ollama:latest \
            || die "GPU not visible in containers — check driver + toolkit."
    fi
    log "GPU passthrough OK (--gpus all)."
    # docker-compose.yml requests the GPU via the CDI device name, NOT --gpus. Verify it
    # explicitly so a green smoke test actually predicts `docker compose up` behavior.
    log "Verifying CDI device 'nvidia.com/gpu=all' (used by docker-compose.yml)..."
    if docker run --rm --device nvidia.com/gpu=all --entrypoint nvidia-smi ollama/ollama:latest >/dev/null 2>&1; then
        log "CDI device OK."
    else
        warn "CDI device 'nvidia.com/gpu=all' not usable — check ${CDI_FILE}. Compose uses CDI, so ollama will not start until this resolves."
    fi
}

build_image() {
    need git
    need docker
    if [ ! -d "$UPSTREAM_DIR/.git" ]; then
        log "Cloning upstream Hermes Agent -> ${UPSTREAM_DIR} (not vendored in this repo)..."
        git clone --depth 1 "$UPSTREAM_REPO" "$UPSTREAM_DIR"
    else
        log "Updating upstream clone in ${UPSTREAM_DIR}..."
        git -C "$UPSTREAM_DIR" pull --ff-only || warn "upstream pull skipped (local changes?)"
    fi
    # The upstream Dockerfile requires BuildKit (COPY --chmod, advanced multi-stage);
    # the legacy builder fails with "the --chmod option requires BuildKit". BuildKit
    # needs the buildx plugin. A Docker-Desktop box may ship only a *dangling*
    # ~/.docker/cli-plugins/docker-buildx symlink — remove it and install a real one.
    if ! docker buildx version >/dev/null 2>&1; then
        die "docker buildx (BuildKit) not found — required to build the upstream image. Install: 'sudo pacman -S docker-buildx', or drop the buildx binary at ~/.docker/cli-plugins/docker-buildx."
    fi
    log "Building ${IMAGE_TAG} from the upstream Dockerfile (BuildKit/buildx)..."
    docker buildx build --load -t "$IMAGE_TAG" "$UPSTREAM_DIR"
}

pull_model() {
    need docker
    log "Starting ollama only, to pull the model..."
    docker compose -f "$HERE/docker-compose.yml" up -d ollama
    warn "Model pull needs egress. Temporarily UNCOMMENT the registry.ollama.ai lines"
    warn "in squid/squid-allowlist.conf — but the pull goes through the Docker daemon,"
    warn "not the gateway, so it works regardless. Re-comment them afterward."
    log "Pulling ${MODEL} (~5 GB, one time; cached in the ollama-models volume)..."
    docker exec hermes-ollama ollama pull "$MODEL"
    log "Verifying GPU offload (expect '100% GPU')..."
    docker exec hermes-ollama ollama ps || true
}

bring_up() {
    need docker
    log "Bringing up the full stack..."
    docker compose -f "$HERE/docker-compose.yml" up -d
    log "Stack up. Dashboard: http://127.0.0.1:${HERMES_DASHBOARD_PORT:-9119} (loopback only)."
    log "E2E check:  docker exec hermes hermes chat -q 'ping'"
}

case "${1:-all}" in
    gpu)   setup_gpu ;;
    build) build_image ;;
    pull)  pull_model ;;
    up)    bring_up ;;
    all)
        [ -f "$HERE/.env" ] || warn "No .env yet — copy .env.example to .env first."
        setup_gpu
        build_image
        pull_model
        bring_up
        ;;
    *) die "usage: $0 [all|gpu|build|pull|up]" ;;
esac
