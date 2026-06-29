"""Phase 1 — Capture PoC.

Capture a frame (live Pi camera or a replay folder) -> crop the piece out against the
pale belt -> optionally POST to Brickognize -> print the identification and record a
structured `BrickScan`.

`--defer` skips classification (scan-only / deferred-classification mode, the road
default): crops are saved and logged now, and `classification.batch` resolves them
later on a good connection. Online classification here is mainly for the demo / first
win and for tuning.

Examples:
    # Laptop dev — replay a folder of brick photos, classify online:
    python -m machine.orchestrator.phase1 --source folder --input ./sample_images --host-id grandma

    # On the Pi — live camera, defer classification to a later batch run:
    python -m machine.orchestrator.phase1 --source picamera --defer
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import cv2

from classification.brickognize_client import BrickognizeClient, BrickognizeError
from data.schema import BrickScan, Session
from data.store import ScanStore
from machine.capture import make_source
from machine.config import Settings
from machine.vision import crop_by_belt_colour


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase 1 Lego capture PoC")
    p.add_argument("--source", choices=["folder", "picamera"], default="folder")
    p.add_argument("--input", help="Image folder (required for --source folder)")
    p.add_argument("--host-id", default=None, help="Whose collection this is (label)")
    p.add_argument("--session-id", default=None, help="Override session id")
    p.add_argument("--defer", action="store_true", help="Skip online classification")
    p.add_argument("--data-dir", default=None, help="Override data dir (default from env/Settings)")
    p.add_argument(
        "--belt-bgr", default=None, help="Belt colour as 'B,G,R' (overrides config)"
    )
    p.add_argument(
        "--saturation", type=float, default=None, help="Saturation boost (overrides config)"
    )
    return p.parse_args(argv)


def _settings_from_args(args: argparse.Namespace) -> Settings:
    s = Settings.from_env()
    overrides: dict = {}
    if args.data_dir:
        overrides["data_dir"] = args.data_dir
    if args.saturation is not None:
        overrides["saturation_boost"] = args.saturation
    if args.belt_bgr:
        b, g, r = (int(x) for x in args.belt_bgr.split(","))
        overrides["belt_bgr"] = (b, g, r)
    return s if not overrides else Settings(**{**s.__dict__, **overrides})


def run(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    settings = _settings_from_args(args)

    session_id = args.session_id or f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:4]}"
    store = ScanStore(settings.data_dir)
    captures_dir = Path(settings.data_dir) / "captures" / session_id
    captures_dir.mkdir(parents=True, exist_ok=True)

    session = Session(session_id=session_id, host_id=args.host_id)
    store.append_session(session)

    client = None if args.defer else BrickognizeClient(
        url=settings.brickognize_url,
        timeout_s=settings.request_timeout_s,
        max_retries=settings.max_retries,
    )

    print(f"Session {session_id} | source={args.source} | "
          f"{'deferred (no classify)' if args.defer else 'online classify'}")

    try:
        source = make_source(args.source, input_path=args.input)
    except (ValueError, NotADirectoryError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    n_seen = n_cropped = n_classified = 0
    try:
        for frame in source:
            n_seen += 1
            crop = crop_by_belt_colour(
                frame.image,
                settings.belt_bgr,
                saturation_boost=settings.saturation_boost,
                distance_threshold=settings.fg_distance_threshold,
                min_area_frac=settings.min_blob_area_frac,
                pad=settings.crop_pad_px,
            )
            if crop is None:
                print(f"  [{frame.frame_id}] no piece found (check belt colour / threshold)")
                continue
            n_cropped += 1

            crop_path = captures_dir / f"{frame.frame_id}.jpg"
            cv2.imwrite(str(crop_path), crop.image)

            scan = BrickScan(
                frame_id=frame.frame_id,
                timestamp=frame.timestamp,
                image_path=str(crop_path),
                session_id=session_id,
                host_id=args.host_id,
                declared_partition="tub",  # scan-only: everything to one tub
            )

            if client is not None:
                try:
                    result = client.predict_path(crop_path)
                    scan.apply_classification(result)
                    n_classified += 1
                    best = result.best
                    if best:
                        print(f"  [{frame.frame_id}] {best.id} — {best.name} "
                              f"({(best.score or 0) * 100:.0f}%)")
                    else:
                        print(f"  [{frame.frame_id}] no identification returned")
                except BrickognizeError as e:
                    print(f"  [{frame.frame_id}] classify failed: {e}", file=sys.stderr)
            else:
                print(f"  [{frame.frame_id}] captured -> {crop_path.name} (deferred)")

            store.append_scan(scan)
    except KeyboardInterrupt:
        print("\ninterrupted")
    finally:
        source.close()

    print(f"\nDone. seen={n_seen} cropped={n_cropped} classified={n_classified}")
    print(f"Scans appended to {store.scans_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
