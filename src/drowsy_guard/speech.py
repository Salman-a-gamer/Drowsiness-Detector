"""Local speech cache, phrase selection, and deterministic horror effects."""
from __future__ import annotations

import hashlib
import json
import random
import string
import wave
from pathlib import Path

import numpy as np
from .config import default_phrases

DEFAULT_PHRASES = [phrase["text"] for phrase in default_phrases() if "{" not in phrase["text"]]
EFFECT = "horror-v3-breath-growl"


def resolve_phrase(text: str, context: dict[str, str]) -> str | None:
    if not text.strip() or len(text) > 80:
        return None
    try:
        for _, field, spec, conversion in string.Formatter().parse(text):
            if field is not None and (field not in context or spec or conversion):
                return None
        rendered = text.format_map(context)
        return rendered if len(rendered) <= 80 else None
    except (ValueError, KeyError):
        return None


def select_phrase(phrases: list[dict], last: str | None, context: dict[str, str]) -> str | None:
    candidates = list(dict.fromkeys(
        rendered for phrase in phrases if phrase.get("enabled", True)
        if (rendered := resolve_phrase(phrase["text"], context)) is not None
    ))
    choices = [text for text in candidates if text != last]
    return random.choice(choices) if choices else None


def cache_path(folder: Path, text: str, voice: Path, effect: str = EFFECT) -> Path:
    signature = []
    for path in (voice, Path(str(voice) + ".json")):
        if path.exists():
            stat = path.stat()
            signature.append((stat.st_size, stat.st_mtime_ns))
    key = json.dumps([text, str(voice.resolve()), signature, effect], sort_keys=True)
    return folder / (hashlib.sha256(key.encode()).hexdigest() + ".wav")


def creepy_effect(samples: np.ndarray, rate: int) -> np.ndarray:
    """Lower pitch, layered growl, metallic modulation, and decaying echoes."""
    samples = samples.astype(np.float64) / 32768.0
    slowed = np.interp(np.arange(0, len(samples), 0.73), np.arange(len(samples)), samples)
    time = np.arange(len(slowed)) / rate
    growl = np.interp(np.arange(len(slowed)) * 0.73, np.arange(len(slowed)), slowed)
    dry = np.tanh((slowed + 0.42 * growl) * 2.1) * (0.76 + 0.24 * np.sin(2 * np.pi * 31 * time))
    mixed = np.pad(dry, (0, int(rate * 0.45)))
    for delay, gain in ((0.09, 0.32), (0.19, 0.22), (0.34, 0.12)):
        offset = int(rate * delay)
        mixed[offset:offset + len(dry)] += gain * dry
    # Speech begins at 2s; leave room inside the 15s maximum scene.
    limit = int(rate * 12.5)
    if len(mixed) > limit:
        mixed = np.interp(np.linspace(0, len(mixed) - 1, limit), np.arange(len(mixed)), mixed)
    fade = min(int(rate * 0.04), len(mixed) // 2)
    if fade:
        mixed[:fade] *= np.linspace(0, 1, fade)
        mixed[-fade:] *= np.linspace(1, 0, fade)
    # A breath layer follows the syllables; it is not a second music track.
    envelope = np.convolve(np.abs(mixed), np.ones(221) / 221, mode="same")
    noise = np.random.default_rng(41).normal(0, 1, len(mixed))
    breath = (noise - np.convolve(noise, np.ones(9) / 9, mode="same")) * envelope
    whisper = np.zeros(len(mixed))
    delay = int(rate * 0.065)
    if len(mixed) > delay:
        whisper[delay:] = breath[:-delay] + np.diff(mixed[:-delay], prepend=0) * 0.3
    pan = np.sin(np.arange(len(mixed)) / rate * 2 * np.pi * 0.65)
    stereo = np.column_stack((mixed + whisper * (1 - pan) * 0.24,
                              mixed + whisper * (1 + pan) * 0.24))
    if fade:
        stereo[:fade] *= np.linspace(0, 1, fade)[:, None]
        stereo[-fade:] *= np.linspace(1, 0, fade)[:, None]
    stereo *= 0.80 / max(1.0, float(np.max(np.abs(stereo))))
    return (stereo * 32767).astype("<i2")


def build_cache(voice_path: Path, texts: list[str], folder: Path) -> None:
    from piper import PiperVoice

    folder.mkdir(parents=True, exist_ok=True)
    missing = [(text, cache_path(folder, text, voice_path)) for text in set(texts)
               if not cache_path(folder, text, voice_path).exists()]
    if not missing:
        return
    voice = PiperVoice.load(str(voice_path))
    import io
    for text, target in missing:
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as output:
            voice.synthesize_wav(text, output)
        buffer.seek(0)
        with wave.open(buffer, "rb") as source:
            rate = source.getframerate()
            samples = np.frombuffer(source.readframes(source.getnframes()), dtype="<i2")
        temporary = target.with_suffix(".tmp")
        with wave.open(str(temporary), "wb") as output:
            output.setnchannels(2)
            output.setsampwidth(2)
            output.setframerate(rate)
            output.writeframes(creepy_effect(samples, rate).tobytes())
        temporary.replace(target)
