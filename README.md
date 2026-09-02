# win-computer-use

**High-Performance Windows Desktop Automation & Computer Use Bridge** leveraging OpenAI Codex CUA engine (`SendInput`, `UI Automation`, `Windows.Graphics.Capture`).

---

## 🌟 Features

- **Direct Native Engine Integration:** Uses `codex-computer-use.exe` directly over fast JSON-RPC 2.0.
- **Desktop Isolation Bypass:** Seamlessly bridges Antigravity/agent sandboxes to `WinSta0\Default` using `CreateProcessW` desktop targeting.
- **Automatic App Authorizations:** Intercepts and auto-resolves OpenAI approval requests (`x-oai-cua-approved-app`).
- **Hardware Cursor Guardian:** Automatically restores system cursor visibility (`SPI_SETCURSORS`, `ShowCursor`) on process exit, turn end, or crash.
- **Occluded Screenshots:** Captures accurate window states even when windows are completely covered or in background via WGC.
- **Stdio MCP Server:** Plug-and-play Model Context Protocol (MCP) server for Antigravity, Claude, and Codex agents.

---

## 🚀 Quick Start (CLI)

```powershell
# 1. List active windows on taskbar
python -m win_computer_use list

# 2. Activate a window
python -m win_computer_use activate "Chrome"

# 3. Click center of window (e.g. video player toggle)
python -m win_computer_use click-center "Chrome"

# 4. Click specific window-relative coordinates
python -m win_computer_use click "Chrome" --x 637 --y 492

# 5. Capture screenshot of target window
python -m win_computer_use screenshot "Hearthstone" --out hearthstone.png

# 6. Type text into active control
python -m win_computer_use type "Notepad" "Hello from Antigravity"

# 7. Press keyboard shortcuts
python -m win_computer_use press "Chrome" "Control_L+w"

# 8. Cycle through all open windows
python -m win_computer_use cycle --delay 1.2

# 9. Emergency cursor unhide
python -m win_computer_use restore-cursor
```

---

## 🐍 Python API

```python
from win_computer_use import ComputerUseClient

with ComputerUseClient() as cua:
    # 1. Find window
    target = cua.find_window("Google Chrome")
    
    # 2. Bring to front
    cua.activate_window(target)
    
    # 3. Click
    cua.click_center(target)
    
    # 4. Capture screenshot
    meta = cua.save_screenshot(target, "chrome_state.png")
    print(f"Captured {meta['width']}x{meta['height']}")
```

---

## 🤖 MCP Server Setup

Add this block to your agent's MCP configuration:

```json
{
  "mcpServers": {
    "win-computer-use": {
      "command": "python",
      "args": ["C:/Users/mist8/.gemini/antigravity/scratch/win-computer-use/mcp_server.py"]
    }
  }
}
```

### Exposed MCP Tools:
- `computer_list_windows`
- `computer_activate_window`
- `computer_get_window_state`
- `computer_click`
- `computer_click_center`
- `computer_type_text`
- `computer_press_key`
- `computer_scroll`
- `computer_restore_cursor`
