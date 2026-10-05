"""Build a windowed Windows app folder with local models and assets."""
from pathlib import Path
import subprocess
import sys
root = Path(__file__).resolve().parents[1]
args = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--windowed', '--onedir',
        '--name', 'WakeyWakeyLilBro', '--paths', str(root/'src'),
        '--collect-data', 'mediapipe', '--collect-binaries', 'mediapipe',
        '--collect-data', 'piper', '--collect-binaries', 'piper',
        '--hidden-import', 'PySide6.QtMultimedia', '--hidden-import', 'PySide6.QtSvg',
        '--icon', str(root / 'assets/icons/wakey-icon.ico')]
for unused in ('piper.train', 'piper.http_server', 'onnxruntime.quantization',
               'onnxruntime.transformers', 'pytest', 'sounddevice'):
    args.extend(['--exclude-module', unused])
for source, target in (('assets', 'assets'), ('models/face_landmarker.task', 'models'),
                       ('models/voices/en_US-ryan-medium.onnx', 'models/voices'),
                       ('models/voices/en_US-ryan-medium.onnx.json', 'models/voices')):
    if (root/source).exists():
        args.extend(['--add-data', str(root/source)+';'+target])
subprocess.run(args + [str(root/'launch.pyw')], cwd=root, check=True)
print('Built:', root/'dist/WakeyWakeyLilBro/WakeyWakeyLilBro.exe')
