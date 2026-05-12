# Response

ADV7Sec 1.0 provides safe automatic response with preview by default.

## Model

- `monitor` shows raw live sources.
- `analyze` builds a normalized event stream from journald, Suricata EVE, Falco JSON, and ClamAV logs.
- The policy layer selects only reversible actions with explicit confidence.
- Real execution remains opt-in through `--execute`.

## Allowed Automatic Actions

- `quarantine-path` for high-confidence malware or infected-file events
- `kill-pid` for hostile process patterns with usable PID context
- `stop-service` and `disable-service` only through explicit operator action with `respond`

## Safety Gates

- No raw auto-drop firewall rules from unverified alerts
- No irreversible wipe or destructive cleanup
- No execution without elevated privileges
- No hidden response path outside the Python control plane
- No live `install --apply --root /` without `--yes` confirmation
- No service enable after a failed validation command for the same feature

## Examples

```bash
python3 ADV7Sec_1.0v.py analyze --lines 50
sudo python3 ADV7Sec_1.0v.py analyze --lines 50 --execute
python3 ADV7Sec_1.0v.py respond quarantine-path /tmp/suspect.bin
```

Use preview mode first. Promote a rule to execution only after the event pattern is understood and produces stable high-confidence matches.
