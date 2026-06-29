"""Off-Pi tests: cropping + store round-trip, no hardware, no network."""

from __future__ import annotations

import numpy as np

from data.schema import BrickognizeItem, BrickognizeResult, BrickScan
from data.store import ScanStore
from machine.config import DEFAULT_BELT_BGR
from machine.vision import boost_saturation, crop_by_belt_colour


def _belt_with_brick(w=320, h=240, brick_bgr=(60, 60, 220)):
    img = np.full((h, w, 3), DEFAULT_BELT_BGR, dtype=np.uint8)
    # a brick block in the middle third
    img[80:160, 110:210] = brick_bgr
    return img


def test_crop_finds_red_brick():
    img = _belt_with_brick()
    crop = crop_by_belt_colour(img, DEFAULT_BELT_BGR)
    assert crop is not None
    # bbox should roughly cover the brick (with padding), not the whole frame
    _, _, bw, bh = crop.bbox
    assert 80 < bw < 200
    assert 60 < bh < 160
    assert 0.05 < crop.area_frac < 0.6


def test_crop_finds_white_brick_after_saturation_boost():
    # White is the hard case — it should still be found against pale pink.
    img = _belt_with_brick(brick_bgr=(245, 245, 245))
    crop = crop_by_belt_colour(img, DEFAULT_BELT_BGR, saturation_boost=2.0)
    assert crop is not None


def test_crop_returns_none_on_empty_belt():
    img = np.full((240, 320, 3), DEFAULT_BELT_BGR, dtype=np.uint8)
    assert crop_by_belt_colour(img, DEFAULT_BELT_BGR) is None


def test_boost_saturation_is_identity_at_one():
    img = _belt_with_brick()
    assert np.array_equal(boost_saturation(img, 1.0), img)


def test_store_round_trip(tmp_path):
    store = ScanStore(tmp_path)
    scan = BrickScan(
        frame_id="abc123",
        image_path="x.jpg",
        session_id="sess1",
        host_id="grandma",
        declared_partition="tub",
    )
    store.append_scan(scan)
    back = list(store.read_scans())
    assert len(back) == 1
    assert back[0].frame_id == "abc123"
    assert back[0].brickognize_result is None  # unclassified by default


def test_apply_classification_sets_resolved_fields():
    scan = BrickScan(frame_id="f", image_path="x.jpg", session_id="s")
    result = BrickognizeResult(
        best=BrickognizeItem(id="3001", name="Brick 2x4", score=0.92),
        items=[BrickognizeItem(id="3001", name="Brick 2x4", score=0.92)],
    )
    scan.apply_classification(result)
    assert scan.resolved_part_id == "3001"
    assert scan.confidence == 0.92
