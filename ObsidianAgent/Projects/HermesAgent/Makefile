# HermesAgent — convenience targets. Run on the local RTX 4070 Ti box.
# Most targets need Docker; `setup`/`gpu-check` need sudo (pacman / CDI / docker).

COMPOSE := docker compose -f docker-compose.yml

.PHONY: help setup gpu-check build pull-model up down logs verify

help:
	@echo "HermesAgent targets:"
	@echo "  make setup       # nvidia-container-toolkit + CDI + build + pull + up"
	@echo "  make gpu-check   # verify GPU is visible inside a container"
	@echo "  make build       # clone upstream + build hermes-agent:local"
	@echo "  make pull-model  # pull hermes3:8b into the ollama volume (one time)"
	@echo "  make up          # docker compose up -d (full stack)"
	@echo "  make down        # docker compose down"
	@echo "  make logs        # follow gateway logs"
	@echo "  make verify      # static checks (compose config, shell parse)"

setup:
	bash setup.sh all

gpu-check:
	docker run --rm --gpus all --entrypoint nvidia-smi ollama/ollama:latest

build:
	bash setup.sh build

pull-model:
	bash setup.sh pull

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f gateway

verify:
	bash -n setup.sh
	$(COMPOSE) config >/dev/null && echo "compose config OK"
	@command -v shellcheck >/dev/null 2>&1 && shellcheck -S warning setup.sh || echo "shellcheck not installed (skipped)"
