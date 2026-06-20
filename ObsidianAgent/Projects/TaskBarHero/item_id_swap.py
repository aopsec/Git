#!/usr/bin/env python3
"""
item_id_swap.py — TaskBarHero ES3 save item-ID substitution
Authorized security testing PoC for F1 (PlayerDataTransactionWrite trust boundary).

Crypto: ES3 AES-128-CBC
        key = PBKDF2-SHA1(password, salt=IV, 100 iters, 16B)
        password from ES3Defaults.asset (resources.assets pathID 12223)

Usage:
  python3 item_id_swap.py                             # interactive TUI (bare launch)
  python3 item_id_swap.py --from OLD_ID --to NEW_ID   # swap item ID, write back
  python3 item_id_swap.py --legendary                  # category-aware batch legendary swap
  python3 item_id_swap.py --legendary --watch          # race server sync (0.5 s poll)
  python3 item_id_swap.py --dump                       # print raw decrypted JSON
  python3 item_id_swap.py --watch --from A --to B      # live-watch single swap
  python3 item_id_swap.py --interval N --watch ...     # poll every N seconds (N > 0)
  python3 item_id_swap.py --save /path/to/file         # override save path

All writes are atomic (temp file + os.replace) so a crash can never corrupt the save.
Single-shot swaps back up the original before writing; watch mode takes ONE session
backup at start (per-cycle writes don't back up individually):
  SaveFile_Live.es3.bak.YYYYMMDD_HHMMSS

Platform support:
  WSL  : python3 item_id_swap.py  (default /mnt/c/Users/... path)
  Win  : py item_id_swap.py       (auto-detects C:\\Users\\... path via %USERNAME%)
"""

import argparse
import base64
import hashlib
import hmac
import json
import os
import platform
import re
import shutil
import sys
import time
from pathlib import Path

try:
    import fcntl          # POSIX only (WSL / Linux)
    _HAS_FCNTL = True
except ImportError:
    _HAS_FCNTL = False    # Windows native — file locking skipped

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# ── Crypto constants ─────────────────────────────────────────────────────────────
PASSWORD   = "emuMqG3bLYJ938ZDCfieWJ"
PBKDF2_ALG = "sha1"
PBKDF2_N   = 100
KEY_LEN    = 16   # AES-128
BLOCK      = 16

# ── Default save path — WSL or native Windows ────────────────────────────────────
if platform.system() == "Windows":
    _WIN_USER    = os.environ.get("USERNAME", os.environ.get("WIN_USER", "AOPSec"))
    DEFAULT_SAVE = Path(
        rf"C:\Users\{_WIN_USER}\AppData\LocalLow\TesseractStudio\TaskbarHero\SaveFile_Live.es3"
    )
else:
    _WIN_USER    = os.environ.get("WIN_USER", "AOPSec")
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


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    """Crash-safe write: stage to a temp file, then os.replace (atomic on POSIX+Win).
    A partial/short write can never leave `path` in a corrupted, undecryptable state.
    """
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _timestamped_backup(save: Path) -> Path:
    """Copy `save` to save.name + '.bak.YYYYMMDD_HHMMSS' and return the backup path."""
    ts     = time.strftime("%Y%m%d_%H%M%S")
    backup = save.with_name(save.name + f".bak.{ts}")
    shutil.copy2(save, backup)
    return backup

# ── SystemInfo anti-tamper hash ──────────────────────────────────────────────────
# Reverse-engineered from GameAssembly.dll (IL2CPP):
#   bal.mbs() builds HMAC-SHA256(key=bgbp, msg=UTF8(av+"|"+pv+"|"+ownerSteamId))
#   bgbp = PBKDF2-SHA1(UTF8(fim+fiy), salt, 12000 iters, GetBytes(64))[:32]
#   fim  = "tesseractTBH0901!!"  (GUPS idx 0x1efb3, len 18)
#   fiy  = "SaveSecretDeriveHmacKeyComposeHmacInputComposeSaltC"  (GUPS idx 0x1f1ed, len 51)
#   salt = big-endian bytes of fin() groups at class_data offsets +0x2C..+0x38
#          (chars 72-103 of the 112-char fin() hex string, 4 groups × 4 bytes)
_BGBP_PASSWORD = b"tesseractTBH0901!!SaveSecretDeriveHmacKeyComposeHmacInputComposeSaltC"
_BGBP_SALT     = bytes.fromhex("4D7A2E5F6B0C8D31A5183F6229E4F70A")
_BGBP_KEY      = hashlib.pbkdf2_hmac("sha1", _BGBP_PASSWORD, _BGBP_SALT, 12000, dklen=64)[:32]


def _recompute_system_info(data: dict) -> str:
    """
    Compute the correct SystemInfo HMAC-SHA256 hash matching the game's anti-tamper check.
    Returns base64-encoded result (the format ES3 stores it in).
    Handles dicts that are missing AccountSaveData/PlayerSaveData gracefully (tests/stubs).
    """
    acc_entry = data.get("AccountSaveData", "")
    pla_entry = data.get("PlayerSaveData", "")
    av = acc_entry.get("value", "") if isinstance(acc_entry, dict) else str(acc_entry)
    pv = pla_entry.get("value", "") if isinstance(pla_entry, dict) else str(pla_entry)
    try:
        owner_id = json.loads(av).get("ownerSteamId", "") if av else ""
    except (json.JSONDecodeError, AttributeError):
        owner_id = ""
    msg    = (av + "|" + pv + "|" + owner_id).encode("utf-8")
    digest = hmac.new(_BGBP_KEY, msg, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def update_system_info(data: dict, skip: bool = False) -> None:
    if skip or "SystemInfo" not in data:
        return
    new_hash = _recompute_system_info(data)
    entry = data["SystemInfo"]
    # ES3 wraps: {"__type": "...", "value": <hash_string>}
    if isinstance(entry, dict) and "value" in entry:
        entry["value"] = new_hash
    else:
        data["SystemInfo"] = new_hash

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
        outer     = json.loads(plaintext)
    except (ValueError, KeyError) as exc:
        sys.exit(
            f"[!] Cannot decrypt/parse save: {exc}\n"
            "    Verify the file path and that the game is not currently writing."
        )

    # Collect hits from outer dict, then from each nested JSON blob
    hits = find_item_entries(outer)
    for key in ("PlayerSaveData", "AccountSaveData"):
        entry = outer.get(key)
        if entry is None:
            continue
        pv_str = entry["value"] if isinstance(entry, dict) else entry
        if not isinstance(pv_str, str):
            continue
        try:
            inner = json.loads(pv_str)
            hits += [(f"{key}.value > {p}", v) for p, v in find_item_entries(inner)]
        except json.JSONDecodeError:
            pass

    if not hits:
        print("[!] No item-ID fields matched — try --dump to inspect full structure.")
        return
    print(f"[+] {len(hits)} item-related field(s):\n")
    for path, val in hits:
        display = json.dumps(val, ensure_ascii=False)
        if len(display) > 160:
            display = display[:157] + "..."
        print(f"  {path}\n    {display}\n")


def cmd_items(save: Path) -> None:
    """
    Inventory viewer: print every item in itemSaveDatas with its slot index,
    ItemKey, 2-digit sub-category prefix, equipping hero (if any), and whether
    the key is a known legendary target. Helps pick source/target IDs to swap.
    """
    try:
        plaintext = decrypt_save(save)
        outer     = json.loads(plaintext)
        pv_entry  = outer.get("PlayerSaveData", {})
        pv_str    = pv_entry["value"] if isinstance(pv_entry, dict) else pv_entry
        inner     = json.loads(pv_str)
        items     = inner["itemSaveDatas"]
    except Exception as exc:
        print(f"[!] Cannot read save: {exc}")
        sys.exit(1)

    equipped_ids = _get_equipped_ids(inner)
    # UniqueId → heroKey for every equipped item across all hero slots.
    hero_by_uid: dict[int, str] = {}
    for hero in inner.get("heroSaveDatas", []):
        hero_key = hero.get("heroKey", "?")
        for uid in hero.get("equippedItemIds", []):
            if uid:
                hero_by_uid[uid] = str(hero_key)

    equipped_count  = 0
    legendary_count = 0
    rows: list[tuple[int, int, int, str, str]] = []
    for slot, item in enumerate(items):
        item_key = item.get("ItemKey", 0)
        prefix2  = item_key // 10000
        uid      = item.get("UniqueId")
        is_equipped = uid in equipped_ids if uid is not None else False
        equipped_to = hero_by_uid.get(uid, "—") if is_equipped else "—"
        if is_equipped:
            equipped_count += 1
        is_legendary = item_key in _LEGENDARY_KEYS
        if is_legendary:
            legendary_count += 1
        rows.append((slot, item_key, prefix2, equipped_to, "✓" if is_legendary else ""))

    try:
        from rich.console import Console
        from rich.table import Table
        console: object | None = Console()
    except ImportError:
        console = None

    if console is not None:
        t = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
        t.add_column("Slot",       style="dim",    justify="right", no_wrap=True)
        t.add_column("ItemKey",    style="yellow", justify="right", no_wrap=True)
        t.add_column("Prefix2",    style="cyan",   justify="right", no_wrap=True)
        t.add_column("Equipped",   style="green",  no_wrap=True)
        t.add_column("Legendary?", style="magenta", justify="center", no_wrap=True)
        for slot, item_key, prefix2, equipped_to, legendary in rows:
            t.add_row(str(slot), str(item_key), str(prefix2), equipped_to, legendary)
        console.print(t)  # type: ignore[attr-defined]
    else:
        print(f"  {'Slot':>4}  {'ItemKey':>8}  {'Prefix2':>7}  {'Equipped':<10}  Legendary?")
        print(f"  {'-' * 50}")
        for slot, item_key, prefix2, equipped_to, legendary in rows:
            print(f"  {slot:>4}  {item_key:>8}  {prefix2:>7}  {equipped_to:<10}  {legendary}")

    print(
        f"\nTotal: {len(items)} items | "
        f"Equipped: {equipped_count} | Legendary: {legendary_count}"
    )


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


def _coerce_id(raw: str) -> str | int:
    """Return int when raw is a pure decimal string, else the original str."""
    return int(raw) if raw.lstrip("-").isdigit() else raw


def _parse_targets_file(path: Path) -> list[tuple[int, str]]:
    """
    Read target IDs from a .txt file (one ID per line). Blank lines and lines
    whose stripped form starts with '#' are skipped; inline '# …' comments are
    stripped. Each remaining token is parsed as int.
    Returns [(int_id, str(int_id)), …] — ID as string, no human-readable name.
    Raises ValueError with a clear message on the first non-integer token.
    """
    targets: list[tuple[int, str]] = []
    for lineno, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        text = stripped.split("#", 1)[0].strip()
        if not text:
            continue
        try:
            int_id = int(text)
        except ValueError as exc:
            raise ValueError(
                f"{path}:{lineno}: invalid target ID {text!r} (expected integer)"
            ) from exc
        targets.append((int_id, str(int_id)))
    return targets


def _parse_target_ids(raw_ids: list[str]) -> list[tuple[int, str]]:
    """
    Parse a list of raw ID strings (CLI --target args, TUI comma/newline split).
    Whitespace is stripped; blank tokens are skipped; each remaining token is
    parsed as int. Returns [(int_id, str(int_id)), …].
    Raises ValueError with a clear message on the first non-integer token.
    """
    targets: list[tuple[int, str]] = []
    for raw in raw_ids:
        token = raw.strip()
        if not token:
            continue
        try:
            int_id = int(token)
        except ValueError as exc:
            raise ValueError(
                f"invalid target ID {token!r} (expected integer)"
            ) from exc
        targets.append((int_id, str(int_id)))
    return targets


def _patch_nested_json(outer: dict, old: str | int, new: str | int) -> int:
    """
    Parse PlayerSaveData.value (and AccountSaveData.value) as a nested JSON string,
    apply substitute_id inside it, then re-serialize back into outer[key]["value"].
    Returns total replacement count across all nested blobs.
    """
    count = 0
    for key in ("PlayerSaveData", "AccountSaveData"):
        entry = outer.get(key)
        if entry is None:
            continue
        pv_str = entry["value"] if isinstance(entry, dict) else entry
        if not isinstance(pv_str, str):
            continue
        try:
            inner = json.loads(pv_str)
        except json.JSONDecodeError:
            continue
        n = substitute_id(inner, old, new)
        if n:
            count += n
            new_str = json.dumps(inner, separators=(",", ":"), ensure_ascii=False)
            if isinstance(entry, dict):
                entry["value"] = new_str
            else:
                outer[key] = new_str
    return count


def cmd_swap(save: Path, old_id: str, new_id: str, no_hash: bool = False) -> None:
    plaintext = decrypt_save(save)
    outer     = json.loads(plaintext)

    old = _coerce_id(old_id)
    new = _coerce_id(new_id)

    # Search outer dict first (keys that live directly there)
    n  = substitute_id(outer, old, new)
    # Then search/patch inside nested JSON blobs (PlayerSaveData.value etc.)
    n += _patch_nested_json(outer, old, new)

    if n == 0:
        print(f"[!] ID '{old_id}' not found anywhere in save — no changes written.")
        return

    print(f"[+] Replaced {n} occurrence(s): '{old_id}' → '{new_id}'")

    # Backup only when there are actual changes (mirrors cmd_legendary behaviour).
    backup = _timestamped_backup(save)
    print(f"[*] Backup  → {backup}")

    update_system_info(outer, skip=no_hash)
    if no_hash:
        print("[*] --no-hash: SystemInfo left unchanged (tests raw server trust)")

    new_plain   = json.dumps(outer, separators=(",", ":"), ensure_ascii=False).encode()
    _atomic_write_bytes(save, encrypt_save(new_plain))
    print(f"[+] Written → {save}")


_LOCK_TIMEOUT = 2.0   # seconds to wait for an exclusive lock before skipping a cycle


def _patch_locked(save: Path, old_id: str, new_id: str, no_hash: bool) -> int:
    """
    Read, patch, and rewrite the save under an exclusive advisory lock so we never
    race the game's own writes. Returns the substitution count.
    Raises BlockingIOError if the lock cannot be acquired within _LOCK_TIMEOUT.
    """
    old = _coerce_id(old_id)
    new = _coerce_id(new_id)
    # Read under an advisory lock to serialize against another copy of this tool,
    # then write atomically (temp + os.replace) so a crash can't corrupt the save.
    # The lock is released before the replace: holding an open handle blocks
    # os.replace on Windows, and the game (the real concurrent writer) does not
    # honour flock anyway — the watch loop re-patches on the next mtime change.
    fd = open(save, "rb")
    try:
        _flock_acquire(fd, _LOCK_TIMEOUT)
        outer = json.loads(_decrypt_bytes(fd.read()))
    finally:
        _flock_release(fd)
        fd.close()
    n  = substitute_id(outer, old, new)
    n += _patch_nested_json(outer, old, new)
    if n:
        update_system_info(outer, skip=no_hash)
        new_plain = json.dumps(outer, separators=(",", ":"), ensure_ascii=False).encode()
        _atomic_write_bytes(save, encrypt_save(new_plain))
    return n


def cmd_watch(
    save: Path,
    old_id: str,
    new_id: str,
    interval: float,
    no_hash: bool,
) -> None:
    """Poll the save file; re-patch each time the game overwrites it."""
    print(f"[*] Watching {save}  (poll every {interval}s) — Ctrl-C to stop")
    # One recovery point for the whole watch session: the per-cycle writes below
    # are atomic but never back up, so capture the pristine save before any patch.
    _bk = _timestamped_backup(save)
    print(f"[*] Session backup → {_bk}")
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

# ── Legendary batch swap (F1 PoC automation) ─────────────────────────────────────
# Only TARGET IDs are defined here. Source items are selected at runtime by
# category-prefix similarity (same 3-digit → 2-digit → 1-digit), avoiding equipped
# and already-used slots. This prevents multi-hit over-swaps on stacked item types.
_LEGENDARY_TARGETS: list[tuple[int, str]] = [
    (315102, "Arco Rúnico[B]"),
    (335102, "Cetro Lendário[B]"),
    (345092, "Besta de Elite[B]"),
    (415101, "Flecha Tribal[A]"),
    (435102, "Tomo Carmesim[B]"),
    (445102, "Virote do Herói[B]"),
]
_LEGENDARY_KEYS = {t for t, _ in _LEGENDARY_TARGETS}

_STATUS_RICH = {
    "ready":    "[green]ready[/green]",
    "present":  "[blue]present[/blue]",
    "no match": "[yellow]no match[/yellow]",
}


def _get_equipped_ids(inner: dict) -> set[int]:
    """Return set of UniqueIds currently equipped by any hero slot."""
    equipped: set[int] = set()
    for hero in inner.get("heroSaveDatas", []):
        for uid in hero.get("equippedItemIds", []):
            if uid:
                equipped.add(uid)
    return equipped


def _prefix_priority(item_key: int, target_key: int) -> int:
    """0=same 3-digit prefix (best), 1=same 2-digit, 2=same 1-digit, 3=none."""
    if item_key // 1000  == target_key // 1000:  return 0
    if item_key // 10000 == target_key // 10000: return 1
    if item_key // 100000 == target_key // 100000: return 2
    return 3


def _find_best_candidate(items: list, target_key: int,
                          equipped_ids: set, used_indices: set,
                          skip_keys: set | None = None) -> int:
    """
    Return index of the most category-similar unequipped/unused item for target_key.
    Returns -1 when no valid candidate exists.
    Skips items that are equipped, already used, whose ItemKey is in skip_keys,
    or whose prefix priority against target_key is p3 (no category overlap).
    `skip_keys` defaults to the global legendary target keys when None.
    """
    skip = _LEGENDARY_KEYS if skip_keys is None else skip_keys
    candidates: list[tuple[int, int]] = []
    for idx, item in enumerate(items):
        if idx in used_indices:
            continue
        ik = item.get("ItemKey")
        if ik is None or ik in skip:
            continue  # malformed item (no ItemKey) or an already-targeted key
        if item.get("UniqueId") in equipped_ids:
            continue
        prio = _prefix_priority(ik, target_key)
        if prio == 3:
            continue  # reject items with no 1-digit prefix overlap (wrong category)
        candidates.append((prio, idx))
    if not candidates:
        return -1
    candidates.sort()
    return candidates[0][1]


def _apply_legendary_swaps(
    outer: dict,
    targets: list[tuple[int, str]] | None = None,
) -> list[tuple[int, int, int, str]]:
    """
    Parse inner PlayerSaveData JSON, apply category-based single-slot legendary swaps,
    re-serialize pv, update outer["PlayerSaveData"]["value"].
    When `targets` is None, falls back to the global _LEGENDARY_TARGETS list.
    Returns list of (slot_idx, old_key, new_key, name) for each swap performed.
    Targets whose ID is already present in the inventory are skipped (Bug 1+2 fix).
    """
    active_targets = _LEGENDARY_TARGETS if targets is None else targets
    skip_keys = {t for t, _ in active_targets}
    pv_entry = outer.get("PlayerSaveData", {})
    pv_str   = pv_entry["value"] if isinstance(pv_entry, dict) else pv_entry
    inner    = json.loads(pv_str)
    items    = inner["itemSaveDatas"]
    equipped = _get_equipped_ids(inner)
    # Keys currently in inventory — skip targets already owned to avoid duplicates.
    present_keys: set[int] = {item["ItemKey"] for item in items if "ItemKey" in item}
    used: set[int] = set()
    log: list[tuple[int, int, int, str]] = []

    for tgt_key, tgt_name in active_targets:
        if tgt_key in present_keys:
            continue  # Bug 1+2: already in inventory from a previous run
        idx = _find_best_candidate(items, tgt_key, equipped, used, skip_keys)
        if idx < 0:
            continue
        old_key = items[idx]["ItemKey"]
        items[idx]["ItemKey"] = tgt_key
        present_keys.add(tgt_key)
        used.add(idx)
        log.append((idx, old_key, tgt_key, tgt_name))

    if log:
        new_pv = json.dumps(inner, separators=(",", ":"), ensure_ascii=False)
        if isinstance(pv_entry, dict):
            pv_entry["value"] = new_pv
        else:
            outer["PlayerSaveData"] = new_pv
    return log


# Server-authority flags that gate an item. Clearing them ("unblock") is the
# write-side of the F1 test: does the backend accept a client-authored save that
# flips IsBlocked → false? The game resolves all stats/specialities by ItemKey
# (see SECURITY_ASSESSMENT.md), but a blocked item is gated, so the speciality
# does not "run" until these flags are cleared.
_UNBLOCK_FLAGS = ("IsBlocked", "IsServerPendingItem", "IsChaotic")


def _apply_unblock(
    outer: dict,
    keys: set[int] | None = None,
) -> list[tuple[int, int, list[str]]]:
    """
    Clear the server-authority gate flags (_UNBLOCK_FLAGS) on inventory items,
    re-serialize PlayerSaveData.value.
    keys=None  → every flagged item in the inventory.
    keys=set   → only items whose ItemKey is in `keys`.
    Returns list of (slot_idx, item_key, [cleared_flag, ...]) for each item changed.
    """
    pv_entry = outer.get("PlayerSaveData", {})
    pv_str   = pv_entry["value"] if isinstance(pv_entry, dict) else pv_entry
    inner    = json.loads(pv_str)
    items    = inner.get("itemSaveDatas", [])
    log: list[tuple[int, int, list[str]]] = []

    for idx, item in enumerate(items):
        ik = item.get("ItemKey")
        if keys is not None and ik not in keys:
            continue
        cleared = [f for f in _UNBLOCK_FLAGS if item.get(f)]
        if not cleared:
            continue
        for f in cleared:
            item[f] = False
        log.append((idx, ik, cleared))

    if log:
        new_pv = json.dumps(inner, separators=(",", ":"), ensure_ascii=False)
        if isinstance(pv_entry, dict):
            pv_entry["value"] = new_pv
        else:
            outer["PlayerSaveData"] = new_pv
    return log


def _flock_acquire(fd, timeout: float) -> None:
    if not _HAS_FCNTL:
        return
    deadline = time.monotonic() + timeout
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.05)


def _flock_release(fd) -> None:
    if _HAS_FCNTL:
        fcntl.flock(fd, fcntl.LOCK_UN)


def _patch_legendary_locked(save: Path, no_hash: bool,
                            targets: list[tuple[int, str]] | None = None) -> int:
    """Single read-modify-write cycle: read under flock, swap + unblock targets,
    then atomic write. Returns count of changed items (swaps + unblocks)."""
    active = _LEGENDARY_TARGETS if targets is None else targets
    target_keys = {t for t, _ in active}
    fd = open(save, "rb")
    try:
        _flock_acquire(fd, _LOCK_TIMEOUT)
        outer = json.loads(_decrypt_bytes(fd.read()))
    finally:
        _flock_release(fd)
        fd.close()
    swap_log = _apply_legendary_swaps(outer, targets)
    # Make every target item usable: clear server-authority gate flags so the
    # swapped/owned legendaries are not neutralized (the IsBlocked = unlocked fix).
    unblock_log = _apply_unblock(outer, keys=target_keys)
    if swap_log or unblock_log:
        update_system_info(outer, skip=no_hash)
        _atomic_write_bytes(save, encrypt_save(
            json.dumps(outer, separators=(",", ":"), ensure_ascii=False).encode()
        ))
    return len(swap_log) + len(unblock_log)


def cmd_legendary(save: Path, no_hash: bool = False, watch: bool = False,
                  interval: float = 0.5,
                  targets: list[tuple[int, str]] | None = None) -> None:
    """
    Category-aware batch legendary swap (F1 PoC).
    Selects the most type-similar unequipped item for each legendary target;
    replaces exactly ONE slot per target regardless of stack size.
    When `targets` is None, uses the global _LEGENDARY_TARGETS list.
    """
    active_targets = _LEGENDARY_TARGETS if targets is None else targets
    print(f"[*] Legendary targets: {', '.join(f'{k} {n}' for k, n in active_targets)}")

    if not watch:
        outer = json.loads(decrypt_save(save))

        # Snapshot present keys BEFORE the swap to classify skipped targets accurately.
        _pv_pre = outer.get("PlayerSaveData", {})
        _pv_pre_str = _pv_pre["value"] if isinstance(_pv_pre, dict) else _pv_pre
        present_before: set[int] = {
            item["ItemKey"]
            for item in json.loads(_pv_pre_str).get("itemSaveDatas", [])
        }

        log = _apply_legendary_swaps(outer, targets)

        swapped_keys = {r[2] for r in log}
        for tgt_key, tgt_name in active_targets:
            if tgt_key in swapped_keys:
                continue
            if tgt_key in present_before:
                print(f"  [=] {tgt_name!r} already in inventory — will unblock if gated")
            else:
                print(f"  [-] no same-category candidate for {tgt_name!r} — skipped")

        for idx, old_k, new_k, name in log:
            prio = _prefix_priority(old_k, new_k)
            tag  = ["p0(3-digit)", "p1(2-digit)", "p2(1-digit)"][prio]
            print(f"  [+] slot[{idx}] {old_k} → {new_k} {name!r}  [{tag}]")

        # Clear server-authority gate flags on every target key (swapped + owned)
        # so the legendary specialities actually run (IsBlocked = unlocked).
        target_keys = {t for t, _ in active_targets}
        unblock_log = _apply_unblock(outer, keys=target_keys)
        for idx, ik, cleared in unblock_log:
            print(f"  [U] slot[{idx}] ItemKey={ik} unblocked ({', '.join(cleared)})")

        if not log and not unblock_log:
            print("[!] Nothing to write — targets absent or already unlocked.")
            return

        # Backup only written when there are actual changes.
        backup = _timestamped_backup(save)
        print(f"[*] Backup → {backup}")

        update_system_info(outer, skip=no_hash)
        _atomic_write_bytes(save, encrypt_save(
            json.dumps(outer, separators=(",", ":"), ensure_ascii=False).encode()
        ))
        print(f"[+] Written → {save}  ({len(log)} swap(s), {len(unblock_log)} unblock(s))")
        return

    print(f"[*] Watch mode — polling every {interval}s  (Ctrl-C to stop)")
    print("[*] TIP: restart the game NOW so it loads before server sync overwrites")
    # One recovery point for the whole watch session (per-cycle writes don't back up).
    _bk = _timestamped_backup(save)
    print(f"[*] Session backup → {_bk}")
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
                    n  = _patch_legendary_locked(save, no_hash, targets)
                    ts = time.strftime("%H:%M:%S")
                    if n:
                        print(f"  [{ts}] {n} change(s) applied (swap/unblock)")
                    else:
                        print(f"  [{ts}] all targets present & unlocked, or no match — idle")
                    last_mtime = mtime
                except BlockingIOError:
                    print("[!] File locked — skipping cycle", file=sys.stderr)
                except Exception as exc:
                    print(f"[!] Patch error: {exc}", file=sys.stderr)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[*] Watch stopped.")


def cmd_unblock(save: Path, keys: set[int] | None = None, no_hash: bool = False) -> None:
    """
    Clear the server-authority gate flags (IsBlocked/IsServerPendingItem/IsChaotic)
    so gated items become usable (IsBlocked = unlocked). keys=None clears every
    flagged item; a key set scopes the change to those ItemKeys.
    """
    scope = "all flagged items" if keys is None else f"{len(keys)} target key(s)"
    print(f"[*] Unblock scope: {scope}")
    outer = json.loads(decrypt_save(save))
    log = _apply_unblock(outer, keys)
    if not log:
        print("[=] No blocked/pending/chaotic items to clear — nothing to write.")
        return
    for idx, ik, cleared in log:
        print(f"  [U] slot[{idx}] ItemKey={ik} unblocked ({', '.join(cleared)})")
    backup = _timestamped_backup(save)
    print(f"[*] Backup → {backup}")
    update_system_info(outer, skip=no_hash)
    _atomic_write_bytes(save, encrypt_save(
        json.dumps(outer, separators=(",", ":"), ensure_ascii=False).encode()
    ))
    print(f"[+] Written → {save}  ({len(log)} item(s) unblocked)")

# ── Interactive TUI (bare launch) ────────────────────────────────────────────────

def _getch() -> str:
    """Read one raw keypress without waiting for Enter. Returns lowercase char."""
    if platform.system() == "Windows":
        import msvcrt
        return msvcrt.getch().decode("utf-8", errors="replace").lower()
    import tty, termios
    fd = sys.stdin.fileno()
    if not sys.stdin.isatty():
        ch = sys.stdin.read(1)
        return ch.lower() if ch else "q"
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1).lower()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _build_preview(items: list, equipped: set,
                   targets: list[tuple[int, str]] | None = None) -> list[tuple]:
    """Return one row per legendary target: (tgt_key, tgt_name, src_key, tag, status).
    Status values: 'ready' | 'present' | 'no match'
      present  — target ID already in inventory (previous run; will be skipped)
      ready    — valid same-category candidate found (p0/p1/p2)
      no match — no candidate with ≥1-digit prefix overlap (p3 or no items)
    """
    active_targets = targets if targets is not None else _LEGENDARY_TARGETS
    skip_keys = {t for t, _ in active_targets}
    present_keys: set[int] = {item["ItemKey"] for item in items if "ItemKey" in item}
    used: set[int] = set()
    rows = []
    for tgt_key, tgt_name in active_targets:
        if tgt_key in present_keys:
            rows.append((tgt_key, tgt_name, "—", "—", "present"))
            continue
        idx = _find_best_candidate(items, tgt_key, equipped, used, skip_keys)
        if idx >= 0:
            src_key = items[idx]["ItemKey"]
            prio    = _prefix_priority(src_key, tgt_key)
            tag     = ["p0 ✓", "p1 ✓", "p2 ~"][prio]
            used.add(idx)
            rows.append((tgt_key, tgt_name, src_key, tag, "ready"))
        else:
            rows.append((tgt_key, tgt_name, "—", "—", "no match"))
    return rows


def cmd_gui(save: Path) -> None:
    """Interactive TUI — launched when no CLI flags are given."""
    # Snapshot the terminal's original (cooked) settings so the [C]ustom handler
    # can restore line-editing/echo before calling input(). POSIX TTY only.
    _orig_tty_settings = None
    if platform.system() != "Windows" and sys.stdin.isatty():
        try:
            import termios
            _orig_tty_settings = termios.tcgetattr(sys.stdin.fileno())
        except Exception:
            _orig_tty_settings = None

    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich.text import Text
        from rich.align import Align
        console: Console | None = Console()
    except ImportError:
        console = None

    def _render() -> tuple:
        try:
            outer    = json.loads(decrypt_save(save))
            inner    = json.loads(outer["PlayerSaveData"]["value"])
            items    = inner["itemSaveDatas"]
            equipped = _get_equipped_ids(inner)
            size_kb  = save.stat().st_size // 1024

            av  = outer["AccountSaveData"]["value"]
            pv  = outer["PlayerSaveData"]["value"]
            si  = outer["SystemInfo"]["value"]
            oid = json.loads(av).get("ownerSteamId", "")
            msg = (av + "|" + pv + "|" + oid).encode()
            exp = base64.b64encode(hmac.new(_BGBP_KEY, msg, hashlib.sha256).digest()).decode()
            return items, equipped, size_kb, exp == si, _build_preview(items, equipped), None
        except Exception as exc:
            return [], set(), 0, False, [], str(exc)

    while True:
        os.system("cls" if platform.system() == "Windows" else "clear")
        items, equipped, size_kb, hmac_ok, preview, err = _render()

        if console:
            header = Text.assemble(("TaskBarHero Legendary Swap", "bold white"),
                                   "   ", ("F1 PoC", "dim"))
            hmac_badge = "[green]VALID[/green]" if hmac_ok else "[red]MISMATCH[/red]"
            subtitle   = f"[cyan]{save.name}[/cyan]  {size_kb} KB  HMAC: {hmac_badge}"
            console.print(Panel(Align.center(header), subtitle=subtitle, style="blue"))

            if err:
                console.print(f"[red][!] {err}[/red]")
            else:
                t = Table(show_header=True, header_style="bold cyan",
                          show_lines=False, box=None, padding=(0, 2))
                t.add_column("Target",  style="yellow",  width=9, no_wrap=True)
                t.add_column("Name",    style="white",   width=26, no_wrap=True)
                t.add_column("Source",  style="dim",     width=9,  no_wrap=True)
                t.add_column("Match",   style="green",   width=6,  no_wrap=True)
                t.add_column("Status",                   width=14, no_wrap=True)
                for (tk, tn, sk, tag, status) in preview:
                    st = _STATUS_RICH.get(status, f"[red]{status}[/red]")
                    t.add_row(str(tk), tn, str(sk), tag, st)
                console.print(t)
                console.print(f"\n  Items total: {len(items)}")

            console.print(
                "\n  [bold][A][/bold]pply once   "
                "[bold][W][/bold]atch   "
                "[bold][C][/bold]ustom   "
                "[bold][U][/bold]nblock   "
                "[bold][I][/bold]tems   "
                "[bold][L][/bold]ist   "
                "[bold][D][/bold]ump   "
                "[bold][Q][/bold]uit\n  > ",
                end="",
            )
        else:
            # plain fallback (no rich)
            print("=" * 64)
            print("  TaskBarHero Legendary Swap  |  F1 PoC")
            print(f"  {save.name}  {size_kb} KB  HMAC: {'VALID' if hmac_ok else 'MISMATCH'}")
            print("=" * 64)
            if err:
                print(f"  [!] {err}")
            else:
                print(f"  {'Target':<9} {'Name':<26} {'Source':<9} {'Match':<6} Status")
                print(f"  {'-'*64}")
                for (tk, tn, sk, tag, status) in preview:
                    print(f"  {tk:<9} {tn:<26} {str(sk):<9} {tag:<6} {status}")
                print(f"\n  Items total: {len(items)}")
            print("\n  [A]pply once  [W]atch  [C]ustom  [U]nblock  [I]tems  [L]ist  [D]ump  [Q]uit\n  > ",
                  end="", flush=True)

        try:
            ch = _getch()
        except KeyboardInterrupt:
            ch = "q"

        if ch in ("q", "\x03", "\x04"):
            print("\nBye.")
            break

        elif ch == "a":
            print("\n")
            if not os.access(save, os.W_OK):
                print("[!] Save file not writable")
            else:
                cmd_legendary(save, no_hash=False, watch=False)
            print("\nPress any key to continue…")
            try:
                _getch()
            except KeyboardInterrupt:
                pass

        elif ch == "u":
            print("\n")
            if not os.access(save, os.W_OK):
                print("[!] Save file not writable")
            else:
                cmd_unblock(save, keys=None, no_hash=False)  # unblock ALL flagged items
            print("\nPress any key to continue…")
            try:
                _getch()
            except KeyboardInterrupt:
                pass

        elif ch == "c":
            print("\n\n[Custom targets]")
            # Restore the terminal to cooked mode so input() echoes and edits work.
            if (platform.system() != "Windows" and sys.stdin.isatty()
                    and _orig_tty_settings is not None):
                try:
                    import termios
                    termios.tcsetattr(
                        sys.stdin.fileno(), termios.TCSADRAIN, _orig_tty_settings
                    )
                except Exception:
                    pass

            # Abbreviated inventory to help pick target IDs (plain print, no rich).
            try:
                _inner = json.loads(decrypt_save(save))
                _pv    = _inner["PlayerSaveData"]["value"]
                _items = json.loads(_pv)["itemSaveDatas"]
                print(f"  {'Slot':<5} {'ItemKey':<9} Prefix2")
                for _slot, _item in enumerate(_items[:20]):
                    _ik = _item.get("ItemKey", 0)
                    print(f"  {_slot:<5} {_ik:<9} {_ik // 10000}")
                if len(_items) > 20:
                    print(f"  … {len(_items) - 20} more items")
            except Exception as exc:
                print(f"  [!] Could not list inventory: {exc}")

            print("\nEnter IDs (comma or newline-separated) OR path to a .txt file:")
            print("> ", end="", flush=True)
            try:
                raw_input_str = input()
            except (EOFError, KeyboardInterrupt):
                raw_input_str = ""

            parsed_targets: list[tuple[int, str]] = []
            parse_ok = True
            stripped_input = raw_input_str.strip()
            try:
                if stripped_input.endswith(".txt") and Path(stripped_input).exists():
                    parsed_targets = _parse_targets_file(Path(stripped_input))
                else:
                    parsed_targets = _parse_target_ids(
                        re.split(r"[,\n]+", raw_input_str)
                    )
            except ValueError as exc:
                print(f"[!] Parse error: {exc}")
                parse_ok = False

            if parse_ok and not parsed_targets:
                print("[!] No valid IDs — skipped")
            elif parse_ok:
                if not os.access(save, os.W_OK):
                    print("[!] Save file not writable")
                else:
                    cmd_legendary(save, targets=parsed_targets,
                                  no_hash=False, watch=False)

            print("\nPress any key to continue…")
            try:
                _getch()
            except KeyboardInterrupt:
                pass

        elif ch == "w":
            print("\n")
            if not os.access(save, os.W_OK):
                print("[!] Save file not writable")
            else:
                cmd_legendary(save, no_hash=False, watch=True, interval=0.5)

        elif ch == "l":
            print("\n")
            cmd_list(save)
            print("\nPress any key to continue…")
            try:
                _getch()
            except KeyboardInterrupt:
                pass

        elif ch == "d":
            print("\n")
            cmd_dump(save)
            print("\nPress any key to continue…")
            try:
                _getch()
            except KeyboardInterrupt:
                pass

        elif ch == "i":
            print("\n")
            cmd_items(save)
            print("\nPress any key to continue…")
            try:
                _getch()
            except KeyboardInterrupt:
                pass

# ── CLI entry point ──────────────────────────────────────────────────────────────

def positive_float(v: str) -> float:
    f = float(v)
    if f <= 0:
        raise argparse.ArgumentTypeError("--interval must be > 0")
    return f


def _force_utf8_stdio() -> None:
    """Make Unicode output (→ — ✓ …) safe on any Windows console codepage or when
    stdout is redirected to a pipe/file. Without this, plain prints of chars outside
    the legacy codepage (e.g. ✓) can raise UnicodeEncodeError on a fresh Windows box."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass


def main() -> None:
    _force_utf8_stdio()
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
    ap.add_argument("--dump",     action="store_true", help="print decrypted JSON and exit")
    ap.add_argument("--items",    action="store_true",
                    help="print an inventory table of all items and exit")
    ap.add_argument("--legendary", action="store_true",
                    help="batch-swap 6 source slots to legendary IDs (F1 PoC)")
    ap.add_argument("--from",  dest="old_id", metavar="OLD_ID", help="item ID to replace")
    ap.add_argument("--to",    dest="new_id", metavar="NEW_ID", help="replacement item ID")
    ap.add_argument(
        "--watch", action="store_true",
        help="live-watch: re-patch each time the game writes (use with --legendary to race sync)",
    )
    ap.add_argument(
        "--interval", type=positive_float, default=0.5,
        help="watch poll interval in seconds, must be > 0 (default: 0.5)",
    )
    ap.add_argument(
        "--no-hash", action="store_true",
        help="skip SystemInfo hash recomputation (tests raw server trust without valid hash)",
    )
    ap.add_argument(
        "--target", action="append", metavar="ID", default=None,
        help="Target item ID to swap to (repeatable); incompatible with --targets-file",
    )
    ap.add_argument(
        "--targets-file", type=Path, default=None,
        help="Path to .txt file with target IDs (one per line)",
    )
    ap.add_argument(
        "--unblock", action="store_true",
        help="clear IsBlocked/IsServerPendingItem/IsChaotic so items are usable "
             "(scope: --target/--targets-file keys, else --legendary keys, else ALL items)",
    )
    args = ap.parse_args()

    _has_custom = args.target is not None or args.targets_file is not None
    if args.unblock and (args.dump or args.items or args.old_id or args.new_id):
        ap.error("--unblock cannot be combined with --dump/--items or --from/--to")
    if args.unblock and args.watch:
        ap.error("--unblock is one-shot; use --legendary/--target with --watch to unblock continuously")
    if args.items and (args.dump or args.legendary or args.old_id or args.new_id or _has_custom):
        ap.error("--items cannot be combined with --dump/--legendary, --from/--to, or --target/--targets-file")
    if args.dump and (args.old_id or args.new_id or args.legendary):
        ap.error("--dump cannot be combined with --from/--to or --legendary")
    if args.legendary and (args.old_id or args.new_id):
        ap.error("--legendary cannot be combined with --from/--to")
    if args.legendary and _has_custom:
        ap.error("--legendary and --target/--targets-file are mutually exclusive — use one or the other")
    if args.old_id == "" or args.new_id == "":
        ap.error("--from and --to must not be empty strings")
    if args.target is not None and args.targets_file is not None:
        ap.error("--target and --targets-file are mutually exclusive")
    if _has_custom and (args.old_id or args.new_id):
        ap.error("--target/--targets-file cannot be combined with --from/--to")

    save = args.save
    if not save.exists():
        sys.exit(
            f"[!] Save file not found: {save}\n"
            f"    Set --save or WIN_USER env var (current: '{_WIN_USER}')."
        )

    # Build custom targets from --target / --targets-file (mutually exclusive above).
    custom_targets: list[tuple[int, str]] | None = None
    if args.targets_file is not None:
        if not args.targets_file.exists():
            sys.exit(f"[!] File not found: {args.targets_file}")
        try:
            custom_targets = _parse_targets_file(args.targets_file)
        except ValueError as exc:
            sys.exit(f"[!] {exc}")
    elif args.target is not None:
        try:
            custom_targets = _parse_target_ids(args.target)
        except ValueError as exc:
            sys.exit(f"[!] {exc}")

    if args.unblock:
        if not os.access(save, os.W_OK):
            sys.exit(f"[!] Save file is not writable: {save}")
        if custom_targets is not None:
            unblock_keys: set[int] | None = {k for k, _ in custom_targets}
        elif args.legendary:
            unblock_keys = set(_LEGENDARY_KEYS)
        else:
            unblock_keys = None  # all flagged items
        cmd_unblock(save, keys=unblock_keys, no_hash=args.no_hash)
    elif args.items:
        cmd_items(save)
    elif args.dump:
        cmd_dump(save)
    elif custom_targets is not None:
        if not os.access(save, os.W_OK):
            sys.exit(f"[!] Save file is not writable: {save}")
        cmd_legendary(save, no_hash=args.no_hash, watch=args.watch,
                      interval=args.interval, targets=custom_targets)
    elif args.legendary:
        if not os.access(save, os.W_OK):
            sys.exit(f"[!] Save file is not writable: {save}")
        cmd_legendary(save, no_hash=args.no_hash, watch=args.watch, interval=args.interval)
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
        cmd_gui(save)


if __name__ == "__main__":
    main()
