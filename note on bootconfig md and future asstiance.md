# z-manager: Architectural Review & Roadmap Note
# Topic: core/boot_config.py & The Heuristic Health Engine

## 1. Current State of `boot_config.py` (The Good)
The module acts as the "System Persistence Layer", mapping user intent (e.g., ZRAM tuning, hibernation) into permanent Linux configurations (`sysctl.d`, `grub.d`, `initramfs`). The current code is highly modernized, adhering to Python 3.11+ standards (walrus operators, robust error handling, `match` statements) and is significantly hardened compared to earlier iterations.

## 2. Completed Tasks (Done)
- [x] **Graceful Refusal (Safety Valve):** Added `detect_bootloader() != "grub"` guards to `set_zswap_in_grub`, `set_psi_in_grub`, and `update_grub_resume`. These functions now return a clear `TuneResult` with manual instructions for non-GRUB users.

## 3. Identified Architectural Problems & Engineering Traps (The Bad)
During our deep-dive analysis, several critical caveats were identified that could cause silent failures or system instability on non-Ubuntu/Debian systems:

### A. The "Default Value" Mirage (Destructive Override)
- **Status:** *Pending Health Engine implementation.*
- **The Problem:** When disabling the performance profile, the app hardcodes "defaults" (e.g., `vm.swappiness = 60`). This destroys any custom tuning the user or their distro (like Pop!_OS or SteamOS) had prior to installing z-manager.
- **The Solution:** Rely on the Linux "Hierarchy of Truth". To revert, the app should simply delete its own `/etc/sysctl.d/99-z-manager.conf` file and run `sysctl --system`. This safely falls back to the system's true vendor defaults (`/usr/lib/sysctl.d/`).

### C. The "Next Boot" Blindness (State Desync)
- **The Problem:** The app reads `/proc/cmdline` to check if a kernel parameter is active. This only shows the *live* state. If a user made a change but hasn't rebooted, the app assumes the parameter is missing and might create duplicate entries.
- **The Solution:** The logic must verify both the live state AND the on-disk configuration state before acting.

### D. The Initramfs "Nuclear Option" (System Risk)
- **The Problem:** Rebuilding the initial RAM disk (`update-initramfs`, `dracut`) is a heavy, risky operation. If the `/boot` partition is 100% full, the command will fail halfway, leaving the system unbootable.
- **The Solution:** Implement a pre-flight disk space check for the `/boot` partition before ever triggering an initramfs rebuild.

### E. The Path Hardcoding Wall (Distro Compatibility)
- **The Problem:** Arch Linux and Gentoo often do not use the `.d` drop-in directory structure for GRUB (`/etc/default/grub.d/`).
- **The Solution:** Need to detect if the OS supports `.d` drop-ins, or fallback to parsing/modifying the main `/etc/default/grub` file.

### F. The "Atomic Move" Bug (Cross-Device Failure)
- **The Problem:** Standard `os.rename` for atomic file writes fails with "Invalid cross-device link" if `/tmp` (where the temp file is made) and `/etc` are on different disk partitions.
- **The Solution:** Ensure `os_utils.atomic_write_to_file` uses `shutil.move` to handle cross-partition copying safely.

---

## 3. The Future Roadmap: The Heuristic Health Engine
To make `z-manager` truly smart without relying on heavy AI/LLMs, we are moving away from spaghetti `if/else` logic into a declarative **Heuristic Expert System**.

### Architecture: Separation of Concerns
We agreed that hardcoding paragraphs of text, warnings, and numbers in Python is poor design. We will split the engine into two parts:

1. **The Knowledge Base (`core/health_engine/rules.toml`):**
   - Written in TOML (Tom's Obvious, Minimal Language).
   - Contains 100% of the data: "Sane Zones" (min/max/ideal values), Contexts (ZRAM vs Disk), Warning strings, and Health Scores.
   - Easily translatable, readable, and editable by the community without touching Python code.

2. **The Processor/Sensor (`core/health_engine/processor.py`):**
   - Pure Python 3.11 logic using the built-in `tomllib`.
   - Its only job is to gather system data (RAM, Disk type, current sysctl values), cross-reference it with `rules.toml`, and output a dynamic "Health Score" and actionable advice to the GTK dashboard.
   - Capable of Context-Aware Intelligence (knowing 60 swappiness is bad if you have 128GB RAM) and Correlation Intelligence (knowing Zswap and ZRAM conflict).
