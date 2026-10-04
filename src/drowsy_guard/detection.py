"""Pure eye-closure calculations and state machine.

This module deliberately has no camera, GUI, or MediaPipe dependency so it can
be tested on any machine.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import dist
from typing import Sequence


LEFT_EYE = (33, 160, 158, 133, 153, 144)
RIGHT_EYE = (362, 385, 387, 263, 373, 380)


def eye_aspect_ratio(points: Sequence[Sequence[float]]) -> float:
    """Return EAR for six points: outer, upper-1, upper-2, inner, lower-2, lower-1."""
    if len(points) != 6:
        raise ValueError("EAR requires six eye landmarks")
    width = dist(points[0], points[3])
    if width == 0:
        return 0.0
    return (dist(points[1], points[5]) + dist(points[2], points[4])) / (2.0 * width)


def landmarks_ear(landmarks: Sequence[object], width=1.0, height=1.0) -> tuple[float, float]:
    """Calculate left and right EAR from a MediaPipe landmark list."""
    def xy(index: int) -> tuple[float, float]:
        point = landmarks[index]
        return float(point.x) * width, float(point.y) * height

    return (
        eye_aspect_ratio([xy(i) for i in LEFT_EYE]),
        eye_aspect_ratio([xy(i) for i in RIGHT_EYE]),
    )


@dataclass(frozen=True)
class DetectionUpdate:
    status: str
    closed_for: float
    triggered: bool = False


class EyeClosureTracker:
    """Convert EAR samples into stable human-readable detection states."""

    def __init__(self, threshold: float = 0.21, closure_duration: float = 1.5) -> None:
        self.threshold = threshold
        self.closure_duration = closure_duration
        self.closed_since: float | None = None
        self.alerted = False

    def reset(self) -> None:
        self.closed_since = None
        self.alerted = False

    def update(self, ear: float | None, timestamp: float, face_present: bool = True) -> DetectionUpdate:
        if not face_present or ear is None:
            self.closed_since = None
            self.alerted = False
            return DetectionUpdate("No face detected", 0.0)

        if ear < self.threshold:
            if self.closed_since is None:
                self.closed_since = timestamp
            closed_for = max(0.0, timestamp - self.closed_since)
            if closed_for >= self.closure_duration and not self.alerted:
                self.alerted = True
                return DetectionUpdate("Eyes closed — alert", closed_for, True)
            return DetectionUpdate(f"Eyes closed ({closed_for:.1f}s)", closed_for)

        self.closed_since = None
        self.alerted = False
        return DetectionUpdate("Eyes open", 0.0)

    def calibrate(self, open_ears: Sequence[float]) -> float:
        """Set a threshold to 70% of the average open-eye EAR."""
        valid = [value for value in open_ears if value > 0]
        if not valid:
            raise ValueError("Need at least one positive open-eye EAR sample")
        self.threshold = sum(valid) / len(valid) * 0.70
        self.reset()
        return self.threshold
