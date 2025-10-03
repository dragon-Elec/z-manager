#!/usr/bin/env python3
# test_writeback.py

import sys
import argparse
from typing import List

# This is a critical assumption: the script expects the provided files
# to be in a subdirectory named 'core'.
try:
    from core.zdevice_ctl import get_writeback_status, ensure_writeback_state
    from core.os_utils import is_root
except ImportError as e:
    print(f"Error: Failed to import from 'core' module. Make sure this script is in the parent directory of 'core/'.\nDetails: {e}")
    sys.exit(1)

def check_permissions():
    """Ensure the script is run as root."""
    if not is_root():
        print("Error: This script requires root privileges. Please run with 'sudo'.")
        sys.exit(1)

def handle_check(args):
    """Handler for the 'check' command."""
    print(f"--> Checking writeback status for {args.device}...")
    try:
        status = get_writeback_status(args.device)
        print("...Success.")
        print(f"  Device: {status.device}")
        print(f"  Backing Device: {status.backing_dev or 'None'}")
    except Exception as e:
        print(f"...Error: {e}")

def handle_set(args):
    """Handler for the 'set' command."""
    print(f"--> Ensuring writeback device for {args.device} is set to {args.backing_device}...")
    # force=True is required because the device is active [SWAP]
    result = ensure_writeback_state(args.device, args.backing_device, force=True)
    
    print("\n--- Actions Taken ---")
    for action in result.actions:
        status = "✅" if action.success else "❌"
        print(f"  {status} {action.name}: {action.message}")
    print("---------------------")

    if result.success:
        print(f"\n...Overall Success: {result.message}")
    else:
        print(f"\n...Overall Failure: {result.message}")

def handle_clear(args):
    """Handler for the 'clear' command."""
    print(f"--> Ensuring writeback is cleared for {args.device}...")
    # force=True is required because the device is active [SWAP]
    result = ensure_writeback_state(args.device, None, force=True)

    print("\n--- Actions Taken ---")
    for action in result.actions:
        status = "✅" if action.success else "❌"
        print(f"  {status} {action.name}: {action.message}")
    print("---------------------")

    if result.success:
        print(f"\n...Overall Success: {result.message}")
    else:
        print(f"\n...Overall Failure: {result.message}")

def main(argv: List[str]):
    parser = argparse.ArgumentParser(description="Test zram writeback functionality.")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # Check command
    parser_check = subparsers.add_parser("check", help="Check the current writeback device.")
    parser_check.add_argument("device", help="The zram device name (e.g., zram0).")
    parser_check.set_defaults(func=handle_check)

    # Set command
    parser_set = subparsers.add_parser("set", help="Set the writeback device.")
    parser_set.add_argument("device", help="The zram device name.")
    parser_set.add_argument("backing_device", help="Path to the backing block device (e.g., /swapfile).")
    parser_set.set_defaults(func=handle_set)
    
    # Clear command
    parser_clear = subparsers.add_parser("clear", help="Clear the writeback device.")
    parser_clear.add_argument("device", help="The zram device name.")
    parser_clear.set_defaults(func=handle_clear)

    if not argv:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args(argv)
    check_permissions()
    args.func(args)

if __name__ == "__main__":
    main(sys.argv[1:])
