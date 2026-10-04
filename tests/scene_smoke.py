"""Headless integration checks with real Piper audio and synthetic input."""
from pathlib import Path
import tempfile
import time
import wave
from unittest.mock import patch

from PySide6.QtCore import QPoint, QPointF, QEvent, QEventLoop, QTimer, Qt
from PySide6.QtGui import QFontDatabase, QMouseEvent
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from drowsy_guard.config import PROJECT
from drowsy_guard.scene import ScenePanel
from drowsy_guard.speech import DEFAULT_PHRASES, cache_path


def qt_wait(milliseconds):
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()


def wait_for(predicate, timeout=60):
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() >= deadline:
            raise AssertionError("Timed out waiting for background work")
        qt_wait(25)


def main():
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    QFontDatabase.addApplicationFont("C:/Windows/Fonts/arial.ttf")
    (PROJECT / "cache").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=PROJECT / "cache") as temporary:
        with patch("drowsy_guard.scene.pressed_keys", return_value=set()), patch(
            "drowsy_guard.scene.QCursor.pos", return_value=QPoint(0, 0)
        ), patch("drowsy_guard.overlay.QCursor.pos", return_value=QPoint(0, 0)):
            panel = ScenePanel(data_dir=Path(temporary))
            try:
                panel.context = {"time": "3:00 AM"}  # Deterministic even across a real minute boundary.
                panel.settings["desktop_glitch"] = False
                wait_for(lambda: panel.ready)
                print("Speech preparation passed", flush=True)
                assert panel.font_family == "Creepster", panel.font_family
                for text in DEFAULT_PHRASES:
                    path = cache_path(panel.cache_folder, text, Path(panel.settings["voice"]))
                    if not path.exists():
                        continue
                    with wave.open(str(path)) as audio:
                        assert audio.getnchannels() == 2
                        assert 0 < audio.getnframes() / audio.getframerate() <= 12.5
                events = []
                panel.speech_player.playbackStateChanged.connect(
                    lambda state: events.append((time.monotonic(), state)))
                panel.preview_scene()
                assert panel.overlays, (panel.message.text(), panel.ready, panel.prepared_context, panel.current_context())
                first = panel.last_phrase
                started = time.monotonic()
                qt_wait(1200)
                panel.overlays[0].grab().save(str(PROJECT / "cache/scene-preview.png"))
                assert not any(state == QMediaPlayer.PlaybackState.PlayingState for _, state in events)
                qt_wait(1150)
                assert any(state == QMediaPlayer.PlaybackState.PlayingState and when - started >= 1.9
                           for when, state in events), "Speech did not start after two seconds"
                assert panel.overlays, "Scene ended prematurely"
                print("Delayed speech passed", flush=True)
                wait_for(lambda: not panel.overlays, timeout=14)
                assert 14.8 <= time.monotonic() - started <= 16.2, "Wrong scene maximum"
                assert not panel.voice_timer.isActive() and not panel.music_timer.isActive()
                panel.preview_scene()
                assert panel.last_phrase != first
                QTest.keyClick(panel.overlays[0], Qt.Key.Key_A)
                assert not panel.overlays, "Any key should dismiss"
                qt_wait(2200)
                assert panel.speech_player.playbackState() == QMediaPlayer.PlaybackState.StoppedState
                panel.preview_scene()
                overlay = panel.overlays[0]
                event = QMouseEvent(QEvent.Type.MouseMove, QPointF(20, 20), QPointF(20, 20),
                                    Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
                overlay.mouseMoveEvent(event)
                assert not panel.overlays, "Mouse movement should dismiss"
                panel.preview_scene()
                with patch("drowsy_guard.scene.pressed_keys", return_value={66}):
                    panel.check_mouse()
                assert not panel.overlays, "Global input polling should dismiss"
                for phrase in panel.settings['phrases']:
                    phrase['enabled'] = False
                panel.schedule_speech()
                wait_for(lambda: panel.ready)
                assert panel.choose_line() == ('', None), 'Unchecked phrases must never use a hidden fallback'
                panel.preview_scene()
                assert panel.overlays and not panel.voice_timer.isActive()
                panel.dismiss_scene()
                panel.new_phrase()
                panel.phrase_text.setText("I am right behind you.")
                previous = len(panel.settings["phrases"])
                panel.preview_draft()
                wait_for(lambda: not panel.preview_workers)
                assert len(panel.settings["phrases"]) == previous, "Unsaved preview modified phrases"
                panel.save_phrase()
                wait_for(lambda: panel.ready)
                assert len(panel.settings["phrases"]) == previous + 1
                recording = panel.cache_folder / "soundscape-v1.wav"
                panel.recording.setText(str(recording))
                panel.save_phrase()
                wait_for(lambda: panel.ready)
                panel.settings["phrases"] = [dict(id="recorded", text="Recorded line", enabled=True,
                                                  audio_file=str(recording))]
                text, path = panel.choose_line()
                assert text == "Recorded line" and path == recording
                print("PASS: real stereo speech, font, delayed voice, 15s cap, local/global input dismissal, cancelled timers,")
                print("      draft preview without saving, phrase persistence, custom recording selection")
            finally:
                panel.shutdown()
                panel.deleteLater()
                qt_wait(50)


if __name__ == "__main__":
    main()
