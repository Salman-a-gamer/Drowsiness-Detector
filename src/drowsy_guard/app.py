"""WakeyMonster desktop application: monitoring, studio, and local privacy."""
from __future__ import annotations
import sys
import time
from pathlib import Path

import cv2
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (QApplication, QComboBox, QDoubleSpinBox, QFileDialog,
    QFormLayout, QHBoxLayout, QLabel, QMainWindow, QPushButton, QTabWidget, QVBoxLayout, QWidget, QSizePolicy, QScrollArea)

from .activity import active_window_title
from .camera import CameraWorker, CameraScan
from .config import PROJECT
from .detection import EyeClosureTracker
from .monitoring import ScareGate
from .scene import ScenePanel

STYLE = '''
QWidget { background: #10131b; color: #e4e8f1; font-family: 'Segoe UI'; font-size: 13px; }
QLabel#title { font-size: 27px; font-weight: 700; color: white; }
QLabel#muted { color: #9ca8bd; }
QPushButton { background: #252d40; border: 1px solid #34415c; border-radius: 8px; padding: 10px 16px; }
QPushButton:hover { background: #34415c; }
QPushButton:disabled { color: #68758d; background: #1b2230; }
QPushButton#primary { background: #8e3046; border: 1px solid #c74a68; color: white; }
QLineEdit, QComboBox, QDoubleSpinBox, QListWidget { background: #1b2230; border: 1px solid #34415c; border-radius: 6px; padding: 7px; }
QListWidget::item { padding: 10px; } QListWidget::item:selected { background: #34415c; }
QTabWidget::pane { border: 0; } QTabBar::tab { padding: 12px 22px; background: #1b2230; }
QTabBar::tab:selected { background: #34415c; color: white; }
QScrollArea { border: none; } QCheckBox { padding: 4px; }
'''


class DrowsyGuardWindow(QMainWindow):
    def __init__(self, model_path=None, data_dir=None, *, scan_on_start=True):
        super().__init__()
        self.setWindowTitle('Drowsiness Detector')
        self.resize(1100, 800)
        self.setStyleSheet(STYLE)
        self.model_path = Path(model_path or PROJECT / 'models/face_landmarker.task')
        self.running = False
        self.worker = self.scanner = None
        self.calibration_samples = None
        self.last_app = None
        self.scene_panel = ScenePanel(self, data_dir=data_dir)
        self.scene_panel.setWindowFlags(Qt.WindowType.Widget)
        self.settings = self.scene_panel.settings
        self.tracker = EyeClosureTracker(threshold=self.settings['ear_threshold'], closure_duration=self.settings['closure_duration'])
        self.gate = ScareGate(self.settings['cooldown'])
        self.scene_panel.scene_ended.connect(self.scene_finished)
        self.scene_panel.preparation_changed.connect(self.speech_ready)
        root = QVBoxLayout()
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)
        title = QLabel('Drowsiness Detector')
        title.setObjectName('title')
        root.addWidget(title)
        privacy = QLabel('LOCAL BY DESIGN  •  Webcam video is never saved or uploaded. Speech stays on your PC.')
        privacy.setObjectName('muted')
        root.addWidget(privacy)
        actions = QHBoxLayout()
        self.start_button = QPushButton('Start monitoring')
        self.start_button.setObjectName('primary')
        self.start_button.clicked.connect(self.toggle_camera)
        self.test_button = QPushButton('Test scare')
        self.test_button.clicked.connect(self.test_scare)
        self.test_button.setEnabled(False)
        actions.addWidget(self.start_button)
        actions.addWidget(self.test_button)
        actions.addStretch()
        root.addLayout(actions)
        tabs = QTabWidget()
        monitor = QWidget()
        layout = QVBoxLayout(monitor)
        self.preview = QLabel('Your camera is off. Start monitoring when you are ready.')
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(440, 280)
        self.preview.setStyleSheet('background:#080b11; border-radius:12px; color:#9ca8bd;')
        layout.addWidget(self.preview, 1)
        metrics = QHBoxLayout()
        self.eye_state = QLabel('Eyes: camera off')
        self.ear_label = QLabel('EAR: —')
        self.threshold_label = QLabel(f'Threshold: {self.tracker.threshold:.3f}')
        for widget in (self.eye_state, self.ear_label, self.threshold_label):
            metrics.addWidget(widget)
        layout.addLayout(metrics)
        form = QFormLayout()
        self.camera_select = QComboBox()
        for index in range(5):
            self.camera_select.addItem(f'Camera {index}', index)
        self.camera_select.setCurrentIndex(self.settings['camera_index'])
        self.duration = QDoubleSpinBox()
        self.duration.setRange(0.5, 10)
        self.duration.setValue(self.tracker.closure_duration)
        self.duration.setSuffix(' seconds')
        self.duration.valueChanged.connect(self.duration_changed)
        self.cooldown = QDoubleSpinBox()
        self.cooldown.setRange(5, 120)
        self.cooldown.setValue(self.gate.cooldown)
        self.cooldown.setSuffix(' seconds')
        self.cooldown.valueChanged.connect(self.cooldown_changed)
        form.addRow('Laptop camera', self.camera_select)
        form.addRow('Eyes closed before scare', self.duration)
        form.addRow('Cooldown after dismissal', self.cooldown)
        layout.addLayout(form)
        buttons = QHBoxLayout()
        self.calibrate_button = QPushButton('Calibrate with eyes open')
        self.calibrate_button.clicked.connect(self.start_calibration)
        self.scan_camera_button = QPushButton('Find cameras')
        self.scan_camera_button.clicked.connect(self.scan_cameras)
        choose = QPushButton('Face model…')
        choose.clicked.connect(self.choose_model)
        for button in (self.calibrate_button, self.scan_camera_button, choose):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.activity_label = QLabel('Active window context: waiting for another app')
        self.activity_label.setObjectName('muted')
        layout.addWidget(self.activity_label)
        tabs.addTab(monitor, 'Monitor')
        tabs.addTab(self.scene_panel, 'Scene studio')
        about = QLabel('Everything runs on this PC.\n\nWebcam frames are processed in memory and discarded.\n'
                       'Desktop glitch pixels are discarded after the intro.\n'
                       'Window titles are read locally; no activity log is kept.\n'
                       'Contextual phrases and their audio cache can contain a window title.\n'
                       'Delete the local cache to remove these files.\n\n'
                       'Move the mouse or press any key to dismiss a scare.\nMaximum scene length: 15 seconds.\n\n'
                       'An experimental hackathon project, not a medical device.')
        about.setWordWrap(True)
        about.setMargin(24)
        tabs.addTab(about, 'Privacy & help')
        root.addWidget(tabs, 1)
        self.status = QLabel('Stopped • Test scare works without a camera')
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        container = QWidget()
        container.setLayout(root)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)
        self.setCentralWidget(scroll)
        self.activity_timer = QTimer(self)
        self.activity_timer.timeout.connect(self.poll_activity)
        self.activity_timer.start(1000)
        # Scan after the event loop starts so opening the window stays responsive.
        if scan_on_start:
            QTimer.singleShot(0, self.scan_cameras)
        for control in self.findChildren(QPushButton) + self.findChildren(QComboBox) + self.findChildren(QDoubleSpinBox):
            control.setMinimumHeight(control.fontMetrics().height() + 24)
            control.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    def poll_activity(self):
        title = active_window_title()
        if title:
            self.last_app = title
            self.activity_label.setText(f'Active window: {title} • stays local')
            if not self.gate.active and not self.scene_panel.overlays:
                self.scene_panel.context = {'app': title}

    def duration_changed(self, value):
        self.tracker.closure_duration = value
        self.settings['closure_duration'] = value
        self.scene_panel.persist()

    def cooldown_changed(self, value):
        self.gate.cooldown = value
        self.settings['cooldown'] = value
        self.scene_panel.persist()

    def speech_ready(self, ready):
        self.test_button.setEnabled(ready and not self.scene_panel.overlays)

    def test_scare(self):
        context = {'app': self.last_app} if self.last_app else {}
        self.test_button.setEnabled(False)
        self.scene_panel.request_scare(context)

    def toggle_camera(self):
        self.stop_camera() if self.running else self.start_camera()

    def start_camera(self):
        if self.worker is not None and self.worker.isRunning():
            self.status.setText('Camera is still stopping. Try again shortly.')
            return
        if not self.model_path.is_file():
            self.status.setText('Face model missing. Run setup or choose face_landmarker.task.')
            return
        index = int(self.camera_select.currentData() or 0)
        self.settings['camera_index'] = index
        self.scene_panel.persist()
        self.tracker.reset()
        self.gate.reset()
        self.running = True
        self.start_button.setText('Stop monitoring')
        self.camera_select.setEnabled(False)
        self.worker = CameraWorker(index, self.model_path, self)
        self.worker.frame.connect(self.process_frame)
        self.worker.failed.connect(self.camera_failed)
        self.worker.start()
        self.status.setText('Starting local camera…')

    def stop_camera(self):
        self.running = False
        if self.worker:
            self.worker.stop()
        self.scene_panel.cancel_pending()
        self.scene_panel.draft_player.stop()
        self.tracker.reset()
        self.gate.reset()
        self.calibration_samples = None
        self.start_button.setText('Start monitoring')
        self.camera_select.setEnabled(True)
        self.eye_state.setText('Eyes: camera off')
        self.preview.clear()
        self.preview.setText('Camera stopped')
        self.status.setText('Stopped • camera released as its worker exits')

    def camera_failed(self, message):
        self.stop_camera()
        self.status.setText(message)

    def process_frame(self, frame, ears, now):
        if not self.running:
            return
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, _ = rgb.shape
        image = QImage(rgb.data, w, h, 3*w, QImage.Format.Format_RGB888).copy()
        self.preview.setPixmap(QPixmap.fromImage(image).scaled(self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                                              Qt.TransformationMode.SmoothTransformation))
        if self.gate.active or self.scene_panel.overlays or self.scene_panel.pending_scare:
            return
        if ears is None:
            self.tracker.update(None, now, False)
            self.eye_state.setText('Eyes: no face')
            self.ear_label.setText('EAR: —')
            self.status.setText('No face detected • closure timer reset')
            return
        left, right = ears
        ear = (left + right) / 2
        opened = ear >= self.tracker.threshold
        self.eye_state.setText('Eyes: OPEN' if opened else 'Eyes: CLOSED')
        self.ear_label.setText(f'EAR  L {left:.3f}  R {right:.3f}')
        if self.calibration_samples is not None:
            self.calibration_samples.append(ear)
            self.status.setText(f'Keep eyes fully open • calibration {len(self.calibration_samples)}/30')
            if len(self.calibration_samples) >= 30:
                self.tracker.calibrate(self.calibration_samples)
                self.settings['ear_threshold'] = self.tracker.threshold
                self.scene_panel.persist()
                self.threshold_label.setText(f'Threshold: {self.tracker.threshold:.3f}')
                self.calibration_samples = None
            return
        self.gate.observe(opened)
        update = self.tracker.update(ear, now)
        self.status.setText(update.status)
        if now < self.gate.until:
            self.status.setText(f'Cooldown • {self.gate.until-now:.0f}s remaining • {update.status}')
        if update.triggered and self.gate.request(now):
            seconds = f'{update.closed_for:.1f}'
            context = {'seconds': seconds, 'closed_seconds': seconds}
            if self.last_app:
                context['app'] = self.last_app
            self.status.setText('Closure detected • preparing local scare')
            self.scene_panel.request_scare(context)

    def scene_finished(self):
        if self.gate.active or self.running:
            self.gate.finish(time.monotonic())
            self.gate.armed = False
        self.tracker.reset()
        self.test_button.setEnabled(self.scene_panel.ready)

    def start_calibration(self):
        if self.running:
            self.calibration_samples = []
            self.tracker.reset()
        else:
            self.status.setText('Start monitoring before calibration.')

    def scan_cameras(self):
        if self.running or (self.scanner and self.scanner.isRunning()):
            return
        self.scan_camera_button.setEnabled(False)
        self.start_button.setEnabled(False)
        self.camera_select.setEnabled(False)
        self.status.setText('Scanning local cameras…')
        self.scanner = CameraScan(self)
        self.scanner.found.connect(self.cameras_found)
        self.scanner.start()

    def cameras_found(self, indexes):
        previous = self.camera_select.currentData()
        self.camera_select.clear()
        for index in indexes:
            self.camera_select.addItem(f'Camera {index}', index)
        selected = self.camera_select.findData(previous)
        self.camera_select.setCurrentIndex(max(0, selected))
        self.scan_camera_button.setEnabled(True)
        self.start_button.setEnabled(bool(indexes))
        self.camera_select.setEnabled(bool(indexes))
        self.status.setText(f'Found {len(indexes)} camera(s).' if indexes else
                            'No camera available. Connect a camera, check Windows permissions, then Find cameras. Test scare still works.')

    def choose_model(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Face model', str(PROJECT), 'MediaPipe (*.task)')
        if path:
            self.stop_camera()
            self.model_path = Path(path)

    def closeEvent(self, event):
        self.activity_timer.stop()
        self.stop_camera()
        if self.worker:
            self.worker.wait()
        if self.scanner:
            self.scanner.wait()
        self.scene_panel.shutdown()
        event.accept()


def run(model_path=None):
    app = QApplication(sys.argv)
    app.setApplicationName('Drowsiness Detector')
    testing = '--self-test' in sys.argv
    data_dir = Path(sys.argv[sys.argv.index('--data-dir')+1]) if '--data-dir' in sys.argv else None
    window = DrowsyGuardWindow(model_path, data_dir=data_dir, scan_on_start=not testing)
    if testing:
        import json
        app.setQuitOnLastWindowClosed(False)
        window.activity_timer.stop()
        window.scene_panel.context_timer.stop()
        window.scene_panel.context = {'time': '3:00 AM'}
        window.scene_panel.settings.update(image=str(PROJECT / 'assets/monster.svg'),
            voice=str(PROJECT / 'models/voices/en_US-ryan-medium.onnx'),
            font=str(PROJECT / 'assets/fonts/Creepster-Regular.ttf'), random_assets=False)
        window.scene_panel.load_font()
        window.scene_panel.schedule_speech()
        deadline = time.monotonic()+90
        check = QTimer()
        def verify():
            if not window.scene_panel.ready and time.monotonic() < deadline:
                return
            check.stop()
            result = {'passed': False}
            try:
                assert window.scene_panel.ready, window.scene_panel.message.text()
                assert window.model_path.is_file(), 'Packaged face model missing'
                import mediapipe as mp
                model = mp.tasks.vision.FaceLandmarker.create_from_options(mp.tasks.vision.FaceLandmarkerOptions(
                    base_options=mp.tasks.BaseOptions(model_asset_path=str(window.model_path)), num_faces=1))
                model.close()
                assert window.scene_panel.font_family == 'Creepster'
                window.scene_panel.settings['desktop_glitch'] = False
                window.scene_panel.preview_scene()
                assert window.scene_panel.overlays, 'Overlay did not open: ' + window.scene_panel.message.text()
                window.scene_panel.dismiss_scene()
                result['passed'] = True
            except Exception as exc:
                result['error'] = f'{type(exc).__name__}: {exc}'
            window.scene_panel.data_dir.mkdir(parents=True, exist_ok=True)
            (window.scene_panel.data_dir/'self-test.json').write_text(json.dumps(result), encoding='utf-8')
            window.close()
            app.quit()
        check.timeout.connect(verify)
        check.start(100)
    else:
        window.show()
    return app.exec()
