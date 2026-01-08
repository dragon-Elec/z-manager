#!/usr/bin/env python3
import os
import subprocess
import sys

def run(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True).strip()
    except subprocess.CalledProcessError as e:
        return f"Error: {e}"

def print_header(title):
    print(f"\n{'='*50}")
    print(f" {title}")
    print(f"{'='*50}")

def main():
    print_header("1. Active ZRAM Devices (zramctl)")
    print(run("zramctl"))

    print_header("2. Config File (/etc/systemd/zram-generator.conf)")
    if os.path.exists("/etc/systemd/zram-generator.conf"):
        print(run("cat /etc/systemd/zram-generator.conf"))
    else:
        print("File not found.")

    print_header("3. System Swaps (/proc/swaps)")
    print(run("cat /proc/swaps"))

    print_header("4. Kernel Parameters")
    print(f"vm.swappiness = {run('cat /proc/sys/vm/swappiness')}")
    
    print_header("5. Service Status (zram0)")
    print(run("systemctl status systemd-zram-setup@zram0.service --no-pager | head -n 5"))

if __name__ == "__main__":
    main()
