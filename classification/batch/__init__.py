"""Deferred (at-home) classification.

Scan-only mode captures crops now and classifies later on a good connection. This
module reads unclassified `BrickScan`s from the store, runs each crop through
Brickognize, and writes the enriched scans back.
"""

from .batch import classify_pending

__all__ = ["classify_pending"]
