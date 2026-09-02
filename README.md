# win-computer-use

**High-Performance Windows Desktop Automation & Computer Use Bridge** leveraging the OpenAI Codex CUA native engine (`SendInput`, `UI Automation`, `Windows.Graphics.Capture`).

---

## 📋 Prerequisites (Что нужно для работы)

Для работы приложения требуются:

1. **Операционная система**:
   - Windows 10 или Windows 11 (64-bit).
2. **Python**:
   - Python 3.10+ (используются **только** стандартные библиотеки `ctypes`, `subprocess`, `json`, сторонних pip-зависимостей нет).
3. **Установленный OpenAI Codex / ChatGPT Desktop**:
   - Данная библиотека работает как нативный мост к бинарному хелперу автоматизации `codex-computer-use.exe`, поставляемому в составе официального приложения OpenAI Codex / ChatGPT Desktop для Windows.
   - **Где он находится:** при установке Codex/ChatGPT бинарник автоматически распаковывается в:
     ```
     %LOCALAPPDATA%\OpenAI\Codex\runtimes\cua_node\<hash>\bin\node_modules\@oai\sky\bin\windows\codex-computer-use.exe
     ```
   - **Подписка / Онлайн:** Для работы самого движка автоматизации подключение к серверам OpenAI или платная подписка **не требуются** — бинарник исполняется полностью локально на вашем компьютере как фоновый Win32/UIA демон.
   - **Автоматическое обнаружение:** Библиотека автоматически сканирует `%LOCALAPPDATA%\OpenAI\Codex` и находит актуальную версию бинарника, даже если хэш директории изменится после обновления приложения.
   - *(Опционально)* Если файл находится в нестандартном месте, путь можно задать через переменную окружения:
     ```powershell
     $env:CODEX_CUA_HELPER_PATH = "C:\Path\To\codex-computer-use.exe"
     ```

---

## 🌟 Ключевые возможности и решённые проблемы

- **Обход изоляции десктопов Windows (WinSta0\Default Bridge):**
  Агенты вроде Antigravity или Claude Code по умолчанию выполняют команды в скрытом изолированном десктопе (`exebox-...`), где нет окон пользователя. Наш клиент использует прямой Win32 `CreateProcessW` с явной привязкой к интерактивному десктопу `WinSta0\Default`, предоставляя агенту полный доступ к реальному рабочему столу.
- **Автоматический обход подтверждений (Auto-Approval Loop):**
  В движок CUA встроена защита прав приложений: при первом обращении он возвращает `approvalRequest`. Наш клиент автоматически перехватывает этот ответ и подставляет заголовок авторизации `x-oai-cua-approved-app`, исключая застревание скриптов.
- **Аппаратный хранитель курсора (Hardware Cursor Guardian):**
  Драйвер OpenAI CUA скрывает физический курсор мыши при автоматизации. В библиотеку встроен сторож курсора, который при любом выходе, ошибке или сигнале завершения гарантированно восстанавливает системные указатели Windows через `SPI_SETCURSORS` и `ShowCursor`.
- **Скриншоты перекрытых окон (WGC):**
  Скриншоты создаются через `Windows.Graphics.Capture`, что позволяет делать снимки окон, даже если они полностью закрыты другими окнами.
- **Stdio MCP Server:**
  Готовый сервер протокола Model Context Protocol (MCP) для подключения к Antigravity, Claude Code, Cursor и другим AI-ассистентам.

---

## 🚀 Использование через CLI

Запуск из директории проекта:

```powershell
# 1. Список активных окон на рабочем столе:
python -m win_computer_use list

# 2. Вывести окно на передний план:
python -m win_computer_use activate "Chrome"

# 3. Кликнуть точно в геометрический центр окна (пауза видео, фокус):
python -m win_computer_use click-center "Chrome"

# 4. Кликнуть по относительным координатам окна:
python -m win_computer_use click "Chrome" --x 637 --y 492

# 5. Сделать скриншот окна (сохраняется в PNG):
python -m win_computer_use screenshot "Hearthstone" --out hs.png

# 6. Напечатать текст в активный элемент ввода:
python -m win_computer_use type "Notepad" "Привет из Antigravity"

# 7. Нажать горячую клавишу или сочетание:
python -m win_computer_use press "Chrome" "Control_L+w"

# 8. Прогнать переключение по всем активным окнам (с задержкой 1 сек):
python -m win_computer_use cycle --delay 1.0

# 9. Экстренное восстановление курсора:
python -m win_computer_use restore-cursor
```

---

## 🐍 Использование в Python

```python
from win_computer_use import ComputerUseClient

# Контекстный менеджер автоматически завершает сессию и восстанавливает курсор
with ComputerUseClient() as cua:
    # Поиск окна по подстроке заголовка или HWND
    target = cua.find_window("Google Chrome")
    if target:
        cua.activate_window(target)
        
        # Клик в центр окна
        cua.click_center(target)
        
        # Захват скриншота
        meta = cua.save_screenshot(target, "chrome_state.png")
        print(f"Скриншот сохранён: {meta['path']} ({meta['width']}x{meta['height']})")
```

---

## 🤖 Подключение MCP-сервера в AI-агенты

Для добавления инструментов Computer Use в Antigravity, Claude Desktop или другие клиенты MCP добавьте блок в конфигурацию (`mcp_config.json`):

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

### Доступные инструменты (MCP Tools):
- `computer_list_windows` — получить список открытых пользовательских окон.
- `computer_activate_window` — вывести окно на передний план.
- `computer_get_window_state` — получить снимок и координаты окна.
- `computer_click` — клик по координатам внутри окна.
- `computer_click_center` — клик точно в центр окна.
- `computer_type_text` — ввод текста в фокус.
- `computer_press_key` — отправка клавиатурного сочетания / клавиши.
- `computer_scroll` — прокрутка колеса мыши.
- `computer_restore_cursor` — сброс скрытого курсора в нормальный режим.

---

## 📄 Лицензия

MIT License.
