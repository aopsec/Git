"""Post-boot validation systemd service generator."""

from __future__ import annotations

from pathlib import Path

from blk7rch.utils.logger import log
from blk7rch.utils.run import chroot_run

_SERVICE_NAME = "blk7rch-postboot-validate.service"

_SCRIPT_CONTENT = """\
#!/bin/bash
# BLK7rch post-boot validation script — runs once after first boot.
set -euo pipefail

PASS=0
FAIL=0

_check() {
    local desc="$1"
    local result="$2"
    if [[ "$result" == "true" ]]; then
        echo "[OK]   $desc"
        ((PASS++))
    else
        echo "[FAIL] $desc"
        ((FAIL++))
    fi
}

# 1. Verify cryptdevice is present in kernel cmdline
grep -q "cryptdevice=" /proc/cmdline \\
    && _check "cryptdevice in cmdline" true \\
    || _check "cryptdevice in cmdline" false

# 2. Verify NetworkManager is enabled
systemctl is-enabled NetworkManager &>/dev/null \\
    && _check "NetworkManager enabled" true \\
    || _check "NetworkManager enabled" false

# 3. Verify /etc/fstab exists and is non-empty
[[ -s /etc/fstab ]] \\
    && _check "/etc/fstab present and non-empty" true \\
    || _check "/etc/fstab present and non-empty" false

# 4. Verify LUKS device is open
ls /dev/mapper/cryptroot &>/dev/null \\
    && _check "LUKS mapper device present" true \\
    || _check "LUKS mapper device present" false

echo ""
echo "Post-boot validation complete: ${PASS} passed, ${FAIL} failed."
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
"""

_SERVICE_CONTENT = f"""\
[Unit]
Description=BLK7rch Post-Boot System Validation
After=network.target
ConditionPathExists=!/var/lib/blk7rch-postboot-done

[Service]
Type=oneshot
ExecStart=/usr/local/bin/blk7rch-postboot-validate
ExecStartPost=/usr/bin/touch /var/lib/blk7rch-postboot-done
StandardOutput=journal
StandardError=journal
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
"""


def install_postboot_validation(target: Path, dry_run: bool = False) -> None:
    """Write and enable the post-boot validation service.

    Writes:
    * ``/usr/local/bin/blk7rch-postboot-validate`` (executable script)
    * ``/etc/systemd/system/blk7rch-postboot-validate.service``

    Then enables the service via ``systemctl enable``.

    Parameters
    ----------
    target:
        Mount point of the installed system.
    dry_run:
        When *True*, writes and chroot commands are skipped.
    """
    log.step("Post-boot validation: installing service")

    script_dest = target / "usr" / "local" / "bin" / "blk7rch-postboot-validate"
    service_dest = target / "etc" / "systemd" / "system" / _SERVICE_NAME

    if not dry_run:
        script_dest.parent.mkdir(parents=True, exist_ok=True)
        script_dest.write_text(_SCRIPT_CONTENT)
        script_dest.chmod(0o755)

        service_dest.parent.mkdir(parents=True, exist_ok=True)
        service_dest.write_text(_SERVICE_CONTENT)
    else:
        log.dry(f"write {script_dest}")
        log.dry(f"write {service_dest}")

    chroot_run(
        target,
        ["systemctl", "enable", _SERVICE_NAME],
        dry_run=dry_run,
    )

    log.ok("Post-boot validation: service installed and enabled")
