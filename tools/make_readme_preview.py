"""Render 1.5 seconds of the home UI, then a simulated scare. No capture."""
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from PIL import Image, ImageDraw, ImageFont
from PySide6.QtCore import QEventLoop, QRect, QTimer
from PySide6.QtGui import QFontDatabase, QImage
from PySide6.QtWidgets import QApplication
import imageio_ffmpeg
from drowsy_guard.app import DrowsyGuardWindow
from drowsy_guard.config import PROJECT
from drowsy_guard.overlay import MonsterOverlay


def grab(widget):
    image = widget.grab().toImage().convertToFormat(QImage.Format.Format_RGB888)
    return Image.frombytes('RGB', (image.width(), image.height()), bytes(image.bits()),
                           'raw', 'RGB', image.bytesPerLine())


def main():
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
    (PROJECT / 'cache').mkdir(exist_ok=True)
    output = PROJECT / 'demo/readme-preview.gif'
    font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 16)
    random.seed(17)
    with tempfile.TemporaryDirectory(dir=PROJECT / 'cache') as folder:
        window = DrowsyGuardWindow(data_dir=Path(folder), scan_on_start=False)
        window.resize(1100, 800)
        window.show()
        loop = QEventLoop()
        QTimer.singleShot(50, loop.quit)
        loop.exec()
        home = grab(window)
        overlay = MonsterOverlay(QRect(0, 0, 1100, 800), str(PROJECT / 'assets/monster.svg'),
            '', '#ffffff', 'I can see you.', True, window.scene_panel.font_family, clock=lambda: 0)
        overlay.animation.stop()
        overlay.show()
        frames = []
        for index in range(60):
            if index < 15:
                shot = home.copy()
            else:
                overlay.clock = lambda index=index: (index - 15) / 10
                overlay.tick()
                shot = grab(overlay)
            shot = shot.resize((770, 560), Image.Resampling.LANCZOS)
            canvas = Image.new('RGB', (770, 590), '#10131b')
            canvas.paste(shot, (0, 0))
            ImageDraw.Draw(canvas).text((12, 565), 'Simulated scare • local processing • no webcam recorded',
                                       font=font, fill='white')
            frames.append(canvas)
        gif_frames = [frame.resize((616, 472), Image.Resampling.LANCZOS).quantize(
            colors=32, dither=Image.Dither.NONE) for frame in frames]
        gif_frames[0].save(output, save_all=True, append_images=gif_frames[1:], duration=100,
                       loop=0, optimize=True)
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-loglevel', 'error', '-i', str(output),
                        '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(output.with_suffix('.mp4'))], check=True)
        window.grab().save(str(PROJECT / 'docs/screenshots/desktop.png'))
        overlay.close()
        window.close()
    print('Created:', output)


if __name__ == '__main__':
    main()
