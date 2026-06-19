#!/usr/bin/env python3
"""
item_id_swap.py — TaskBarHero ES3 save item-ID substitution
Authorized security testing PoC for F1 (PlayerDataTransactionWrite trust boundary).

Crypto: ES3 AES-128-CBC
        key = PBKDF2-SHA1(password, salt=IV, 100 iters, 16B)
        password from ES3Defaults.asset (resources.assets pathID 12223)

Usage:
  python3 item_id_swap.py                            # list item-related fields in save
  python3 item_id_swap.py --from OLD_ID --to NEW_ID  # swap item ID, write back
  python3 item_id_swap.py --dump                     # print raw decrypted JSON
  python3 item_id_swap.py --watch --from A --to B    # live-watch: re-patch each game write
  python3 item_id_swap.py --interval N --watch ...   # poll every N seconds (N must be > 0)
  python3 item_id_swap.py --save /path/to/file       # override save path

Before --from/--to writes, the original save is copied to a timestamped backup
alongside it: SaveFile_Live.es3.bak.YYYYMMDD_HHMMSS (previous backups are kept).

Run inside WSL with:
  source ~/.unitypy-venv/bin/activate
  python3 ~/TaskbarHero/item_id_swap.py
"""

import argparse
import base64
import fcntl
import hashlib
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# ── Crypto constants ─────────────────────────────────────────────────────────────
PASSWORD   = "emuMqG3bLYJ938ZDCfieWJ"
PBKDF2_ALG = "sha1"
PBKDF2_N   = 100
KEY_LEN    = 16   # AES-128
BLOCK      = 16

# ── Default save path (Windows user via WSL /mnt/c) ─────────────────────────────
_WIN_USER = os.environ.get("WIN_USER", "AOPSec")
DEFAULT_SAVE = Path(
    f"/mnt/c/Users/{_WIN_USER}/AppData/LocalLow/TesseractStudio/TaskbarHero/SaveFile_Live.es3"
)

# ── Crypto helpers ───────────────────────────────────────────────────────────────

def _derive_key(iv: bytes) -> bytes:
    return hashlib.pbkdf2_hmac(PBKDF2_ALG, PASSWORD.encode(), iv, PBKDF2_N, KEY_LEN)


def _decrypt_bytes(raw: bytes) -> bytes:
    if len(raw) < BLOCK:
        raise ValueError(f"File too short to contain IV ({len(raw)} bytes)")
    iv  = raw[:BLOCK]
    ct  = raw[BLOCK:]
    key = _derive_key(iv)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(ct), BLOCK)


def decrypt_save(path: Path) -> bytes:
    return _decrypt_bytes(path.read_bytes())


def encrypt_save(plaintext: bytes) -> bytes:
    iv  = os.urandom(BLOCK)
    key = _derive_key(iv)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return iv + cipher.encrypt(pad(plaintext, BLOCK))

# ── SystemInfo anti-tamper hash ──────────────────────────────────────────────────

def _recompute_system_info(data: dict) -> str:
    """
    SHA-256 over the canonical JSON of all keys except SystemInfo.
    Returns the 64-char hex digest; update_system_info re-encodes it to base64
    when the live save already stores SystemInfo that way.
    """
    payload   = {k: v for k, v in data.items() if k != "SystemInfo"}
    canonical = json.dumps(payload, separators=(",", ":"), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _format_digest(hex_digest: str, existing: object) -> str:
    """Encode the digest to match the existing value's format (base64 vs hex)."""
    # ES3 base64 of a 32-byte digest is 44 chars ending in '='; hex is 64 chars.
    if isinstance(existing, str) and len(existing) == 44 and existing.endswith("="):
        return base64.b64encode(bytes.fromhex(hex_digest)).decode()
    return hex_digest


def update_system_info(data: dict, skip: bool = False) -> None:
    if skip or "SystemInfo" not in data:
        return
    entry = data["SystemInfo"]
    hex_digest = _recompute_system_info(data)
    # ES3 wraps: {"__type": "...", "value": <hash_string>}
    if isinstance(entry, dict) and "value" in entry:
        entry["value"] = _format_digest(hex_digest, entry["value"])
    else:
        data["SystemInfo"] = _format_digest(hex_digest, entry)

# ── Item ID discovery ────────────────────────────────────────────────────────────

_ITEM_PATS = re.compile(
    r"\b(?:itemId|itemKey|itemSaveData|itemSaveDatas"
    r"|inventorySaveDatas|stashSaveDatas|stashItem|tradingStashSaveDatas"
    r"|runeId|RuneSaveData|charId|charKey)\b",
    re.IGNORECASE,
)


def find_item_entries(obj: object, path: str = "") -> list[tuple[str, object]]:
    """Walk the decoded JSON and return (json-path, value) for item-ID looking fields."""
    results: list[tuple[str, object]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            cur = f"{path}.{k}" if path else k
            if _ITEM_PATS.search(k):
                results.append((cur, v))
            results.extend(find_item_entries(v, cur))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            results.extend(find_item_entries(item, f"{path}[{i}]"))
    return results

# ── In-place substitution ────────────────────────────────────────────────────────

def _matches_id(value: object, target: str | int) -> bool:
    # bool is a subclass of int; exclude it so True/1 and False/0 never collide.
    if isinstance(value, bool):
        return False
    if isinstance(value, str) and isinstance(target, str):
        return value == target
    if isinstance(value, int) and isinstance(target, int):
        return value == target
    return False


def substitute_id(obj: object, old: str | int, new: str | int) -> int:
    """Recursively replace every value equal to `old` (str or int) with `new`. Returns hit count."""
    count = 0
    if isinstance(obj, dict):
        for k in list(obj.keys()):
            v = obj[k]
            if _matches_id(v, old):
                obj[k] = new
                count += 1
            else:
                count += substitute_id(v, old, new)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if _matches_id(item, old):
                obj[i] = new
                count += 1
            else:
                count += substitute_id(item, old, new)
    return count

# ── Command implementations ──────────────────────────────────────────────────────

def cmd_list(save: Path) -> None:
    print(f"[*] Save : {save}")
    print(f"[*] Size : {save.stat().st_size} bytes")
    try:
        plaintext = decrypt_save(save)
        data      = json.loads(plaintext)
    except (ValueError, KeyError) as exc:
        sys.exit(
            f"[!] Cannot decrypt/parse save: {exc}\n"
            "    Verify the file path and that the game is not currently writing."
        )
    hits      = find_item_entries(data)
    if not hits:
        print("[!] No item-ID fields matched — try --dump to inspect full structure.")
        return
    print(f"[+] {len(hits)} item-related field(s):\n")
    for path, val in hits:
        display = json.dumps(val, ensure_ascii=False)
        if len(display) > 160:
            display = display[:157] + "..."
        print(f"  {path}\n    {display}\n")


def cmd_dump(save: Path) -> None:
    try:
        plaintext = decrypt_save(save)
        data      = json.loads(plaintext)
    except (ValueError, KeyError) as exc:
        sys.exit(
            f"[!] Cannot decrypt/parse save: {exc}\n"
            "    Verify the file path and that the game is not currently writing."
        )
    print(json.dumps(data, indent=2, ensure_ascii=False))


def cmd_swap(save: Path, old_id: str, new_id: str, no_hash: bool = False) -> None:
    ts     = time.strftime("%Y%m%d_%H%M%S")
    backup = save.with_name(save.name + f".bak.{ts}")
    shutil.copy2(save, backup)
    print(f"[*] Backup  → {backup}")

    plaintext = decrypt_save(save)
    data      = json.loads(plaintext)

    n = substitute_id(data, old_id, new_id)
    if n == 0:
        print(f"[!] ID '{old_id}' not found anywhere in save — no changes written.")
        return

    print(f"[+] Replaced {n} occurrence(s): '{old_id}' → '{new_id}'")

    update_system_info(data, skip=no_hash)
    if no_hash:
        print("[*] --no-hash: SystemInfo left unchanged (tests raw server trust)")

    new_plain = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode()
    save.write_bytes(encrypt_save(new_plain))
    print(f"[+] Written → {save}")


_LOCK_TIMEOUT = 2.0   # seconds to wait for an exclusive lock before skipping a cycle


def _patch_locked(save: Path, old_id: str | int, new_id: str | int, no_hash: bool) -> int:
    """
    Read, patch, and rewrite the save under an exclusive advisory lock so we never
    race the game's own writes. Returns the substitution count.
    Raises BlockingIOError if the lock cannot be acquired within _LOCK_TIMEOUT.
    """
    fd = open(save, "r+b")
    try:
        deadline = time.monotonic() + _LOCK_TIMEOUT
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.1)
        try:
            data = json.loads(_decrypt_bytes(fd.read()))
            n    = substitute_id(data, old_id, new_id)
            if n:
                update_system_info(data, skip=no_hash)
                new_plain = json.dumps(
                    data, separators=(",", ":"), ensure_ascii=False
                ).encode()
                ciphertext = encrypt_save(new_plain)
                fd.seek(0)
                fd.write(ciphertext)
                fd.truncate()
            return n
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        fd.close()


def cmd_watch(
    save: Path,
    old_id: str,
    new_id: str,
    interval: float,
    no_hash: bool,
) -> None:
    """Poll the save file; re-patch each time the game overwrites it."""
    print(f"[*] Watching {save}  (poll every {interval}s) — Ctrl-C to stop")
    last_mtime: float | None = None
    try:
        while True:
            try:
                mtime = save.stat().st_mtime
            except FileNotFoundError:
                time.sleep(interval)
                continue

            if mtime != last_mtime:
                try:
                    n  = _patch_locked(save, old_id, new_id, no_hash)
                    ts = time.strftime("%H:%M:%S")
                    if n:
                        print(f"  [{ts}] patched {n} occurrence(s)")
                    else:
                        print(f"  [{ts}] save updated — ID '{old_id}' not present")
                    # Only advance the watermark once the cycle succeeds, so a
                    # skipped (locked) cycle is retried on the next poll.
                    last_mtime = mtime
                except BlockingIOError:
                    print(
                        "[!] Could not acquire file lock — skipping this cycle",
                        file=sys.stderr,
                    )
                except Exception as exc:
                    print(f"[!] Patch error: {exc}", file=sys.stderr)

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n[*] Watch stopped.")

# ── CLI entry point ──────────────────────────────────────────────────────────────

def positive_float(v: str) -> float:
    f = float(v)
    if f <= 0:
        raise argparse.ArgumentTypeError("--interval must be > 0")
    return f


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "TaskBarHero ES3 save item-ID substitution — authorized testing PoC.\n"
            "Tests whether the client-authored PlayerDataTransactionWrite path "
            "accepts arbitrary item grants (F1 in SECURITY_ASSESSMENT.md)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--save", type=Path, default=DEFAULT_SAVE,
        help=f"path to SaveFile_Live.es3 (default: {DEFAULT_SAVE})",
    )
    ap.add_argument("--dump",  action="store_true", help="print decrypted JSON and exit")
    ap.add_argument("--from",  dest="old_id", metavar="OLD_ID", help="item ID to replace")
    ap.add_argument("--to",    dest="new_id", metavar="NEW_ID", help="replacement item ID")
    ap.add_argument(
        "--watch", action="store_true",
        help="live-watch mode: re-patch each time the game writes the save",
    )
    ap.add_argument(
        "--interval", type=positive_float, default=1.0,
        help="watch poll interval in seconds, must be > 0 (default: 1.0)",
    )
    ap.add_argument(
        "--no-hash", action="store_true",
        help="skip SystemInfo hash recomputation (tests raw server trust without valid hash)",
    )
    args = ap.parse_args()

    if args.dump and (args.old_id or args.new_id):
        ap.error("--dump cannot be used together with --from/--to")
    if args.old_id == "" or args.new_id == "":
        ap.error("--from and --to must not be empty strings")

    save = args.save
    if not save.exists():
        sys.exit(
            f"[!] Save file not found: {save}\n"
            f"    Set --save or WIN_USER env var (current: '{_WIN_USER}')."
        )

    if args.dump:
        cmd_dump(save)
    elif args.old_id and args.new_id:
        if not os.access(save, os.W_OK):
            sys.exit(f"[!] Save file is not writable: {save}")
        if args.watch:
            cmd_watch(save, args.old_id, args.new_id, args.interval, args.no_hash)
        else:
            cmd_swap(save, args.old_id, args.new_id, args.no_hash)
    elif args.old_id or args.new_id:
        ap.error("--from and --to must be used together")
    else:
        cmd_list(save)


if __name__ == "__main__":
    main()
