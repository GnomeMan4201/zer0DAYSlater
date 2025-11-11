#!/usr/bin/env python3
import os
import signal
import subprocess


def terminate_agents():
    try:
        output = subprocess.check_output(["pgrep", "-f", "zer0DAYSlater"]).decode()
        for pid in output.strip().split("\n"):
            os.kill(int(pid), signal.SIGKILL)
        print("[+] All zer0DAYSlater processes terminated.")
    except subprocess.CalledProcessError:
        print("[-] No matching processes found.")


def wipe_logs():
    for target in [
        "session_memory.json",
        "loot_log.json",
        "loot_summary.pdf",
        "mission_report.pdf",
    ]:
        if os.path.exists(target):
            os.remove(target)
            print(f"[+] Removed {target}")


if __name__ == "__main__":
    terminate_agents()
    wipe_logs()
    print("[+] Kill switch executed successfully.")
