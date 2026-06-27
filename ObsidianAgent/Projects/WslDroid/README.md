# WslDroid — Android via WSL2

`versão 0.1.0` · `status: beta` · `licença: MIT`

Provisionador bash para instalar **Waydroid** (Android 13, LineageOS) no **WSL2 Ubuntu**,
com display via **WSLg**, **Google Play Store** (GAPPS) e **ADB**.

O Waydroid roda um sistema Android completo em um container **LXC**, integrado ao desktop
do Windows 11 através do WSLg (servidor Wayland nativo do WSL2). Não requer emulador
pesado nem servidor X externo.

## Requisitos

- **Windows 11** (build 22000+) com WSL2 atualizado (`wsl --update`)
- **Ubuntu 22.04 ou 24.04** no WSL2 (root obrigatório durante a instalação)
- **WSLg** habilitado — incluso no Windows 11, sem VcXsrv necessário
- Acesso à internet (download de imagens Waydroid e GAPPS)

## Início Rápido

```bash
git clone <repo>
cd ObsidianAgent/Projects/WslDroid
sudo bash install.sh
```

Opções úteis:

```bash
sudo bash install.sh --dry-run             # mostra o que seria feito, sem executar
sudo bash install.sh --phase 03-waydroid   # roda uma fase isolada
```

## Fases

A instalação é faseada e idempotente. Cada fase vive em `install.d/` e pode ser
executada isoladamente via `--phase`:

| Fase | Papel |
|---|---|
| `00-base` | Pacotes base e guarda WSL2 |
| `01-gui` | Configuração WSLg / Wayland |
| `02-kernel` | Instalação do kernel WSL2 com `binder_linux` |
| `03-waydroid` | Instalação e inicialização do Waydroid GAPPS |
| `04-adb` | Configuração ADB + perfil de ambiente |
| `05-gapps` | Certificação do dispositivo no Google |
| `06-validate` | Smoke tests de integração |

## Arquitetura

Quatro camadas, do display Windows até o app Android:

```
+------------------------------------------------------------+
|  CAMADA 4 — GApps / Play Store                             |
|  Google Play Services + Store (GAPPS, device certificado)  |
+------------------------------------------------------------+
|  CAMADA 3 — Container LXC Waydroid                         |
|  Android 13 (LineageOS) em LXC, sessão + container         |
+------------------------------------------------------------+
|  CAMADA 2 — Kernel WSL2 customizado                        |
|  Módulo binder_linux (ashmem/binder) habilitado            |
+------------------------------------------------------------+
|  CAMADA 1 — WSLg (display Wayland)                         |
|  Compositor Wayland nativo do WSL2 → janelas no Windows    |
+------------------------------------------------------------+
```

## Aviso de Licença

O código deste projeto é MIT (ver `LICENSE`). Porém os **builds GApps** (Google Play
Services / Play Store) são **software proprietário** da Google/Intel e destinam-se
**apenas a uso não-comercial**. O projeto baixa e instala esses componentes a pedido
do usuário; a responsabilidade pelos termos de licença do Google é do próprio usuário.

## Limitações Conhecidas

- **Aceleração GPU parcialmente suportada** no WSL2 — o render do Android pode cair em
  software rendering (issue do MESA sobre WSL2).
- O **WSA da Microsoft** (Windows Subsystem for Android) foi **descontinuado em
  05/03/2025**; este projeto usa **Waydroid** como alternativa de código aberto.
- Requer **recompilação/substituição do kernel WSL2** (fase `02-kernel`) para expor
  `binder_linux` — o kernel padrão do WSL2 não inclui o módulo binder por default.

## Referências

- Documentação Waydroid — <https://docs.waydro.id>
- Waydroid (código-fonte) — <https://github.com/waydroid/waydroid>
- WSLg (código-fonte) — <https://github.com/microsoft/wslg>

## Licença

MIT — ver `LICENSE`.
