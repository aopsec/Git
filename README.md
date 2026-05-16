# H 3 L L 0    W O 4 L D !

[GitHub Pages](https://aopsec.github.io/Git/) · [LinkedIn](https://www.linkedin.com/in/aops/) · [Currículo Completo](CV-AOPS.html) · [aops@outlook.com.br](mailto:aops@outlook.com.br)

Repositório público de **Alcides Olivo Pollazzon Soterio**, estudante de Bacharelado em Ciência da Computação no UniCEUB (Brasília, DF). Reúne projetos acadêmicos, ferramentas de segurança, exercícios de programação e automações pessoais, organizados com boas práticas de versionamento Git e documentação.

**Objetivo:** atuar em operações ofensivas — Red Team / Red Ops.

---

## GitHub Pages

O portfólio completo — com currículo, projetos, certificações e habilidades — está publicado em:

**[https://aopsec.github.io/Git/](https://aopsec.github.io/Git/)**

Desenvolvido com Jekyll (tema Hacker) via GitHub Pages a partir deste repositório.

---

## Repo DIR:

```
aopsec/Git
├── BootCamp1/
│   └── Projeto_Intermediario/        # Entrega Intermediária — Git + GitHub Pages (PDF)
├── CV-AOPS.html                      # Currículo completo (HTML com print-CSS)
├── FreeCodeCamp/
│   └── PinExtractor.py               # Utilitário de extração de coordenadas geográficas
├── IC01-aops/                        # Disciplina Introdução à Computação — UniCEUB
│   ├── ADV7ia/                       # Stack local de IA (LM Studio + OpenHands + Aider)
│   └── AVAL01-IC/                    # AV01 — Análise de segurança em IoT (MXQ Pro 4k)
├── JustVibing/
│   └── Snippets/                     # BugBounty recon toolkit JS v1.0.3 (score 95/100)
├── KALInit/                          # Scripts de provisionamento Kali / Arch Linux
├── Logica_Programacao_I/             # Exercícios Python — 9 módulos, 40+ arquivos
│   ├── Aula29.04/  06.05/
│   └── PPI/ PPII/ PPIII/ PPIV/ PPV/ PPVI/ Revisao_Prova01/
├── ObsidianAgent/                    # Meta-vault orquestrador de notas Obsidian
│   └── Projects/
│       ├── bbWebScan/                # Orquestrador Python de recon bug bounty v0.5.3
│       ├── IPS_IDS/                  # ADV7Sec — runtime IDS/IPS (auditd, Falco, Suricata, Zeek)
│       └── OpenBox0.1v/             # Appliance Linux hardened (nftables, WireGuard, Tor, DNSCrypt)
├── Revisao_Prova01/                  # 6 exercícios Python para revisão de prova
├── wordlists/                        # SecLists submodule + wordlists customizadas
│   ├── bbWebScan/
│   ├── blackarch/
│   └── kali/
├── _config.yml                       # Jekyll — GitHub Pages (tema Hacker)
└── index.md                          # Portfólio principal (GitHub Pages)
```

### Diretórios por categoria

| Diretório | Tipo | Descrição |
| --- | --- | --- |
| `BootCamp1/` | Acadêmico | Entrega Intermediária — Criação de Repositório com Versionamento (Git + GitHub Pages) |
| `FreeCodeCamp/` | Acadêmico | PinExtractor.py — utilitário de extração de coordenadas geográficas |
| `IC01-aops/` | Acadêmico | Projetos da disciplina Introdução à Computação (UniCEUB): ADV7ia e AVAL01-IC |
| `JustVibing/` | Pesquisa | Snippets de reconhecimento bug bounty — scanner client-side JS v1.0.3 |
| `KALInit/` | Utilitário | Scripts de inicialização para ambientes Kali / Arch Linux |
| `Logica_Programacao_I/` | Acadêmico | Exercícios de Lógica e Programação I — Python, 40+ arquivos em 9 módulos |
| `ObsidianAgent/` | Ferramenta/Segurança | Meta-vault Obsidian + projetos de segurança: bbWebScan, IPS_IDS, OpenBox0.1v |
| `Revisao_Prova01/` | Acadêmico | Revisão para prova — 6 exercícios Python |
| `wordlists/` | Segurança | SecLists submodule + wordlists customizadas (bbWebScan, blackarch, kali) |

---

## Projetos em Destaque

### bbWebScan — Orquestrador de Recon para Bug Bounty
`ObsidianAgent/Projects/bbWebScan/`

Ferramenta Python (v0.5.3) para reconhecimento automatizado em programas de bug bounty. Orquestra estágios em pipeline: httpx (discovery), katana (crawler), Scrapy (scraping), Nuclei (template scan), Amass (enumeração de subdomínios), Kiterunner (API discovery). CLI unificado com `bbwebscan {scan,install,doctor,init,history,show,compare}`. Gates obrigatórios: ruff + mypy --strict + pytest com cobertura ≥ 85%.

### OpenBox0.1v — Appliance Linux Hardened
`ObsidianAgent/Projects/OpenBox0.1v/`

Appliance doméstico seguro para Debian/Raspbian com instalador faseado (fases 00–09). Inclui: nftables (firewall), WireGuard (VPN), Tor (anonimização), DNSCrypt-Proxy (DNS cifrado), fail2ban, Monit (watchdogs), Caddy (proxy reverso), Stremio. Utilizado como referência técnica no projeto AVAL01-IC.

### IPS_IDS / ADV7Sec — Runtime de Detecção de Intrusões
`ObsidianAgent/Projects/IPS_IDS/`

Runtime Python de IDS/IPS para Arch Linux (ADV7Sec 1.0). CLI unificado com modos `audit`, `doctor`, `backend` e `install`. Sensores integrados: auditd, Falco, Kunai, Suricata e Zeek. Implementado como mitigação host-side no projeto AVAL01-IC (AV01 UniCEUB).

### ADV7ia — Stack Local de IA
`IC01-aops/ADV7ia/`

Mesh de controle para tarefas de IA local em Arch Linux. Integra LM Studio (modelo de linguagem local), OpenHands, Aider e Cline com rollover de estado de tarefas e proxy LAN via Caddy. Suporte a VM via túnel reverso (GNOME Boxes). Inclui suite de testes e vault Obsidian integrado.

### JustVibing/Snippets — BugBounty Recon Toolkit (Client-side)
`JustVibing/Snippets/`

Scanner client-side em JavaScript v1.0.3 (security score 95/100). Três módulos: `master-bugbounty.js` (scanner unificado), `finder.js` (análise de scripts externos) e `window.js` (variáveis globais). Correções aplicadas: CORS, race condition em download, vazamento de memória, validação RFC-791, proteção contra ReDoS.

### AVAL01-IC — Projeto Técnico de Segurança em IoT
`IC01-aops/AVAL01-IC/`

Projeto técnico da disciplina Introdução à Computação (UniCEUB, 2026). Análise de segurança do dispositivo MXQ Pro 4k (firmware Android comprometido com botnet Satori), proposta de arquitetura defensiva com OpenBox, ADV7Sec (IDS/IPS) e segmentação de rede. Fontes primárias: FBI PSA, HUMAN Security Satori, Dr.Web, Anatel, MJSP/PF.

---

## Tecnologias & Ferramentas

| Categoria | Ferramentas |
| --- | --- |
| Linux | Arch · Debian · Fedora · QubesOS |
| Windows | Windows · Windows Server |
| Virtualização | Hyper-V · VirtualBox · VMware · KVM · GNOME Boxes |
| Versionamento | Git · GitHub · GitHub Pages |
| Linguagens | Python 3 · JavaScript · Bash |
| Redes & Privacy | nftables · WireGuard · Tor · dnscrypt-proxy · Mullvad VPN · iptables · Caddy |
| IDS / IPS | Suricata · Falco · Zeek · ClamAV · auditd · Kunai · fail2ban |
| Recon & BugBounty | httpx · katana · Scrapy · ffuf · feroxbuster · nuclei · amass · naabu · sqlmap · SecLists |
| IA Local | LM Studio · OpenHands · Aider · Cline · Qdrant |
| Build & Deploy | Docker · Pandoc · Chromium · GitHub Actions |

---

## Integração LinkedIn

Este repositório e os projetos aqui contidos estão integrados ao perfil profissional do autor no LinkedIn:

**[linkedin.com/in/aops/](https://www.linkedin.com/in/aops/)**

Os projetos acadêmicos e as certificações estão adicionados à seção de projetos e cursos do perfil profissional.

---

## Apresentação

Em breve: apresentação em vídeo do repositório destacando os principais projetos e funcionalidades.

*(Requisito 6 — Revisão Final: vídeo de 5 minutos no YouTube sobre o portfólio.)*

---

## Versão

**v1.0** — Entrega Intermediária BootCamp1 · BootCamp TCS · UniCEUB · 2026

Autor: Alcides Olivo Pollazzon Soterio · [aops@outlook.com.br](mailto:aops@outlook.com.br)
