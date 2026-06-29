# CLAUDE.md

Orientation for working in this repo. The authoritative, detailed spec is
[docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md) — read it for rationale before
changing any settled decision. This file is the quick map.

## What this is

A transportable **Lego sorting machine** that doubles as a **ground-truth data
generator** for a **Bayesian collection-estimator**. Two goals, one machine:

- **A — the machine:** hopper → singulate → conveyor → camera → identify → (optional) divert into buckets.
- **B — the research (the prize):** dataset of `(top-down photo of a jumbled pile → true part-by-part inventory)` pairs, used to fit a model that estimates a whole collection's composition from one pile photo.

The machine is the label generator: photograph the pile *before* sorting, let the
machine produce the exact inventory, and every run is one labelled example.

## Stack

| Area | Tech |
|---|---|
| Runtime host | Raspberry Pi 5 (8GB), Build HAT, Camera Module 3 |
| Image capture | `picamera2` (Pi-only) |
| Cropping | OpenCV — colour-key vs pale belt (Phase 1) / MOG2 background subtraction (Phase 2 conveyor). **Not** AI. |
| Part ID | **Brickognize** REST API (free, one part per image). No custom model. |
| Motor control | Build HAT Python lib (Pi-only) |
| Catalogue / valuation / build ideas | Rebrickable + BrickLink |
| Bayesian model | PyMC (separate `bayesian/` module) |
| Pile-photo object detection | trained detector — the one place AI is needed (Phase 5) |

## Layout

```
machine/          Pi-side runtime
  capture/        camera sources (Picamera2 + a folder-backed dev source) + Frame type
  vision/         OpenCV cropping (colour-key + MOG2)
  motors/         Build HAT control (later phases)
  orchestrator/   mode state machine + Phase 1 capture CLI
classification/
  brickognize_client/   API client w/ retry & rate-limit
  batch/                deferred at-home classification pipeline
catalogue/        Rebrickable/BrickLink enrichment, valuation, report gen (later)
bayesian/         research model (PyMC), kept separate from machine runtime
data/             schema (pydantic) + JSONL store. RAW IMAGES/DATA NOT COMMITTED.
docs/             PROJECT_BRIEF.md (the spec), architecture.md, decisions/ (ADRs)
scripts/
```

## Conventions

- **Python 3.10+.** Core deps (opencv, numpy, pydantic, requests) install on any
  laptop. Pi-only deps (`picamera2`, `buildhat`) are the `[pi]` extra and are
  imported lazily so the rest of the code runs and is testable off-Pi.
- **Dev without hardware:** anything camera/motor-shaped sits behind an interface
  with a non-hardware fallback. `FolderFrameSource` replays a directory of images
  so the full capture→crop→classify pipeline runs on a laptop.
- **No secrets in git.** Brickognize needs none. Rebrickable/BrickLink keys go in
  `.env` (gitignored).
- **`data/` holds schema only.** Captured images and inventories are gitignored —
  they're large and may contain host info.
- Record notable, contestable choices as ADRs in `docs/decisions/`.

## Current phase

**Phase 1 — Capture PoC.** Hold a brick under the camera → crop against the pale
belt → POST to Brickognize → print part ID + confidence, and record a structured
row. Hardware capture only runs on the Pi; everything else runs and is testable on
a laptop via the folder-backed source.

Run it:

```bash
# Off-Pi (replay images from a folder):
python -m machine.orchestrator.phase1 --source folder --input ./sample_images

# On the Pi (live camera):
python -m machine.orchestrator.phase1 --source picamera
```

See [docs/PROJECT_BRIEF.md §9](docs/PROJECT_BRIEF.md) for the full phase plan.
