"""Download official local detection/speech models; app runtime needs no network."""
from pathlib import Path
import subprocess
import sys
import urllib.request
root = Path(__file__).resolve().parents[1]
model = root/'models/face_landmarker.task'
model.parent.mkdir(exist_ok=True)
if not model.exists():
    urllib.request.urlretrieve('https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task', model)
subprocess.run([sys.executable, '-m', 'piper.download_voices', 'en_US-ryan-medium', '--download-dir',
                str(root/'models/voices')], check=True)
