# Changelog

## [0.1.0] - 2026-06-26

### Added
- install.sh: orquestrador de fases com suporte a --dry-run e --phase
- install.d/_lib.sh: helpers compartilhados (log, run, detect_wsl2, detect_binder)
- Fase 00-base: pacotes base e guarda WSL2
- Fase 01-gui: configuração WSLg/Wayland
- Fase 02-kernel: instalação do kernel com binder_linux
- Fase 03-waydroid: instalação e inicialização do Waydroid GAPPS
- Fase 04-adb: configuração ADB + perfil de ambiente
- Fase 05-gapps: certificação do dispositivo no Google
- Fase 06-validate: smoke tests de integração
- tests/ci-syntax-check.sh: gate bash-n + shellcheck
- tests/validate-stack.sh: testes de integração ao vivo
