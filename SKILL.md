---
name: win-computer-use
description: Control and automate Microsoft Windows desktop applications via OpenAI CUA native engine.
---

# Windows Computer Use Skill

This skill enables Antigravity and other AI coding assistants to interact with desktop GUI applications on Windows 10/11 using the high-performance OpenAI CUA helper.

## Prerequisites
1. Windows 10 / 11 (x64)
2. Python 3.10+ (standard library only, zero pip dependencies)
3. OpenAI Codex or ChatGPT Desktop installed (the helper `codex-computer-use.exe` is auto-discovered in `%LOCALAPPDATA%\OpenAI\Codex`).
   * No active subscription or cloud calls are needed; the engine runs strictly on the local machine via Win32/UIA.

## Capabilities
- **Window Enumeration**: List open visible application windows (`list_windows`).
- **Window Activation**: Bring target windows to the foreground (`activate_window`).
- **Occluded Screenshots**: Capture crisp window screenshots even if the window is behind other windows via `Windows.Graphics.Capture`.
- **Input Automation**: Click (`click`, `click_center`), type text (`type_text`), send keyboard chords (`press_key`), scroll (`scroll`), drag (`drag`).
- **Auto-Approval**: Handles app authorization challenges transparently.
- **Cursor Guardian**: Automatically recovers the hardware mouse cursor on turn exit or error.

## Quick CLI Reference

```powershell
# List active windows
python -m win_computer_use list

# Bring window to foreground
python -m win_computer_use activate "Hearthstone"

# Click center of window
python -m win_computer_use click-center "Google Chrome"

# Click exact coordinates
python -m win_computer_use click "Chrome" --x 637 --y 492

# Take screenshot
python -m win_computer_use screenshot "Hearthstone" --out hs.png

# Type text into focused control
python -m win_computer_use type "Notepad" "Hello world"

# Press shortcut / key
python -m win_computer_use press "Chrome" "Control_L+w"

# Cycle through all active windows with 1s delay
python -m win_computer_use cycle --delay 1.0

# Emergency cursor restore
python -m win_computer_use restore-cursor
```

## MCP Server Integration

Add to your MCP configuration (`mcp_config.json`):

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
