import ctypes
from ctypes import wintypes
import unittest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication
from drowsy_guard.hotkey import GlobalScareHotkey, hotkey_parts


class HotkeyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_combination_validation(self):
        self.assertEqual(hotkey_parts('Ctrl+Alt+J'), (0x4003, 74))
        self.assertEqual(hotkey_parts('Ctrl+Shift+F9'), (0x4006, 120))
        for invalid in ('J', '', 'Ctrl+F12', 'Meta+J', 'Ctrl+J, Ctrl+K'):
            with self.assertRaises(ValueError):
                hotkey_parts(invalid)

    def test_conflict_keeps_old_shortcut_and_native_message_triggers(self):
        api, callback = MagicMock(), MagicMock()
        api.RegisterHotKey.return_value = True
        manager = GlobalScareHotkey(callback, api=api)
        try:
            manager.configure('Ctrl+Alt+J', True)
            original = manager.active_id
            api.RegisterHotKey.return_value = False
            with self.assertRaises(ValueError):
                manager.configure('Ctrl+Alt+K', True)
            self.assertEqual(manager.active_id, original)
            api.UnregisterHotKey.assert_not_called()
            msg = wintypes.MSG()
            msg.message, msg.wParam = 0x312, original
            self.assertEqual(manager.nativeEventFilter(b'windows_dispatcher_MSG', ctypes.addressof(msg)), (True, 0))
            callback.assert_called_once()
            manager.configure('', False)
            self.assertIsNone(manager.active_id)
            api.UnregisterHotKey.assert_called_once_with(None, original)
        finally:
            manager.close()
