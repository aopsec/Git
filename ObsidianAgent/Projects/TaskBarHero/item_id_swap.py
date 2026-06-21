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
  python3 item_id_swap.py --save /path/to/file       # override save path

Run inside WSL with:
  source ~/.unitypy-venv/bin/activate
  python3 ~/TaskbarHero/item_id_swap.py
"""

import argparse
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


def decrypt_save(path: Path) -> bytes:
    raw = path.read_bytes()
    if len(raw) < BLOCK:
        raise ValueError(f"File too short to contain IV ({len(raw)} bytes): {path}")
    iv  = raw[:BLOCK]
    ct  = raw[BLOCK:]
    key = _derive_key(iv)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(ct), BLOCK)


def encrypt_save(plaintext: bytes) -> bytes:
    iv  = os.urandom(BLOCK)
    key = _derive_key(iv)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return iv + cipher.encrypt(pad(plaintext, BLOCK))

# ── SystemInfo anti-tamper hash ──────────────────────────────────────────────────

def _recompute_system_info(data: dict) -> str:
    """
    SHA-256 over the canonical JSON of all keys except SystemInfo.
    ES3 stores the 32-byte digest; we return a 64-char hex string (common ES3 representation).
    If the live format differs (e.g. base64), the game will re-reject on load — use --no-hash
    to skip recomputation and test raw server trust instead.
    """
    payload   = {k: v for k, v in data.items() if k != "SystemInfo"}
    canonical = json.dumps(payload, separators=(",", ":"), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def update_system_info(data: dict, skip: bool = False) -> None:
    if skip or "SystemInfo" not in data:
        return
    entry = data["SystemInfo"]
    # ES3 wraps: {"__type": "...", "value": <hash_string>}
    if isinstance(entry, dict) and "value" in entry:
        entry["value"] = _recompute_system_info(data)
    else:
        data["SystemInfo"] = _recompute_system_info(data)

# ── Item ID discovery ────────────────────────────────────────────────────────────

_ITEM_PATS = re.compile(
    r"itemId|ItemId|ItemID|itemKey|ItemKey|itemSaveData|itemSaveDatas"
    r"|runeId|RuneId|stashItem|StashItem|charId|CharId|charKey|CharKey",
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

def substitute_id(obj: object, old: str, new: str) -> int:
    """Recursively replace every string equal to `old` with `new`. Returns hit count."""
    count = 0
    if isinstance(obj, dict):
        for k in list(obj.keys()):
            v = obj[k]
            if isinstance(v, str) and v == old:
                obj[k] = new
                count += 1
            else:
                count += substitute_id(v, old, new)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, str) and item == old:
                obj[i] = new
                count += 1
            else:
                count += substitute_id(item, old, new)
    return count

# ── Command implementations ──────────────────────────────────────────────────────

def cmd_list(save: Path) -> None:
    print(f"[*] Save : {save}")
    print(f"[*] Size : {save.stat().st_size} bytes")
    plaintext = decrypt_save(save)
    data      = json.loads(plaintext)
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
    plaintext = decrypt_save(save)
    data      = json.loads(plaintext)
    print(json.dumps(data, indent=2, ensure_ascii=False))


def cmd_swap(save: Path, old_id: str, new_id: str, no_hash: bool = False) -> None:
    backup = save.with_suffix(".es3.bak")
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
                last_mtime = mtime
                try:
                    plaintext = decrypt_save(save)
                    data      = json.loads(plaintext)
                    n         = substitute_id(data, old_id, new_id)
                    if n:
                        update_system_info(data, skip=no_hash)
                        new_plain = json.dumps(
                            data, separators=(",", ":"), ensure_ascii=False
                        ).encode()
                        save.write_bytes(encrypt_save(new_plain))
                        ts = time.strftime("%H:%M:%S")
                        print(f"  [{ts}] patched {n} occurrence(s)")
                    else:
                        ts = time.strftime("%H:%M:%S")
                        print(f"  [{ts}] save updated — ID '{old_id}' not present")
                except Exception as exc:
                    print(f"[!] Patch error: {exc}", file=sys.stderr)

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n[*] Watch stopped.")

# ── CLI entry point ──────────────────────────────────────────────────────────────

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
        "--interval", type=float, default=1.0,
        help="watch poll interval in seconds (default: 1.0)",
    )
    ap.add_argument(
        "--no-hash", action="store_true",
        help="skip SystemInfo hash recomputation (tests raw server trust without valid hash)",
    )
    args = ap.parse_args()

    save = args.save
    if not save.exists():
        sys.exit(
            f"[!] Save file not found: {save}\n"
            f"    Set --save or WIN_USER env var (current: '{_WIN_USER}')."
        )

    if args.dump:
        cmd_dump(save)
    elif args.old_id and args.new_id:
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
