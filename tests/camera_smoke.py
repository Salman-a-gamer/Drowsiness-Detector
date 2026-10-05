"""Manual hardware check: real CameraWorker frames and MediaPipe inference."""
import sys
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication
from drowsy_guard.camera import CameraWorker
from drowsy_guard.config import PROJECT

app = QApplication([])
loop = QEventLoop()
frames, errors = [], []
worker = CameraWorker(int(sys.argv[1]) if len(sys.argv) > 1 else 0, PROJECT / 'models/face_landmarker.task')


def receive(image, ears, now):
    frames.append((image.shape, ears, now))
    if len(frames) >= 3:
        worker.stop()
        loop.quit()


worker.frame.connect(receive)
worker.failed.connect(lambda text: (errors.append(text), loop.quit()))
QTimer.singleShot(10000, loop.quit)
worker.start()
loop.exec()
worker.stop()
worker.wait()
assert not errors, errors
assert len(frames) >= 3, 'No webcam frames before timeout'
assert all(frames[i][2] > frames[i - 1][2] for i in range(1, len(frames)))
print('PASS: actual camera worker, frame delivery and MediaPipe inference; face present:', frames[-1][1] is not None)
