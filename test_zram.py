# === PASTE THIS ENTIRE BLOCK ===
print("--- Starting minimal python-systemd test ---")
try:
    # 1. We directly import the library, bypassing the failing shell check.
    from systemd import journal
    print("✅  'systemd.journal' module imported successfully.")

    # 2. Create a journal reader object.
    reader = journal.Reader()
    print("✅  Journal reader created.")

    # 3. Filter for the specific ZRAM service logs.
    unit_name = "systemd-zram-setup@zram0.service"
    reader.add_match(_SYSTEMD_UNIT=unit_name)
    print(f"✅  Filtered for unit: {unit_name}")

    # 4. Go to the end of the log to get the most recent entries.
    reader.seek_tail()
    print("✅  Seeked to tail of journal.")

    # 5. Read the last 5 entries backwards and print them.
    print("\n--- Reading last 5 log entries ---")
    count = 0
    while count < 5:
        # get_previous() is an efficient way to read backwards.
        entry = reader.get_previous()
        if not entry:
            break # Stop if there are no more entries.
        
        message = entry.get('MESSAGE', 'No message found.')
        timestamp = entry.get('__REALTIME_TIMESTAMP', 'No timestamp')
        print(f"[{timestamp}] {message}")
        count += 1

    if count == 0:
        print("No log entries were found for this unit.")

except Exception as e:
    print(f"\n⚠️  AN ERROR OCCURRED: {e}")

finally:
    print("--- Test complete ---")
# === END OF BLOCK ===
