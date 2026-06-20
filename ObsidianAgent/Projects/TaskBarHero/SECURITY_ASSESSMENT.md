# TaskBarHero — Security Assessment (Authorized PoC)

> **Scope & authorization.** This is authorized security-testing research bounded to
> **local save-file analysis** of TaskBarHero on the researcher's own machine. No live
> game servers, accounts other than the researcher's own, or third-party systems are
> targeted. All reverse-engineering findings below were derived locally from the
> shipped client binary and asset bundles; no external reference prose is reproduced
> here (per the repo `cyberref` convention).

## Findings

### F1 — `PlayerDataTransactionWrite` trust boundary (client-authored item grants)

**Summary.** The client serializes the full player inventory into the local ES3 save
and is trusted to author item grants. Because the save is client-side encrypted with a
key fully recoverable from the shipped client (see Crypto provenance), an attacker can
mint arbitrary items (e.g. legendary-tier `ItemKey`s) and re-seal the save with a valid
anti-tamper hash. If the backend accepts the resulting `PlayerDataTransactionWrite`
without server-side validation of item legitimacy, the grant persists.

**PoC.** [`item_id_swap.py`](item_id_swap.py) decrypts the save, swaps source-slot
`ItemKey`s to target legendary IDs by category similarity, recomputes the `SystemInfo`
HMAC, and re-encrypts. `--watch` races the server-sync overwrite window.

**Impact.** Unauthorized inventory inflation / economy bypass, if the server trusts
client-authored writes.

**F1.a — `IsBlocked` gate is client-writable.** The per-item gate flags
(`IsBlocked`, `IsServerPendingItem`, `IsChaotic`) live in `ItemSaveData` and are part
of the client-authored save. The game resolves all stats/specialities by `ItemKey`, but
a gated (`IsBlocked=true`) item is neutralized, so the speciality does not run until the
flag is cleared. `item_id_swap.py --unblock` clears the flags and re-seals the save with
a valid HMAC — the write-side of F1: a legitimate-looking save with `IsBlocked=false`.
Whether the grant persists depends entirely on whether the backend re-validates on sync
(`CheckServerPendingItemValid` / `InventoryProcessPending`) or trusts the client write.

**Certified by disassembly (GameAssembly.dll, capstone).** `IsBlocked` is a *live,
anti-cheat-protected* client gate — not cosmetic and not dead:
- The runtime-item field-copier `cmz(ItemSaveData)` (VA `0x1808FBC10`) reads
  `ItemSaveData+0x21` (IsBlocked) with `movzx edx, byte [rbx+0x21]`, passes it to the
  CodeStage ACTk `ObscuredBool` constructor (`0x1806df940`), and stores the obscured
  value into the live item at `this+0x180` (sibling to IsChaotic@`+0x168` from `+0x20`).
- A dedicated getter `ive()` (VA `0x1808FE4E0`) loads `this+0x180`/`+0x188` and calls the
  ACTk decode (`0x1806df9c0`) to return the bool — i.e. game code queries "is blocked?".
- Wrapping the flag in `ObscuredBool` means the in-memory value is anti-tamper-guarded,
  which is only done for values the client actually checks. The on-disk JSON save is
  edited *before* ACTk loads it, so `--unblock` is effective at load time.

What disassembly cannot answer (server-side, not in the client binary): whether the
backend re-asserts `IsBlocked` after sync. Enumerating every `ive()` call site
(equip vs stat-contribution vs trade) needs xref tooling (Ghidra/IDA).

**Remediation.** Treat the client save as untrusted input: validate item grants
server-side (provenance, drop tables, transaction ledger) rather than relying on the
client-side `SystemInfo` HMAC, which is a tamper-evidence signal an attacker can forge.

## Crypto provenance (locally reverse-engineered)

| Layer | Derivation | Source artifact |
|---|---|---|
| ES3 payload | AES-128-CBC, `key = PBKDF2-SHA1(password, salt=IV, 100, 16B)` | `password` from `ES3Defaults` ScriptableObject (`resources.assets`), **not** a code literal |
| `SystemInfo` anti-tamper | `HMAC-SHA256(key=bgbp, msg=UTF8(av + "\|" + pv + "\|" + ownerSteamId))`, base64 | `bgbp = PBKDF2-SHA1(fim+fiy, salt, 12000)[:32]`; `fim`/`fiy`/`salt` recovered from `GameAssembly.dll` (IL2CPP) |

Exact constants and the IL2CPP derivation notes live inline in
[`item_id_swap.py`](item_id_swap.py) (crypto-constants section). Both layers are
**fully recoverable client-side**, which is the precondition for F1.

## Test coverage

`tests/test_item_id_swap.py` (pytest) covers the crypto round-trip, the `SystemInfo`
HMAC (base64), ID substitution, the legendary-swap selection/dedup/category logic, the
CLI surface, atomic-write/backup safety, and certifies the 6 target item IDs end-to-end.
