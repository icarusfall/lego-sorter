"""Machine configuration.

Kept dependency-light: a frozen dataclass with sensible defaults and per-field
environment-variable overrides (prefix ``LEGO_``). The belt/background colour and
the saturation boost are the two cropping knobs the brief calls out as needing to be
configurable (docs/PROJECT_BRIEF.md §10.3).

Colours are stored as OpenCV **BGR** tuples (not RGB) since that is what cv2 uses.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_float(name: str, default: float) -> float:
    val = os.environ.get(name)
    return float(val) if val is not None else default


def _env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _env_bgr(name: str, default: tuple[int, int, int]) -> tuple[int, int, int]:
    """Parse 'B,G,R' from env, else default."""
    val = os.environ.get(name)
    if not val:
        return default
    parts = [int(p) for p in val.split(",")]
    if len(parts) != 3:
        raise ValueError(f"{name} must be 'B,G,R', got {val!r}")
    return (parts[0], parts[1], parts[2])


# Pale pink belt (Daniel West trick): a hue no Lego brick is, so nothing is lost
# against it. RGB ~ (255, 209, 220) -> BGR (220, 209, 255).
DEFAULT_BELT_BGR: tuple[int, int, int] = (220, 209, 255)


@dataclass(frozen=True)
class Settings:
    # --- cropping ---
    belt_bgr: tuple[int, int, int] = field(default_factory=lambda: DEFAULT_BELT_BGR)
    # Multiply HSV saturation before keying so white/grey pieces don't vanish (West).
    saturation_boost: float = 1.8
    # Foreground threshold: min colour distance (0..1, normalised) from belt colour.
    fg_distance_threshold: float = 0.18
    # Ignore blobs smaller than this fraction of frame area (noise/specks).
    min_blob_area_frac: float = 0.002
    # Padding (px) around the detected piece bounding box before cropping.
    crop_pad_px: int = 12

    # --- classification ---
    brickognize_url: str = "https://api.brickognize.com/predict/"
    request_timeout_s: float = 30.0
    max_retries: int = 4

    # --- storage ---
    data_dir: str = "data"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            belt_bgr=_env_bgr("LEGO_BELT_BGR", DEFAULT_BELT_BGR),
            saturation_boost=_env_float("LEGO_SATURATION_BOOST", 1.8),
            fg_distance_threshold=_env_float("LEGO_FG_THRESHOLD", 0.18),
            min_blob_area_frac=_env_float("LEGO_MIN_BLOB_AREA_FRAC", 0.002),
            crop_pad_px=int(_env_float("LEGO_CROP_PAD_PX", 12)),
            brickognize_url=_env_str("LEGO_BRICKOGNIZE_URL", "https://api.brickognize.com/predict/"),
            request_timeout_s=_env_float("LEGO_REQUEST_TIMEOUT_S", 30.0),
            max_retries=int(_env_float("LEGO_MAX_RETRIES", 4)),
            data_dir=_env_str("LEGO_DATA_DIR", "data"),
        )
