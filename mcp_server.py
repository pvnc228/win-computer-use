import sys
import json
import traceback
from typing import Any, Dict
from win_computer_use.client import ComputerUseClient
from win_computer_use.cursor import restore_system_cursor

TOOLS = [
    {
        "name": "computer_list_windows",
        "description": "List all interactive, visible Windows application windows on the desktop.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "include_system": {
                    "type": "boolean",
                    "description": "Whether to include background/system handles (default false)"
                }
            }
        }
    },
    {
        "name": "computer_activate_window",
        "description": "Bring a target window to the foreground by its title substring or HWND ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Window title substring or numeric HWND ID"
                }
            },
            "required": ["target"]
        }
    },
    {
        "name": "computer_get_window_state",
        "description": "Capture the screenshot and state of a target window (even if partially occluded).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Window title substring or numeric HWND ID"
                },
                "save_path": {
                    "type": "string",
                    "description": "Optional file path to save the screenshot PNG image directly"
                }
            },
            "required": ["target"]
        }
    },
    {
        "name": "computer_click",
        "description": "Click coordinates inside a window.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Window title substring or numeric HWND ID"
                },
                "x": {
                    "type": "integer",
                    "description": "Window-relative X coordinate"
                },
                "y": {
                    "type": "integer",
                    "description": "Window-relative Y coordinate"
                },
                "mouse_button": {
                    "type": "string",
                    "enum": ["left", "right", "middle"],
                    "default": "left"
                },
                "click_count": {
                    "type": "integer",
                    "default": 1
                }
            },
            "required": ["target", "x", "y"]
        }
    },
    {
        "name": "computer_click_center",
        "description": "Convenience tool: click exactly in the geometric center of the target window (e.g. video player toggle).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Window title substring or numeric HWND ID"
                },
                "mouse_button": {
                    "type": "string",
                    "enum": ["left", "right", "middle"],
                    "default": "left"
                }
            },
            "required": ["target"]
        }
    },
    {
        "name": "computer_type_text",
        "description": "Type text into the currently focused control in the target window.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Window title substring or numeric HWND ID"
                },
                "text": {
                    "type": "string",
                    "description": "Text to type"
                }
            },
            "required": ["target", "text"]
        }
    },
    {
        "name": "computer_press_key",
        "description": "Press a key or shortcut chord (e.g. 'Return', 'Tab', 'Escape', 'Control_L+a').",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Window title substring or numeric HWND ID"
                },
                "key": {
                    "type": "string",
                    "description": "Key or chord string"
                }
            },
            "required": ["target", "key"]
        }
    },
    {
        "name": "computer_scroll",
        "description": "Scroll at coordinates in the target window.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Window title substring or numeric HWND ID"
                },
                "x": { "type": "integer" },
                "y": { "type": "integer" },
                "scroll_x": { "type": "integer", "default": 0 },
                "scroll_y": { "type": "integer", "default": 600 }
            },
            "required": ["target", "x", "y"]
        }
    },
    {
        "name": "computer_restore_cursor",
        "description": "Emergency utility: unclip and restore standard Windows mouse cursor.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]

def handle_call(name: str, arguments: Dict[str, Any]) -> Any:
    if name == "computer_restore_cursor":
        res = restore_system_cursor()
        return {"status": "ok", "cursor_restored": res}

    with ComputerUseClient() as cua:
        if name == "computer_list_windows":
            inc_sys = arguments.get("include_system", False)
            windows = cua.list_windows(filter_system=not inc_sys)
            return {"windows": windows, "count": len(windows)}

        target = arguments.get("target")

        if name == "computer_activate_window":
            cua.activate_window(target)
            return {"status": "ok", "activated": target}

        if name == "computer_click":
            cua.click(
                target,
                x=arguments["x"],
                y=arguments["y"],
                mouse_button=arguments.get("mouse_button", "left"),
                click_count=arguments.get("click_count", 1)
            )
            return {"status": "ok", "clicked": {"target": target, "x": arguments["x"], "y": arguments["y"]}}

        if name == "computer_click_center":
            res = cua.click_center(
                target,
                mouse_button=arguments.get("mouse_button", "left")
            )
            return {"status": "ok", "clicked_center": res}

        if name == "computer_type_text":
            cua.type_text(target, arguments["text"])
            return {"status": "ok", "typed": arguments["text"]}

        if name == "computer_press_key":
            cua.press_key(target, arguments["key"])
            return {"status": "ok", "pressed": arguments["key"]}

        if name == "computer_scroll":
            cua.scroll(
                target,
                x=arguments["x"],
                y=arguments["y"],
                scroll_x=arguments.get("scroll_x", 0),
                scroll_y=arguments.get("scroll_y", 600)
            )
            return {"status": "ok", "scrolled": True}

        if name == "computer_get_window_state":
            save_path = arguments.get("save_path")
            if save_path:
                meta = cua.save_screenshot(target, save_path)
                return {"status": "ok", "screenshot": meta}
            else:
                state = cua.get_window_state(target, include_screenshot=True)
                s = state.get("screenshots", [{}])[0]
                return {
                    "status": "ok",
                    "id": s.get("id"),
                    "width": s.get("width"),
                    "height": s.get("height"),
                    "originX": s.get("originX"),
                    "originY": s.get("originY")
                }

    raise ValueError(f"Unknown tool: {name}")

def main():
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

        if method == "initialize":
            resp = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": True}
                    },
                    "serverInfo": {
                        "name": "win-computer-use",
                        "version": "1.0.0"
                    }
                }
            }
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()

        elif method == "notifications/initialized":
            pass

        elif method == "tools/list":
            resp = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": TOOLS
                }
            }
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()

        elif method == "tools/call":
            params = req.get("params", {})
            name = params.get("name")
            args = params.get("arguments", {})

            try:
                result_data = handle_call(name, args)
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": json.dumps(result_data, ensure_ascii=False, indent=2)}
                        ],
                        "isError": False
                    }
                }
            except Exception as e:
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": f"Error: {e}\n{traceback.format_exc()}"}
                        ],
                        "isError": True
                    }
                }

            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
