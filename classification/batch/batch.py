"""Batch-classify scans that were captured but not yet identified.

Run after a visit, on your own connection:
    python -m classification.batch --data-dir data
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from classification.brickognize_client import BrickognizeClient, BrickognizeError
from data.schema import BrickScan
from data.store import ScanStore


def classify_pending(
    store: ScanStore,
    client: BrickognizeClient | None = None,
    *,
    limit: int | None = None,
) -> int:
    """Classify every scan with no `brickognize_result`. Returns count classified.

    Rewrites the scans file in place (append-only JSONL doesn't support update, so we
    read all, enrich pending rows, and atomically replace).
    """
    client = client or BrickognizeClient()
    scans = list(store.read_scans())
    classified = 0

    for scan in scans:
        if scan.brickognize_result is not None:
            continue
        if limit is not None and classified >= limit:
            break
        if not Path(scan.image_path).exists():
            print(f"  [{scan.frame_id}] missing image {scan.image_path}, skipping", file=sys.stderr)
            continue
        try:
            result = client.predict_path(scan.image_path)
        except BrickognizeError as e:
            print(f"  [{scan.frame_id}] failed: {e}", file=sys.stderr)
            continue
        scan.apply_classification(result)
        classified += 1
        best = result.best
        print(f"  [{scan.frame_id}] {best.id if best else '?'} — "
              f"{best.name if best else 'no id'}")

    if classified:
        _rewrite_scans(store, scans)
    return classified


def _rewrite_scans(store: ScanStore, scans: list[BrickScan]) -> None:
    tmp = store.scans_path.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for scan in scans:
            f.write(scan.model_dump_json())
            f.write("\n")
    tmp.replace(store.scans_path)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Batch-classify pending Lego scans")
    p.add_argument("--data-dir", default="data")
    p.add_argument("--limit", type=int, default=None, help="Max scans to classify this run")
    args = p.parse_args(argv)

    store = ScanStore(args.data_dir)
    n = classify_pending(store, limit=args.limit)
    print(f"Classified {n} pending scan(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
