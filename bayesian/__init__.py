"""Bayesian collection-estimator (Phase 5) — the research prize.

Estimates P(true collection composition | one top-down pile photo). Kept entirely
separate from the machine runtime; fed by the (pile_photo -> inventory) pairs the
machine generates.

Planned structure (see docs/PROJECT_BRIEF.md §7):
  - Dirichlet-multinomial hierarchical prior over true part-type proportions, with
    era/vintage hyperpriors (a pile is a latent mixture of eras).
  - Observation layer: a per-part visibility/thinning function of size, height and
    colour-contrast, capturing occlusion + the Brazil-nut size-segregation bias that
    makes the visible surface a *biased* sample of the interior.
  - The thinning function is calibrated empirically from the machine's ground-truth
    runs — that calibration is what makes the bias modellable rather than noise.

Stub for now; fit once a few dozen labelled piles exist.
"""
