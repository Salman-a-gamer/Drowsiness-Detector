import unittest

from drowsy_guard.detection import EyeClosureTracker, eye_aspect_ratio


class EyeClosureTrackerTests(unittest.TestCase):
    def test_normal_blink_does_not_trigger(self):
        tracker = EyeClosureTracker(threshold=0.2, closure_duration=1.0)
        tracker.update(0.1, 10.0)
        result = tracker.update(0.3, 10.3)
        self.assertFalse(result.triggered)
        self.assertEqual(result.status, "Eyes open")

    def test_sustained_closure_triggers_once(self):
        tracker = EyeClosureTracker(threshold=0.2, closure_duration=1.0)
        self.assertFalse(tracker.update(0.1, 10.0).triggered)
        self.assertFalse(tracker.update(0.1, 10.9).triggered)
        self.assertTrue(tracker.update(0.1, 11.0).triggered)
        self.assertFalse(tracker.update(0.1, 11.2).triggered)
        self.assertEqual(tracker.update(0.3, 11.3).status, "Eyes open")

    def test_tracking_loss_resets_timer(self):
        tracker = EyeClosureTracker(threshold=0.2, closure_duration=1.0)
        tracker.update(0.1, 10.0)
        self.assertEqual(tracker.update(None, 10.8, face_present=False).status, "No face detected")
        self.assertFalse(tracker.update(0.1, 10.9).triggered)
        self.assertTrue(tracker.update(0.1, 11.9).triggered)

    def test_calibration_uses_open_eye_samples(self):
        tracker = EyeClosureTracker()
        self.assertAlmostEqual(tracker.calibrate([0.30, 0.32]), 0.217, places=3)

    def test_ear_shape(self):
        points = [(0, 0), (1, 1), (2, 1), (4, 0), (2, -1), (1, -1)]
        self.assertAlmostEqual(eye_aspect_ratio(points), 0.5)


if __name__ == "__main__":
    unittest.main()
