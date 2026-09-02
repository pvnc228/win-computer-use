import ctypes

def restore_system_cursor() -> bool:
    """
    Restores the Windows hardware mouse cursor if it was hidden or altered
    by OpenAI CUA driver or any other automation hook.
    """
    user32 = ctypes.windll.user32
    try:
        h_desk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if h_desk:
            user32.SetThreadDesktop(h_desk)

        # 1. Unclip cursor
        user32.ClipCursor(None)

        # 2. Reload system cursors from registry: SPI_SETCURSORS = 0x0057
        SPI_SETCURSORS = 0x0057
        SPIF_SENDCHANGE = 0x0002
        res = user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, SPIF_SENDCHANGE)

        # 3. Ensure ShowCursor count is non-negative
        for _ in range(10):
            if user32.ShowCursor(True) >= 0:
                break

        return bool(res)
    except Exception:
        return False

if __name__ == "__main__":
    success = restore_system_cursor()
    print("Cursor restored:", success)
