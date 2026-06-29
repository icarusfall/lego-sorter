"""The `Frame` value type passed through the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import numpy as np


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Frame:
    """One captured image plus its identity.

    `image` is a BGR uint8 numpy array (OpenCV convention). `frame_id` is the stable
    key that, in scan-only mode, joins a later Brickognize result back to this capture
    (the brick is already in the tub by then).
    """

    frame_id: str
    image: np.ndarray  # HxWx3, BGR, uint8
    timestamp: datetime = field(default_factory=_utcnow)
    source_path: Optional[str] = None  # set when the frame came from a file
