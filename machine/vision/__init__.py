"""OpenCV cropping. Two strategies, matched to the two stages:

- `crop_by_belt_colour`  — Phase 1 still capture: key the piece out by colour
  distance from the known pale belt. Works on a single frame, no background model.
- `MOG2Cropper`          — Phase 2 conveyor: background subtraction on the moving
  belt, one blob at a time.

Both apply the saturation boost first so white/grey pieces don't vanish against the
pale belt (Daniel West's trick — see docs/PROJECT_BRIEF.md §3).
"""

from .crop import Crop, MOG2Cropper, boost_saturation, crop_by_belt_colour

__all__ = ["Crop", "MOG2Cropper", "boost_saturation", "crop_by_belt_colour"]
