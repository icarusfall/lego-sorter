"""Generate fake "brick on a pale belt" images so the pipeline runs with no hardware.

Each image is a pale-pink background with one coloured rounded rectangle (a stand-in
brick) at a random position. Useful for exercising the crop + store path and, with a
real connection, sanity-checking the Brickognize call shape (it won't recognise these
fakes as real parts — that's expected).

    python scripts/make_synthetic_belt_images.py --out ./sample_images --n 8
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import cv2
import numpy as np

BELT_BGR = (220, 209, 255)  # pale pink, matches machine.config default

# A few saturated "brick" colours (BGR).
BRICK_COLOURS = [
    (60, 60, 220),   # red
    (220, 120, 40),  # blue
    (40, 180, 240),  # yellow
    (60, 180, 60),   # green
    (40, 40, 40),    # black
    (240, 240, 240), # white (the hard case for keying)
]


def make_image(w: int, h: int, rng: random.Random) -> np.ndarray:
    img = np.full((h, w, 3), BELT_BGR, dtype=np.uint8)
    # slight belt texture so it's not perfectly flat
    noise = rng.randint(0, 6)
    img = cv2.add(img, np.random.randint(0, noise + 1, img.shape, dtype=np.uint8))

    bw, bh = rng.randint(w // 6, w // 3), rng.randint(h // 6, h // 3)
    x = rng.randint(10, w - bw - 10)
    y = rng.randint(10, h - bh - 10)
    colour = rng.choice(BRICK_COLOURS)
    cv2.rectangle(img, (x, y), (x + bw, y + bh), colour, thickness=-1)
    # a couple of studs for flavour
    for i in range(2):
        cx = x + bw // 3 * (i + 1)
        cv2.circle(img, (cx, y + bh // 2), min(bw, bh) // 6, colour, -1)
    return img


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="sample_images")
    p.add_argument("--n", type=int, default=8)
    p.add_argument("--width", type=int, default=640)
    p.add_argument("--height", type=int, default=480)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    np.random.seed(args.seed)

    for i in range(args.n):
        img = make_image(args.width, args.height, rng)
        cv2.imwrite(str(out / f"brick_{i:03d}.jpg"), img)
    print(f"Wrote {args.n} images to {out}/")


if __name__ == "__main__":
    main()
