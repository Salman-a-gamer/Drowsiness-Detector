"""Verify the integrated UI, automatic trigger, Stop cancellation, and all-off speech."""
import tempfile
import time
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from drowsy_guard.app import DrowsyGuardWindow
from drowsy_guard.config import PROJECT

def wait(ms):
    loop = QEventLoop(); QTimer.singleShot(ms, loop.quit); loop.exec()

app = QApplication([])
app.setQuitOnLastWindowClosed(False)
QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
with tempfile.TemporaryDirectory(dir=PROJECT/'cache') as folder:
    window = DrowsyGuardWindow(data_dir=Path(folder))
    try:
        window.show()
        wait(100)
        window.grab().save(str(PROJECT/'cache/desktop-ui.png'))
        assert len(window.settings['phrases']) >= 15
        window.running = True
        image = np.zeros((480,640,3),np.uint8)
        with patch.object(window.scene_panel, 'request_scare', return_value=True) as request:
            window.process_frame(image,(.32,.31),100)
            window.process_frame(image,(.1,.1),101)
            window.process_frame(image,(.1,.1),102.6)
            request.assert_called_once()
            assert request.call_args.args[0]['seconds'] == '1.6'
            window.process_frame(image,(.1,.1),110)
            request.assert_called_once()
        window.scene_panel.pending_scare = True
        window.stop_camera()
        assert not window.running and not window.scene_panel.pending_scare
        for phrase in window.settings['phrases']:
            phrase['enabled'] = False
        window.scene_panel.prepared_context = window.scene_panel.current_context()
        assert window.scene_panel.choose_line() == ('',None)
        print('PASS: clean desktop UI, trigger context, one scare per closure, Stop cancellation, visible catalog, all-off silent')
    finally:
        window.close()
