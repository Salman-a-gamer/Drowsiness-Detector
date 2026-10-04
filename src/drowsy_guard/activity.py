"""Read the foreground window title locally; never store activity history."""
import ctypes
import os
import sys
from ctypes import wintypes


def active_window_title():
    if sys.platform != 'win32':
        return None
    user = ctypes.windll.user32
    user.GetForegroundWindow.restype = wintypes.HWND
    handle = user.GetForegroundWindow()
    if not handle:
        return None
    process = wintypes.DWORD()
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user.GetWindowThreadProcessId(handle, ctypes.byref(process))
    if process.value == os.getpid():
        return None
    user.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    length = user.GetWindowTextLengthW(handle)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user.GetWindowTextW(handle, buffer, length + 1)
    title = ' '.join(buffer.value.split())
    return (title[:29] + '...') if len(title) > 32 else title or None
