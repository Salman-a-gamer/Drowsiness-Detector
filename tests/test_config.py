import json
import tempfile
import unittest
from unittest.mock import patch
import wave
from pathlib import Path

import numpy as np

from drowsy_guard.config import IMAGE_TYPES, app_data_dir, choose_asset, load_config, normalize_phrases, save_config
from drowsy_guard.overlay import rush_scale
from drowsy_guard.scene_input import new_key_pressed
from drowsy_guard.soundscape import build_soundscape


class ConfigTests(unittest.TestCase):
    def test_appdata_path(self):
        with patch.dict("os.environ", {"APPDATA": "D:/example/AppData/Roaming"}):
            self.assertEqual(app_data_dir(), Path("D:/example/AppData/Roaming/WakeyMonster"))

    def test_asset_folder_selection_skips_unknown_files_and_last(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temporary:
            root = Path(temporary)
            first = root / "one.png"
            second = root / "two.png"
            for file in (first, second, root / "not-image.txt"):
                file.write_bytes(b"test")
            self.assertEqual(choose_asset("fallback", str(root), IMAGE_TYPES, True, str(first)), str(second))
            self.assertEqual(choose_asset("fallback", str(root), IMAGE_TYPES, False), "fallback")

    def test_save_and_load_phrase_ids_and_recordings(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temporary:
            root = Path(temporary)
            config = load_config(root)
            config["phrases"] = [dict(id="a1", text="I see you", enabled=False, audio_file="whisper.wav")]
            save_config(config, root)
            restored = load_config(root)
            self.assertEqual(config["phrases"], restored["phrases"])
            self.assertIsNone(restored["phrases"][0].get("not-a-field"))
            self.assertFalse((root / "config.tmp").exists())

    def test_migrate_old_phrases(self):
        phrases = normalize_phrases([dict(text="Old phrase", enabled=True),
                                     dict(id="duplicate", text="One"), dict(id="duplicate", text="Two")])
        self.assertEqual(len({phrase["id"] for phrase in phrases}), 3)
        self.assertTrue(all(phrase["audio_file"] is None for phrase in phrases))

    def test_bad_config_does_not_crash_and_text_is_limited(self):
        self.assertEqual(normalize_phrases([None, {}, dict(text=4)]), [])
        self.assertEqual(len(normalize_phrases([dict(text="x" * 100)])[0]["text"]), 80)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temporary:
            root = Path(temporary)
            (root / "config.json").write_text(json.dumps({"voice": None, "music_volume": "oops"}))
            config = load_config(root)
            self.assertIsInstance(config["voice"], str)
            self.assertIsInstance(config["music_volume"], int)

    def test_rush_finishes_in_half_second(self):
        self.assertLess(rush_scale(0), rush_scale(0.25))
        self.assertGreater(rush_scale(0.5), 1)
        self.assertEqual(rush_scale(0.5), rush_scale(15))

    def test_only_new_keys_dismiss(self):
        self.assertFalse(new_key_pressed({13}, {13}))
        self.assertTrue(new_key_pressed({13}, {13, 65}))
        self.assertFalse(new_key_pressed({13}, set()))

    def test_sound_bed_starts_with_silence(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temporary:
            path = build_soundscape(Path(temporary))
            with wave.open(str(path)) as audio:
                self.assertEqual(audio.getnchannels(), 2)
                self.assertEqual(audio.getnframes() / audio.getframerate(), 15)
                samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2").reshape(-1, 2)
                silence = int(audio.getframerate() * 0.5)
                self.assertTrue(np.all(samples[:silence] == 0))
                self.assertGreater(np.max(np.abs(samples[silence:].astype(float))), 1000)


if __name__ == "__main__":
    unittest.main()
