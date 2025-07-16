import os
import shutil

def wipe_logs():
    paths = [
        "session_memory.json",
        "loot_log.json",
        "session_key.bin",
        "mission_report.pdf"
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, "wb") as f:
                    f.write(b"\x00" * 1024)
                os.remove(p)
                print(f"[+] Wiped: {p}")
            except Exception as e:
                print(f"[!] Failed to wipe {p}: {e}")

def self_delete():
    try:
        os.remove(__file__)
        print("[+] Self-deletion triggered.")
    except Exception as e:
        print(f"[!] Self-delete failed: {e}")

if __name__ == "__main__":
    print("[!] Kill switch activated.")
    wipe_logs()
    self_delete()
