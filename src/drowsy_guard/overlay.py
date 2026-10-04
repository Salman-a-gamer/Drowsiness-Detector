"""Animated scare renderer; screenshots remain in memory and are discarded."""
from __future__ import annotations

import random
import time

import numpy as np
from PySide6.QtCore import QRectF, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QWidget


def capture_desktops() -> dict[str, QPixmap]:
    """Match native captures to Qt screens by position, without writing files."""
    from mss import MSS
    captures = {}
    with MSS() as source:
        monitors = sorted(source.monitors[1:], key=lambda monitor: (monitor["left"], monitor["top"]))
        screens = sorted(QApplication.screens(), key=lambda screen: (screen.geometry().x(), screen.geometry().y()))
        for screen, monitor in zip(screens, monitors):
            shot = source.grab(monitor)
            # copy() owns the pixel bytes after MSS releases its buffer.
            image = QImage(shot.bgra, shot.width, shot.height, shot.width * 4, QImage.Format.Format_RGB32).copy()
            captures[screen.name()] = QPixmap.fromImage(image)
    return captures


def rush_scale(elapsed: float) -> float:
    progress = max(0.0, min(1.0, elapsed / 0.5))
    return 0.16 + 0.98 * (1 - (1 - progress) ** 3)


class MonsterOverlay(QWidget):
    dismissed = Signal()

    def __init__(self, geometry, image, background, color, phrase, flashing, font_family,
                 screenshot=None, clock=time.monotonic):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setGeometry(geometry)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.monster = QPixmap(image)
        self.background = QPixmap(background)
        self.color = QColor(color)
        self.phrase, self.font_family, self.flashing = phrase, font_family, flashing
        self.screenshot = screenshot or QPixmap()
        self.intro_duration = 0.18 if not self.screenshot.isNull() else 0.0
        self.clock = clock
        self.started = clock()
        self.mouse_origin = QCursor.pos()
        self.frame = 0
        self.flash_color = self.color
        self.next_flash = 0.0
        self.noise = []
        rng = np.random.default_rng(24)
        for _ in range(4):
            pixels = rng.integers(0, 256, (100, 160), dtype=np.uint8)
            self.noise.append(QPixmap.fromImage(QImage(pixels.data, 160, 100, 160,
                                                       QImage.Format.Format_Grayscale8).copy()))
        self.animation = QTimer(self)
        self.animation.setTimerType(Qt.TimerType.PreciseTimer)
        self.animation.timeout.connect(self.tick)
        self.animation.start(33)

    def tick(self):
        elapsed = self.clock() - self.started
        if elapsed > 0.18:
            self.screenshot = QPixmap()
        if self.flashing and elapsed >= self.next_flash:
            self.flash_color = QColor(random.choice(["#ffffff", "#ffffff", "#000000", "#dddddd", "#680000"]))
            self.next_flash = elapsed + random.choice((0.045, 0.075, 0.12, 0.19, 0.06))
        self.frame += 1
        self.update()

    def paintEvent(self, event):
        elapsed = self.clock() - self.started
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.fillRect(self.rect(), self.flash_color)
        if not self.screenshot.isNull() and elapsed < 0.18:
            desktop = self.screenshot.scaled(self.size())
            painter.drawPixmap(0, 0, desktop)
            for _ in range(12):
                y = random.randrange(max(1, self.height()))
                height = random.randint(3, 28)
                painter.drawPixmap(random.randint(-65, 65), y, desktop.copy(0, y, self.width(), height))
            painter.fillRect(self.rect(), QColor(180, 0, 0, 45))
            return
        # A few entire black frames interrupt the animation, not just its background.
        if self.flashing and self.flash_color == QColor("#000000"):
            return
        if not self.background.isNull():
            image = self.background.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                           Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap((self.width() - image.width()) // 2, (self.height() - image.height()) // 2, image)
            if self.flashing:
                painter.fillRect(self.rect(), QColor(self.flash_color.red(), self.flash_color.green(),
                                                    self.flash_color.blue(), 120))
        painter.save()
        shake = 13 if elapsed < 0.8 else 4
        painter.translate(random.randint(-shake, shake), random.randint(-shake, shake))
        animation_elapsed = max(0.0, elapsed - self.intro_duration)
        scale = rush_scale(animation_elapsed)
        size = self.monster.size().scaled(int(self.width() * scale), int(self.height() * scale),
                                         Qt.AspectRatioMode.KeepAspectRatio)
        target = QRectF((self.width() - size.width()) / 2, (self.height() - size.height()) / 2 - self.height() * 0.04,
                        size.width(), size.height())
        painter.drawPixmap(target, self.monster, QRectF(self.monster.rect()))
        # Eye flicker aligned to the supplied monster; arbitrary replacements use the same relative mask.
        if 0.57 <= animation_elapsed <= 0.68:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#090909"))
            painter.drawRect(QRectF(target.x() + target.width() * 0.39, target.y() + target.height() * 0.27,
                                    target.width() * 0.27, target.height() * 0.075))
        painter.restore()
        painter.setOpacity(0.12)
        painter.drawPixmap(self.rect(), self.noise[self.frame % len(self.noise)])
        painter.setOpacity(1)
        painter.setPen(QColor(0, 0, 0, 65))
        for y in range(0, self.height(), 5):
            painter.drawLine(0, y, self.width(), y)
        if self.frame % 7 == 0:
            for _ in range(4):
                painter.fillRect(0, random.randrange(max(1, self.height())), self.width(), random.randint(2, 10),
                                 QColor(255, 255, 255, 130))
        font = QFont(self.font_family)
        font.setPixelSize(max(28, min(62, self.width() // 22)))
        painter.setFont(font)
        bounds = self.rect().adjusted(25, int(self.height() * 0.79), -25, -10)
        flags = Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap
        painter.setPen(QColor("#000000"))
        painter.drawText(bounds.translated(2, 2), flags, self.phrase)
        painter.setPen(QColor("#e50000"))
        painter.drawText(bounds, flags, self.phrase)

    def keyPressEvent(self, event):
        if not event.isAutoRepeat():
            self.dismissed.emit()

    def mouseMoveEvent(self, event):
        if (event.globalPosition().toPoint() - self.mouse_origin).manhattanLength() > 2:
            self.dismissed.emit()

    def mousePressEvent(self, event):
        self.dismissed.emit()

    def closeEvent(self, event):
        self.animation.stop()
        self.screenshot = QPixmap()
        self.dismissed.emit()
        event.accept()
