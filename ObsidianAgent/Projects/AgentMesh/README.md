# AgentMesh

---

*Um "porteiro" único e seguro para todos os seus agentes de IA — uma porta de entrada,
um cérebro local na placa de vídeo, e ferramentas compartilhadas.*

---

## O que é o AgentMesh?

Você tinha vários assistentes de IA cada um por conta própria (OpenHands, OpenCode, Cline,
Claude, Copilot, e o HermesAgent). O **AgentMesh** une todos eles num **mesh** (uma malha):

1. **Um único porteiro de IA (gateway).** Em vez de cada agente falar com um modelo
   diferente, todos falam com **um endereço só** (`http://127.0.0.1:4000`). Esse porteiro
   (LiteLLM) decide qual "cérebro" responde — rodando **localmente na sua RTX 4070 Ti**
   (modelos `hermes3` e `qwen2.5-coder` via Ollama). Sem nuvem por padrão.

2. **Ferramentas compartilhadas (MCP).** Todos os agentes enxergam o mesmo conjunto de
   ferramentas: arquivos do projeto, git, e o **vault do Obsidian** (memória comum). E há
   ferramentas que deixam um agente **chamar outro agente** (ex.: o Claude planeja e manda
   o Hermes ou o OpenCode executar).

3. **Planejadores e executores.** **Claude e Copilot planejam**; **Hermes, OpenCode e
   OpenHands executam**. A "cola" entre eles é o **MCP**.

4. **Acesso remoto seguro (multiusuário).** Pelo **Tailscale** (uma rede privada
   criptografada), você usa o mesh de outro computador, e cada usuário tem sua **chave
   própria com orçamento** (virtual key) — ninguém compartilha a chave-mestra.

## Como está montado (resumo)

| Camada | O que roda | Onde |
|---|---|---|
| Porteiro (LLM) | LiteLLM + Postgres + Ollama (GPU) | `gateway/` — `127.0.0.1:4000` |
| Ferramentas | MCP: `fs-mesh`, `git-mesh`, `vault-mesh`, `exec-mesh` | `mcp/` |
| Acesso remoto | Tailscale (overlay privado) + chaves por usuário | `docs/RUNBOOK.md` |

> **Privacidade:** por padrão tudo é **local** — suas perguntas e arquivos não saem do seu
> computador. Nuvem é opt-in (e passa por uma lista de permissão). Detalhes de segurança em
> [`docs/HARDENING.md`](docs/HARDENING.md).

## Como usar (rápido)

```bash
# Subir o porteiro (uma vez):
cd gateway && cp .env.example .env   # defina LITELLM_MASTER_KEY + POSTGRES_PASSWORD
docker compose up -d
docker exec mesh-ollama ollama pull hermes3:8b
docker exec mesh-ollama ollama pull qwen2.5-coder:7b

# Usar (qualquer agente já apontado para o porteiro). Teste direto:
curl http://127.0.0.1:4000/v1/models -H "Authorization: Bearer <sua-chave>"
```

**Guia do usuário completo** (passo a passo, do zero ao uso de cada agente, com
solução de problemas; em inglês): **[`docs/USER_GUIDE.md`](docs/USER_GUIDE.md)**.
Cheat-sheet de operação: **[`docs/RUNBOOK.md`](docs/RUNBOOK.md)**.
Arquitetura: **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)**.

## Segurança em uma frase

A IA pensa na sua placa de vídeo, as ferramentas são compartilhadas via MCP, o acesso de fora
é só pela rede privada Tailscale, e cada usuário tem chave com orçamento — a chave-mestra
nunca sai do servidor.
