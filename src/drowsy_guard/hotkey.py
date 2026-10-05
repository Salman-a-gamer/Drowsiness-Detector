"""Windows registered shortcut, without keyboard hooks or keystroke logging."""
import ctypes
from ctypes import wintypes
import sys

from PySide6.QtCore import QAbstractNativeEventFilter, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication


def hotkey_parts(text):
    sequence = QKeySequence.fromString(text, QKeySequence.SequenceFormat.PortableText)
    if sequence.count() != 1:
        raise ValueError('Choose one combination, such as Ctrl+Alt+J.')
    combination = sequence[0]
    key = combination.key().value
    qt_modifiers = combination.keyboardModifiers()
    modifiers = 0
    for qt_flag, windows_flag in ((Qt.KeyboardModifier.AltModifier, 1),
                                 (Qt.KeyboardModifier.ControlModifier, 2),
                                 (Qt.KeyboardModifier.ShiftModifier, 4)):
        if qt_modifiers & qt_flag:
            modifiers |= windows_flag
    if not modifiers or qt_modifiers & Qt.KeyboardModifier.MetaModifier:
        raise ValueError('Use Ctrl, Alt or Shift with a letter, number, or F1–F11. Windows-key shortcuts are reserved.')
    if 65 <= key <= 90 or 48 <= key <= 57:
        virtual_key = key
    elif Qt.Key.Key_F1.value <= key <= Qt.Key.Key_F11.value:
        virtual_key = 112 + key - Qt.Key.Key_F1.value
    else:
        raise ValueError('Use a letter, number, or F1–F11. F12 is reserved by Windows.')
    return modifiers | 0x4000, virtual_key  # MOD_NOREPEAT prevents held-key repeats.


class GlobalScareHotkey(QAbstractNativeEventFilter):
    def __init__(self, callback, api=None):
        super().__init__()
        self.callback = callback
        self.api = api if api is not None else (ctypes.windll.user32 if sys.platform == 'win32' else None)
        self.active_id = None
        self.installed = False
        if self.api is not None:
            self.api.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
            self.api.RegisterHotKey.restype = wintypes.BOOL
            self.api.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
            self.api.UnregisterHotKey.restype = wintypes.BOOL

    def configure(self, text, enabled):
        if not enabled:
            self.unregister()
            return
        modifiers, key = hotkey_parts(text)
        if self.api is None:
            raise ValueError('Global shortcuts are available on Windows only.')
        if getattr(self, 'registered_parts', None) == (modifiers, key) and self.active_id is not None:
            return
        next_id = 0x571 if self.active_id != 0x571 else 0x572
        if not self.api.RegisterHotKey(None, next_id, modifiers, key):
            raise ValueError('Shortcut is already used or unavailable. Choose another combination; the previous shortcut is unchanged.')
        self.unregister()
        self.active_id = next_id
        self.registered_parts = (modifiers, key)
        if not self.installed:
            QApplication.instance().installNativeEventFilter(self)
            self.installed = True

    def unregister(self):
        if self.active_id is not None:
            self.api.UnregisterHotKey(None, self.active_id)
        self.active_id = None

    def nativeEventFilter(self, event_type, message):
        if self.active_id is not None and bytes(event_type) in (b'windows_generic_MSG', b'windows_dispatcher_MSG'):
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x0312 and msg.wParam == self.active_id:
                self.callback()
                return True, 0
        return False, 0

    def close(self):
        self.unregister()
        if self.installed:
            QApplication.instance().removeNativeEventFilter(self)
            self.installed = False
