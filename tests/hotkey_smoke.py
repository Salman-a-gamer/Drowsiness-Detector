"""Exercise real Windows shortcut registration and Qt native message delivery."""
import ctypes
from ctypes import wintypes
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication
from drowsy_guard.hotkey import GlobalScareHotkey

app = QApplication([])
calls = []
manager = GlobalScareHotkey(lambda: calls.append(True))
collision = GlobalScareHotkey(lambda: None)
try:
    manager.configure('Ctrl+Alt+J', True)
    try:
        collision.configure('Ctrl+Alt+J', True)
    except ValueError:
        pass
    else:
        raise AssertionError('Windows failed to reject a conflicting shortcut')
    user = ctypes.windll.user32
    user.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    assert user.PostThreadMessageW(ctypes.windll.kernel32.GetCurrentThreadId(), 0x312, manager.active_id, 0)
    loop = QEventLoop()
    QTimer.singleShot(200, loop.quit)
    loop.exec()
    assert calls == [True], 'Qt did not receive the registered Windows hotkey message'
    manager.close()
    collision.configure('Ctrl+Alt+J', True)
    print('PASS: Windows global registration, conflict handling, Qt message delivery and unregistration')
finally:
    manager.close()
    collision.close()
