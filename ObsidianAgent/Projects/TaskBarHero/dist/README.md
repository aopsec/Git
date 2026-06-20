# TaskBarHero Save Editor — distribution

Authorized security-testing PoC for the F1 trust boundary (see `../SECURITY_ASSESSMENT.md`).
Edits the **local** `SaveFile_Live.es3` on the machine it runs on. Use only on your own save.

The tool is **self-contained**: the ES3 key and the `SystemInfo` HMAC key are baked in, and
it auto-detects the save at
`C:\Users\<you>\AppData\LocalLow\TesseractStudio\TaskbarHero\SaveFile_Live.es3`
via `%USERNAME%`. No game assets, config, or network access are needed.

## Two ways to run on another Windows PC

### A) Standalone `.exe` — no Python required (recommended, "just works")

On a build machine with **Python 3.9+**:

```bat
build_exe.bat
```

This produces `out\TBH_SaveEditor.exe`. Copy that **single file** to any Windows 10/11 x64
machine and run it — double-click for the interactive menu, or from a terminal:

```bat
TBH_SaveEditor.exe                 :: interactive TUI
TBH_SaveEditor.exe --help          :: all options
TBH_SaveEditor.exe --items         :: list inventory
TBH_SaveEditor.exe --legendary     :: category-aware legendary swap (+ auto-unblock)
TBH_SaveEditor.exe --unblock       :: clear IsBlocked/IsServerPendingItem/IsChaotic
```

### B) From source — for machines that already have Python

```bat
run_from_source.bat --help
```

First run creates a venv and installs `requirements.txt` automatically, then forwards all
arguments to `item_id_swap.py`.

## Safety

- Every write first copies the save to a timestamped backup
  (`SaveFile_Live.es3.bak.YYYYMMDD_HHMMSS`) and writes atomically (temp + rename), so a
  crash can never corrupt the save. Watch mode takes one session backup at start.
- To target a non-default save path: add `--save "C:\path\to\SaveFile_Live.es3"`.
- Close the game (or use `--watch`) before editing so the client reloads your changes.

## What's in this folder

| File | Purpose |
|------|---------|
| `build_exe.bat` | Build the standalone `TBH_SaveEditor.exe` (PyInstaller one-file). |
| `run_from_source.bat` | Run from `..\item_id_swap.py` via an auto-provisioned venv. |
| `requirements.txt` | `pycryptodome` + `rich`. |
| `.gitignore` | Keeps build outputs (`out/`, `build/`, venvs, the `.exe`) out of git. |

The canonical script lives one level up at `..\item_id_swap.py`.
