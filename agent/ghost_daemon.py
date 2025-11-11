import os
import subprocess
import time

WATCH_PATH = os.path.expanduser("~/.config/.sessx.py")


def ensure_running():
    while True:
        time.sleep(15)
        if not is_process_alive("sessx"):
            print("[*] Ghost daemon: Respawning sessx.")
            subprocess.Popen(["python3", WATCH_PATH])


def is_process_alive(identifier):
    import psutil

    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if any(identifier in str(arg) for arg in proc.info["cmdline"]):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False


if __name__ == "__main__":
    ensure_running()
