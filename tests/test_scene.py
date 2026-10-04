import tempfile
import unittest
from pathlib import Path

import numpy as np

from drowsy_guard.speech import (
    DEFAULT_PHRASES, cache_path, creepy_effect, resolve_phrase, select_phrase,
)


class SceneTests(unittest.TestCase):
    def test_no_consecutive_repeat_even_single_phrase(self):
        phrases = [{"text": "I can see you.", "enabled": True}]
        last = None
        for _ in range(20):
            selected = select_phrase(phrases, last, {})
            self.assertNotEqual(last, selected)
            last = selected

    def test_disabled_phrases_are_silent(self):
        self.assertIsNone(select_phrase([{"text": "Disabled", "enabled": False}], None, {}))

    def test_unresolved_placeholders_are_skipped(self):
        self.assertIsNone(resolve_phrase("Why are you in {app}?", {}))
        self.assertEqual(resolve_phrase("Why are you in {app}?", {"app": "VS Code"}), "Why are you in VS Code?")
        self.assertIsNone(resolve_phrase("Bad {", {}))
        self.assertIsNone(resolve_phrase("{app.__class__}", {"app": "VS Code"}))

    def test_character_limit(self):
        self.assertIsNotNone(resolve_phrase("x" * 80, {}))
        self.assertIsNone(resolve_phrase("x" * 81, {}))
        self.assertIsNone(resolve_phrase("{app}", {"app": "x" * 81}))

    def test_cache_changes_with_text_voice_effect_and_model(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as folder:
            root = Path(folder)
            voice = root / "voice.onnx"
            voice.write_bytes(b"one")
            original = cache_path(root, "Hello", voice)
            self.assertEqual(original, cache_path(root, "Hello", voice))
            self.assertNotEqual(original, cache_path(root, "Changed", voice))
            self.assertNotEqual(original, cache_path(root, "Hello", root / "other.onnx"))
            self.assertNotEqual(original, cache_path(root, "Hello", voice, "other"))
            voice.write_bytes(b"different size")
            self.assertNotEqual(original, cache_path(root, "Hello", voice))

    def test_effects_fit_scene_and_stay_in_audio_range(self):
        rate = 22050
        signal = (np.sin(np.arange(rate * 8) * 0.1) * 32000).astype(np.int16)
        effected = creepy_effect(signal, rate)
        self.assertLessEqual(len(effected) / rate, 12.5)
        self.assertEqual(effected.shape[1], 2)
        self.assertLessEqual(np.max(np.abs(effected.astype(float))), 32767 * 0.81)
        self.assertTrue(np.all(effected[0] == 0))
        self.assertTrue(np.all(effected[-1] == 0))


if __name__ == "__main__":
    unittest.main()
