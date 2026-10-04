"""Create a 60-second UI walkthrough using simulated EAR; no webcam is recorded."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import time
import wave

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from PySide6.QtCore import QEventLoop, QTimer, Qt
from PySide6.QtGui import QColor, QFontDatabase, QImage
from PySide6.QtWidgets import QApplication, QTabWidget
import imageio_ffmpeg
from drowsy_guard.app import DrowsyGuardWindow
from drowsy_guard.config import PROJECT
from drowsy_guard.overlay import MonsterOverlay

def wait(ms):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()

def pil(widget):
    image = widget.grab().toImage().convertToFormat(QImage.Format.Format_RGB888)
    return Image.frombytes('RGB', (image.width(), image.height()), bytes(image.bits()), 'raw', 'RGB', image.bytesPerLine())

app = QApplication([])
app.setQuitOnLastWindowClosed(False)
QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
QFontDatabase.addApplicationFont('C:/Windows/Fonts/arial.ttf')
folder = PROJECT/'demo'
folder.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(dir=PROJECT/'cache') as temp:
    window = DrowsyGuardWindow(data_dir=Path(temp))
    window.resize(1160, 690)
    window.scene_panel.settings['desktop_glitch'] = False
    window.scene_panel.settings['music'] = ''
    window.show()
    wait(100)
    tabs = window.centralWidget().findChildren(QTabWidget)[0]
    snapshots = [pil(window)]
    frame = np.full((480,640,3), (22,18,15), dtype=np.uint8)
    cv2.putText(frame, 'SIMULATED CAMERA INPUT', (70,210), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (140,170,200), 2)
    cv2.putText(frame, 'No personal video recorded', (100,255), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (140,170,200), 1)
    window.running = True
    window.process_frame(frame, (.31,.30), time.monotonic())
    window.status.setText('Eyes open • normal blinks are ignored')
    snapshots.append(pil(window))
    window.process_frame(frame, (.10,.11), time.monotonic())
    window.status.setText('Eyes closed • sustained closure triggers one scare')
    snapshots.append(pil(window))
    tabs.setCurrentIndex(1)
    wait(50)
    snapshots.append(pil(window))
    window.scene_panel.findChild(QTabWidget).setCurrentIndex(1)
    snapshots.append(pil(window))
    tabs.setCurrentIndex(2)
    snapshots.append(pil(window))
    overlay = MonsterOverlay(window.geometry(), str(PROJECT/'assets/monster.svg'), '', '#ffffff',
                             'I can see you.', True, window.scene_panel.font_family)
    overlay.animation.stop()
    overlay.show()
    overlay.started = 0
    font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 29)
    small = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 18)
    encoder = imageio_ffmpeg.get_ffmpeg_exe()
    output = folder/'demo-silent.mp4'
    process = subprocess.Popen([encoder,'-y','-loglevel','error','-f','rawvideo','-vcodec','rawvideo',
        '-pix_fmt','rgb24','-s','1280x800','-r','12','-i','-','-an','-vcodec','libx264','-preset','fast',
        '-pix_fmt','yuv420p',str(output)], stdin=subprocess.PIPE)
    for index in range(720):
        second = index/12
        if second < 8:
            shot, caption = snapshots[0], 'WakeyMonster • local drowsiness detection for Windows'
        elif second < 17:
            shot, caption = snapshots[1], 'Start monitoring, calibrate open eyes, and choose a closure duration'
        elif second < 24:
            shot, caption = snapshots[2], 'Normal blinks pass. Sustained closure triggers one scare.'
        elif second < 31:
            overlay.clock = lambda second=second: second-24
            overlay.frame = index
            overlay.flash_color = QColor('#000000' if index%19 == 0 else '#ffffff')
            shot, caption = pil(overlay), 'Monster rush + stereo horror audio • move mouse or press a key to dismiss'
        elif second < 41:
            shot, caption = snapshots[3], 'All phrases are visible. Preview, edit, disable, or attach your recording.'
        elif second < 50:
            shot, caption = snapshots[4], 'Customize monsters, backgrounds, music, voices, and cooldown'
        else:
            shot, caption = snapshots[5], 'Everything runs on your PC. No webcam video is saved or uploaded.'
        canvas = Image.new('RGB',(1280,800),'#10131b')
        shot.thumbnail((1280,670))
        canvas.paste(shot,((1280-shot.width)//2,90))
        draw = ImageDraw.Draw(canvas)
        draw.text((28,18),caption,font=font,fill='white')
        draw.text((28,767),'60-second UI walkthrough • simulated eye readings • no personal desktop or webcam captured',font=small,fill='#9ca8bd')
        process.stdin.write(canvas.tobytes())
    process.stdin.close()
    if process.wait():
        raise RuntimeError('Video encoding failed')
    sound = np.zeros((22050*60,2),dtype='<i2')
    from drowsy_guard.soundscape import build_soundscape
    with wave.open(str(build_soundscape(Path(temp)))) as source:
        samples = np.frombuffer(source.readframes(22050*7),dtype='<i2').reshape(-1,2)
    sound[22050*24:22050*31] = (samples*.5).astype('<i2')
    wav = Path(temp)/'demo.wav'
    with wave.open(str(wav),'wb') as audio:
        audio.setnchannels(2); audio.setsampwidth(2); audio.setframerate(22050); audio.writeframes(sound.tobytes())
    subprocess.run([encoder,'-y','-loglevel','error','-i',str(output),'-i',str(wav),'-c:v','copy','-c:a','aac',
                    '-t','60','-movflags','+faststart',str(folder/'demo-60s.mp4')],check=True)
    overlay.close()
    window.close()
print('Created 60-second walkthrough:', folder/'demo-60s.mp4')
