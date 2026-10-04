"""Procedurally generated horror bed. No external recordings are required."""
from pathlib import Path
import wave
import numpy as np


def build_soundscape(folder: Path) -> Path:
    target = folder / "soundscape-v1.wav"
    if target.exists():
        return target
    folder.mkdir(parents=True, exist_ok=True)
    rate = 22050
    t = np.arange(rate * 15) / rate
    rng = np.random.default_rng(1701)
    active = t >= 0.5
    drone = 0.13 * (np.sin(2 * np.pi * 47 * t) + 0.6 * np.sin(2 * np.pi * 48.7 * t))
    beat = np.mod(t - 0.5, 0.86)
    heartbeat = 0.27 * np.sin(2 * np.pi * 65 * t) * (
        np.exp(-beat * 45) + 0.65 * np.exp(-np.maximum(0, beat - 0.17) * 50) * (beat >= 0.17))
    onset = t - 0.5
    screech_envelope = np.where(onset >= 0, np.exp(-np.maximum(0, onset) * 3), 0)
    screech = 0.18 * screech_envelope * (np.sin(2 * np.pi * (1400 * t + 110 * np.sin(3 * t)))
                                       + 0.5 * np.sin(2 * np.pi * 2103 * t))
    static = rng.normal(0, 0.11, len(t)) * ((onset >= 0) & (onset < 0.32))
    box = np.zeros(len(t))
    for index, frequency in enumerate((880, 1046.5, 831, 659, 784, 622, 880, 587)):
        local = t - (0.5 + index * 1.6)
        envelope = np.where(local >= 0, np.exp(-np.maximum(0, local) * 3.2), 0)
        box += 0.05 * envelope * (np.sin(2 * np.pi * frequency * local)
                                  + np.sin(2 * np.pi * frequency * 1.008 * local))
    mono = (drone + heartbeat + screech + static + box) * active
    stereo = np.column_stack((mono, mono + 0.015 * np.sin(2 * np.pi * 51 * t) * active))
    stereo *= 0.72 / max(1.0, float(np.max(np.abs(stereo))))
    with wave.open(str(target), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes((stereo * 32767).astype("<i2").tobytes())
    return target
