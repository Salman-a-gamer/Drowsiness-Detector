"""Manual scare settings, phrase editor, and asynchronous prepared audio."""
from __future__ import annotations

import random
import time
import uuid
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QCursor, QFontDatabase, QPixmap, QDesktopServices
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QColorDialog, QDialog, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton,
    QSlider, QVBoxLayout,
    QScrollArea, QWidget, QTabWidget, QSizePolicy,
)

from .config import PROJECT, AUDIO_TYPES, IMAGE_TYPES, app_data_dir, choose_asset, load_config, save_config
from .overlay import MonsterOverlay, capture_desktops
from .soundscape import build_soundscape
from .scene_input import new_key_pressed, pressed_keys
from .speech import DEFAULT_PHRASES, build_cache, cache_path, resolve_phrase
from .branding import APP_TITLE
from .identity import device_name, name_context, clean_name

MAX_SCENE_MS = 15000
VOICE_DELAY_MS = 2000
MUSIC_DELAY_MS = 500


class WorkerSignals(QObject):
    finished = Signal(int, str)


class SpeechWorker(QRunnable):
    def __init__(self, revision, voice, texts, folder):
        super().__init__()
        self.revision, self.voice, self.texts, self.folder = revision, voice, texts, folder
        self.signals = WorkerSignals()

    def run(self):
        error = ""
        try:
            build_soundscape(self.folder)
            build_cache(self.voice, self.texts, self.folder)
        except Exception as exc:
            error = str(exc)
        self.signals.finished.emit(self.revision, error)


class ScenePanel(QDialog):
    scene_started = Signal()
    scene_ended = Signal()
    preparation_changed = Signal(bool)
    def __init__(self, parent=None, data_dir: Path | None = None):
        super().__init__(parent)
        self.setWindowTitle(APP_TITLE + ' — scene studio')
        self.resize(830, 740)
        self.data_dir = data_dir or app_data_dir()
        self.settings_path = self.data_dir / "config.json"
        self.cache_folder = self.data_dir / "cache/speech"
        self.settings = load_config(self.data_dir)
        self.last_phrase = None
        self.last_assets = {}
        self.context = {}  # Stage 3 supplies real app/closed_seconds facts.
        self.prepared_context = self.current_context()
        self.overlays = []
        self.revision = 0
        self.ready = False
        self.pending_scare = False
        self.worker = None
        self.preview_workers = {}
        self.preview_targets = {}
        self.preview_sequence = 0
        self.selected_id = None
        self.refreshing = False
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self.rebuild_timer = self.single_timer(self.prepare_speech)
        self.dismiss_timer = self.single_timer(self.dismiss_scene)
        self.voice_timer = self.single_timer(self.start_scene_voice)
        self.music_timer = self.single_timer(self.start_scene_music)
        self.input_timer = QTimer(self)
        self.input_timer.timeout.connect(self.check_mouse)
        self.context_timer = QTimer(self)
        self.context_timer.timeout.connect(self.refresh_context)
        self.context_timer.start(1000)
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.addWidget(QLabel("Scene studio • move mouse or press any key to dismiss • 15-second maximum"))
        studio_tabs = QTabWidget()
        root.addWidget(studio_tabs, 1)
        scene_page = QWidget()
        scene_layout = QVBoxLayout(scene_page)
        phrase_page = QWidget()
        phrase_layout = QVBoxLayout(phrase_page)
        studio_tabs.addTab(phrase_page, 'Phrases')
        studio_tabs.addTab(scene_page, 'Appearance & audio')
        form = QFormLayout()
        self.asset_fields = {}
        for key, label, filters in (
            ("image", "Monster image", "Images (*.png *.jpg *.jpeg *.webp)"),
            ("background", "Background image (optional)", "Images (*.png *.jpg *.jpeg *.webp)"),
            ("music", "Background music", "Audio (*.mp3 *.wav *.ogg *.flac)"),
            ("voice", "Piper voice (.onnx)", "Piper models (*.onnx)"),
            ("font", "Horror font", "Fonts (*.ttf *.otf)"),
        ):
            row = QHBoxLayout()
            field = QLineEdit(self.settings[key])
            self.asset_fields[key] = field
            field.setCursorPosition(0)
            field.setToolTip(self.settings[key])
            field.textChanged.connect(field.setToolTip)
            field.textChanged.connect(lambda value, key=key: self.setting_changed(key, value))
            browse = QPushButton("Browse")
            browse.setFixedWidth(104)
            browse.clicked.connect(lambda checked=False, field=field, filters=filters: self.browse(field, filters))
            row.addWidget(field, 1)
            row.addWidget(browse)
            form.addRow(label, row)
        color = QPushButton("Choose background color")
        color.clicked.connect(self.choose_color)
        form.addRow(color)
        for key, label in (("monster_folder", "Monster folder"), ("background_folder", "Background folder"),
                           ("music_folder", "Music folder")):
            row = QHBoxLayout()
            field = QLineEdit(self.settings[key])
            self.asset_fields[key] = field
            field.setCursorPosition(0)
            field.setToolTip(self.settings[key])
            field.textChanged.connect(field.setToolTip)
            field.textChanged.connect(lambda value, key=key: self.setting_changed(key, value))
            button = QPushButton("Folder…")
            button.setFixedWidth(104)
            button.clicked.connect(lambda checked=False, field=field: self.browse_folder(field))
            row.addWidget(field, 1)
            row.addWidget(button)
            form.addRow(label, row)
        folders = QHBoxLayout()
        open_assets = QPushButton('Open default asset folders')
        open_assets.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.data_dir / 'assets'))))
        reset_assets = QPushButton('Use default assets')
        reset_assets.clicked.connect(self.restore_default_assets)
        folders.addWidget(open_assets)
        folders.addWidget(reset_assets)
        form.addRow(folders)
        for key, label in (("flashing", "Irregular flashing / black frames"),
                           ("desktop_glitch", "Glitch real desktop briefly (memory only)"),
                           ("random_assets", "Pick random monsters, backgrounds and music from folders")):
            check = QCheckBox(label)
            check.setChecked(self.settings[key])
            check.toggled.connect(lambda value, key=key: self.setting_changed(key, value))
            form.addRow(check)
        for key, label in (("music_volume", "Background audio volume"), ("speech_volume", "Voice volume")):
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(self.settings[key])
            slider.valueChanged.connect(lambda value, key=key: self.setting_changed(key, value))
            form.addRow(label, slider)
        preferences = QWidget()
        preferences.setLayout(form)
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setWidget(preferences)
        scene_layout.addWidget(settings_scroll)
        phrase_layout.addWidget(QLabel('Every phrase used is listed here. Uncheck all for a scene with music only.'))
        self.phrase_list = QListWidget()
        self.phrase_list.setUniformItemSizes(True)
        self.phrase_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.phrase_list.currentItemChanged.connect(self.select_item)
        self.phrase_list.itemChanged.connect(self.toggle_phrase)
        phrase_layout.addWidget(self.phrase_list, 1)
        bulk = QHBoxLayout()
        for label, enabled in (('Select all', True), ('Unselect all', False)):
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, enabled=enabled: self.set_all_phrases(enabled))
            bulk.addWidget(button)
        phrase_layout.addLayout(bulk)
        buttons = QHBoxLayout()
        for label, callback in (("Add", self.new_phrase), ("Edit", self.edit_phrase), ("Delete", self.delete_phrase)):
            button = QPushButton(label)
            button.clicked.connect(callback)
            buttons.addWidget(button)
        phrase_layout.addLayout(buttons)
        self.phrase_text = QLineEdit()
        self.phrase_text.setMaxLength(80)
        self.phrase_text.setPlaceholderText("Phrase, up to 80 characters; {time}, {app}, {closed_seconds}")
        phrase_layout.addWidget(self.phrase_text)
        recording_row = QHBoxLayout()
        self.recording = QLineEdit()
        self.recording.setPlaceholderText("Optional recording; blank uses generated Piper voice")
        recording_browse = QPushButton("Recording…")
        recording_browse.clicked.connect(lambda: self.browse(self.recording, "Audio (*.wav *.mp3 *.ogg *.flac)"))
        recording_row.addWidget(self.recording)
        recording_row.addWidget(recording_browse)
        phrase_layout.addLayout(recording_row)
        self.enabled = QCheckBox("Enabled")
        self.enabled.setChecked(True)
        phrase_layout.addWidget(self.enabled)
        editor_buttons = QHBoxLayout()
        save = QPushButton("Save phrase")
        save.clicked.connect(self.save_phrase)
        self.phrase_preview = QPushButton("Preview voice before saving")
        self.phrase_preview.clicked.connect(self.preview_draft)
        editor_buttons.addWidget(save)
        editor_buttons.addWidget(self.phrase_preview)
        phrase_layout.addLayout(editor_buttons)
        identity_row = QHBoxLayout()
        self.personalization = QCheckBox('Use {name} in phrases')
        self.personalization.setChecked(self.settings['personalization_enabled'])
        self.personalization.toggled.connect(lambda value: self.setting_changed('personalization_enabled', value))
        self.user_name = QLineEdit(self.settings['user_name'])
        self.user_name.setMaxLength(24)
        self.user_name.setPlaceholderText('Optional name, stays on this PC')
        self.user_name.editingFinished.connect(lambda: self.setting_changed('user_name', clean_name(self.user_name.text())))
        autofill = QPushButton('Use Windows name')
        autofill.clicked.connect(self.autofill_name)
        identity_row.addWidget(self.personalization)
        identity_row.addWidget(self.user_name, 1)
        identity_row.addWidget(autofill)
        phrase_layout.addLayout(identity_row)
        self.message = QLabel("Preparing speech…")
        self.message.setWordWrap(True)
        root.addWidget(self.message)
        self.preview_button = QPushButton("Preview monster scene")
        self.preview_button.setEnabled(False)
        self.preview_button.clicked.connect(self.preview_scene)
        root.addWidget(self.preview_button)
        self.music_player, self.music_output = self.create_player()
        self.speech_player, self.speech_output = self.create_player()
        self.effects_player, self.effects_output = self.create_player()
        self.draft_player, self.draft_output = self.create_player()
        self.refresh_list()
        row_height = self.phrase_list.sizeHintForRow(0)
        self.phrase_list.setMinimumHeight(4 * row_height + 24)
        for control in self.findChildren(QPushButton) + self.findChildren(QLineEdit):
            control.setMinimumHeight(control.fontMetrics().height() + 24)
            control.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        form.setVerticalSpacing(10)
        self.font_family = "Arial"
        self.load_font()
        self.persist()
        self.schedule_speech()
        self.rebuild_timer.start(0)

    def single_timer(self, callback):
        timer = QTimer(self)
        timer.setTimerType(Qt.TimerType.PreciseTimer)
        timer.setSingleShot(True)
        timer.timeout.connect(callback)
        return timer

    def create_player(self):
        output = QAudioOutput(self)
        player = QMediaPlayer(self)
        player.setAudioOutput(output)
        player.errorOccurred.connect(lambda error, text: self.message.setText(f"Audio playback: {text}"))
        return player, output

    def current_context(self):
        return {"time": datetime.now().strftime("%I:%M %p").lstrip("0"), **self.context, **name_context(self.settings)}

    def autofill_name(self):
        name = device_name()
        self.user_name.setText(name)
        self.setting_changed('user_name', name)
        self.message.setText('Windows account name suggested. Edit it if needed, then enable {name} phrases.')

    def set_all_phrases(self, enabled):
        for phrase in self.settings['phrases']:
            phrase['enabled'] = enabled
        self.refresh_list()
        self.persist()
        self.schedule_speech()

    def restore_default_assets(self):
        root = self.data_dir / 'assets'
        defaults = dict(image=str(root / 'monsters/shadow-monster.svg'), background='',
            music=str(root / 'music/midnight-signal.wav'), monster_folder=str(root / 'monsters'),
            background_folder=str(root / 'backgrounds'), music_folder=str(root / 'music'))
        for key, value in defaults.items():
            self.asset_fields[key].setText(value)

    def refresh_context(self):
        context = self.current_context()
        if context != self.prepared_context and not self.overlays:
            self.schedule_speech()
            self.prepared_context = context

    def load_font(self):
        index = QFontDatabase.addApplicationFont(self.settings["font"])
        families = QFontDatabase.applicationFontFamilies(index) if index >= 0 else []
        self.font_family = families[0] if families else "Arial"

    def browse(self, field, filters):
        path, _ = QFileDialog.getOpenFileName(self, "Choose scene file", str(PROJECT), filters)
        if path:
            field.setText(path)

    def choose_color(self):
        color = QColorDialog.getColor(QColor(self.settings["color"]), self)
        if color.isValid():
            self.setting_changed("color", color.name())

    def browse_folder(self, field):
        path = QFileDialog.getExistingDirectory(self, "Choose scene asset folder", str(PROJECT))
        if path:
            field.setText(path)

    def persist(self):
        try:
            save_config(self.settings, self.data_dir)
        except OSError as exc:
            self.message.setText(f"Cannot save preferences: {exc}")

    def setting_changed(self, key, value):
        self.settings[key] = value
        self.persist()
        if key in ("voice", 'user_name', 'personalization_enabled'):
            self.schedule_speech()
        elif key == "font":
            self.load_font()

    def refresh_list(self):
        self.refreshing = True
        self.phrase_list.clear()
        for phrase in self.settings["phrases"]:
            marker = " [recording]" if phrase.get("audio_file") else ""
            item = QListWidgetItem(phrase["text"] + marker)
            item.setData(Qt.ItemDataRole.UserRole, phrase["id"])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if phrase["enabled"] else Qt.CheckState.Unchecked)
            self.phrase_list.addItem(item)
            if phrase["id"] == self.selected_id:
                self.phrase_list.setCurrentItem(item)
        self.refreshing = False

    def select_item(self, item, previous=None):
        if item is None:
            return
        identity = item.data(Qt.ItemDataRole.UserRole)
        phrase = next(phrase for phrase in self.settings["phrases"] if phrase["id"] == identity)
        self.selected_id = identity
        self.phrase_text.setText(phrase["text"])
        self.recording.setText(phrase.get("audio_file") or "")
        self.enabled.setChecked(phrase["enabled"])

    def toggle_phrase(self, item):
        if self.refreshing:
            return
        identity = item.data(Qt.ItemDataRole.UserRole)
        phrase = next(phrase for phrase in self.settings["phrases"] if phrase["id"] == identity)
        phrase["enabled"] = item.checkState() == Qt.CheckState.Checked
        if identity == self.selected_id:
            self.enabled.setChecked(phrase["enabled"])
        self.persist()
        self.schedule_speech()

    def new_phrase(self):
        self.selected_id = None
        self.phrase_list.clearSelection()
        self.phrase_text.clear()
        self.recording.clear()
        self.enabled.setChecked(True)
        self.phrase_text.setFocus()

    def edit_phrase(self):
        item = self.phrase_list.currentItem()
        if item:
            self.select_item(item)
        self.phrase_text.setFocus()

    def delete_phrase(self):
        if self.selected_id is None:
            return
        self.settings["phrases"] = [phrase for phrase in self.settings["phrases"] if phrase["id"] != self.selected_id]
        self.new_phrase()
        self.refresh_list()
        self.persist()
        self.schedule_speech()

    def draft(self):
        return dict(id=self.selected_id or uuid.uuid4().hex, text=self.phrase_text.text().strip(),
                    enabled=self.enabled.isChecked(), audio_file=self.recording.text().strip() or None)

    def recording_path(self, phrase):
        path = Path(phrase["audio_file"])
        return path if path.is_absolute() else self.data_dir / path

    def save_phrase(self):
        phrase = self.draft()
        if not phrase["text"]:
            self.message.setText("Enter a phrase before saving.")
            return
        if phrase["audio_file"] and not self.recording_path(phrase).is_file():
            self.message.setText("Recording file does not exist.")
            return
        self.settings["phrases"] = [p for p in self.settings["phrases"] if p["id"] != phrase["id"]] + [phrase]
        self.selected_id = phrase["id"]
        self.refresh_list()
        self.persist()
        self.schedule_speech()

    def schedule_speech(self):
        self.revision += 1
        self.ready = False
        self.preparation_changed.emit(False)
        self.preview_button.setEnabled(False)
        self.message.setText("Preparing current phrases in the background…")
        self.rebuild_timer.start(350)

    def prepare_speech(self):
        self.prepared_context = self.current_context()
        texts = [rendered for phrase in self.settings['phrases'] if phrase['enabled'] and not phrase.get('audio_file')
                 if (rendered := resolve_phrase(phrase['text'], self.prepared_context)) is not None]
        worker = SpeechWorker(self.revision, Path(self.settings["voice"]), texts, self.cache_folder)
        worker.signals.finished.connect(self.speech_finished)
        self.worker = worker
        self.pool.start(worker)

    def speech_finished(self, revision, error):
        if revision != self.revision:
            return
        self.ready = not bool(error)
        self.preparation_changed.emit(self.ready)
        self.preview_button.setEnabled(self.ready and not self.overlays)
        self.message.setText(f"Speech preparation failed: {error}. Choose a valid Piper model."
                             if error else "Speech ready. Preview without starting the camera.")
        if self.pending_scare:
            self.pending_scare = False
            if self.ready:
                self.preview_scene()
            else:
                self.scene_ended.emit()

    def play_draft(self, path):
        self.draft_output.setVolume(self.settings["speech_volume"] / 100)
        self.draft_player.setSource(QUrl.fromLocalFile(str(path)))
        self.draft_player.play()

    def preview_draft(self):
        phrase = self.draft()
        rendered = resolve_phrase(phrase["text"], self.current_context())
        if rendered is None:
            self.message.setText("Enter a valid phrase. Missing {app}/{closed_seconds} values cannot be previewed yet.")
            return
        if phrase.get("audio_file"):
            path = self.recording_path(phrase)
            if not path.is_file():
                self.message.setText("Recording file does not exist.")
                return
            self.play_draft(path)
            return
        voice = Path(self.settings["voice"])
        path = cache_path(self.cache_folder, rendered, voice)
        if path.exists():
            self.play_draft(path)
            return
        self.phrase_preview.setEnabled(False)
        self.message.setText("Preparing unsaved phrase preview…")
        self.preview_sequence += 1
        identity = self.preview_sequence
        worker = SpeechWorker(identity, voice, [rendered], self.cache_folder)
        self.preview_workers[identity] = worker
        self.preview_targets[identity] = path
        worker.signals.finished.connect(self.draft_finished)
        self.pool.start(worker)

    def draft_finished(self, identity, error):
        path = self.preview_targets.pop(identity)
        self.preview_workers.pop(identity, None)
        self.phrase_preview.setEnabled(True)
        if error:
            self.message.setText(f"Preview failed: {error}")
        else:
            self.message.setText("Playing unsaved phrase; Save phrase keeps it.")
            if not self.overlays:
                self.play_draft(path)

    def choose_line(self):
        candidates = []
        for phrase in self.settings["phrases"]:
            rendered = resolve_phrase(phrase["text"], self.prepared_context)
            if not phrase["enabled"] or rendered is None:
                continue
            path = self.recording_path(phrase) if phrase.get("audio_file") else cache_path(
                self.cache_folder, rendered, Path(self.settings["voice"]))
            if path.is_file():
                candidates.append((rendered, path))
        choices = [candidate for candidate in candidates if candidate[0] != self.last_phrase]
        if not choices:
            return '', None
        return random.choice(choices)

    def request_scare(self, context):
        if self.overlays or self.pending_scare:
            return False
        self.context = dict(context)
        if self.ready and self.current_context() == self.prepared_context:
            self.preview_scene()
        else:
            self.pending_scare = True
            self.schedule_speech()
        return True

    def cancel_pending(self):
        pending = self.pending_scare
        self.pending_scare = False
        self.dismiss_scene()
        if pending:
            self.scene_ended.emit()

    def preview_scene(self):
        if not self.ready or self.overlays:
            return
        if self.current_context() != self.prepared_context:
            self.schedule_speech()
            return
        assets = {}
        for key, folder, types in (("image", "monster_folder", IMAGE_TYPES),
                                   ("background", "background_folder", IMAGE_TYPES),
                                   ("music", "music_folder", AUDIO_TYPES)):
            assets[key] = choose_asset(self.settings[key], self.settings[folder], types,
                                      self.settings["random_assets"], self.last_assets.get(key, ""))
        if QPixmap(assets["image"]).isNull():
            self.message.setText("Choose a valid monster image before previewing.")
            return
        phrase, speech = self.choose_line()
        if speech is not None and not speech.is_file():
            self.schedule_speech()
            return
        self.last_phrase = phrase or None
        self.last_assets = assets
        self.draft_player.stop()
        self.preview_button.setEnabled(False)
        captures = {}
        if self.settings["desktop_glitch"]:
            try:
                captures = capture_desktops()
            except Exception as exc:
                self.message.setText(f"Desktop capture unavailable; scene continues: {exc}")
        self.mouse_origin = QCursor.pos()
        self.keys_before = pressed_keys()
        self.scene_started_at = time.monotonic()
        for screen in QApplication.screens():
            overlay = MonsterOverlay(screen.geometry(), assets["image"], assets["background"],
                                     self.settings["color"], phrase, self.settings["flashing"], self.font_family,
                                     captures.get(screen.name()))
            overlay.dismissed.connect(self.dismiss_scene)
            self.overlays.append(overlay)
            overlay.show()
            overlay.raise_()
            overlay.activateWindow()
            overlay.setFocus()
        captures.clear()
        self.music_output.setVolume(self.settings["music_volume"] / 100)
        self.speech_output.setVolume(self.settings["speech_volume"] / 100)
        # Exactly one background source: chosen recording OR generated fallback.
        music = Path(assets["music"]) if assets["music"] else None
        background_audio = music if music and music.is_file() else build_soundscape(self.cache_folder)
        self.effects_player.stop()
        self.effects_player.setSource(QUrl())
        self.music_player.setSource(QUrl.fromLocalFile(str(background_audio)))
        self.music_player.setLoops(QMediaPlayer.Loops.Infinite)
        self.speech_player.setSource(QUrl.fromLocalFile(str(speech)) if speech else QUrl())
        self.music_timer.start(MUSIC_DELAY_MS)
        if speech:
            self.voice_timer.start(VOICE_DELAY_MS)
        self.dismiss_timer.start(MAX_SCENE_MS)
        self.input_timer.start(25)
        self.scene_started.emit()

    def start_scene_music(self):
        if self.overlays:
            self.music_player.play()

    def start_scene_voice(self):
        if self.overlays:
            self.speech_player.play()

    def check_mouse(self):
        if self.overlays:
            keys = pressed_keys()
            moved = (QCursor.pos() - self.mouse_origin).manhattanLength() > 2
            if moved or new_key_pressed(self.keys_before, keys):
                self.dismiss_scene()
            self.keys_before = keys

    def dismiss_scene(self):
        for timer in (self.dismiss_timer, self.voice_timer, self.music_timer, self.input_timer):
            timer.stop()
        for player in (self.music_player, self.speech_player, self.effects_player):
            player.stop()
        overlays, self.overlays = self.overlays, []
        for overlay in overlays:
            overlay.dismissed.disconnect(self.dismiss_scene)
            overlay.close()
            overlay.deleteLater()
        self.preview_button.setEnabled(self.ready)
        if overlays:
            self.scene_ended.emit()

    def closeEvent(self, event):
        self.dismiss_scene()
        self.draft_player.stop()
        event.accept()

    def shutdown(self):
        self.rebuild_timer.stop()
        self.context_timer.stop()
        self.dismiss_scene()
        self.draft_player.stop()
        self.pool.waitForDone()
        for player in (self.music_player, self.speech_player, self.effects_player, self.draft_player):
            player.setSource(QUrl())
