# Threat Model

## In Scope

- Persistence via systemd units, pacman hooks, shell startup, SSH keys, and kernel modules.
- Local privilege escalation and suspicious root command execution.
- Unexpected listeners and pivot tools.
- DNS, TLS, HTTP, SSH, and flow visibility from the workstation.
- Malware scanning of high-ingress user paths.

## Out Of Scope

- Enterprise SIEM deployment.
- Inline IPS blocking.
- Fleet management.
- Full disk forensic acquisition.
- Tor/VPN anonymity guarantees.

## Assumptions

- The operator can inspect alerts daily during tuning.
- The workstation is not a production gateway.
- High-noise detections must be tuned before response.
