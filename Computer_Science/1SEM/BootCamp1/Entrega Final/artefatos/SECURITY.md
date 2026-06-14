# Política de Segurança — PortfolioHUB

## Versões suportadas

A branch `main` é a versão suportada e publicada (GitHub Pages).

| Versão | Suportada |
| ------ | --------- |
| main   | ✅        |
| outras | ❌        |

## Como reportar uma vulnerabilidade

Reporte de forma **responsável e privada**:

1. Preferencialmente via **GitHub Security Advisories** — botão
   *"Report a vulnerability"* na aba **Security** do repositório; ou
2. Por e-mail privado ao mantenedor.

**Não** abra uma *issue* pública para falhas de segurança.

- Confirmação de recebimento: até **72 horas**.
- Correção coordenada antes de qualquer divulgação pública.

## Práticas de segurança adotadas

- Autenticação de dois fatores (2FA) obrigatória.
- Secret scanning + push protection.
- Dependabot (alertas e atualizações de segurança).
- Code scanning (CodeQL) nos Pull Requests.
- Proteção de branch (ruleset) em `main` com revisão obrigatória.
- Tokens de acesso *fine-grained* com expiração e menor privilégio.
- Revisão de Pull Requests assistida por IA (Google Gemini).
