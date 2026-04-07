2"""BlackArchBootstrap — download, SHA256-verify, and execute the BlackArch strap.sh."""

from __future__ import annotations

import hashlib
import os
import stat
import tempfile
from pathlib import Path

from blk7rch.utils.logger import log
from blk7rch.utils.run import chroot_run, run_cmd

_STRAP_URL = "https://blackarch.org/strap.sh"
_STRAP_SHA_URL = "https://blackarch.org/strap.sh.sha256"


class BlackArchBootstrap:
    """Downloads, verifies, and installs the BlackArch Linux repository.

    The strap.sh script is executed inside *target* via ``arch-chroot``.
    SHA256 verification is mandatory — installation is aborted on mismatch.

    Parameters
    ----------
    target:
        Mount point of the new system (e.g. ``Path('/mnt')``).
    dry_run:
        When *True*, all network and chroot operations are skipped.
    """

    def __init__(self, target: Path, dry_run: bool = False) -> None:
        """Initialise with the installation target path."""
        self.target = target
        self.dry_run = dry_run

    def install(self) -> None:
        """Run the full BlackArch bootstrap sequence.

        Steps:
        1. Download ``strap.sh`` and its ``strap.sh.sha256`` with curl (retry 3).
        2. Verify SHA256 digest; abort on mismatch.
        3. Set permissions to ``0o700``.
        4. Execute inside chroot via ``arch-chroot``.

        Raises
        ------
        RuntimeError
            On SHA256 mismatch or curl failure.
        """
        log.step("BlackArch: bootstrapping repository")

        with tempfile.TemporaryDirectory() as tmp:
            strap_host = Path(tmp) / "strap.sh"
            sha_host = Path(tmp) / "strap.sh.sha256"

            self._download(_STRAP_URL, strap_host)
            self._download(_STRAP_SHA_URL, sha_host)
            self._verify_sha256(strap_host, sha_host)

            # Copy into chroot's /tmp
            chroot_strap = self.target / "tmp" / "strap.sh"
            if not self.dry_run:
                chroot_strap.write_bytes(strap_host.read_bytes())
                chroot_strap.chmod(stat.S_IRWXU)

            chroot_run(self.target, ["/bin/bash", "/tmp/strap.sh"], dry_run=self.dry_run)

            # Clean up
            if not self.dry_run and chroot_strap.exists():
                chroot_strap.unlink()

        log.ok("BlackArch: repository bootstrapped")

    def _download(self, url: str, dest: Path) -> None:
        """Download *url* to *dest* using curl with retry logic."""
        run_cmd(
            ["curl", "-fsSL", "--max-time", "60", "--retry", "3", "-o", str(dest), url],
            dry_run=self.dry_run,
        )

    def _verify_sha256(self, strap: Path, sha_file: Path) -> None:
        """Compare the SHA256 of *strap* against the expected digest in *sha_file*.

        Raises
        ------
        RuntimeError
            If the digests do not match or the sha_file cannot be read.
        """
        if self.dry_run:
            log.dry("SHA256 verification skipped in dry-run mode")
            return

        expected_line = sha_file.read_text().strip()
        # sha256 file may be "HASH  filename" or just "HASH"
        expected = expected_line.split()[0].lower()

        actual = hashlib.sha256(strap.read_bytes()).hexdigest().lower()

        if actual != expected:
            raise RuntimeError(
                f"BlackArch strap.sh SHA256 mismatch!\n"
                f"  Expected : {expected}\n"
                f"  Actual   : {actual}\n"
                "Aborting to prevent installation of tampered software."
            )

        log.ok(f"BlackArch strap.sh SHA256 OK: {actual[:16]}…")
