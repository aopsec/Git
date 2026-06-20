"""pytest suite for item_id_swap.py — TaskBarHero ES3 save editor.

Authorized security-testing PoC. Tests crypto round-trip, SystemInfo anti-tamper
hashing, item-field discovery, in-place ID substitution, the swap/list pipelines,
the argparse CLI, and certification of 6 specific in-game item IDs.

Certified item IDs:
  315102  Arco Rúnico[B]
  335102  Cetro Lendário[B]
  345092  Besta de Elite[B]
  415101  Flecha Tribal[A]
  435102  Tomo Carmesim[B]
  445102  Virote do Herói[B]
"""

import base64
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import item_id_swap  # noqa: E402

SCRIPT_PATH = Path(__file__).parent.parent / "item_id_swap.py"
_HEX64 = re.compile(r"\A[0-9a-f]{64}\Z")


@pytest.fixture
def make_es3_save(tmp_path):
    """Create an encrypted ES3 save file from a dict. Returns a factory function."""

    def _factory(data: dict, path: Path | None = None) -> Path:
        if path is None:
            path = tmp_path / "SaveFile_Live.es3"
        plaintext = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode()
        path.write_bytes(item_id_swap.encrypt_save(plaintext))
        return path

    return _factory


# ── Group 1: Crypto round-trip ───────────────────────────────────────────────────


def test_encrypt_decrypt_roundtrip(tmp_path):
    plaintext = b'{"itemId":"abc","count":42}'
    path = tmp_path / "save.es3"
    path.write_bytes(item_id_swap.encrypt_save(plaintext))
    assert item_id_swap.decrypt_save(path) == plaintext


def test_different_plaintexts_different_ciphertext():
    plaintext = b'{"itemId":"abc"}'
    first = item_id_swap.encrypt_save(plaintext)
    second = item_id_swap.encrypt_save(plaintext)
    assert first != second


def test_derive_key_deterministic():
    iv_a = b"\x00" * 16
    iv_b = b"\x11" * 16
    assert item_id_swap._derive_key(iv_a) == item_id_swap._derive_key(iv_a)
    assert item_id_swap._derive_key(iv_a) != item_id_swap._derive_key(iv_b)


def test_decrypt_save_too_short(tmp_path):
    path = tmp_path / "short.es3"
    path.write_bytes(b"\x00" * 8)
    with pytest.raises(ValueError):
        item_id_swap.decrypt_save(path)


# ── Group 2: SystemInfo hash ─────────────────────────────────────────────────────


def test_recompute_system_info_returns_base64():
    result = item_id_swap._recompute_system_info({"a": "b", "c": 1})
    assert len(result) == 44 and result.endswith("=")


def test_recompute_system_info_excludes_system_info_key():
    with_si = item_id_swap._recompute_system_info({"SystemInfo": "x", "a": "b"})
    without_si = item_id_swap._recompute_system_info({"a": "b"})
    assert with_si == without_si


def test_update_system_info_plain_string():
    data = {"SystemInfo": "oldhash", "x": 1}
    item_id_swap.update_system_info(data)
    new_val = data["SystemInfo"]
    assert len(new_val) == 44 and new_val.endswith("=")


def test_update_system_info_wrapped():
    data = {"SystemInfo": {"__type": "t", "value": "old"}, "x": 1}
    item_id_swap.update_system_info(data)
    new_val = data["SystemInfo"]["value"]
    assert len(new_val) == 44 and new_val.endswith("=")
    assert data["SystemInfo"]["__type"] == "t"


def test_update_system_info_skip():
    data = {"SystemInfo": "oldhash", "x": 1}
    item_id_swap.update_system_info(data, skip=True)
    assert data["SystemInfo"] == "oldhash"


def test_update_system_info_no_key():
    data = {"x": 1, "y": 2}
    item_id_swap.update_system_info(data)
    assert data == {"x": 1, "y": 2}


# ── Group 3: find_item_entries ───────────────────────────────────────────────────


def test_find_item_entries_basic():
    data = {
        "itemId": "sword",
        "itemSaveDatas": [],
        "runeId": "fire",
        "charKey": "hero",
    }
    keys = {path for path, _ in item_id_swap.find_item_entries(data)}
    assert {"itemId", "itemSaveDatas", "runeId", "charKey"} <= keys


def test_find_item_entries_nested():
    data = {"player": {"inventory": {"itemId": "potion"}}}
    paths = {path for path, _ in item_id_swap.find_item_entries(data)}
    assert "player.inventory.itemId" in paths


def test_find_item_entries_in_list():
    data = {"items": [{"itemId": "a"}, {"itemId": "b"}]}
    paths = {path for path, _ in item_id_swap.find_item_entries(data)}
    assert "items[0].itemId" in paths
    assert "items[1].itemId" in paths


def test_find_item_entries_no_false_positives():
    data = {"username": "bob", "level": 5, "score": 100}
    assert item_id_swap.find_item_entries(data) == []


def test_find_item_entries_missing_containers():
    data = {
        "inventorySaveDatas": [],
        "stashSaveDatas": [],
        "tradingStashSaveDatas": [],
        "RuneSaveData": {},
    }
    keys = {path for path, _ in item_id_swap.find_item_entries(data)}
    assert {
        "inventorySaveDatas",
        "stashSaveDatas",
        "tradingStashSaveDatas",
        "RuneSaveData",
    } <= keys


# ── Group 4: substitute_id ───────────────────────────────────────────────────────


def test_substitute_id_string_match():
    data = {"itemId": "old", "other": "old"}
    count = item_id_swap.substitute_id(data, "old", "new")
    assert count == 2
    assert data == {"itemId": "new", "other": "new"}


def test_substitute_id_no_match():
    data = {"itemId": "abc"}
    count = item_id_swap.substitute_id(data, "xyz", "new")
    assert count == 0
    assert data == {"itemId": "abc"}


def test_substitute_id_nested_dict():
    data = {"a": {"b": {"c": "old"}}}
    count = item_id_swap.substitute_id(data, "old", "new")
    assert count == 1
    assert data["a"]["b"]["c"] == "new"


def test_substitute_id_in_list():
    data = {"ids": ["old", "keep", "old"]}
    count = item_id_swap.substitute_id(data, "old", "new")
    assert count == 2
    assert data["ids"] == ["new", "keep", "new"]


def test_substitute_id_integer():
    data = {"itemId": 1001}
    count = item_id_swap.substitute_id(data, 1001, 2002)
    assert count == 1
    assert data["itemId"] == 2002


def test_substitute_id_bool_not_matched_as_int():
    data = {"flag": True, "n": 1}
    count = item_id_swap.substitute_id(data, 1, 99)
    assert count == 1
    assert data["flag"] is True
    assert data["n"] == 99


def test_substitute_id_no_key_replacement():
    data = {"old": "value"}
    count = item_id_swap.substitute_id(data, "old", "new")
    assert count == 0
    assert data == {"old": "value"}


def test_substitute_id_count_accuracy():
    data = {"a": "old", "b": ["old", {"c": "old"}], "d": "keep"}
    count = item_id_swap.substitute_id(data, "old", "new")
    assert count == 3


# ── Group 5: cmd_swap integration ────────────────────────────────────────────────


def test_cmd_swap_roundtrip(make_es3_save):
    save = make_es3_save({"itemId": "old_sword", "count": 1})
    item_id_swap.cmd_swap(save, "old_sword", "new_sword")
    data = json.loads(item_id_swap.decrypt_save(save))
    assert data["itemId"] == "new_sword"


def test_cmd_swap_backup_created(make_es3_save):
    save = make_es3_save({"itemId": "old"})
    item_id_swap.cmd_swap(save, "old", "new")
    backups = list(save.parent.glob(save.name + ".bak.*"))
    assert backups


def test_cmd_swap_no_match_does_not_write(make_es3_save):
    save = make_es3_save({"itemId": "present"})
    before = save.read_bytes()
    item_id_swap.cmd_swap(save, "absent", "new")
    assert save.read_bytes() == before


def test_cmd_swap_no_hash_flag(make_es3_save):
    save = make_es3_save({"itemId": "old", "SystemInfo": "sentinel_hash"})
    item_id_swap.cmd_swap(save, "old", "new", no_hash=True)
    data = json.loads(item_id_swap.decrypt_save(save))
    assert data["SystemInfo"] == "sentinel_hash"


# ── Group 6: cmd_list smoke tests ────────────────────────────────────────────────


def test_cmd_list_with_items(make_es3_save, capsys):
    save = make_es3_save({"itemSaveDatas": [{"itemId": "x"}]})
    item_id_swap.cmd_list(save)
    out = capsys.readouterr().out
    assert "itemSaveDatas" in out


def test_cmd_list_no_items(make_es3_save, capsys):
    save = make_es3_save({"username": "bob", "level": 3})
    item_id_swap.cmd_list(save)
    out = capsys.readouterr().out
    assert "No item-ID fields matched" in out


# ── Group 7: CLI via subprocess ──────────────────────────────────────────────────


def _run_cli(*args, timeout=30, **kwargs):
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        **kwargs,
    )


def test_main_help():
    result = _run_cli("--help")
    assert result.returncode == 0
    assert "usage" in result.stdout.lower()


def test_main_missing_save(tmp_path):
    missing = tmp_path / "does_not_exist.es3"
    result = _run_cli("--save", str(missing))
    assert result.returncode != 0


def test_main_interval_negative(make_es3_save):
    save = make_es3_save({"itemId": "old"})
    result = _run_cli(
        "--save", str(save), "--from", "old", "--to", "new",
        "--watch", "--interval", "-1",
        timeout=10,
    )
    assert result.returncode != 0
    assert result.stderr


def test_main_interval_zero(make_es3_save):
    save = make_es3_save({"itemId": "old"})
    result = _run_cli(
        "--save", str(save), "--from", "old", "--to", "new",
        "--watch", "--interval", "0",
        timeout=10,
    )
    assert result.returncode != 0
    assert result.stderr


def test_main_empty_from_to(make_es3_save):
    save = make_es3_save({"itemId": "old"})
    result = _run_cli("--save", str(save), "--from", "", "--to", "")
    assert result.returncode != 0


def test_main_dump_and_swap_conflict(make_es3_save):
    save = make_es3_save({"itemId": "old"})
    result = _run_cli("--save", str(save), "--dump", "--from", "old", "--to", "new")
    assert result.returncode != 0


# ── Group 8: SystemInfo format auto-detection ────────────────────────────────────


def test_update_system_info_base64_preserved(make_es3_save):
    """When the live SystemInfo value is base64-encoded, the new hash must also be base64."""
    # Simulate a 44-char base64 existing value (32-byte SHA-256 in base64 = 44 chars, ends '=')
    fake_b64 = base64.b64encode(hashlib.sha256(b"seed").digest()).decode()  # 44 chars, ends '='
    data = {"SystemInfo": fake_b64, "itemId": "x"}
    item_id_swap.update_system_info(data)
    new_val = data["SystemInfo"]
    assert len(new_val) == 44 and new_val.endswith("="), (
        f"Expected base64 output to preserve format, got: {new_val!r}"
    )


def test_update_system_info_always_base64():
    """update_system_info always writes base64 HMAC regardless of previous format."""
    data = {"SystemInfo": "a" * 64, "itemId": "x"}  # 64-char old-style value
    item_id_swap.update_system_info(data)
    new_val = data["SystemInfo"]
    assert new_val != "a" * 64  # value must change
    assert len(new_val) == 44 and new_val.endswith("=")


# ── Group 9: Certification — 6 specific TaskBarHero item IDs ─────────────────────
#
# Each parametrized run exercises the complete pipeline:
#   1. Build a synthetic ES3 save containing the certified item ID.
#   2. Confirm substitute_id replaces it correctly.
#   3. Confirm cmd_swap (encrypt → patch → reencrypt) round-trips cleanly.
#   4. Confirm a timestamped backup is created.
#   5. Confirm SystemInfo is updated after the swap.

CERTIFIED_IDS = [
    ("315102", "Arco Rúnico[B]"),
    ("335102", "Cetro Lendário[B]"),
    ("345092", "Besta de Elite[B]"),
    ("415101", "Flecha Tribal[A]"),
    ("435102", "Tomo Carmesim[B]"),
    ("445102", "Virote do Herói[B]"),
]

_SWAP_TARGET = "000000"


def _make_item_save(item_id: str, tmp_path: Path) -> Path:
    """ES3 save with a single itemSaveDatas entry for item_id.

    Uses integer ItemKey matching the real TBH save schema so that
    cmd_swap (which coerces IDs to int via _coerce_id) finds a match.
    """
    data = {
        "SystemInfo": "placeholder",
        "itemSaveDatas": [{"ItemKey": int(item_id), "qty": 1, "enhance": 0}],
        "inventorySaveDatas": [],
        "stashSaveDatas": [],
    }
    p = tmp_path / f"save_{item_id}.es3"
    plaintext = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode()
    p.write_bytes(item_id_swap.encrypt_save(plaintext))
    return p


@pytest.mark.parametrize("item_id, item_name", CERTIFIED_IDS)
def test_certified_substitute(item_id, item_name):
    """substitute_id replaces the certified ID in a raw dict — no I/O."""
    data = {"itemSaveDatas": [{"itemId": item_id, "qty": 1}]}
    n = item_id_swap.substitute_id(data, item_id, _SWAP_TARGET)
    assert n == 1, f"{item_name} ({item_id}): expected 1 replacement, got {n}"
    assert data["itemSaveDatas"][0]["itemId"] == _SWAP_TARGET


@pytest.mark.parametrize("item_id, item_name", CERTIFIED_IDS)
def test_certified_roundtrip(item_id, item_name, tmp_path):
    """Full pipeline: encrypt → cmd_swap → decrypt → verify ID replaced."""
    save = _make_item_save(item_id, tmp_path)

    item_id_swap.cmd_swap(save, item_id, _SWAP_TARGET)

    result = json.loads(item_id_swap.decrypt_save(save))
    # _make_item_save uses integer ItemKey; cmd_swap coerces IDs to int via _coerce_id
    found = [e.get("ItemKey") for e in result.get("itemSaveDatas", [])]
    assert int(_SWAP_TARGET) in found, (
        f"{item_name} ({item_id}): swap target not found after cmd_swap. Got: {found}"
    )
    assert int(item_id) not in found, (
        f"{item_name} ({item_id}): original ID still present after swap. Got: {found}"
    )


@pytest.mark.parametrize("item_id, item_name", CERTIFIED_IDS)
def test_certified_backup_created(item_id, item_name, tmp_path):
    """A timestamped .bak.YYYYMMDD_HHMMSS backup must exist after cmd_swap."""
    save = _make_item_save(item_id, tmp_path)
    item_id_swap.cmd_swap(save, item_id, _SWAP_TARGET)
    backups = list(tmp_path.glob(f"save_{item_id}.es3.bak.*"))
    assert len(backups) == 1, (
        f"{item_name} ({item_id}): expected 1 backup, found {len(backups)}"
    )
    assert re.search(r"\.bak\.\d{8}_\d{6}$", backups[0].name), (
        f"Unexpected backup name format: {backups[0].name}"
    )


@pytest.mark.parametrize("item_id, item_name", CERTIFIED_IDS)
def test_certified_system_info_updated(item_id, item_name, tmp_path):
    """SystemInfo hash must change after each certified swap (anti-tamper updated)."""
    save = _make_item_save(item_id, tmp_path)
    before = json.loads(item_id_swap.decrypt_save(save))["SystemInfo"]

    item_id_swap.cmd_swap(save, item_id, _SWAP_TARGET)

    after = json.loads(item_id_swap.decrypt_save(save))["SystemInfo"]
    assert after != before, (
        f"{item_name} ({item_id}): SystemInfo unchanged after swap (hash not updated)"
    )


# ── Group 10: Legendary-swap core (category selection, dedup, parsers) ────────────
#
# Previously untested region that every audit pass touched (dedup, p3 rejection,
# "clean after one run"). These lock in that behaviour against regression.


def _wrap_outer(items: list[dict], heroes: list[dict] | None = None) -> dict:
    """Build a realistic outer ES3 dict with itemSaveDatas nested in PlayerSaveData.value."""
    inner = {"itemSaveDatas": items, "heroSaveDatas": heroes or []}
    account = {"ownerSteamId": "76561198065188664"}
    return {
        "PlayerSaveData":  {"__type": "PD", "value": json.dumps(inner, separators=(",", ":"))},
        "AccountSaveData": {"__type": "AD", "value": json.dumps(account, separators=(",", ":"))},
        "SystemInfo":      {"__type": "SI", "value": "placeholder"},
    }


def _inner_items(outer: dict) -> list[dict]:
    return json.loads(outer["PlayerSaveData"]["value"])["itemSaveDatas"]


# ── _prefix_priority ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "item_key, target_key, expected",
    [
        (315001, 315102, 0),  # same 3-digit prefix (315) → p0 (best)
        (316001, 315102, 1),  # same 2-digit (31) only      → p1
        (325001, 315102, 2),  # same 1-digit (3) only       → p2
        (425001, 315102, 3),  # no overlap (4 vs 3)         → p3 (reject)
    ],
)
def test_prefix_priority(item_key, target_key, expected):
    assert item_id_swap._prefix_priority(item_key, target_key) == expected


# ── _find_best_candidate ──────────────────────────────────────────────────────────


def test_find_best_candidate_prefers_lowest_priority():
    items = [{"ItemKey": 325001}, {"ItemKey": 315001}]  # p2, then p0
    idx = item_id_swap._find_best_candidate(items, 315102, set(), set(), set())
    assert idx == 1  # the p0 match wins


def test_find_best_candidate_rejects_p3():
    items = [{"ItemKey": 425001}]  # no category overlap with 315102
    idx = item_id_swap._find_best_candidate(items, 315102, set(), set(), set())
    assert idx == -1


def test_find_best_candidate_skips_equipped():
    items = [{"ItemKey": 315001, "UniqueId": 7}]
    idx = item_id_swap._find_best_candidate(items, 315102, {7}, set(), set())
    assert idx == -1


def test_find_best_candidate_skips_used():
    items = [{"ItemKey": 315001}, {"ItemKey": 315002}]
    idx = item_id_swap._find_best_candidate(items, 315102, set(), {0}, set())
    assert idx == 1  # index 0 already used → next match


def test_find_best_candidate_skips_skip_keys():
    items = [{"ItemKey": 315001}]
    idx = item_id_swap._find_best_candidate(items, 315102, set(), set(), {315001})
    assert idx == -1


def test_find_best_candidate_tolerates_missing_itemkey():
    items = [{"qty": 1}, {"ItemKey": 315001}]  # first item malformed → must not crash
    idx = item_id_swap._find_best_candidate(items, 315102, set(), set(), set())
    assert idx == 1


# ── _apply_legendary_swaps ────────────────────────────────────────────────────────


def test_apply_legendary_swaps_basic():
    outer = _wrap_outer([{"ItemKey": 315001}])
    log = item_id_swap._apply_legendary_swaps(outer, [(315102, "Arco")])
    assert len(log) == 1
    assert _inner_items(outer)[0]["ItemKey"] == 315102


def test_apply_legendary_swaps_skips_already_present():
    outer = _wrap_outer([{"ItemKey": 315102}, {"ItemKey": 315001}])
    log = item_id_swap._apply_legendary_swaps(outer, [(315102, "Arco")])
    assert log == []  # target already owned → no swap, no re-injection


def test_apply_legendary_swaps_one_slot_per_target():
    outer = _wrap_outer([{"ItemKey": 315001}, {"ItemKey": 315002}])
    log = item_id_swap._apply_legendary_swaps(outer, [(315102, "Arco")])
    keys = [it["ItemKey"] for it in _inner_items(outer)]
    assert keys.count(315102) == 1  # exactly one slot converted


def test_apply_legendary_swaps_rejects_wrong_category():
    outer = _wrap_outer([{"ItemKey": 425001}])  # p3 vs 315102
    log = item_id_swap._apply_legendary_swaps(outer, [(315102, "Arco")])
    assert log == []
    assert _inner_items(outer)[0]["ItemKey"] == 425001  # untouched


# ── _parse_target_ids / _parse_targets_file ───────────────────────────────────────


def test_parse_target_ids_valid():
    assert item_id_swap._parse_target_ids(["315102", " 335102 ", ""]) == [
        (315102, "315102"),
        (335102, "335102"),
    ]


def test_parse_target_ids_invalid_raises():
    with pytest.raises(ValueError):
        item_id_swap._parse_target_ids(["notanint"])


def test_parse_targets_file_valid(tmp_path):
    f = tmp_path / "ids.txt"
    f.write_text("315102\n# a comment\n335102  # inline\n\n", encoding="utf-8")
    assert item_id_swap._parse_targets_file(f) == [
        (315102, "315102"),
        (335102, "335102"),
    ]


def test_parse_targets_file_invalid_raises(tmp_path):
    f = tmp_path / "bad.txt"
    f.write_text("315102\noops\n", encoding="utf-8")
    with pytest.raises(ValueError):
        item_id_swap._parse_targets_file(f)


# ── _build_preview statuses ───────────────────────────────────────────────────────


def test_build_preview_statuses():
    items = [{"ItemKey": 335102}, {"ItemKey": 315001}]  # present target, p0 candidate
    rows = item_id_swap._build_preview(
        items, set(), [(335102, "Cetro"), (315102, "Arco"), (445102, "Virote")]
    )
    status_by_target = {r[0]: r[4] for r in rows}
    assert status_by_target[335102] == "present"   # already owned
    assert status_by_target[315102] == "ready"     # p0 candidate available
    assert status_by_target[445102] == "no match"  # no category-compatible item


# ── Group 11: Watch-path atomicity + backup helpers (regression for review fix) ───


def test_atomic_write_bytes_no_tmp_left(tmp_path):
    target = tmp_path / "out.bin"
    item_id_swap._atomic_write_bytes(target, b"hello")
    assert target.read_bytes() == b"hello"
    assert not list(tmp_path.glob("*.tmp")), "temp staging file must be cleaned up"


def test_timestamped_backup(tmp_path):
    save = tmp_path / "SaveFile_Live.es3"
    save.write_bytes(b"\x01\x02\x03")
    backup = item_id_swap._timestamped_backup(save)
    assert backup.exists()
    assert backup.read_bytes() == b"\x01\x02\x03"
    assert re.search(r"\.bak\.\d{8}_\d{6}$", backup.name)


def test_patch_legendary_locked_atomic_and_decryptable(tmp_path):
    """The watch-path writer must produce a valid, decryptable save and leave no .tmp."""
    save = tmp_path / "SaveFile_Live.es3"
    outer = _wrap_outer([{"ItemKey": 315001}])
    save.write_bytes(item_id_swap.encrypt_save(
        json.dumps(outer, separators=(",", ":"), ensure_ascii=False).encode()
    ))

    n = item_id_swap._patch_legendary_locked(save, no_hash=False, targets=[(315102, "Arco")])

    assert n == 1
    result = json.loads(item_id_swap.decrypt_save(save))  # must still decrypt
    keys = [it["ItemKey"] for it in json.loads(result["PlayerSaveData"]["value"])["itemSaveDatas"]]
    assert 315102 in keys
    assert not list(tmp_path.glob("*.tmp")), "atomic write must not leave a .tmp file"


# ── Group 12: Unblock (IsBlocked = unlocked) ─────────────────────────────────────


def _blocked_item(item_key: int, **flags) -> dict:
    base = {"ItemKey": item_key, "UniqueId": item_key * 10,
            "IsBlocked": True, "IsServerPendingItem": False, "IsChaotic": False}
    base.update(flags)
    return base


def test_apply_unblock_all_clears_every_flag():
    outer = _wrap_outer([
        _blocked_item(315102, IsBlocked=True, IsServerPendingItem=True, IsChaotic=True),
        _blocked_item(999999, IsBlocked=False),  # not flagged → untouched
    ])
    log = item_id_swap._apply_unblock(outer, keys=None)
    items = _inner_items(outer)
    assert items[0]["IsBlocked"] is False
    assert items[0]["IsServerPendingItem"] is False
    assert items[0]["IsChaotic"] is False
    assert len(log) == 1 and log[0][1] == 315102
    assert set(log[0][2]) == {"IsBlocked", "IsServerPendingItem", "IsChaotic"}


def test_apply_unblock_scoped_to_keys():
    outer = _wrap_outer([_blocked_item(315102), _blocked_item(445102)])
    log = item_id_swap._apply_unblock(outer, keys={315102})
    items = {it["ItemKey"]: it for it in _inner_items(outer)}
    assert items[315102]["IsBlocked"] is False  # in scope → cleared
    assert items[445102]["IsBlocked"] is True   # out of scope → untouched
    assert [r[1] for r in log] == [315102]


def test_apply_unblock_noop_when_nothing_flagged():
    outer = _wrap_outer([{"ItemKey": 315102, "IsBlocked": False}])
    assert item_id_swap._apply_unblock(outer, keys=None) == []


def test_patch_legendary_locked_unblocks_present_target(tmp_path):
    """A blocked legendary already in inventory must be unblocked (no swap needed)."""
    save = tmp_path / "SaveFile_Live.es3"
    outer = _wrap_outer([_blocked_item(315102)])  # target already present, blocked
    save.write_bytes(item_id_swap.encrypt_save(
        json.dumps(outer, separators=(",", ":"), ensure_ascii=False).encode()
    ))

    n = item_id_swap._patch_legendary_locked(save, no_hash=False, targets=[(315102, "Arco")])

    assert n == 1  # one unblock, zero swaps
    items = json.loads(json.loads(item_id_swap.decrypt_save(save))["PlayerSaveData"]["value"])["itemSaveDatas"]
    assert items[0]["IsBlocked"] is False


def test_cmd_unblock_roundtrip_and_backup(tmp_path):
    save = tmp_path / "SaveFile_Live.es3"
    outer = _wrap_outer([_blocked_item(315102), _blocked_item(445102)])
    outer["SystemInfo"] = {"__type": "SI", "value": "x" * 44}
    save.write_bytes(item_id_swap.encrypt_save(
        json.dumps(outer, separators=(",", ":"), ensure_ascii=False).encode()
    ))

    item_id_swap.cmd_unblock(save, keys=None)

    items = json.loads(json.loads(item_id_swap.decrypt_save(save))["PlayerSaveData"]["value"])["itemSaveDatas"]
    assert all(it["IsBlocked"] is False for it in items)
    assert list(tmp_path.glob("SaveFile_Live.es3.bak.*")), "unblock must back up before writing"


def test_cmd_unblock_no_change_no_backup(tmp_path):
    save = tmp_path / "SaveFile_Live.es3"
    outer = _wrap_outer([{"ItemKey": 315102, "IsBlocked": False}])
    save.write_bytes(item_id_swap.encrypt_save(
        json.dumps(outer, separators=(",", ":"), ensure_ascii=False).encode()
    ))
    before = save.read_bytes()
    item_id_swap.cmd_unblock(save, keys=None)
    assert save.read_bytes() == before  # nothing flagged → no write
    assert not list(tmp_path.glob("SaveFile_Live.es3.bak.*"))


# ── Group 13: End-to-end swap+unblock certification ──────────────────────────────


def test_e2e_swap_unblock_certification(tmp_path):
    """Full pipeline cert: an owned-but-blocked target + a same-category swap source
    (also blocked) → cmd_legendary swaps, unblocks both, re-signs. Certifies the
    resulting save is decryptable, has both targets present AND unlocked, and carries
    a VALID anti-tamper HMAC (i.e. a save the game would accept)."""
    save = tmp_path / "SaveFile_Live.es3"
    outer = _wrap_outer([
        _blocked_item(315102),                       # owned target, blocked
        _blocked_item(335001),                       # p0 swap source for 335102, blocked
    ])
    save.write_bytes(item_id_swap.encrypt_save(
        json.dumps(outer, separators=(",", ":"), ensure_ascii=False).encode()
    ))

    item_id_swap.cmd_legendary(save, targets=[(315102, "Arco"), (335102, "Cetro")])

    result = json.loads(item_id_swap.decrypt_save(save))            # 1) still decryptable
    items = json.loads(result["PlayerSaveData"]["value"])["itemSaveDatas"]
    by_key = {it["ItemKey"]: it for it in items}
    assert 315102 in by_key and 335102 in by_key                   # 2) owned + swapped present
    assert by_key[315102]["IsBlocked"] is False                    # 3) owned target unblocked
    assert by_key[335102]["IsBlocked"] is False                    # 4) swapped target unblocked
    assert 335001 not in by_key                                    # 5) source consumed by swap
    # 6) anti-tamper HMAC matches the written payload → game would accept the save
    assert result["SystemInfo"]["value"] == item_id_swap._recompute_system_info(result)
    assert list(tmp_path.glob("*.bak.*"))                          # 7) backup taken
    assert not list(tmp_path.glob("*.tmp"))                        # 8) atomic, no temp left

