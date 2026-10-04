"""Read current Windows input state without installing hooks or logging keys."""
import ctypes
import sys


def pressed_keys() -> set[int]:
    if sys.platform != "win32":
        return set()
    get_state = ctypes.windll.user32.GetAsyncKeyState
    # Ignore mouse buttons (VK 1..6); Qt and cursor polling handle those.
    return {key for key in range(8, 255) if get_state(key) & 0x8000}


def new_key_pressed(before: set[int], current: set[int]) -> bool:
    return bool(current - before)
