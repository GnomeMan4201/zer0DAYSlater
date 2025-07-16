
import os, time, platform
import ctypes

def is_low_uptime(threshold=300):
    try:
        if platform.system() == "Windows":
            GetTickCount64 = ctypes.windll.kernel32.GetTickCount64
            GetTickCount64.restype = ctypes.c_ulonglong
            uptime_ms = GetTickCount64()
        else:
            with open("/proc/uptime", "r") as f:
                uptime_ms = float(f.readline().split()[0]) * 1000
        return uptime_ms < threshold * 1000
    except:
        return False

def no_mouse_activity():
    try:
        if platform.system() == "Windows":
            pt = ctypes.wintypes.POINT()
            x1, y1 = pt.x, pt.y
            time.sleep(3)
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            x2, y2 = pt.x, pt.y
            return (x1 == x2) and (y1 == y2)
    except:
        return False
    return False

def is_sandbox():
    if is_low_uptime():
        return True
    if no_mouse_activity():
        return True
    return False
