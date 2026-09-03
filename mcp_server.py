import sys
import os
import json
import time
import traceback
import threading
from typing import Any, Dict, Optional, List

# Ensure project package is importable
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from win_computer_use.client import ComputerUseClient
from win_computer_use.cursor import restore_system_cursor

try:
    from mcp.server.mcpserver import MCPServer
    from mcp.types import CallToolResult, TextContent
    _MCP_SDK_AVAILABLE = True
except ImportError:
    _MCP_SDK_AVAILABLE = False


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


# =====================================================================
# Shared Native Client Lifecycle for MCP Server
# =====================================================================

_CLIENT_LOCK = threading.RLock()
_CLIENT_INSTANCE: Optional[ComputerUseClient] = None

def get_client() -> ComputerUseClient:
    """Returns a shared, lazily started ComputerUseClient instance for the MCP server."""
    global _CLIENT_INSTANCE
    with _CLIENT_LOCK:
        if _CLIENT_INSTANCE is None:
            _CLIENT_INSTANCE = ComputerUseClient()
            _CLIENT_INSTANCE.start()
        elif _CLIENT_INSTANCE._process_info is None:
            _CLIENT_INSTANCE.start()
        return _CLIENT_INSTANCE

def reset_client():
    """Stops the shared client and resets the singleton instance."""
    global _CLIENT_INSTANCE
    with _CLIENT_LOCK:
        if _CLIENT_INSTANCE is not None:
            try:
                _CLIENT_INSTANCE.stop()
            except Exception:
                pass
            _CLIENT_INSTANCE = None
        restore_system_cursor()


# =====================================================================
# Native Tool Implementations (Shared between MCP SDK & Raw Fallback)
# =====================================================================

def tool_list_windows(include_system: bool = False) -> str:
    try:
        cua = get_client()
        windows = cua.list_windows(filter_system=not include_system)
        return _json({"windows": windows, "count": len(windows)})
    finally:
        restore_system_cursor()

def tool_activate_window(target: str) -> str:
    try:
        cua = get_client()
        cua.activate_window(target)
        return _json({"status": "ok", "activated": target})
    finally:
        restore_system_cursor()

def tool_get_window_state(target: str, save_path: str = "", crop: str = "") -> str:
    try:
        cua = get_client()
        if save_path:
            meta = cua.save_screenshot(target, save_path)
            if crop:
                try:
                    cx, cy, cw, ch = [int(v.strip()) for v in crop.split(",")]
                    from PIL import Image
                    with Image.open(meta['path']) as img:
                        cropped = img.crop((cx, cy, cx + cw, cy + ch))
                        cropped.save(meta['path'])
                    meta["cropped"] = [cx, cy, cw, ch]
                except Exception as e:
                    meta["crop_error"] = str(e)
            return _json({"status": "ok", "screenshot": meta})
        else:
            state = cua.get_window_state(target, include_screenshot=True)
            s = state.get("screenshots", [{}])[0]
            return _json({
                "status": "ok",
                "id": s.get("id"),
                "width": s.get("width"),
                "height": s.get("height"),
                "originX": s.get("originX"),
                "originY": s.get("originY")
            })
    finally:
        restore_system_cursor()

def tool_screenshot(target: str, out_path: str = "screenshot.png", crop: str = "") -> str:
    return tool_get_window_state(target, save_path=out_path, crop=crop)

def tool_click(target: str, x: int, y: int, mouse_button: str = "left", click_count: int = 1) -> str:
    try:
        cua = get_client()
        cua.click(target, x=x, y=y, mouse_button=mouse_button, click_count=click_count)
        return _json({"status": "ok", "clicked": {"target": target, "x": x, "y": y, "button": mouse_button, "count": click_count}})
    finally:
        restore_system_cursor()

def tool_click_center(target: str, mouse_button: str = "left", click_count: int = 1) -> str:
    try:
        cua = get_client()
        res = cua.click_center(target, mouse_button=mouse_button, click_count=click_count)
        return _json({"status": "ok", "clicked_center": res})
    finally:
        restore_system_cursor()

def tool_type_text(target: str, text: str) -> str:
    try:
        cua = get_client()
        cua.type_text(target, text)
        return _json({"status": "ok", "typed": text})
    finally:
        restore_system_cursor()

def tool_press_key(target: str, key: str) -> str:
    try:
        cua = get_client()
        cua.press_key(target, key)
        return _json({"status": "ok", "pressed": key})
    finally:
        restore_system_cursor()

def tool_scroll(target: str, x: int, y: int, scroll_x: int = 0, scroll_y: int = 600) -> str:
    try:
        cua = get_client()
        cua.scroll(target, x=x, y=y, scroll_x=scroll_x, scroll_y=scroll_y)
        return _json({"status": "ok", "scrolled": True})
    finally:
        restore_system_cursor()

def tool_drag(target: str, from_x: int, from_y: int, to_x: int, to_y: int) -> str:
    try:
        cua = get_client()
        cua.drag(target, from_x=from_x, from_y=from_y, to_x=to_x, to_y=to_y)
        return _json({"status": "ok", "dragged": {"from": [from_x, from_y], "to": [to_x, to_y]}})
    finally:
        restore_system_cursor()

def tool_aim(dx: int, dy: int, target: str = "") -> str:
    try:
        cua = get_client()
        res = cua.aim(target if target else None, dx=dx, dy=dy)
        return _json({"status": "ok", "aim_moved": {"dx": dx, "dy": dy, "result": res}})
    finally:
        restore_system_cursor()

def tool_hold_key(key: str, duration: float = 0.5, target: str = "") -> str:
    try:
        cua = get_client()
        res = cua.hold_key(target if target else None, key=key, duration=duration)
        return _json({"status": "ok", "held_key": {"key": key, "duration": duration, "result": res}})
    finally:
        restore_system_cursor()

def tool_mouse_down(button: str = "left", target: str = "") -> str:
    try:
        cua = get_client()
        res = cua.mouse_down(target if target else None, button=button)
        return _json({"status": "ok", "mouse_down": button, "result": res})
    finally:
        restore_system_cursor()

def tool_mouse_up(button: str = "left", target: str = "") -> str:
    try:
        cua = get_client()
        res = cua.mouse_up(target if target else None, button=button)
        return _json({"status": "ok", "mouse_up": button, "result": res})
    finally:
        restore_system_cursor()

def tool_shoot(button: str = "left", duration: float = 0.15, target: str = "") -> str:
    try:
        cua = get_client()
        res = cua.shoot(target if target else None, button=button, duration=duration)
        return _json({"status": "ok", "fired": {"button": button, "duration": duration, "result": res}})
    finally:
        restore_system_cursor()

def tool_run_macro(actions: list, target: str = "") -> str:
    try:
        cua = get_client()
        results = cua.run_macro(target if target else None, actions)
        return _json({"status": "ok", "macro_results": results})
    finally:
        restore_system_cursor()

def tool_cycle_windows(delay: float = 1.0) -> str:
    try:
        cua = get_client()
        wins = cua.list_windows()
        for w in wins:
            cua.activate_window(w)
            time.sleep(delay)
        return _json({"status": "ok", "cycled_count": len(wins)})
    finally:
        restore_system_cursor()

def tool_restore_cursor() -> str:
    reset_client()
    res = restore_system_cursor()
    return _json({"status": "ok", "cursor_restored": res})


TOOL_DEFINITIONS = [
    {
        "name": "computer_list_windows",
        "description": "List all interactive, visible Windows application windows on the desktop.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "include_system": {"type": "boolean", "description": "Include system and background windows"}
            }
        },
        "handler": tool_list_windows
    },
    {
        "name": "computer_activate_window",
        "description": "Bring a target window to foreground by title, substring, HWND ID, or #index.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Window title, HWND ID, or #index (e.g. '#1', '132290', 'Chrome')"}
            },
            "required": ["target"]
        },
        "handler": tool_activate_window
    },
    {
        "name": "computer_get_window_state",
        "description": "Capture screenshot and state bounds of a target window.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Window title, HWND ID, or #index"},
                "save_path": {"type": "string", "description": "Optional file path to save PNG screenshot"},
                "crop": {"type": "string", "description": "Optional crop box 'x,y,w,h'"}
            },
            "required": ["target"]
        },
        "handler": tool_get_window_state
    },
    {
        "name": "computer_screenshot",
        "description": "Save screenshot of target window to a PNG file, with optional crop.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Window title, HWND ID, or #index"},
                "out_path": {"type": "string", "description": "Output PNG path (default: screenshot.png)"},
                "crop": {"type": "string", "description": "Optional crop box 'x,y,w,h'"}
            },
            "required": ["target"]
        },
        "handler": tool_screenshot
    },
    {
        "name": "computer_click",
        "description": "Click coordinates inside a window.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Window title, HWND ID, or #index"},
                "x": {"type": "integer", "description": "X coordinate"},
                "y": {"type": "integer", "description": "Y coordinate"},
                "mouse_button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"},
                "click_count": {"type": "integer", "default": 1}
            },
            "required": ["target", "x", "y"]
        },
        "handler": tool_click
    },
    {
        "name": "computer_click_center",
        "description": "Click at the exact geometric center of a target window.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Window title, HWND ID, or #index"},
                "mouse_button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"},
                "click_count": {"type": "integer", "default": 1}
            },
            "required": ["target"]
        },
        "handler": tool_click_center
    },
    {
        "name": "computer_type_text",
        "description": "Type text into focused control in target window.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Window title, HWND ID, or #index"},
                "text": {"type": "string", "description": "Text to type"}
            },
            "required": ["target", "text"]
        },
        "handler": tool_type_text
    },
    {
        "name": "computer_press_key",
        "description": "Press key or keyboard shortcut chord (e.g. 'Return', 'Tab', 'Control_L+a').",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Window title, HWND ID, or #index"},
                "key": {"type": "string", "description": "Key or shortcut chord"}
            },
            "required": ["target", "key"]
        },
        "handler": tool_press_key
    },
    {
        "name": "computer_scroll",
        "description": "Scroll at coordinates inside the target window.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Window title, HWND ID, or #index"},
                "x": {"type": "integer", "description": "X coordinate"},
                "y": {"type": "integer", "description": "Y coordinate"},
                "scroll_x": {"type": "integer", "default": 0},
                "scroll_y": {"type": "integer", "default": 600}
            },
            "required": ["target", "x", "y"]
        },
        "handler": tool_scroll
    },
    {
        "name": "computer_drag",
        "description": "Drag mouse from coordinates to coordinates in the target window.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Window title, HWND ID, or #index"},
                "from_x": {"type": "integer", "description": "Start X"},
                "from_y": {"type": "integer", "description": "Start Y"},
                "to_x": {"type": "integer", "description": "End X"},
                "to_y": {"type": "integer", "description": "End Y"}
            },
            "required": ["target", "from_x", "from_y", "to_x", "to_y"]
        },
        "handler": tool_drag
    },
    {
        "name": "computer_aim",
        "description": "Relative mouse delta for 3D games / FPS camera aiming (bypasses absolute window coords).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dx": {"type": "integer", "description": "Delta X"},
                "dy": {"type": "integer", "description": "Delta Y"},
                "target": {"type": "string", "description": "Optional target window"}
            },
            "required": ["dx", "dy"]
        },
        "handler": tool_aim
    },
    {
        "name": "computer_hold_key",
        "description": "Hold keyboard key down with hardware DirectX scan codes (WASD movement).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Key name (w, a, s, d, shift, space, etc.)"},
                "duration": {"type": "number", "default": 0.5, "description": "Duration in seconds"},
                "target": {"type": "string", "description": "Optional target window"}
            },
            "required": ["key"]
        },
        "handler": tool_hold_key
    },
    {
        "name": "computer_mouse_down",
        "description": "Press and hold a mouse button down.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"},
                "target": {"type": "string", "description": "Optional target window"}
            }
        },
        "handler": tool_mouse_down
    },
    {
        "name": "computer_mouse_up",
        "description": "Release a held mouse button.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"},
                "target": {"type": "string", "description": "Optional target window"}
            }
        },
        "handler": tool_mouse_up
    },
    {
        "name": "computer_shoot",
        "description": "Fire weapon burst by holding mouse button down for duration seconds.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"},
                "duration": {"type": "number", "default": 0.15, "description": "Burst duration in seconds"},
                "target": {"type": "string", "description": "Optional target window"}
            }
        },
        "handler": tool_shoot
    },
    {
        "name": "computer_run_macro",
        "description": "Execute an atomic list of gaming or automation actions without LLM latency jitter.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "actions": {
                    "type": "array",
                    "description": "List of action objects: aim, hold_key, press_key, click, mouse_down, mouse_up, shoot, sleep"
                },
                "target": {"type": "string", "description": "Optional target window"}
            },
            "required": ["actions"]
        },
        "handler": tool_run_macro
    },
    {
        "name": "computer_cycle_windows",
        "description": "Sequentially cycle through all interactive application windows with a delay.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "delay": {"type": "number", "default": 1.0, "description": "Delay in seconds between activations"}
            }
        },
        "handler": tool_cycle_windows
    },
    {
        "name": "computer_restore_cursor",
        "description": "Emergency utility: unclip and restore standard Windows hardware mouse cursor.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        },
        "handler": tool_restore_cursor
    }
]

TOOL_MAP = {t["name"]: t for t in TOOL_DEFINITIONS}


def build_mcp_server():
    server = MCPServer(
        name="win-computer-use",
        version="1.0.0",
        instructions=(
            "Interact with Microsoft Windows desktop GUI, applications, games, and windows via native CUA bridge. "
            "Supports window enumeration, activation, clicking, typing, screenshots, gaming input, and cursor recovery."
        )
    )

    for defn in TOOL_DEFINITIONS:
        server.tool(name=defn["name"], description=defn["description"])(defn["handler"])

    return server


def run_raw_stdio_server():
    """Zero-dependency stdio JSON-RPC 2.0 MCP server fallback."""
    import io
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8")
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue

        method = req.get("method")
        msg_id = req.get("id")

        if method == "ping":
            resp = {"jsonrpc": "2.0", "id": msg_id, "result": {}}
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()

        elif method == "initialize":
            resp = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {"listChanged": True}},
                    "serverInfo": {"name": "win-computer-use", "version": "1.0.0"}
                }
            }
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()

        elif method == "notifications/initialized":
            pass

        elif method == "tools/list":
            tools_data = []
            for t in TOOL_DEFINITIONS:
                tools_data.append({
                    "name": t["name"],
                    "description": t["description"],
                    "inputSchema": t["inputSchema"]
                })
            resp = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": tools_data}
            }
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()

        elif method == "tools/call":
            params = req.get("params", {})
            t_name = params.get("name")
            t_args = params.get("arguments") or {}

            if t_name in TOOL_MAP:
                try:
                    result_text = TOOL_MAP[t_name]["handler"](**t_args)
                    resp = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "content": [{"type": "text", "text": str(result_text)}]
                        }
                    }
                except Exception as e:
                    reset_client()
                    resp = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                            "isError": True
                        }
                    }
            else:
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Tool '{t_name}' not found"}
                }
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()

        elif msg_id is not None:
            resp = {"jsonrpc": "2.0", "id": msg_id, "result": {}}
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


def main():
    if _MCP_SDK_AVAILABLE:
        server = build_mcp_server()
        server.run(transport="stdio")
    else:
        run_raw_stdio_server()


if __name__ == "__main__":
    main()
