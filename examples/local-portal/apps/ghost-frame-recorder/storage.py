"""Recording output directory helpers."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path


def default_output_dir() -> Path:
    home_videos = Path.home() / "Videos" / "GhostFrameRecorder"
    if home_videos.parent.exists():
        home_videos.mkdir(parents=True, exist_ok=True)
        return home_videos
    local = Path(__file__).resolve().parent / "recordings"
    local.mkdir(parents=True, exist_ok=True)
    return local


def new_take_basename() -> str:
    return datetime.now().strftime("take_%Y%m%d_%H%M%S")
