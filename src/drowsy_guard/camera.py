"""Camera reads and MediaPipe inference run off the GUI thread."""
import threading
import time

import cv2
from PySide6.QtCore import QThread, Signal

from .detection import landmarks_ear, LEFT_EYE, RIGHT_EYE


class CameraWorker(QThread):
    frame = Signal(object, object, float)
    failed = Signal(str)
    def __init__(self, index, model, parent=None):
        super().__init__(parent)
        self.index, self.model = index, model
        self.stopping = threading.Event()

    def run(self):
        camera = landmarker = None
        try:
            import mediapipe as mp
            options = mp.tasks.vision.FaceLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(self.model)),
                running_mode=mp.tasks.vision.RunningMode.VIDEO, num_faces=1)
            landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)
            if self.stopping.is_set():
                return
            camera = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)
            if not camera.isOpened():
                raise RuntimeError('Camera unavailable. Choose another camera or check Windows permissions.')
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            while not self.stopping.is_set():
                frame_started = time.monotonic()
                ok, image = camera.read()
                if not ok:
                    raise RuntimeError('Camera stopped returning frames.')
                image = cv2.flip(image, 1)
                rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                now = time.monotonic()
                result = landmarker.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), int(now * 1000))
                ears = None
                if result.face_landmarks:
                    landmarks = result.face_landmarks[0]
                    ears = landmarks_ear(landmarks, image.shape[1], image.shape[0])
                    for index in LEFT_EYE + RIGHT_EYE:
                        p = landmarks[index]
                        cv2.circle(image, (int(p.x * image.shape[1]), int(p.y * image.shape[0])), 2, (80, 220, 160), -1)
                self.frame.emit(image, ears, now)
                # Cap inference at 15 fps; closure timing still uses real elapsed time.
                self.stopping.wait(max(0, 1 / 15 - (time.monotonic() - frame_started)))
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            if camera is not None:
                camera.release()
            if landmarker is not None:
                landmarker.close()

    def stop(self):
        self.stopping.set()


class CameraScan(QThread):
    found = Signal(object)
    def run(self):
        indexes = []
        for index in range(5):
            camera = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            try:
                if camera.isOpened() and camera.read()[0]:
                    indexes.append(index)
            finally:
                camera.release()
        self.found.emit(indexes)
