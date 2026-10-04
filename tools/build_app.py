"""Build a windowed Windows app folder with local models and assets."""
from pathlib import Path
import subprocess
import sys
root = Path(__file__).resolve().parents[1]
args = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--windowed', '--onedir',
        '--name', 'WakeyMonster', '--paths', str(root/'src'), '--collect-all', 'mediapipe',
        '--collect-all', 'piper', '--collect-all', 'onnxruntime', '--hidden-import', 'PySide6.QtMultimedia']
for source, target in (('assets', 'assets'), ('models', 'models'), ('Characters', 'Characters')):
    if (root/source).exists():
        args.extend(['--add-data', str(root/source)+';'+target])
subprocess.run(args + [str(root/'launch.pyw')], cwd=root, check=True)
print('Built:', root/'dist/WakeyMonster/WakeyMonster.exe')
