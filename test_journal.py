#!/usr/bin/env python3
# test_journal.py

import sys
from pathlib import Path

# Add the project root to the path so we can import our modules
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from modules.journal import list_zram_logs

def main():
    """
    Fetches and prints ZRAM logs to the console to test the backend module.
    """
    print("--- Attempting to fetch ZRAM logs ---")
    
    # We test with the default unit, zram0
    logs = list_zram_logs(unit="systemd-zram-setup@zram0.service")

    if not logs:
        print("No logs found.")
        return

    print(f"✅ Success! Found {len(logs)} log records.")
    for record in logs:
        print(f"[{record.timestamp}] (Priority: {record.priority}) {record.message}")
    print("--- Test complete ---")


if __name__ == "__main__":
    main()
