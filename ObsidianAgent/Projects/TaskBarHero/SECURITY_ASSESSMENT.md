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

### F1.b — Swaps are NOT placebo (the stat effect is real), certified

A swapped `ItemKey` changes the *actual* combat stats, not just the displayed name/icon —
the display, grade, base/inherent stats, and unique-mod speciality all key off the same
`ItemKey`, so there is no separate "real stat" source the swap could miss.

**Empirical (master charts extracted from `resources.assets` via UnityPy).** The CsvHelper
charts `ItemInfoData` and `GearInfoData` resolve by key. The 6 PoC targets are real
`ARCANA`-grade `GEAR` weapons with concrete stat rows, e.g.:

| ItemKey | Type / Grade | BaseStat1 | vs COMMON sibling | Inherent stats |
|---|---|---|---|---|
| 315102 | BOW / ARCANA | 298 | 2 (×149) | AttackDamage, AttackDamage, CooldownReduction |
| 345092 | CROSSBOW / ARCANA | 344 | 1 | AttackDamage, AttackDamage, AttackSpeed |
| 445102 | BOLT / ARCANA | 1292 | 200 (×6) | AttackDamage, CriticalDamage, AreaOfEffect |

Grade ladder (10 tiers): COMMON < UNCOMMON < RARE < LEGENDARY < **ARCANA** < IMMORTAL <
BEYOND < CELESTIAL < DIVINE < COSMIC. ARCANA is mid-ladder (so even stronger keys exist),
but the swap delta vs a low-grade item is 4×–150× on BaseStat1 alone, plus three named
inherent stats per item.

**Accuracy note on "specialities".** These 6 ARCANA weapons carry an *empty* `UniqueModKey`
— their power is the BaseStat + three inherent stats, not a named `UniqueMod`. The
`UniqueMod` mechanism (e.g. `ArrowRainCriticalCooldown`, `FlameHydraBerserk` in
`UniqueModInfoData`) is real and key-resolved, but is attached to *other* items; swapping to
a key that *does* carry a `UniqueModKey` would grant that speciality too (same code path).

**Disassembly (GameAssembly.dll, capstone) — combat consumes the key-resolved stats.**
The runtime-item setup `edj()` (VA `0x1808FC860`):
- reads `ItemInfoData.GearKey` (`this.beni+0x60`) and resolves `GearInfoData` via the
  `Dictionary<int, GearInfoData>` lookup (`lzd`/`heo(int)`),
- reads `GearInfoData.BaseStat1_Value` (`+0x34`), `BaseStat2_Value` (`+0x38`), and the
  inherent-stat values, wraps each in CodeStage ACTk `ObscuredInt` (`0x1806eb9b0`),
- stores them into the live item's `GearModData` stat fields (`[this+0x58/0x68/0x78]`).

Chain: `ItemKey → ItemInfoData → GearKey → GearInfoData → BaseStat/InherentStat →
ObscuredInt → live item GearModData → hero stat sum`. Every link is driven by the key, and
the stat values are anti-tamper-guarded (`ObscuredInt`), which is only done for values the
game's combat math actually uses. **Conclusion: the swap is a genuine stat grant, not a
cosmetic relabel.**

## Crypto provenance (locally reverse-engineered)

| Layer | Derivation | Source artifact |
|---|---|---|
| ES3 payload | AES-128-CBC, `key = PBKDF2-SHA1(password, salt=IV, 100, 16B)` | `password` from `ES3Defaults` ScriptableObject (`resources.assets`), **not** a code literal |
| `SystemInfo` anti-tamper | `HMAC-SHA256(key=bgbp, msg=UTF8(av + "\|" + pv + "\|" + ownerSteamId))`, base64 | `bgbp = PBKDF2-SHA1(fim+fiy, salt, 12000)[:32]`; `fim`/`fiy`/`salt` recovered from `GameAssembly.dll` (IL2CPP) |

Exact constants and the IL2CPP derivation notes live inline in
[`item_id_swap.py`](item_id_swap.py) (crypto-constants section). Both layers are
**fully recoverable client-side**, which is the precondition for F1.

## Test coverage

`tests/test_item_id_swap.py` (pytest, 90 tests) covers the crypto round-trip, the
`SystemInfo` HMAC (base64), ID substitution, the legendary-swap selection/dedup/category
logic, the unblock logic, the CLI surface, atomic-write/backup safety, certifies the 6
target item IDs, and includes an end-to-end swap+unblock+resign pipeline cert.

## Full certification — swap + unblock

Differential stat profile of the 6 swap targets (decoded `GearInfoData`, vs the COMMON
same-type sibling — proves a large, real, key-resolved stat grant):

| ItemKey | Grade / Type | BaseStat1 (vs COMMON) | Inherent stats (type/mod/value) |
|---|---|---|---|
| 315102 | ARCANA BOW | 298 (vs 2, ×149) | AttackDamage/FLAT/73 · AttackDamage/ADD/661 · CDR/FLAT/68 |
| 335102 | ARCANA SCEPTER | 264 (vs 1, ×264) | CDR/FLAT/68 · AttackDamage/ADD/661 · CritDamage/FLAT/607 |
| 345092 | ARCANA CROSSBOW | 344 (vs 1, ×344) | AttackDamage/FLAT/59 · AttackDamage/ADD/595 · AttackSpeed/MULT/139 |
| 415101 | ARCANA ARROW | 338 (vs 80, ×4) | AttackDamage/FLAT/37 · CritDamage/FLAT/345 · ProjectileDmg/ADD/279 |
| 435102 | ARCANA TOME | 198 (vs 70, ×3) | AreaOfEffect/ADD/202 · BlockChance/FLAT/74 · CDR/FLAT/53 |
| 445102 | ARCANA BOLT | 1292 (vs 200, ×6) | AttackDamage/FLAT/37 · CritDamage/FLAT/345 · AreaOfEffect/ADD/202 |

### Certification matrix

| # | Claim | Status | Evidence |
|---|---|---|---|
| C1 | Stats/grade resolve by `ItemKey` (save holds only identity + `EnchantData`) | **PASS** | `ItemSaveData` schema (dump.cs L356742); `ItemInfoData`/`GearInfoData` `ClassMap` charts |
| C2 | Swap targets are real, distinct, higher-tier rows (not a no-op label) | **PASS** | UnityPy extract: 6 = ARCANA weapons, 4×–344× BaseStat1 vs COMMON, 3 inherent stats each |
| C3 | Swapped stats are consumed by the runtime item (not cosmetic) | **PASS** | capstone: `edj()` @`0x1808FC860` GearKey→`GearInfoData`→BaseStat/Inherent→`ObscuredInt`→`GearModData` |
| C4 | `IsBlocked` is a live, anti-cheat-guarded client gate | **PASS** | capstone: `cmz()` reads `+0x21`→`ObscuredBool`@`+0x180`; getter `ive()` @`0x1808FE4E0` |
| C5 | `--unblock` clears the gate at the save layer (before ACTk loads it) | **PASS** | live save 9→0 blocked, HMAC valid; `_apply_unblock` + e2e pytest |
| C6 | Full swap+unblock+resign yields a game-acceptable save | **PASS** | `test_e2e_swap_unblock_certification`: decryptable, targets present+unlocked, HMAC valid, atomic+backup |
| C7 | Which behaviours `ive()` (IsBlocked) gates | **RESOLVED** | direct-call xref + gate-branch disasm (below) |
| C8 | Server re-asserts `IsBlocked` after sync (persistence) | **OUT OF SCOPE** | server-side code; only a live play→sync→re-check behavioural test can answer |

**Net:** the swap+unblock is fully certified on the **client** axis (C1–C7): a swapped,
unblocked item is a genuine, anti-cheat-consumed stat grant in a save the game will load and
accept, and `IsBlocked` gates exactly the item-manipulation surfaces. The only unresolved
item is server-side persistence (C8), which is not statically knowable.

### C7 — what `IsBlocked` gates (call-site xref)

Direct (`E8 rel32`) call-site scan of `GameAssembly.dll` for the `ive()` getter
(VA `0x1808FE4E0`), each site mapped to its containing method via `dump.cs`:
**18 call sites** across these domains —

| Caller (class :: method) | Surface gated |
|---|---|
| `GearSlot :: lcw(uc)`, `lcz(vd) → bool` | **equip slot** (usability/interactable) |
| `rj :: {mwz,nze}→SlotActionResult`, `{fro,gks,hzf,hzr,igk,lof}→string` | **slot actions** (equip/unequip/use) |
| `re :: hxj(MoveRequest) → ValidationResult` | **move/transfer validation** |
| `vb.Cube :: ina(uc,bool) → EAddCubeResult` | **cube / synthesis** (craft/dismantle) |
| `vb.Stash :: jhf/jhc`, `vb.StashCache :: jik()` | **stash / storage** |
| `vb.ue.uc.ub :: MoveNext()`, `vg :: joz()` | item iterators / predicates |

**Gate-branch proof** — `GearSlot.lcz` (`0x180A07850`):
```asm
0x180A078C3: call 0x1808FE4E0   ; ive()  = IsBlocked
0x180A078C8: xor  al, 1         ; al = !IsBlocked
0x180A078CD: movzx edx, al
0x180A078D3: call 0x1808FC170   ; set slot usable/interactable = !IsBlocked
```
i.e. a blocked item makes its gear slot **not usable**. **Crucially, the stat builder
`edj()` does NOT call `ive()`** (0 xrefs) — so `IsBlocked` is an *eligibility / manipulation*
gate (equip, slot-action, move, cube, stash), **not** a raw-stat suppressor. Clearing it
(`--unblock`) restores full item usability, which is what the `IsBlocked = unlocked` fix does.
