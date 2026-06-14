# Artefatos de configuração — PortfolioHUB

Arquivos prontos para inclusão (commit) no repositório `aopsec/Git`, referenciados nos
Apêndices A–F da *Entrega Final*. Copie cada um para o caminho indicado.

```
.github/workflows/pages.yml            # Apêndice A — build + deploy (GitHub Pages)
.github/workflows/gemini-security.yml  # Apêndice F — revisão de segurança por IA (Gemini)
.github/dependabot.yml                 # Apêndice D — atualizações de dependências
.github/CODEOWNERS                     # Apêndice C — revisão obrigatória
SECURITY.md                            # Apêndice B — política de segurança
```

## Configurações feitas na interface gráfica do GitHub (não são arquivos)

- **2FA obrigatório:** Settings → Password and authentication.
- **Ruleset de `main`** (Apêndice E): Settings → Rules → Rulesets → New branch ruleset
  (PR obrigatório, revisão de Code Owner, status checks `build`/CodeQL, sem force-push,
  histórico linear, bloquear deleção).
- **Secret scanning + push protection, Dependabot, CodeQL:** Settings → Code security.
- **Tokens fine-grained:** Settings → Developer settings → Personal access tokens →
  Fine-grained tokens (escopo mínimo + expiração).
- **Enforce HTTPS / domínio:** Settings → Pages (verificar domínio antes do DNS).
- **Gemini Code Assist:** instalar o GitHub App `gemini-code-assist` no repositório.
