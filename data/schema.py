"""Core data schema (pydantic v2).

The unit of data is a `BrickScan`: one photographed piece, optionally classified.
A `Session` groups the scans from one visit/run and links the *before* pile photo
to the resulting inventory — that (pile_photo -> inventory) join is the training
pair the Bayesian model (see docs/PROJECT_BRIEF.md §7) ultimately learns from.

Classification is deliberately separable from capture: in scan-only mode (the road
default) we capture now and classify later ("deferred classification"). So a
`BrickScan` is valid with `brickognize_result is None`; it gets enriched in a later
batch pass.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BrickognizeItem(BaseModel):
    """One candidate identification returned by Brickognize, normalised.

    Field names mirror the Brickognize response loosely; `raw` keeps the original
    dict so nothing is lost if the API shape differs from what we parsed. Verify
    against https://api.brickognize.com/docs before relying on a specific field.
    """

    id: Optional[str] = None  # part number (BrickLink/Rebrickable-style)
    name: Optional[str] = None
    category: Optional[str] = None
    type: Optional[str] = None  # e.g. "part", "set", "minifig"
    score: Optional[float] = None
    img_url: Optional[str] = None
    raw: dict[str, Any] = Field(default_factory=dict)


class BrickognizeResult(BaseModel):
    """Full result of one classification call (the best item + all candidates)."""

    best: Optional[BrickognizeItem] = None
    items: list[BrickognizeItem] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)
    classified_at: datetime = Field(default_factory=_utcnow)


class BrickScan(BaseModel):
    """One photographed piece. Capture-time fields are required; classification
    fields are filled now (online) or later (deferred batch)."""

    # --- capture-time (always present) ---
    frame_id: str
    timestamp: datetime = Field(default_factory=_utcnow)
    image_path: str
    session_id: str
    host_id: Optional[str] = None
    # which physical partition/bucket this piece was declared to (scan mode: one tub)
    declared_partition: Optional[str] = None

    # --- classification-time (None until classified) ---
    brickognize_result: Optional[BrickognizeResult] = None
    resolved_part_id: Optional[str] = None
    resolved_colour: Optional[str] = None
    confidence: Optional[float] = None

    def apply_classification(self, result: BrickognizeResult) -> None:
        """Fold a Brickognize result into the scan's resolved fields."""
        self.brickognize_result = result
        if result.best is not None:
            self.resolved_part_id = result.best.id
            self.confidence = result.best.score
        # colour is not provided by Brickognize (shape-only); resolved separately
        # from the cropped image's dominant colour vs the Rebrickable palette (TODO).


class Session(BaseModel):
    """One visit/run. Links the before-sorting pile photo to the inventory."""

    session_id: str
    host_id: Optional[str] = None
    started_at: datetime = Field(default_factory=_utcnow)
    ended_at: Optional[datetime] = None
    # The "before" top-down shot of the jumbled pile — the model's input.
    pile_photo_path: Optional[str] = None
    # Optional ground-truth context: estimated era/vintage, source, notes.
    notes: Optional[str] = None
