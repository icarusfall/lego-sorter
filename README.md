# lego-sorter

A transportable **Lego sorting machine** that doubles as a **ground-truth data
generator** for a **Bayesian collection-estimator**: photograph a jumbled pile, let
the machine produce the exact inventory, and learn to estimate a whole collection's
composition from a single pile photo.

Full spec and rationale: **[docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md)**.
Quick map for contributors: **[CLAUDE.md](CLAUDE.md)**. Wiring: **[docs/architecture.md](docs/architecture.md)**.

**Current phase: 1 — Capture PoC.**

## Building the machine (with the family)

The physical build is split into four modules, one owner each. Friendly, tailored
build plans live in **[docs/build/](docs/build/README.md)**:

- 🫗 [RufusPlan.md](docs/build/RufusPlan.md) — the hopper / feeder (singulation)
- 👁️ [JeremyPlan.md](docs/build/JeremyPlan.md) — the capture chamber (camera + lighting)
- 🚦 [PatrickPlan.md](docs/build/PatrickPlan.md) — the diverter (sorting mechanism)
- 🧠 [CharlieInstructions.md](docs/build/CharlieInstructions.md) — the brain (Pi, power, software)

## Quick start (laptop, no hardware)

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# generate fake "brick on a pale belt" images
python scripts/make_synthetic_belt_images.py --out ./sample_images --n 8

# run the Phase 1 pipeline: capture(replay) -> crop -> (optional) classify -> record
python -m machine.orchestrator.phase1 --source folder --input ./sample_images --defer

# later, classify the captured crops (needs internet; uses the free Brickognize API)
python -m classification.batch --data-dir data

pytest        # off-Pi tests for cropping + store
```

`--defer` skips online classification (scan-only / deferred mode, the road default).
Drop it to classify online as you capture. The synthetic images won't be recognised as
real parts — that's expected; swap in real photos of bricks on a pale-pink background
to see real identifications.

## On the Raspberry Pi

```bash
pip install -e ".[pi]"                                  # picamera2 + buildhat
python -m machine.orchestrator.phase1 --source picamera --host-id grandma --defer
```

## Layout

See [CLAUDE.md](CLAUDE.md#layout). Short version: `machine/` (Pi runtime: capture,
vision, motors, orchestrator), `classification/` (Brickognize client + deferred batch),
`catalogue/` (host keepsake, later), `bayesian/` (the research model, later),
`data/` (schema + JSONL store; **raw data is gitignored**).

## Config

Cropping knobs via env (or `--belt-bgr` / `--saturation` on the CLI):
`LEGO_BELT_BGR="220,209,255"`, `LEGO_SATURATION_BOOST=1.8`, `LEGO_FG_THRESHOLD=0.18`.
See [machine/config.py](machine/config.py).
