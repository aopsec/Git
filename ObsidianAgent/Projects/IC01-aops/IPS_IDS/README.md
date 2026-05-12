# IPS_IDS

Linux-first IPS/IDS control plane for host and network visibility, driven by a single Python entrypoint.

`ADV7Sec_1.0v.py` is the control surface. The old Arch-only installer tree has been removed from the active project layout.

## Target

- Scope: single host with local telemetry, live logs, live auto-audit, and safe automatic response preview
- Distros: Arch Linux (`native`), Debian/Ubuntu and Fedora (`adapted`), other Linux targets (`experimental`)
- Runtime: systemd preferred, local JSON logs, journald, packaged resources under `adv7sec_1_0/resource_files/`

## Runtime Layout

```text
Projects/IPS_IDS/
├── ADV7Sec_1.0v.py
├── adv7sec_1_0/
├── tests/
├── docs/
└── README.md
```

The unified source of truth is `adv7sec_1_0/`. Runtime configs are loaded from packaged resources, not from duplicate active examples spread across the tree.

## Main Commands

```bash
python3 ADV7Sec_1.0v.py audit
python3 ADV7Sec_1.0v.py doctor --format json
python3 ADV7Sec_1.0v.py backend
python3 ADV7Sec_1.0v.py install --feature suricata
python3 ADV7Sec_1.0v.py install --feature suricata --root /tmp/adv7sec-stage --apply
python3 ADV7Sec_1.0v.py monitor --lines 20
python3 ADV7Sec_1.0v.py analyze --lines 20
python3 ADV7Sec_1.0v.py smoke --root /tmp/adv7sec-stage
python3 ADV7Sec_1.0v.py respond stop-service suricata.service
```

## Linux-First Adapters

- `doctor` detects distro, package manager, init system, and runtime capabilities.
- `backend` exposes package and service adapters for `pacman`, `apt`, `dnf`, and `zypper`.
- `install` plans or applies packaged resources and backend actions for one feature or the full stack.
- `install --apply` also generates derived configs such as `/etc/default/ipsids-suricata` and ClamAV overrides.
- `install --apply --root /` is non-interactive by design and requires `--yes` before live host execution.
- Service activation is blocked when the feature validation step returns a non-zero status.
- Features with unstable packaging across distros, such as Falco and Zeek, stay explicit as `manual` instead of pretending false parity.

## Response Model

- Default mode is preview-first.
- `analyze` normalizes journald, Suricata EVE, Falco JSON, and ClamAV logs into one event stream.
- Safe automatic response exists for high-confidence cases such as malware paths and hostile processes.
- Execution still requires `--execute` and appropriate privileges.

## Validation

```bash
bash tests/ci-syntax-check.sh
python3 -m unittest discover -s tests -p 'test_*.py'
python3 ADV7Sec_1.0v.py audit --format json
```

## Cleanup Gate

Keep only `ADV7Sec_1.0v.py`, `adv7sec_1_0/`, `tests/`, `docs/`, and supporting metadata in the project root.
