# Guia corrigido para integrar agentes IA locais no Arch + LM Studio

**Ambiente alvo:** Arch Linux + Hyprland + LM Studio + i9 + 64 GB RAM + RTX 4070 Ti 12 GB.  
**Objetivo:** agentes locais para código, automação, análise documental e RAG, com chamadas cloud desativadas por padrão.

Este documento corrige os pontos auditados:

- substitui citações quebradas por referências verificáveis;
- corrige MCP do OpenHands para `config.toml`;
- remove tags flutuantes e execução automática via npx sem pinning;
- ajusta Letta Docker com `--add-host` e `OPENAI_API_KEY`;
- reduz o contexto inicial para 32K/64K;
- corrige OpenCode para o schema oficial;
- adiciona hardening de filesystem, Docker e MCP.

## 0. Modelo operacional recomendado

Use esta hierarquia:

| Camada | Ferramenta | Uso |
|---|---|---|
| Runtime LLM | LM Studio | API local OpenAI-compatible |
| Agente principal | OpenHands | tarefas autônomas |
| Editor | Cline | VS Code / Cursor-like workflow |
| Fallback | Aider | edição via diff no terminal |
| Terminal opcional | OpenCode | TUI local |
| Memória opcional | Letta | memória persistente |
| RAG opcional | Qdrant MCP | busca semântica local |

LM Studio 0.4.x é adequado porque inclui daemon/headless, requisições paralelas e API com suporte a MCP local.[^lmstudio040] O LM Studio também atua como host MCP desde 0.3.17 e usa `~/.lmstudio/mcp.json` para registrar servidores.[^lmstudio_mcp]

## 1. Preparação do sistema

### 1.1 Pacotes base

```bash
sudo pacman -Syu
sudo pacman -S --needed \
  base-devel git curl jq ripgrep fd \
  docker docker-compose \
  nodejs npm \
  uv python-pip

sudo systemctl enable --now docker
```

Opcional, para usar Docker sem `sudo`:

```bash
sudo usermod -aG docker "$USER"
newgrp docker
```

**Nota de segurança:** adicionar o usuário ao grupo `docker` concede poder equivalente a root. Se o host for sensível, prefira `sudo docker ...` e não adicione o usuário ao grupo.

### 1.2 AUR

```bash
yay -S lmstudio-bin aider-chat
```

Se usa `paru`:

```bash
paru -S lmstudio-bin aider-chat
```

### 1.3 Wayland / Hyprland

Crie um wrapper para iniciar o LM Studio com Ozone/Wayland:

```bash
mkdir -p ~/.local/bin
cat > ~/.local/bin/lmstudio-wayland <<'EOF_LMS'
#!/usr/bin/env bash
set -euo pipefail
export ELECTRON_OZONE_PLATFORM_HINT=wayland
exec lm-studio --enable-features=UseOzonePlatform --ozone-platform=wayland "$@"
EOF_LMS
chmod +x ~/.local/bin/lmstudio-wayland
```

Execute:

```bash
lmstudio-wayland
```

## 2. LM Studio: modelo, servidor e validação

### 2.1 Modelo inicial para sua RTX 4070 Ti

Comece com:

```text
Modelo: qwen/qwen3-coder-30b-a3b-instruct
Quantização: UD-Q4_K_XL ou Q4_K_M
Contexto inicial: 32768
Contexto estável: 65536
Contexto experimental: 131072+
Flash Attention: ON
KV Cache Quantization: OFF para tool-calling
Temperatura para agentes: 0.0–0.3
```

A recomendação de Qwen3-Coder-30B-A3B com quantização 4-bit é coerente com a documentação do Unsloth, que mostra execução local do modelo e recomenda memória suficiente para a quantização dinâmica.[^unsloth_qwen] Em uma RTX 4070 Ti 12 GB, **não comece em 262K**. Use 32K primeiro, suba para 64K após validar estabilidade e só teste 128K+ quando o workload exigir.

### 2.2 Iniciar o servidor local

Via UI:

1. Abra LM Studio.
2. Carregue o modelo.
3. Ative o servidor local em **Developer / Server**.
4. Porta padrão: `1234`.

Via CLI, quando disponível:

```bash
lms status
lms server start --port 1234
```

Valide:

```bash
curl -s http://localhost:1234/v1/models | jq .
```

Teste uma chamada OpenAI-compatible:

```bash
curl -s http://localhost:1234/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen/qwen3-coder-30b-a3b-instruct",
    "messages": [{"role": "user", "content": "Responda apenas: OK"}],
    "temperature": 0.1
  }' | jq .
```

## 3. MCP com pinning e sem tags flutuantes

### 3.1 Regra de segurança

Não use MCP configurado para baixar pacote em tempo de execução, aceitar instalação automaticamente e apontar para uma versão flutuante.

Problemas:

- baixa código em tempo de execução;
- aceita versões novas sem revisão;
- dificulta auditoria;
- executa processos MCP com acesso a filesystem/rede;
- amplia o risco de supply chain.

A própria documentação do LM Studio alerta que servidores MCP podem executar código, acessar arquivos locais e usar rede; instale apenas servidores confiáveis.[^lmstudio_mcp]

### 3.2 Diretório isolado para MCPs Node

Crie um prefixo separado:

```bash
export MCP_NODE_ROOT="$HOME/.local/share/mcp-node"
mkdir -p "$MCP_NODE_ROOT"
cd "$MCP_NODE_ROOT"
```

Crie `package.json` com versões **fixas**. Substitua as versões pelo resultado revisado de `npm view <pacote> version` no dia da instalação:

```bash
cat > package.json <<'EOF_JSON'
{
  "private": true,
  "type": "module",
  "dependencies": {
    "@modelcontextprotocol/server-filesystem": "SUBSTITUA_POR_VERSAO_FIXADA",
    "@modelcontextprotocol/server-memory": "SUBSTITUA_POR_VERSAO_FIXADA",
    "@upstash/context7-mcp": "SUBSTITUA_POR_VERSAO_FIXADA",
    "@playwright/mcp": "SUBSTITUA_POR_VERSAO_FIXADA"
  }
}
EOF_JSON
```

Descubra versões e edite o arquivo:

```bash
npm view @modelcontextprotocol/server-filesystem version
npm view @modelcontextprotocol/server-memory version
npm view @upstash/context7-mcp version
npm view @playwright/mcp version
nvim package.json
```

Instale e gere lockfile:

```bash
npm install --ignore-scripts
npm audit --omit=dev
```

Liste os binários instalados:

```bash
ls -la "$MCP_NODE_ROOT/node_modules/.bin"
```

### 3.3 Diretório isolado para MCPs Python

Use `uv tool install` com versões fixas:

```bash
uv tool install 'mcp-server-git==SUBSTITUA_POR_VERSAO_FIXADA'
uv tool install 'mcp-server-qdrant==SUBSTITUA_POR_VERSAO_FIXADA'
```

Para descobrir a versão disponível antes de fixar:

```bash
uvx pip index versions mcp-server-git
uvx pip index versions mcp-server-qdrant
```

### 3.4 Allowlist de filesystem

Não exponha `/`, `/home/aops`, `~/.ssh`, `~/.gnupg`, `~/Downloads` ou diretórios com secrets.

Crie uma raiz segura:

```bash
mkdir -p ~/projects ~/ai-workspace ~/ai-docs
chmod 700 ~/projects ~/ai-workspace ~/ai-docs
```

Use apenas esses diretórios nos MCPs.

### 3.5 `~/.lmstudio/mcp.json` corrigido

Ajuste os nomes dos binários se `node_modules/.bin` mostrar nomes diferentes.

```json
{
  "mcpServers": {
    "filesystem-projects": {
      "command": "npm",
      "args": [
        "--prefix", "/home/aops/.local/share/mcp-node",
        "exec", "--offline", "--",
        "mcp-server-filesystem",
        "/home/aops/projects",
        "/home/aops/ai-workspace",
        "/home/aops/ai-docs"
      ]
    },
    "memory-local": {
      "command": "npm",
      "args": [
        "--prefix", "/home/aops/.local/share/mcp-node",
        "exec", "--offline", "--",
        "mcp-server-memory"
      ]
    },
    "context7-docs": {
      "command": "npm",
      "args": [
        "--prefix", "/home/aops/.local/share/mcp-node",
        "exec", "--offline", "--",
        "context7-mcp"
      ]
    },
    "playwright-headless": {
      "command": "npm",
      "args": [
        "--prefix", "/home/aops/.local/share/mcp-node",
        "exec", "--offline", "--",
        "mcp-server-playwright",
        "--headless"
      ]
    },
    "git-current-repo": {
      "command": "mcp-server-git",
      "args": ["--repository", "/home/aops/projects/meurepo"]
    }
  }
}
```

Se algum binário não existir, rode:

```bash
find "$MCP_NODE_ROOT/node_modules/.bin" -maxdepth 1 -type f -printf '%f\n'
npm --prefix "$MCP_NODE_ROOT" exec --offline -- <BINARIO_CORRETO> --help
```

Depois reinicie o LM Studio.

## 4. OpenHands com `config.toml`

OpenHands documenta MCP no `config.template.toml` com seção `[mcp]` e listas `sse_servers`, `shttp_servers` e `stdio_servers`; para stdio, o formato esperado é TOML, não um `mcp.json` estilo Cursor.[^openhands_config]

### 4.1 Rodar OpenHands

Use bind local e evite publicar a interface em todas as interfaces de rede:

```bash
docker run -it --rm \
  --name openhands \
  --pull=always \
  --add-host host.docker.internal:host-gateway \
  --security-opt no-new-privileges:true \
  -v "$HOME/.openhands:/home/openhands/.openhands" \
  -p 127.0.0.1:3000:3000 \
  ghcr.io/all-hands-ai/openhands:1.6.0 serve
```

**Não use** `--privileged`.  
**Não monte** `/` ou `$HOME` inteiro.  
**Não exponha** `3000` em `0.0.0.0` sem proxy autenticado.

### 4.2 Configurar LLM no OpenHands

No UI:

```text
Provider/model: lm_studio/qwen/qwen3-coder-30b-a3b-instruct
Base URL: http://host.docker.internal:1234/v1
API Key: dummy-api-key
Temperature: 0.1
Context: 32768 primeiro; 65536 depois de validar
```

O provider `lm_studio/` é suportado via LiteLLM para LM Studio.[^litellm_lmstudio]

### 4.3 `~/.openhands/config.toml` corrigido

Crie ou edite:

```bash
mkdir -p ~/.openhands
nvim ~/.openhands/config.toml
```

Conteúdo base:

```toml
[llm]
model = "lm_studio/qwen/qwen3-coder-30b-a3b-instruct"
base_url = "http://host.docker.internal:1234/v1"
api_key = "dummy-api-key"
temperature = 0.1
max_input_tokens = 32768

[security]
confirmation_mode = true
enable_security_analyzer = true

[sandbox]
volumes = "/home/aops/projects:/workspace/projects:rw,/home/aops/ai-docs:/workspace/ai-docs:ro"
use_host_network = false
privileged = false

[mcp]
stdio_servers = [
  { name = "filesystem-projects", command = "npm", args = ["--prefix", "/home/aops/.local/share/mcp-node", "exec", "--offline", "--", "mcp-server-filesystem", "/home/aops/projects", "/home/aops/ai-workspace", "/home/aops/ai-docs"] },
  { name = "memory-local", command = "npm", args = ["--prefix", "/home/aops/.local/share/mcp-node", "exec", "--offline", "--", "mcp-server-memory"] },
  { name = "context7-docs", command = "npm", args = ["--prefix", "/home/aops/.local/share/mcp-node", "exec", "--offline", "--", "context7-mcp"] },
  { name = "git-current-repo", command = "mcp-server-git", args = ["--repository", "/home/aops/projects/meurepo"] }
]
```

Ajuste `/home/aops/projects/meurepo` para o repositório real.

### 4.4 Validação

```bash
curl -s http://localhost:1234/v1/models | jq .
```

Abra:

```text
http://127.0.0.1:3000
```

Teste com uma tarefa pequena:

```text
Liste os arquivos do repositório montado e explique a estrutura sem editar nada.
```

Só depois permita escrita.

## 5. Aider com LM Studio

Aider documenta LM Studio usando `LM_STUDIO_API_KEY`, `LM_STUDIO_API_BASE` e modelo no formato `lm_studio/<model-name>`.[^aider_lmstudio]

```bash
cd /home/aops/projects/meurepo

export LM_STUDIO_API_KEY='dummy-api-key'
export LM_STUDIO_API_BASE='http://localhost:1234/v1'

aider --model lm_studio/qwen/qwen3-coder-30b-a3b-instruct
```

Modo mais seguro para primeira execução:

```bash
aider \
  --model lm_studio/qwen/qwen3-coder-30b-a3b-instruct \
  --read . \
  --no-auto-commits
```

Depois de validar comportamento:

```bash
aider \
  --model lm_studio/qwen/qwen3-coder-30b-a3b-instruct \
  --auto-commits
```

## 6. Cline com LM Studio

A documentação do Cline recomenda o provedor LM Studio, Compact Prompt para reduzir o prompt em cerca de 90%, e KV Cache Quantization OFF para evitar confusão/erros em modelos locais.[^cline_lmstudio][^cline_overview]

Configuração inicial:

```text
Provider: LM Studio
Base URL: http://localhost:1234
Model: qwen/qwen3-coder-30b-a3b-instruct
Use Compact Prompt: ON
Context no LM Studio: 32768 primeiro; 65536 após validar
KV Cache Quantization: OFF
Flash Attention: ON
Temperature: 0.0–0.3
```

Correção importante: **não assuma que Compact Prompt desativa MCP na sua versão**. Trate assim:

- se precisa de estabilidade máxima local: Compact Prompt ON;
- se algum MCP não aparecer ou falhar: teste Compact Prompt OFF apenas para essa tarefa;
- mantenha poucos MCPs habilitados por sessão.

## 7. OpenCode com schema oficial

OpenCode usa config global em `~/.config/opencode/opencode.json`.[^opencode_config] O provider LM Studio é definido com `npm`, `name`, `options.baseURL` e `models`.[^opencode_lmstudio]

Instalação:

```bash
npm install -g opencode-ai
```

Config:

```bash
mkdir -p ~/.config/opencode
nvim ~/.config/opencode/opencode.json
```

Conteúdo:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "lmstudio/qwen/qwen3-coder-30b-a3b-instruct",
  "provider": {
    "lmstudio": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "LM Studio (local)",
      "options": {
        "baseURL": "http://127.0.0.1:1234/v1",
        "apiKey": "dummy-api-key"
      },
      "models": {
        "qwen/qwen3-coder-30b-a3b-instruct": {
          "name": "Qwen3 Coder 30B A3B (LM Studio)",
          "limit": {
            "context": 32768,
            "output": 8192
          }
        }
      }
    }
  },
  "permission": {
    "bash": "ask",
    "edit": "ask",
    "webfetch": "ask"
  }
}
```

Valide:

```bash
opencode --version
opencode
```

Dentro do TUI:

```text
/models
```

Selecione:

```text
lmstudio/qwen/qwen3-coder-30b-a3b-instruct
```

## 8. Letta com Docker corrigido

Letta expõe a API na porta `8283` e recomenda volume persistente para o PostgreSQL embutido.[^letta_docker]

Em Linux, adicione `--add-host host.docker.internal:host-gateway` para permitir que o contêiner alcance o LM Studio no host.

```bash
docker run -d \
  --name letta \
  --restart unless-stopped \
  --add-host host.docker.internal:host-gateway \
  --security-opt no-new-privileges:true \
  -p 127.0.0.1:8283:8283 \
  -v "$HOME/.letta/.persist/pgdata:/var/lib/postgresql/data" \
  -e OPENAI_API_BASE="http://host.docker.internal:1234/v1" \
  -e OPENAI_API_KEY="dummy-api-key" \
  letta/letta:SUBSTITUA_POR_TAG_FIXADA
```

Valide:

```bash
curl -s http://127.0.0.1:8283/v1 | jq . || true
docker logs --tail=100 letta
```

## 9. Qdrant MCP para RAG local opcional

O MCP oficial da Qdrant fornece uma camada de memória semântica sobre o banco vetorial Qdrant.[^qdrant_mcp]

### 9.1 Iniciar Qdrant

```bash
docker run -d \
  --name qdrant \
  --restart unless-stopped \
  --security-opt no-new-privileges:true \
  -p 127.0.0.1:6333:6333 \
  -v qdrant_storage:/qdrant/storage \
  qdrant/qdrant
```

### 9.2 MCP Qdrant

Instale com versão fixada:

```bash
uv tool install 'mcp-server-qdrant==SUBSTITUA_POR_VERSAO_FIXADA'
```

Exemplo para `~/.lmstudio/mcp.json`:

```json
{
  "mcpServers": {
    "qdrant-docs": {
      "command": "mcp-server-qdrant",
      "args": [],
      "env": {
        "QDRANT_URL": "http://127.0.0.1:6333",
        "COLLECTION_NAME": "docs",
        "EMBEDDING_PROVIDER": "fastembed",
        "EMBEDDING_MODEL": "sentence-transformers/all-MiniLM-L6-v2"
      }
    }
  }
}
```

Se usar outro embedding provider, ajuste as variáveis conforme a documentação do servidor MCP da Qdrant.

## 10. Hardening obrigatório

### 10.1 Filesystem

Use allowlist estrita:

```text
Permitido:
/home/aops/projects
/home/aops/ai-workspace
/home/aops/ai-docs

Proibido:
/
/home/aops
/home/aops/.ssh
/home/aops/.gnupg
/home/aops/.config
/home/aops/Downloads
/home/aops/.password-store
```

Crie `.gitignore` global para segredos:

```bash
git config --global core.excludesfile ~/.gitignore_global
cat >> ~/.gitignore_global <<'EOF_GITIGNORE'
.env
.env.*
*.pem
*.key
id_rsa
id_ed25519
secrets.*
credentials.*
EOF_GITIGNORE
```

Antes de entregar um repositório a um agente:

```bash
cd /home/aops/projects/meurepo
git status --short
git secrets --scan 2>/dev/null || true
rg -n "(API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY)" . || true
```

### 10.2 Docker

Evite:

```bash
--privileged
--network host
-v /:/host
-v $HOME:/home/aops
-p 0.0.0.0:PORT:PORT
```

Prefira:

```bash
--security-opt no-new-privileges:true
-p 127.0.0.1:PORT:PORT
-v /caminho/permitido:/workspace:rw
-v /docs/permitidos:/docs:ro
```

Para serviços persistentes, use nomes e restart policy:

```bash
--name nome-do-servico
--restart unless-stopped
```

### 10.3 MCP

Checklist:

```text
[ ] Versões fixadas
[ ] Sem tags flutuantes em MCP
[ ] Sem execução automática via npx direto no mcp.json
[ ] Sem acesso a / ou $HOME inteiro
[ ] Sem tokens em texto claro quando possível
[ ] Confirmação manual ativa para ferramentas destrutivas
[ ] MCPs desnecessários desativados
[ ] Um servidor MCP por finalidade
[ ] Logs revisados após primeira execução
```

Audite os MCPs instalados:

```bash
cd ~/.local/share/mcp-node
npm audit --omit=dev
npm outdated || true

uv tool list
```

Desative MCPs não usados removendo-os de:

```text
~/.lmstudio/mcp.json
~/.openhands/config.toml
~/.config/opencode/opencode.json
Cline Settings → MCP
```

## 11. Ordem correta de execução

### Etapa A — validar LM Studio

```bash
lmstudio-wayland
lms server start --port 1234
curl -s http://localhost:1234/v1/models | jq .
```

### Etapa B — validar modelo com prompt simples

```bash
curl -s http://localhost:1234/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen/qwen3-coder-30b-a3b-instruct",
    "messages": [{"role":"user","content":"Responda só OK"}],
    "temperature": 0.1
  }' | jq -r '.choices[0].message.content'
```

### Etapa C — validar Aider

```bash
cd ~/projects/meurepo
export LM_STUDIO_API_KEY=dummy-api-key
export LM_STUDIO_API_BASE=http://localhost:1234/v1
aider --model lm_studio/qwen/qwen3-coder-30b-a3b-instruct --read . --no-auto-commits
```

### Etapa D — validar Cline

```text
Provider: LM Studio
Base URL: http://localhost:1234
Compact Prompt: ON
Context: 32768
```

Peça apenas leitura inicialmente:

```text
Analise a estrutura do projeto sem modificar arquivos.
```

### Etapa E — validar OpenHands

```bash
docker run -it --rm \
  --name openhands \
  --pull=always \
  --add-host host.docker.internal:host-gateway \
  --security-opt no-new-privileges:true \
  -v "$HOME/.openhands:/home/openhands/.openhands" \
  -p 127.0.0.1:3000:3000 \
  ghcr.io/all-hands-ai/openhands:1.6.0 serve
```

Abra:

```text
http://127.0.0.1:3000
```

### Etapa F — habilitar MCP gradualmente

Ordem recomendada:

1. `filesystem-projects` somente leitura ou diretório controlado;
2. `git-current-repo` apenas no repositório alvo;
3. `context7-docs`;
4. `playwright-headless`;
5. `qdrant-docs`;
6. `memory-local`.

## 12. Troubleshooting rápido

### LM Studio não responde

```bash
lms status
curl -v http://localhost:1234/v1/models
```

Se o modelo não aparece, carregue no UI ou via CLI:

```bash
lms ls
lms load <modelo-exato>
```

### OpenHands não alcança LM Studio

Dentro de Docker, não use `localhost` para o host. Use:

```text
http://host.docker.internal:1234/v1
```

E rode o container com:

```bash
--add-host host.docker.internal:host-gateway
```

### Cline gera tool calls quebradas

Ajuste:

```text
Temperature: 0.0–0.2
KV Cache Quantization: OFF
Compact Prompt: ON
Context: 32768
MCPs ativos: mínimo necessário
```

### MCP não inicia

```bash
cat ~/.lmstudio/mcp.json | jq .
cd ~/.local/share/mcp-node
npm audit --omit=dev
npm --prefix ~/.local/share/mcp-node exec --offline -- <binario> --help
```

### Aider reclama de API key

Defina mesmo que seja dummy:

```bash
export LM_STUDIO_API_KEY=dummy-api-key
export LM_STUDIO_API_BASE=http://localhost:1234/v1
```

## 13. Referências verificáveis

[^lmstudio040]: LM Studio 0.4.0 changelog: https://lmstudio.ai/changelog/lmstudio-v0.4.0
[^lmstudio_mcp]: LM Studio MCP docs: https://lmstudio.ai/docs/app/mcp
[^unsloth_qwen]: Unsloth Qwen3-Coder local guide: https://unsloth.ai/docs/models/tutorials/qwen3-coder-how-to-run-locally
[^openhands_config]: OpenHands `config.template.toml`: https://github.com/OpenHands/OpenHands/blob/main/config.template.toml
[^litellm_lmstudio]: LiteLLM LM Studio provider: https://docs.litellm.ai/docs/providers/lm_studio
[^aider_lmstudio]: Aider LM Studio docs: https://aider.chat/docs/llms/lm-studio.html
[^cline_lmstudio]: Cline LM Studio docs: https://docs.cline.bot/running-models-locally/lm-studio
[^cline_overview]: Cline local models overview: https://docs.cline.bot/running-models-locally/overview
[^opencode_config]: OpenCode config docs: https://opencode.ai/docs/config/
[^opencode_lmstudio]: OpenCode providers / LM Studio: https://opencode.ai/docs/providers/
[^letta_docker]: Letta Docker image docs: https://hub.docker.com/r/letta/letta
[^qdrant_mcp]: Qdrant MCP server: https://github.com/qdrant/mcp-server-qdrant
