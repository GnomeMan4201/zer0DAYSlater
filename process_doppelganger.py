import sys
import ctypes
import os

def hide_process_name(fake_name="systemd"):
    try:
        libc = ctypes.CDLL(None)
        buff = ctypes.create_string_buffer(len(fake_name)+1)
        buff.value = fake_name.encode('utf-8')
        libc.prctl(15, ctypes.byref(buff), 0, 0, 0)  # PR_SET_NAME = 15
    except Exception as e:
        print(f"[!] Failed to set fake name: {e}")

if __name__ == "__main__":
    hide_process_name("rsyslogd")
    print("[+] Process name spoofed. Now sleeping as 'rsyslogd'...")
    while True:
        pass  # simulate idle payload loop
