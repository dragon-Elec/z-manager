# zman/core/profiles.py
"""
Manages configuration profiles for ZRAM and system tuning.

This module implements a hybrid approach:
- It provides reliable, hardcoded built-in profiles that cannot be modified by the user.
- It scans a user-specific directory for custom .json profiles, allowing for extensibility.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

_LOGGER = logging.getLogger(__name__)

# --- Reliable Built-in Profiles ---
# These are hardcoded into the application for guaranteed availability.
_BUILTIN_PROFILES: Dict[str, Dict[str, Any]] = {
    "Desktop / Gaming (Recommended)": {
        "zram-size": "ram",
        "compression-algorithm": "zstd",
        "swap-priority": 100,
        "description": "Optimized for responsiveness on systems with 8GB+ RAM."
    },
    "Server (Conservative)": {
        "zram-size": "min(ram / 2, 8192)",
        "compression-algorithm": "lzo-rle",
        "swap-priority": 75,
        "description": "Balances performance with lower CPU overhead, suitable for servers."
    },
}

# --- User-Defined Profiles ---
# We use a standard XDG Base Directory Specification location.
_PROFILE_DIR = Path(os.path.expanduser("~/.config/zman/profiles"))


def _load_user_profiles() -> Dict[str, Dict[str, Any]]:
    """Scans the user profile directory for .json files and parses them."""
    user_profiles: Dict[str, Dict[str, Any]] = {}
    if not _PROFILE_DIR.is_dir():
        return {}

    _LOGGER.info(f"Scanning for user profiles in {_PROFILE_DIR}...")
    for profile_path in _PROFILE_DIR.glob("*.json"):
        profile_name = profile_path.stem  # Use filename without extension as the name
        try:
            with profile_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                user_profiles[profile_name] = data
                _LOGGER.info(f"Successfully loaded user profile: '{profile_name}'")
            else:
                _LOGGER.warning(f"Skipping profile '{profile_path.name}': content is not a valid dictionary.")
        except json.JSONDecodeError:
            _LOGGER.error(f"Failed to load '{profile_path.name}': Invalid JSON format.")
        except (IOError, PermissionError) as e:
            _LOGGER.error(f"Failed to read '{profile_path.name}': {e}")

    return user_profiles


# --- Public API Functions ---

def get_all_profiles() -> Dict[str, Dict[str, Any]]:
    """Returns a merged dictionary of built-in and user-defined profiles."""
    all_profiles = _BUILTIN_PROFILES.copy()
    # User profiles can override built-in ones if they have the same name
    all_profiles.update(_load_user_profiles())
    return all_profiles


def list_profile_names() -> List[str]:
    """
    Returns a sorted list of all available profile names for use in a UI dropdown.
    Includes a placeholder for the user's current settings.
    """
    profile_names = list(get_all_profiles().keys())
    # Add a static entry for the UI to represent the live system state
    return sorted(["Current System Settings"] + profile_names)


def load_profile(name: str) -> Dict[str, Any] | None:
    """Loads a profile by name from the combined list of built-in and user profiles."""
    if name == "Current System Settings":
        return None # This is a special UI value, not a loadable profile
    return get_all_profiles().get(name)


def save_profile(name: str, profile_data: Dict[str, Any]) -> bool:
    """
    Saves a custom user profile as a JSON file.
    Prevents overwriting built-in profile names.
    """
    if name in _BUILTIN_PROFILES:
        _LOGGER.error(f"Cannot save profile '{name}': name is reserved for a built-in profile.")
        return False

    try:
        # Ensure the directory exists before writing
        _PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        profile_path = _PROFILE_DIR / f"{name}.json"

        with profile_path.open("w", encoding="utf-8") as f:
            json.dump(profile_data, f, indent=4)

        _LOGGER.info(f"Successfully saved user profile to {profile_path}")
        return True
    except (IOError, PermissionError, TypeError) as e:
        _LOGGER.error(f"Failed to save profile '{name}': {e}")
        return False


def delete_profile(name: str) -> bool:
    """
    Deletes a custom user profile file.
    Prevents deleting built-in profiles.
    """
    if name in _BUILTIN_PROFILES:
        _LOGGER.error(f"Cannot delete profile '{name}': it is a built-in profile.")
        return False

    profile_path = _PROFILE_DIR / f"{name}.json"
    if not profile_path.exists():
        _LOGGER.warning(f"Cannot delete profile '{name}': file does not exist.")
        return False

    try:
        profile_path.unlink()
        _LOGGER.info(f"Successfully deleted user profile: {profile_path}")
        return True
    except (IOError, PermissionError) as e:
        _LOGGER.error(f"Failed to delete profile '{name}': {e}")
        return False
