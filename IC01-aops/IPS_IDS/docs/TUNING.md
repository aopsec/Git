<!-- [IPS-PH2] Tuning entrypoint for the active ADV7Sec runtime. -->

# Tuning

Use this file as the quick entrypoint for ongoing tuning after install/apply.

## Daily Minimum

```bash
SINCE="yesterday"
sudo journalctl -u auditd --since "${SINCE}" --no-pager
sudo journalctl -u falco-modern-bpf.service --since "${SINCE}" --no-pager
sudo jq -r '.event_type' /var/log/suricata/eve.json 2>/dev/null | sort | uniq -c | sort -nr
sudo systemctl list-timers '*aide*' '*loki*' '*lynis*' '*chkrootkit*'
```

## Rule

Suppress only after evidence exists, and record every suppression in your local operator notes.

## Promotion

Do not expand response policy beyond the current safe automatic actions until tuning evidence is stable.
