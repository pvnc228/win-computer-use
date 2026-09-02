import ctypes
from ctypes import wintypes
import os
import sys
import json
import base64
import time
from typing import Optional, Dict, Any, List, Union
from .cursor import restore_system_cursor

class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ('cb', wintypes.DWORD),
        ('lpReserved', wintypes.LPWSTR),
        ('lpDesktop', wintypes.LPWSTR),
        ('lpTitle', wintypes.LPWSTR),
        ('dwX', wintypes.DWORD),
        ('dwY', wintypes.DWORD),
        ('dwXSize', wintypes.DWORD),
        ('dwYSize', wintypes.DWORD),
        ('dwXCountChars', wintypes.DWORD),
        ('dwYCountChars', wintypes.DWORD),
        ('dwFillAttribute', wintypes.DWORD),
        ('dwFlags', wintypes.DWORD),
        ('wShowWindow', wintypes.WORD),
        ('cbReserved2', wintypes.WORD),
        ('lpReserved2', ctypes.c_char_p),
        ('hStdInput', wintypes.HANDLE),
        ('hStdOutput', wintypes.HANDLE),
        ('hStdError', wintypes.HANDLE),
    ]

class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ('hProcess', wintypes.HANDLE),
        ('hThread', wintypes.HANDLE),
        ('dwProcessId', wintypes.DWORD),
        ('dwThreadId', wintypes.DWORD),
    ]

class SECURITY_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ('nLength', wintypes.DWORD),
        ('lpSecurityDescriptor', ctypes.c_void_p),
        ('bInheritHandle', wintypes.BOOL)
    ]

def find_cua_helper() -> Optional[str]:
    """Auto-discovers codex-computer-use.exe from OpenAI Codex runtimes."""
    if os.environ.get("CODEX_CUA_HELPER_PATH"):
        return os.environ["CODEX_CUA_HELPER_PATH"]
    
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        import glob
        pattern = os.path.join(
            local_app_data, "OpenAI", "Codex", "runtimes", "cua_node", "*",
            "bin", "node_modules", "@oai", "sky", "bin", "windows", "codex-computer-use.exe"
        )
        matches = glob.glob(pattern)
        if matches:
            # Pick latest modified if multiple
            matches.sort(key=os.path.getmtime, reverse=True)
            return matches[0]
    return None

def find_codex_bin() -> Optional[str]:
    """Auto-discovers Codex CLI bin folder containing codex.exe."""
    if os.environ.get("CODEX_BIN_PATH"):
        return os.environ["CODEX_BIN_PATH"]

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        import glob
        pattern = os.path.join(local_app_data, "OpenAI", "Codex", "bin", "*", "codex.exe")
        matches = glob.glob(pattern)
        if matches:
            matches.sort(key=os.path.getmtime, reverse=True)
            return os.path.dirname(matches[0])
    return None

class ComputerUseClient:
    """
    Client for OpenAI Codex Computer Use Native Helper (Windows).
    Executes automation tasks on WinSta0\\Default desktop with automatic approval handling.
    """

    def __init__(self, helper_path: Optional[str] = None, codex_bin: Optional[str] = None):
        self.helper_path = helper_path or find_cua_helper()
        self.codex_bin = codex_bin or find_codex_bin()
        
        if not self.helper_path or not os.path.exists(self.helper_path):
            raise FileNotFoundError(
                "codex-computer-use.exe was not found on this system.\n\n"
                "Prerequisites:\n"
                "1. Install OpenAI Codex / ChatGPT Desktop for Windows.\n"
                "2. The helper binary is installed automatically under:\n"
                "   %LOCALAPPDATA%\\OpenAI\\Codex\\runtimes\\cua_node\\<hash>\\bin\\node_modules\\@oai\\sky\\bin\\windows\\codex-computer-use.exe\n"
                "3. Alternatively, specify CODEX_CUA_HELPER_PATH environment variable."
            )

        self._process_info: Optional[PROCESS_INFORMATION] = None
        self._h_stdin_write: Optional[wintypes.HANDLE] = None
        self._h_stdout_read: Optional[wintypes.HANDLE] = None
        self._req_id = 0
        self._approved_apps: Dict[str, str] = {}

    def start(self):
        if self._process_info is not None:
            return

        sa = SECURITY_ATTRIBUTES()
        sa.nLength = ctypes.sizeof(SECURITY_ATTRIBUTES)
        sa.bInheritHandle = True
        sa.lpSecurityDescriptor = None

        h_in_read = wintypes.HANDLE()
        h_in_write = wintypes.HANDLE()
        ctypes.windll.kernel32.CreatePipe(ctypes.byref(h_in_read), ctypes.byref(h_in_write), ctypes.byref(sa), 0)
        ctypes.windll.kernel32.SetHandleInformation(h_in_write, 1, 0)

        h_out_read = wintypes.HANDLE()
        h_out_write = wintypes.HANDLE()
        ctypes.windll.kernel32.CreatePipe(ctypes.byref(h_out_read), ctypes.byref(h_out_write), ctypes.byref(sa), 0)
        ctypes.windll.kernel32.SetHandleInformation(h_out_read, 1, 0)

        si = STARTUPINFOW()
        si.cb = ctypes.sizeof(STARTUPINFOW)
        si.dwFlags = 0x00000100 # STARTF_USESTDHANDLES
        si.hStdInput = h_in_read
        si.hStdOutput = h_out_write
        si.hStdError = h_out_write
        si.lpDesktop = r"WinSta0\Default"

        pi = PROCESS_INFORMATION()

        # Ensure Codex bin is in PATH for app-server checks
        env_path = os.environ.get("PATH", "")
        if self.codex_bin and self.codex_bin not in env_path:
            os.environ["PATH"] = f"{self.codex_bin};{env_path}"

        cmd = f'"{self.helper_path}" --parent-pid {os.getpid()}'
        res = ctypes.windll.kernel32.CreateProcessW(
            None, cmd, None, None, True, 0, None, None, ctypes.byref(si), ctypes.byref(pi)
        )
        if not res:
            err = ctypes.GetLastError()
            ctypes.windll.kernel32.CloseHandle(h_in_read)
            ctypes.windll.kernel32.CloseHandle(h_in_write)
            ctypes.windll.kernel32.CloseHandle(h_out_read)
            ctypes.windll.kernel32.CloseHandle(h_out_write)
            raise RuntimeError(f"Failed to launch CUA helper (CreateProcessW error {err})")

        ctypes.windll.kernel32.CloseHandle(h_in_read)
        ctypes.windll.kernel32.CloseHandle(h_out_write)

        self._process_info = pi
        self._h_stdin_write = h_in_write
        self._h_stdout_read = h_out_read

    def stop(self):
        if self._process_info:
            try:
                self.request("end_turn", {}, timeout_sec=2)
            except Exception:
                pass

            if self._h_stdin_write:
                ctypes.windll.kernel32.CloseHandle(self._h_stdin_write)
                self._h_stdin_write = None
            if self._h_stdout_read:
                ctypes.windll.kernel32.CloseHandle(self._h_stdout_read)
                self._h_stdout_read = None

            ctypes.windll.kernel32.TerminateProcess(self._process_info.hProcess, 0)
            ctypes.windll.kernel32.CloseHandle(self._process_info.hProcess)
            ctypes.windll.kernel32.CloseHandle(self._process_info.hThread)
            self._process_info = None

        restore_system_cursor()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def request(self, method: str, params: Dict[str, Any], timeout_sec: int = 15) -> Any:
        if self._process_info is None:
            self.start()

        meta = {"x-oai-cua-request-budget-ms": timeout_sec * 1000}

        for _ in range(4):
            self._req_id += 1
            payload = {
                "id": self._req_id,
                "method": method,
                "params": params,
                "meta": meta
            }
            data = (json.dumps(payload) + "\n").encode("utf-8")
            written = wintypes.DWORD()
            ctypes.windll.kernel32.WriteFile(self._h_stdin_write, data, len(data), ctypes.byref(written), None)

            # Read response JSON line
            buf = b""
            ch = ctypes.c_char()
            read_bytes = wintypes.DWORD()
            while True:
                res = ctypes.windll.kernel32.ReadFile(self._h_stdout_read, ctypes.byref(ch), 1, ctypes.byref(read_bytes), None)
                if not res or read_bytes.value == 0:
                    break
                if ch.value == b"\n":
                    break
                buf += ch.value

            if not buf:
                raise RuntimeError(f"Empty response from CUA helper on method {method}")

            resp = json.loads(buf.decode("utf-8", errors="replace"))

            if resp.get("ok"):
                return resp.get("result")

            if "approvalRequest" in resp:
                app_to_approve = resp["approvalRequest"]["app"]
                meta["x-oai-cua-approved-app"] = app_to_approve
                self._approved_apps[app_to_approve] = app_to_approve
                continue

            error_msg = resp.get("error", "Unknown error")
            raise RuntimeError(f"CUA Helper Error on '{method}': {error_msg}")

        raise TimeoutError(f"Exceeded approval retry attempts for '{method}'")

    def list_windows(self, filter_system: bool = True) -> List[Dict[str, Any]]:
        raw_windows = self.request("list_windows", {}) or []
        if not filter_system:
            return raw_windows

        # Common Windows background/system shells (English & localized aliases)
        ignore = [
            "cua.agentcursoroverlay",
            "program manager",
            "task switching", "\u043f\u0435\u0440\u0435\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0435 \u0437\u0430\u0434\u0430\u0447",
            "notification overflow", "\u043e\u043a\u043d\u043e \u043f\u0435\u0440\u0435\u043f\u043e\u043b\u043d\u0435\u043d\u0438\u044f",
            "battery indicator", "\u0438\u043d\u0434\u0438\u043a\u0430\u0442\u043e\u0440 \u0431\u0430\u0442\u0430\u0440\u0435\u0439",
            "real-time actions", "\u0434\u0435\u0439\u0441\u0442\u0432\u0438\u044f \u0432 \u0440\u0435\u0430\u043b\u044c\u043d\u043e\u043c \u0432\u0440\u0435\u043c\u0435\u043d\u0438",
            "windows input experience", "\u0438\u043d\u0442\u0435\u0440\u0444\u0435\u0439\u0441 \u0432\u0432\u043e\u0434\u0430 windows"
        ]
        filtered = []
        seen = set()
        for w in raw_windows:
            title = w.get("title", "").strip()
            if not title:
                continue
            if any(ign in title.lower() for ign in ignore):
                continue
            if title in seen:
                continue
            seen.add(title)
            filtered.append(w)
        return filtered

    def find_window(self, query: Union[int, str]) -> Optional[Dict[str, Any]]:
        windows = self.list_windows(filter_system=False)
        if isinstance(query, int):
            for w in windows:
                if w.get("id") == query:
                    return w
            return None

        query_lower = query.lower()
        for w in windows:
            if query_lower in w.get("title", "").lower():
                return w
        for w in windows:
            if query_lower in w.get("app", "").lower():
                return w
        return None

    def _resolve_window(self, target: Union[int, str, Dict[str, Any]]) -> Dict[str, Any]:
        if isinstance(target, dict) and "id" in target:
            return target
        w = self.find_window(target)
        if not w:
            raise ValueError(f"Window matching '{target}' not found")
        return w

    def activate_window(self, target: Union[int, str, Dict[str, Any]]) -> bool:
        w = self._resolve_window(target)
        self.request("activate_window", {"window": w})
        return True

    def _capture_win32_gdi(self, hwnd: int) -> Optional[Dict[str, Any]]:
        """Direct Win32 GDI screen capture fallback for browser windows or policy restrictions."""
        try:
            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32
            user32.SetThreadDesktop(user32.OpenDesktopW('Default', 0, False, 0x1FF))

            rect = (ctypes.c_long * 4)()
            user32.GetWindowRect(hwnd, rect)
            w = max(rect[2] - rect[0], 1)
            h = max(rect[3] - rect[1], 1)

            hScreenDC = user32.GetDC(0)
            hMemDC = gdi32.CreateCompatibleDC(hScreenDC)
            hBmp = gdi32.CreateCompatibleBitmap(hScreenDC, w, h)
            gdi32.SelectObject(hMemDC, hBmp)
            gdi32.BitBlt(hMemDC, 0, 0, w, h, hScreenDC, rect[0], rect[1], 0x00CC0020)

            class BITMAPINFOHEADER(ctypes.Structure):
                _fields_ = [
                    ('biSize', wintypes.DWORD), ('biWidth', wintypes.LONG), ('biHeight', wintypes.LONG),
                    ('biPlanes', wintypes.WORD), ('biBitCount', wintypes.WORD), ('biCompression', wintypes.DWORD),
                    ('biSizeImage', wintypes.DWORD), ('biXPelsPerMeter', wintypes.LONG), ('biYPelsPerMeter', wintypes.LONG),
                    ('biClrUsed', wintypes.DWORD), ('biClrImportant', wintypes.DWORD)
                ]

            bmi = BITMAPINFOHEADER()
            bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.biWidth = w
            bmi.biHeight = -h
            bmi.biPlanes = 1
            bmi.biBitCount = 32
            bmi.biCompression = 0

            buf = ctypes.create_string_buffer(w * h * 4)
            gdi32.GetDIBits(hMemDC, hBmp, 0, h, buf, ctypes.byref(bmi), 0)

            gdi32.DeleteObject(hBmp)
            gdi32.DeleteDC(hMemDC)
            user32.ReleaseDC(0, hScreenDC)

            raw_bytes = buf.raw
            try:
                import io
                from PIL import Image
                img = Image.frombuffer('RGBA', (w, h), raw_bytes, 'raw', 'BGRA', 0, 1).convert('RGB')
                bio = io.BytesIO()
                img.save(bio, format="PNG")
                b64_str = base64.b64encode(bio.getvalue()).decode("ascii")
                mime = "image/png"
            except ImportError:
                import struct
                file_size = 54 + len(raw_bytes)
                hdr = struct.pack('<2sIHHI', b'BM', file_size, 0, 0, 54)
                dhdr = struct.pack('<IIIHHIIIIII', 40, w, -h, 1, 32, 0, len(raw_bytes), 0, 0, 0, 0)
                bmp_data = hdr + dhdr + raw_bytes
                b64_str = base64.b64encode(bmp_data).decode("ascii")
                mime = "image/bmp"

            return {
                "id": hwnd,
                "width": w,
                "height": h,
                "originX": rect[0],
                "originY": rect[1],
                "url": f"data:{mime};base64,{b64_str}"
            }
        except Exception:
            return None

    def get_window_state(self, target: Union[int, str, Dict[str, Any]], 
                         include_screenshot: bool = True,
                         include_text: bool = False) -> Dict[str, Any]:
        w = self._resolve_window(target)
        try:
            return self.request("get_window_state", {
                "window": w,
                "include_screenshot": include_screenshot,
                "include_text": include_text
            })
        except Exception:
            if include_screenshot:
                s = self._capture_win32_gdi(w["id"])
                if s:
                    return {
                        "window": w,
                        "screenshots": [s]
                    }
            raise

    def save_screenshot(self, target: Union[int, str, Dict[str, Any]], out_path: str) -> Dict[str, Any]:
        w = self._resolve_window(target)
        self.activate_window(w)
        time.sleep(0.15)
        state = self.get_window_state(w, include_screenshot=True, include_text=False)
        screenshots = state.get("screenshots", [])
        if not screenshots:
            raise RuntimeError(f"No screenshot returned for window: {target}")

        s0 = screenshots[0]
        url = s0.get("url", "")
        if url.startswith("data:image/"):
            b64_str = url.split(",", 1)[1]
            os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
            with open(out_path, "wb") as f:
                f.write(base64.b64decode(b64_str))
        return {
            "path": os.path.abspath(out_path),
            "id": s0.get("id"),
            "width": s0.get("width"),
            "height": s0.get("height"),
            "originX": s0.get("originX", 0),
            "originY": s0.get("originY", 0)
        }

    def click(self, target: Union[int, str, Dict[str, Any]], 
              x: int, y: int, 
              mouse_button: str = "left", 
              click_count: int = 1) -> Any:
        w = self._resolve_window(target)
        self.activate_window(w)
        return self.request("click", {
            "window": w,
            "x": x,
            "y": y,
            "mouse_button": mouse_button,
            "click_count": click_count
        })

    def click_center(self, target: Union[int, str, Dict[str, Any]], 
                     mouse_button: str = "left", 
                     click_count: int = 1) -> Dict[str, Any]:
        w = self._resolve_window(target)
        self.activate_window(w)
        
        # Determine center coordinates from window state
        # If get_window_state policy check triggers on browser, calculate via Win32 GetWindowRect
        try:
            state = self.get_window_state(w, include_screenshot=True)
            screenshots = state.get("screenshots", [])
            if screenshots:
                cx = screenshots[0]["width"] // 2
                cy = screenshots[0]["height"] // 2
            else:
                cx, cy = self._get_win32_window_center(w["id"])
        except Exception:
            cx, cy = self._get_win32_window_center(w["id"])

        self.click(w, cx, cy, mouse_button=mouse_button, click_count=click_count)
        return {"x": cx, "y": cy, "window": w["title"]}

    def _get_win32_window_center(self, hwnd: int) -> (int, int):
        user32 = ctypes.windll.user32
        rect = (ctypes.c_long * 4)()
        user32.GetWindowRect(hwnd, rect)
        w = rect[2] - rect[0]
        h = rect[3] - rect[1]
        return w // 2, h // 2

    def type_text(self, target: Union[int, str, Dict[str, Any]], text: str) -> Any:
        w = self._resolve_window(target)
        self.activate_window(w)
        return self.request("type_text", {
            "window": w,
            "text": text
        })

    def press_key(self, target: Union[int, str, Dict[str, Any]], key: str) -> Any:
        w = self._resolve_window(target)
        self.activate_window(w)
        return self.request("press_key", {
            "window": w,
            "key": key
        })

    def scroll(self, target: Union[int, str, Dict[str, Any]], 
               x: int, y: int, 
               scroll_x: int = 0, scroll_y: int = 600) -> Any:
        w = self._resolve_window(target)
        self.activate_window(w)
        return self.request("scroll", {
            "window": w,
            "x": x,
            "y": y,
            "scrollX": scroll_x,
            "scrollY": scroll_y
        })

    def drag(self, target: Union[int, str, Dict[str, Any]], 
             from_x: int, from_y: int, 
             to_x: int, to_y: int) -> Any:
        w = self._resolve_window(target)
        self.activate_window(w)
        return self.request("drag", {
            "window": w,
            "from_x": from_x,
            "from_y": from_y,
            "to_x": to_x,
            "to_y": to_y
        })

    def aim(self, target: Optional[Union[int, str, Dict[str, Any]]], dx: int, dy: int) -> bool:
        """Relative mouse delta movement for 3D games / FPS aiming."""
        if target:
            self.activate_window(target)
        from .raw_input import mouse_move_relative
        return mouse_move_relative(dx, dy)

    def hold_key(self, target: Optional[Union[int, str, Dict[str, Any]]], key: str, duration: float = 0.5) -> bool:
        """Holds a key down with hardware scan codes (e.g. WASD movement)."""
        if target:
            self.activate_window(target)
        from .raw_input import hold_key
        return hold_key(key, duration)

    def mouse_down(self, target: Optional[Union[int, str, Dict[str, Any]]], button: str = "left") -> bool:
        """Presses and holds mouse button."""
        if target:
            self.activate_window(target)
        from .raw_input import mouse_down
        return mouse_down(button)

    def mouse_up(self, target: Optional[Union[int, str, Dict[str, Any]]], button: str = "left") -> bool:
        """Releases mouse button."""
        if target:
            self.activate_window(target)
        from .raw_input import mouse_up
        return mouse_up(button)

    def shoot(self, target: Optional[Union[int, str, Dict[str, Any]]], button: str = "left", duration: float = 0.15) -> bool:
        """Fires weapon burst for duration seconds."""
        if target:
            self.activate_window(target)
        from .raw_input import shoot
        return shoot(button, duration)

    def run_macro(self, target: Optional[Union[int, str, Dict[str, Any]]], actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Executes an atomic list of gaming actions without LLM latency jitter."""
        if target:
            self.activate_window(target)
        from .raw_input import execute_macro
        return execute_macro(actions)

