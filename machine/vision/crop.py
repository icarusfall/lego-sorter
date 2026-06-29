"""Cropping the single piece out of a frame.

Brickognize expects *one part per image*, reasonably tight. These helpers isolate the
piece and return a padded crop plus the bounding box and mask (useful later for colour
resolution and for the Bayesian visibility model).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np


@dataclass
class Crop:
    image: np.ndarray  # cropped BGR
    bbox: tuple[int, int, int, int]  # x, y, w, h in the original frame
    mask: np.ndarray  # full-frame foreground mask (uint8 0/255)
    area_frac: float  # foreground area as a fraction of the frame


def boost_saturation(bgr: np.ndarray, factor: float) -> np.ndarray:
    """Multiply HSV saturation by `factor`. Stops near-grey/white pieces washing out
    against the pale belt before we key on colour distance."""
    if factor == 1.0:
        return bgr
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * factor, 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)


def _largest_contour_bbox(mask: np.ndarray) -> Optional[tuple[int, int, int, int]]:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    biggest = max(contours, key=cv2.contourArea)
    return cv2.boundingRect(biggest)


def _finish(
    bgr: np.ndarray,
    mask: np.ndarray,
    min_area_frac: float,
    pad: int,
) -> Optional[Crop]:
    """Shared tail: clean the mask, take the largest blob, pad and crop."""
    # Morphological close+open to fill holes and drop specks.
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    h, w = mask.shape[:2]
    frame_area = float(h * w)
    bbox = _largest_contour_bbox(mask)
    if bbox is None:
        return None

    x, y, bw, bh = bbox
    blob = cv2.countNonZero(mask[y : y + bh, x : x + bw])
    area_frac = blob / frame_area
    if area_frac < min_area_frac:
        return None  # too small — noise, not a piece

    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(w, x + bw + pad)
    y1 = min(h, y + bh + pad)
    crop = bgr[y0:y1, x0:x1].copy()
    return Crop(image=crop, bbox=(x0, y0, x1 - x0, y1 - y0), mask=mask, area_frac=area_frac)


def crop_by_belt_colour(
    bgr: np.ndarray,
    belt_bgr: tuple[int, int, int],
    *,
    saturation_boost: float = 1.8,
    distance_threshold: float = 0.18,
    min_area_frac: float = 0.002,
    pad: int = 12,
) -> Optional[Crop]:
    """Phase 1: isolate the piece by colour distance from the pale belt.

    `distance_threshold` is a normalised (0..1) Euclidean distance in BGR space;
    pixels farther than this from the belt colour are treated as foreground. Returns
    `None` if no piece large enough is found.
    """
    boosted = boost_saturation(bgr, saturation_boost)
    belt = np.array(belt_bgr, dtype=np.float32)
    # Boost the belt reference the same way so the comparison is like-for-like.
    belt_boost = boost_saturation(
        np.full((1, 1, 3), belt, dtype=np.uint8), saturation_boost
    )[0, 0].astype(np.float32)

    diff = boosted.astype(np.float32) - belt_boost
    dist = np.sqrt((diff**2).sum(axis=2)) / (np.sqrt(3) * 255.0)  # normalise to 0..1
    mask = (dist > distance_threshold).astype(np.uint8) * 255
    return _finish(bgr, mask, min_area_frac, pad)


class MOG2Cropper:
    """Phase 2 (conveyor): background subtraction on the moving belt.

    Feed it consecutive belt frames; it learns the belt as background and returns the
    moving blob (the piece) when one is present. Stateful — one instance per belt run.
    """

    def __init__(
        self,
        *,
        saturation_boost: float = 1.8,
        history: int = 200,
        var_threshold: float = 32.0,
        min_area_frac: float = 0.002,
        pad: int = 12,
    ) -> None:
        self.saturation_boost = saturation_boost
        self.min_area_frac = min_area_frac
        self.pad = pad
        self._bg = cv2.createBackgroundSubtractorMOG2(
            history=history, varThreshold=var_threshold, detectShadows=False
        )

    def process(self, bgr: np.ndarray) -> Optional[Crop]:
        boosted = boost_saturation(bgr, self.saturation_boost)
        mask = self._bg.apply(boosted)
        return _finish(bgr, mask, self.min_area_frac, self.pad)
