"""Story timeline: chapters laid end to end on the frame timeline, each mapping its
frames linearly onto its own sim-minute window. Pure Python (testable)."""
from __future__ import annotations

from demo import config


def chapters(fps: int = config.STORY_FPS):
    """[(index 1..7, title, frame start, frame end, min start, min end, chapter cfg)]."""
    out, f = [], 1
    for i, c in enumerate(config.STORY, 1):
        n = int(c[1] * fps)
        out.append((i, c[0], f, f + n - 1, c[2], c[3], c))
        f += n
    return out


def total_frames(fps: int = config.STORY_FPS) -> int:
    return chapters(fps)[-1][3]


def chapter_at(frame: int, fps: int = config.STORY_FPS):
    chs = chapters(fps)
    for ch in chs:
        if frame <= ch[3]:
            return ch
    return chs[-1]


def minute_at(frame: int, fps: int = config.STORY_FPS) -> float:
    _, _, f0, f1, m0, m1, _ = chapter_at(max(1, frame), fps)
    u = min(1.0, max(0.0, (frame - f0) / max(1, f1 - f0)))
    return m0 + u * (m1 - m0)
