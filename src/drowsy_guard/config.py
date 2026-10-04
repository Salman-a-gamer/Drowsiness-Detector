"""User configuration, migration, and phrase validation."""
from __future__ import annotations

import json
import os
import random
import uuid
import sys
from pathlib import Path

PROJECT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[2]))


def app_data_dir() -> Path:
    return Path(os.environ.get("APPDATA", str(Path.home() / "AppData/Roaming"))) / "WakeyMonster"


def default_phrases() -> list[dict]:
    return json.loads((PROJECT / "assets/default-config.json").read_text(encoding="utf-8"))["phrases"]


IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
AUDIO_TYPES = {".mp3", ".wav", ".ogg", ".flac"}


def asset_files(folder: str | Path, extensions: set[str]) -> list[Path]:
    if not folder:
        return []
    path = Path(folder)
    if not path.is_dir():
        return []
    return sorted(file for file in path.iterdir() if file.is_file() and file.suffix.lower() in extensions)


def choose_asset(primary: str, folder: str, extensions: set[str], randomize: bool, last: str = "") -> str:
    candidates = asset_files(folder, extensions) if randomize else []
    if candidates:
        choices = [path for path in candidates if str(path) != last] or candidates
        return str(random.choice(choices))
    return primary


def normalize_phrases(phrases) -> list[dict]:
    normalized = []
    seen = set()
    if not isinstance(phrases, list):
        return default_phrases()
    for entry in phrases:
        if not isinstance(entry, dict) or not isinstance(entry.get("text"), str):
            continue
        identity = str(entry.get("id") or uuid.uuid4().hex)
        if identity in seen:
            identity = uuid.uuid4().hex
        seen.add(identity)
        audio = entry.get("audio_file")
        normalized.append(dict(id=identity, text=entry["text"][:80],
                               enabled=bool(entry.get("enabled", True)),
                               audio_file=audio if isinstance(audio, str) and audio else None))
    return normalized


def load_config(folder: Path | None = None) -> dict:
    folder = folder or app_data_dir()
    music_folder = next((folder for folder in (PROJECT / "Backgound Music", PROJECT / "Backgound") if folder.is_dir()),
                        PROJECT / "Backgound Music")
    music_files = asset_files(music_folder, AUDIO_TYPES)
    music = next((path for path in music_files if "Five Nights" in path.name), next(iter(music_files), None))
    image_folder = PROJECT / "Characters"
    image = image_folder / "Sample_character_pic-noBG.png"
    if not image.is_file():
        image = PROJECT / "Sample_character_pic-noBG.png"
    if not image.is_file():
        image = PROJECT / 'assets/monster.svg'
    config = dict(image=str(image), background="", color="#ffffff",
                  music=str(music) if music else "", voice=str(PROJECT / "models/voices/en_US-ryan-medium.onnx"),
                  font=str(PROJECT / "assets/fonts/Creepster-Regular.ttf"), flashing=True,
                  music_volume=25, speech_volume=80, effects_volume=35, desktop_glitch=True,
                  random_assets=True, monster_folder=str(image_folder), background_folder="",
                  music_folder=str(music_folder),
                  phrase_catalog_version=2, closure_duration=1.5, cooldown=20.0, camera_index=0, ear_threshold=0.21,
                  phrases=default_phrases())
    source = folder / "config.json"
    saved = {}
    if not source.exists():
        source = PROJECT / "settings/scene.json"
    try:
        saved = json.loads(source.read_text(encoding="utf-8"))
        if isinstance(saved, dict):
            config.update({key: value for key, value in saved.items()
                           if key in config and isinstance(value, type(config[key]))})
    except (OSError, ValueError):
        pass
    config["phrases"] = normalize_phrases(config["phrases"])
    version = saved.get('phrase_catalog_version', 0) if isinstance(saved, dict) else 0
    if not isinstance(version, int) or version < 2:
        existing = {entry['text'] for entry in config['phrases']}
        additions = [entry for entry in default_phrases() if entry['text'] not in existing]
        if config['phrases'] and not any(entry['enabled'] for entry in config['phrases']):
            for entry in additions:
                entry['enabled'] = False
        config['phrases'].extend(additions)
        config['phrases'] = normalize_phrases(config['phrases'])
        config['phrase_catalog_version'] = 2
    # Repair paths when the user reorganizes supplied assets into these folders.
    for key, directories in (("image", [image_folder]), ("music", [music_folder])):
        old = Path(config[key])
        if not old.is_file():
            replacement = next((folder / old.name for folder in directories if (folder / old.name).is_file()), None)
            if replacement:
                config[key] = str(replacement)
            elif key == 'image':
                config[key] = str(image)
    return config


def save_config(config: dict, folder: Path | None = None) -> None:
    folder = folder or app_data_dir()
    folder.mkdir(parents=True, exist_ok=True)
    temporary = folder / "config.tmp"
    temporary.write_text(json.dumps(config, indent=2), encoding="utf-8")
    temporary.replace(folder / "config.json")
