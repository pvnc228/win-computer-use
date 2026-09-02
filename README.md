# win-computer-use

**High-Performance Windows Desktop Automation & Computer Use Bridge** leveraging the native OpenAI Codex CUA engine (`SendInput`, `UI Automation`, `Windows.Graphics.Capture`).

---

## 📋 Prerequisites

To run this library, you need:

1. **Operating System**:
   - Windows 10 or Windows 11 (64-bit).
2. **Python**:
   - Python 3.10+ (**Zero external pip dependencies** — built purely using Python's standard library: `ctypes`, `subprocess`, and `json`).
3. **OpenAI Codex or ChatGPT Desktop for Windows**:
   - This library acts as a native bridge to the local helper daemon `codex-computer-use.exe`, which is bundled with the official OpenAI Codex / ChatGPT Desktop application for Windows.
   - **Default Location:** When ChatGPT Desktop or Codex is installed, the helper binary is automatically unpackaged to:
     ```
     %LOCALAPPDATA%\OpenAI\Codex\runtimes\cua_node\<hash>\bin\node_modules\@oai\sky\bin\windows\codex-computer-use.exe
     ```
   - **No Subscription / Offline Execution:** An active ChatGPT Plus subscription or cloud API key is **not required**. The helper binary executes 100% locally on your machine as an independent Win32/UIA automation process.
   - **Dynamic Auto-Discovery:** The client automatically scans `%LOCALAPPDATA%\OpenAI\Codex` and resolves the latest version of the binary, ensuring future app updates with new folder hashes work seamlessly without manual configuration.
   - *(Optional)* If the binary is stored in a custom directory, you can override its path using an environment variable:
     ```powershell
     $env:CODEX_CUA_HELPER_PATH = "C:\Path\To\codex-computer-use.exe"
     ```

---

## 🌟 Key Features & Solved Architecture Challenges

- **Desktop Isolation Bypass (`WinSta0\Default` Bridge):**
  AI coding agents (such as Antigravity or Claude Code) run commands in isolated sandbox desktops (`exebox-...`), where normal interactive user windows are inaccessible. Our bridge explicitly launches processes onto `WinSta0\Default` via Win32 `CreateProcessW`, granting full visibility into the user's desktop windows.
- **Auto-Approval Loop:**
  The CUA engine implements an authorization layer that halts when targeting a new app process with an `approvalRequest`. Our client automatically intercepts this prompt, applies the appropriate `x-oai-cua-approved-app` authorization metadata, and retries the command seamlessly without blocking.
- **Hardware Cursor Guardian:**
  The native OpenAI driver hides the hardware mouse pointer during automation sessions (`SetSystemCursor`). Our client includes a built-in cursor guardian that resets system cursors (`SPI_SETCURSORS` and `ShowCursor`) upon exit, error, or interruption, preventing cursor freeze.
- **Occluded Window Capture (WGC):**
  Screenshots are captured via `Windows.Graphics.Capture`, allowing crisp window state captures even when windows are completely covered by other applications or in the background.
- **Stdio MCP Server:**
  Includes a fully compliant Model Context Protocol (MCP) server ready to integrate with Antigravity, Claude Code, Cursor, or any other agent environment.

---

## 🚀 Quick Start (CLI)

Run directly from the terminal:

```powershell
# 1. List active windows on the desktop:
python -m win_computer_use list

# 2. Bring a window to foreground:
python -m win_computer_use activate "Chrome"

# 3. Click exactly in the center of a window (e.g. toggle video playback):
python -m win_computer_use click-center "Chrome"

# 4. Click specific window-relative coordinates:
python -m win_computer_use click "Chrome" --x 637 --y 492

# 5. Capture a window screenshot to PNG:
python -m win_computer_use screenshot "Hearthstone" --out hs.png

# 6. Type text into active control:
python -m win_computer_use type "Notepad" "Hello from Antigravity"

# 7. Press keyboard shortcut / chord:
python -m win_computer_use press "Chrome" "Control_L+w"

# 8. Cycle through all open interactive windows (1s delay each):
python -m win_computer_use cycle --delay 1.0

# 9. Emergency cursor restore:
python -m win_computer_use restore-cursor
```

---

## 🐍 Python API

```python
from win_computer_use import ComputerUseClient

# Context manager automatically cleans up sessions and restores cursor
with ComputerUseClient() as cua:
    # 1. Find target window by title substring or HWND
    target = cua.find_window("Google Chrome")
    if target:
        # 2. Activate window
        cua.activate_window(target)
        
        # 3. Click at center
        cua.click_center(target)
        
        # 4. Capture screenshot
        meta = cua.save_screenshot(target, "chrome_state.png")
        print(f"Screenshot saved: {meta['path']} ({meta['width']}x{meta['height']})")
```

---

## 🤖 MCP Server Setup for AI Agents

To add Windows Computer Use capabilities to your AI agent (Antigravity, Claude Desktop, Cursor), add this entry to your MCP configuration file (`mcp_config.json` or `config.toml`):

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
- `computer_list_windows` — Retrieve active, interactive application windows.
- `computer_activate_window` — Bring target window to foreground.
- `computer_get_window_state` — Capture screenshot and coordinate bounds.
- `computer_click` — Click at window-relative coordinates.
- `computer_click_center` — Click at the exact geometric center of a window.
- `computer_type_text` — Type text into active input focus.
- `computer_press_key` — Send key or chord shortcut (e.g. `Return`, `Tab`, `Escape`).
- `computer_scroll` — Scroll by horizontal and vertical delta.
- `computer_restore_cursor` — Emergency hardware cursor restoration.

---

## 📄 License

MIT License.
