import random


def cloak_process():
    # Look for common system process names
    candidates = ["systemd", "dbus-daemon", "NetworkManager", "cron", "bash", "sshd"]
    new_name = random.choice(candidates)
    try:
        import setproctitle

        setproctitle.setproctitle(new_name)
        print(f"[+] Cloaked process as: {new_name}")
    except ImportError:
        print("[!] setproctitle module not found. Cloaking not applied.")
