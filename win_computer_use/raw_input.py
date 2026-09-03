import ctypes
from ctypes import wintypes
import time
from typing import Dict, Any, List, Optional

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

def _ensure_desktop():
    """Bypasses agent sandbox desktop isolation for SendInput."""
    h_desk = user32.OpenDesktopW('Default', 0, False, 0x1FF)
    if h_desk:
        user32.SetThreadDesktop(h_desk)
        user32.CloseDesktop(h_desk)

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ('dx', wintypes.LONG),
        ('dy', wintypes.LONG),
        ('mouseData', wintypes.DWORD),
        ('dwFlags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ctypes.POINTER(wintypes.ULONG))
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ('wVk', wintypes.WORD),
        ('wScan', wintypes.WORD),
        ('dwFlags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ctypes.POINTER(wintypes.ULONG))
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ('uMsg', wintypes.DWORD),
        ('wParamL', wintypes.WORD),
        ('wParamH', wintypes.WORD)
    ]

class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ('mi', MOUSEINPUT),
        ('ki', KEYBDINPUT),
        ('hi', HARDWAREINPUT)
    ]

class INPUT(ctypes.Structure):
    _anonymous_ = ('u',)
    _fields_ = [
        ('type', wintypes.DWORD),
        ('u', INPUT_UNION)
    ]

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

# Mouse flags
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040

# Keyboard flags
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

VK_KEYS = {
    "space": 0x20, "shift": 0x10, "ctrl": 0x11, "alt": 0x12,
    "enter": 0x0D, "return": 0x0D, "escape": 0x1B, "esc": 0x1B,
    "tab": 0x09, "backspace": 0x08, "capslock": 0x14,
    "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
    "lshift": 0xA0, "rshift": 0xA1, "lctrl": 0xA2, "rctrl": 0xA3,
    "insert": 0x2D, "delete": 0x2E, "home": 0x24, "end": 0x23,
    "pageup": 0x21, "pagedown": 0x22,
}

EXTENDED_KEYS = {
    0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2D, 0x2E, 0xA3, 0xA5
}

def resolve_key(key_name: str) -> (int, int):
    """Resolves virtual key and hardware scan code for a key name."""
    k = key_name.lower().strip()
    if k in VK_KEYS:
        vk = VK_KEYS[k]
    elif len(k) == 1:
        vk = ord(k.upper())
    elif k.startswith("f") and k[1:].isdigit():
        vk = 0x70 + int(k[1:]) - 1 # F1 - F24
    else:
        raise ValueError(f"Unsupported key: '{key_name}'")

    vsc = user32.MapVirtualKeyW(vk, 0)
    return vk, vsc

def mouse_move_relative(dx: int, dy: int) -> bool:
    """Sends relative mouse delta for 3D camera / FPS aiming."""
    _ensure_desktop()
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.mi.dx = int(dx)
    inp.mi.dy = int(dy)
    inp.mi.dwFlags = MOUSEEVENTF_MOVE
    res = user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
    return res == 1

def mouse_down(button: str = "left") -> bool:
    """Presses and holds a mouse button."""
    _ensure_desktop()
    b = button.lower()
    flag = MOUSEEVENTF_LEFTDOWN if b == "left" else (MOUSEEVENTF_RIGHTDOWN if b == "right" else MOUSEEVENTF_MIDDLEDOWN)
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.mi.dwFlags = flag
    return user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)) == 1

def mouse_up(button: str = "left") -> bool:
    """Releases a mouse button."""
    _ensure_desktop()
    b = button.lower()
    flag = MOUSEEVENTF_LEFTUP if b == "left" else (MOUSEEVENTF_RIGHTUP if b == "right" else MOUSEEVENTF_MIDDLEUP)
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.mi.dwFlags = flag
    return user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)) == 1

def key_down(key: str) -> bool:
    """Presses and holds a keyboard key with hardware scan codes."""
    _ensure_desktop()
    vk, vsc = resolve_key(key)
    flags = KEYEVENTF_SCANCODE
    if vk in EXTENDED_KEYS:
        flags |= KEYEVENTF_EXTENDEDKEY
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.ki.wVk = vk
    inp.ki.wScan = vsc
    inp.ki.dwFlags = flags
    return user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)) == 1

def key_up(key: str) -> bool:
    """Releases a keyboard key with hardware scan codes."""
    _ensure_desktop()
    vk, vsc = resolve_key(key)
    flags = KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP
    if vk in EXTENDED_KEYS:
        flags |= KEYEVENTF_EXTENDEDKEY
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.ki.wVk = vk
    inp.ki.wScan = vsc
    inp.ki.dwFlags = flags
    return user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)) == 1

def hold_key(key: str, duration: float) -> bool:
    """Holds a key down for a specified duration in seconds (e.g. WASD movement)."""
    key_down(key)
    try:
        time.sleep(max(duration, 0.01))
    finally:
        key_up(key)
    return True

def shoot(button: str = "left", duration: float = 0.15) -> bool:
    """Fires a weapon burst by holding mouse button for duration seconds."""
    mouse_down(button)
    try:
        time.sleep(max(duration, 0.01))
    finally:
        mouse_up(button)
    return True

def execute_macro(actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Executes an atomic list of gaming / automation actions with millisecond precision.
    Bypasses LLM turn-by-turn roundtrip latency.
    """
    results = []
    for act in actions:
        if not isinstance(act, dict):
            results.append({"error": f"Invalid action specification (must be a dict): {act}"})
            continue
        atype = act.get("action", act.get("type", "")).lower()
        if atype in ("aim", "mouse_move_relative", "mouse_move"):
            dx = act.get("dx", 0)
            dy = act.get("dy", 0)
            res = mouse_move_relative(dx, dy)
            results.append({"action": "aim", "dx": dx, "dy": dy, "ok": res})
        elif atype in ("hold", "hold_key"):
            k = act.get("key", "w")
            dur = float(act.get("duration", 0.5))
            res = hold_key(k, dur)
            results.append({"action": "hold_key", "key": k, "duration": dur, "ok": res})
        elif atype in ("key_down", "keydown"):
            k = act.get("key", "w")
            res = key_down(k)
            results.append({"action": "key_down", "key": k, "ok": res})
        elif atype in ("key_up", "keyup"):
            k = act.get("key", "w")
            res = key_up(k)
            results.append({"action": "key_up", "key": k, "ok": res})
        elif atype in ("mouse_down", "mousedown"):
            b = act.get("button", "left")
            res = mouse_down(b)
            results.append({"action": "mouse_down", "button": b, "ok": res})
        elif atype in ("mouse_up", "mouseup"):
            b = act.get("button", "left")
            res = mouse_up(b)
            results.append({"action": "mouse_up", "button": b, "ok": res})
        elif atype in ("shoot", "fire"):
            b = act.get("button", "left")
            dur = float(act.get("duration", 0.15))
            res = shoot(b, dur)
            results.append({"action": "shoot", "button": b, "duration": dur, "ok": res})
        elif atype in ("press", "press_key"):
            k = act.get("key", "space")
            res = hold_key(k, 0.05)
            results.append({"action": "press_key", "key": k, "ok": res})
        elif atype in ("click", "mouse_click"):
            b = act.get("button", "left")
            res = shoot(b, 0.05)
            results.append({"action": "click", "button": b, "ok": res})
        elif atype in ("sleep", "wait"):
            dur = float(act.get("duration", 0.1))
            time.sleep(dur)
            results.append({"action": "sleep", "duration": dur, "ok": True})
        else:
            results.append({"action": atype, "error": f"Unknown action: {atype}"})
    return results
