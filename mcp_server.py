import sys
import os
import json
import traceback
from typing import Any, Dict, Optional

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


def build_mcp_server():
    server = MCPServer(
        name="win-computer-use",
        version="1.0.0",
        instructions=(
            "Interact with Microsoft Windows desktop GUI, applications, and windows via native CUA bridge. "
            "Supports window enumeration, activation, clicking, typing, screenshots, and cursor recovery."
        )
    )

    @server.tool(
        name="computer_list_windows",
        description="List all interactive, visible Windows application windows on the desktop."
    )
    def computer_list_windows(include_system: bool = False) -> str:
        with ComputerUseClient() as cua:
            windows = cua.list_windows(filter_system=not include_system)
            return _json({"windows": windows, "count": len(windows)})

    @server.tool(
        name="computer_activate_window",
        description="Bring a target window to the foreground by its title substring or HWND ID."
    )
    def computer_activate_window(target: str) -> str:
        with ComputerUseClient() as cua:
            cua.activate_window(target)
            return _json({"status": "ok", "activated": target})

    @server.tool(
        name="computer_get_window_state",
        description="Capture screenshot and state bounds of a target window."
    )
    def computer_get_window_state(target: str, save_path: str = "") -> str:
        with ComputerUseClient() as cua:
            if save_path:
                meta = cua.save_screenshot(target, save_path)
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

    @server.tool(
        name="computer_click",
        description="Click coordinates inside a window."
    )
    def computer_click(target: str, x: int, y: int, mouse_button: str = "left", click_count: int = 1) -> str:
        with ComputerUseClient() as cua:
            cua.click(target, x=x, y=y, mouse_button=mouse_button, click_count=click_count)
            return _json({"status": "ok", "clicked": {"target": target, "x": x, "y": y}})

    @server.tool(
        name="computer_click_center",
        description="Click at the geometric center of a target window."
    )
    def computer_click_center(target: str, mouse_button: str = "left") -> str:
        with ComputerUseClient() as cua:
            res = cua.click_center(target, mouse_button=mouse_button)
            return _json({"status": "ok", "clicked_center": res})

    @server.tool(
        name="computer_type_text",
        description="Type text into the currently focused control in the target window."
    )
    def computer_type_text(target: str, text: str) -> str:
        with ComputerUseClient() as cua:
            cua.type_text(target, text)
            return _json({"status": "ok", "typed": text})

    @server.tool(
        name="computer_press_key",
        description="Press a key or keyboard shortcut chord (e.g. 'Return', 'Tab', 'Control_L+a')."
    )
    def computer_press_key(target: str, key: str) -> str:
        with ComputerUseClient() as cua:
            cua.press_key(target, key)
            return _json({"status": "ok", "pressed": key})

    @server.tool(
        name="computer_scroll",
        description="Scroll at coordinates in the target window."
    )
    def computer_scroll(target: str, x: int, y: int, scroll_x: int = 0, scroll_y: int = 600) -> str:
        with ComputerUseClient() as cua:
            cua.scroll(target, x=x, y=y, scroll_x=scroll_x, scroll_y=scroll_y)
            return _json({"status": "ok", "scrolled": True})

    @server.tool(
        name="computer_drag",
        description="Drag mouse from starting coordinates to ending coordinates in the target window."
    )
    def computer_drag(target: str, from_x: int, from_y: int, to_x: int, to_y: int) -> str:
        with ComputerUseClient() as cua:
            cua.drag(target, from_x=from_x, from_y=from_y, to_x=to_x, to_y=to_y)
            return _json({"status": "ok", "dragged": {"from": [from_x, from_y], "to": [to_x, to_y]}})

    @server.tool(
        name="computer_restore_cursor",
        description="Emergency utility: unclip and restore standard Windows hardware mouse cursor."
    )
    def computer_restore_cursor() -> str:
        res = restore_system_cursor()
        return _json({"status": "ok", "cursor_restored": res})

    return server


def main():
    if _MCP_SDK_AVAILABLE:
        server = build_mcp_server()
        server.run(transport="stdio")
    else:
        # Fallback raw loop with ping and unbuffered I/O
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
            elif msg_id is not None:
                resp = {"jsonrpc": "2.0", "id": msg_id, "result": {}}
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()


if __name__ == "__main__":
    main()
