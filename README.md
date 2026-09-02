# win-computer-use

High-Performance Windows Desktop Automation & Computer Use Bridge leveraging the native OpenAI Codex CUA engine (`SendInput`, `UI Automation`, `Windows.Graphics.Capture`).

Fully operable both as an interactive command-line interface (CLI) and as a zero-dependency Model Context Protocol (MCP) server with 100% feature parity.

---

## Highlights

- **Full MCP Protocol Support:** 100% feature parity with the CLI. An agent can control Windows entirely through MCP without needing command-line execution access.
- **Zero Third-Party Dependencies:** Built strictly on the Python standard library (`ctypes`, `subprocess`, `json`, `os`, `sys`). Requires no external pip packages for core runtime or MCP stdio transport.
- **Desktop Isolation Bypass (`WinSta0\Default`):** Launches helper processes directly onto the interactive user desktop, bypassing Windows sandbox isolation (`exebox-...`) where AI agents normally see 0 windows.
- **Auto-Approval Interception:** Automatically intercepts OpenAI CUA `approvalRequest` challenges, authorizes the target application, and completes the action without human intervention.
- **Hardware Cursor Guardian:** Unconditionally resets the Windows mouse cursor via `SPI_SETCURSORS` and `ShowCursor(True)` on exit or error, preventing mouse pointer disappearance.
- **Browser Policy Bypass & GDI Fallback:** Automatically falls back to Win32 GDI `BitBlt` capture if the CUA helper halts on browser URL checks or minimized windows.
- **Hardware Gaming Engine:** DirectInput and Raw Input support with hardware DirectX scan codes (`KEYEVENTF_SCANCODE`), relative mouse delta movement for 3D/FPS camera aiming, button holding, weapon bursts, and atomic macro execution.

---

## Prerequisites

1. **Operating System:** Windows 10 or Windows 11 (64-bit).
2. **Python:** Python 3.10+ (Standard library only).
3. **OpenAI Codex or ChatGPT Desktop for Windows:**
   - Provides the local helper daemon `codex-computer-use.exe`.
   - Installed automatically at `%LOCALAPPDATA%\OpenAI\Codex\runtimes\cua_node\<hash>\bin\node_modules\@oai\sky\bin\windows\codex-computer-use.exe`.
   - **Offline & Local:** No ChatGPT subscription or cloud API key is required. The binary runs 100% locally.
   - The path can optionally be overridden via the `CODEX_CUA_HELPER_PATH` environment variable.

---

## Model Context Protocol (MCP) Server

`win-computer-use` can run as a standard stdio MCP server for AI agents (Gemini in Antigravity, Claude Code, Cursor, Codex). The server contains a built-in JSON-RPC 2.0 stdio engine that works on pure Python standard library (no pip packages needed) and automatically upgrades to the official `mcp` SDK when installed.

### Configuration (`mcp_config.json`):

```json
{
  "mcpServers": {
    "win-computer-use": {
      "command": "python",
      "args": ["C:/path/to/win-computer-use/mcp_server.py"]
    }
  }
}
```

### Complete MCP Tools Reference (18 Tools):

| Tool Name | Description |
|---|---|
| `computer_list_windows` | Enumerate visible, interactive desktop windows with HWNDs. |
| `computer_activate_window` | Bring window to foreground by title, substring, HWND ID, or `#index`. |
| `computer_get_window_state` | Capture screenshot, window dimensions, and coordinate bounds. |
| `computer_screenshot` | Save screenshot to a PNG file with optional bounding-box crop (`x,y,w,h`). |
| `computer_click` | Click coordinates inside window (`left`, `right`, `middle`, single/double). |
| `computer_click_center` | Click at geometric center of target window. |
| `computer_type_text` | Type text into currently focused control. |
| `computer_press_key` | Send key or chord shortcut (e.g. `Return`, `Tab`, `Control_L+s`). |
| `computer_scroll` | Scroll by horizontal and vertical pixel deltas. |
| `computer_drag` | Drag mouse between two sets of coordinates. |
| `computer_aim` | Relative mouse delta for 3D games and FPS camera aiming. |
| `computer_hold_key` | Hold keyboard key with hardware DirectX scan codes (WASD movement). |
| `computer_mouse_down` | Press and hold a mouse button down. |
| `computer_mouse_up` | Release a held mouse button. |
| `computer_shoot` | Fire weapon burst by holding mouse button for duration. |
| `computer_run_macro` | Execute atomic composite action sequences without LLM turn latency. |
| `computer_cycle_windows` | Sequentially cycle through all interactive application windows with a delay. |
| `computer_restore_cursor` | Emergency hardware mouse cursor unclip and restoration. |

---

## CLI Usage

Every tool is also accessible directly from the command line:

```powershell
# List active windows
python -m win_computer_use list

# Bring window to foreground by name, HWND, or #index
python -m win_computer_use activate "#1"
python -m win_computer_use activate "Chrome"
python -m win_computer_use activate 132290

# Click window center
python -m win_computer_use click-center "Chrome"

# Click relative coordinates
python -m win_computer_use click "Chrome" --x 637 --y 492 --button left --count 1

# Take screenshot (with optional crop)
python -m win_computer_use screenshot "Chrome" --out screen.png --crop 100,100,300,300

# Type text
python -m win_computer_use type "Notepad" "Hello from Gemini"

# Press shortcut / key
python -m win_computer_use press "Chrome" "Control_L+w"

# Scroll
python -m win_computer_use scroll "Chrome" --x 500 --y 500 --scroll-y 600

# Drag
python -m win_computer_use drag "App" --from-x 100 --from-y 200 --to-x 400 --to-y 500

# 3D / FPS relative aiming
python -m win_computer_use aim "Game" --dx 120 --dy -15

# Hold key with hardware scan codes (WASD movement)
python -m win_computer_use hold "Game" --key w --duration 1.5

# Weapon burst
python -m win_computer_use shoot "Game" --button left --duration 0.2

# Atomic macro execution
python -m win_computer_use macro "Game" '[{"action":"hold_key","key":"w","duration":1.0},{"action":"aim","dx":80,"dy":0},{"action":"shoot","duration":0.2}]'

# Cycle windows
python -m win_computer_use cycle --delay 1.0

# Emergency cursor restore
python -m win_computer_use restore-cursor
```

---

## Python Library API

```python
from win_computer_use import ComputerUseClient

with ComputerUseClient() as cua:
    target = cua.find_window("Google Chrome")
    if target:
        cua.activate_window(target)
        cua.click_center(target)
        meta = cua.save_screenshot(target, "chrome_state.png")
        print(f"Screenshot saved: {meta['path']}")

    # Hardware gaming / DirectInput actions
    cua.hold_key(target, "w", duration=1.0)
    cua.aim(target, dx=100, dy=0)
    cua.shoot(target, button="left", duration=0.2)
```

---

## License

MIT License.
