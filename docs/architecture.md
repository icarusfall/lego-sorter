# Architecture

High-level map of how the pieces fit. The *why* lives in
[PROJECT_BRIEF.md](PROJECT_BRIEF.md); this is the *how it's wired*.

## Data flow (scan-only, the road default)

```
                         ┌─────────────────────────────────────────┐
  pile photo (before) ───┤ Session (pile_photo_path -> inventory)   │  ← Bayesian training pair
                         └─────────────────────────────────────────┘
                                          │
 hopper → singulate → belt → camera ──────┤
                                          ▼
                                   machine.capture.Frame  (frame_id, image, ts)
                                          │
                                          ▼
                          machine.vision.crop_by_belt_colour     (Phase 1, still)
                          machine.vision.MOG2Cropper              (Phase 2, conveyor)
                                          │  Crop (image, bbox, mask)
                                          ▼
                                save crop -> data/captures/<session>/<frame>.jpg
                                          │
                                          ▼
                                   data.schema.BrickScan ──► data.store.ScanStore (JSONL)
                                          │
                  ┌───────────────────────┴────────────────────────┐
                  ▼ (online, demo/tuning)                           ▼ (deferred, road default)
        BrickognizeClient.predict_path                  classification.batch.classify_pending
                  └───────────────────────┬────────────────────────┘
                                          ▼
                          BrickScan.resolved_part_id / confidence
                                          │
                                          ▼
                       catalogue/ (Phase 4): counts, valuation, build ideas → host keepsake
                                          │
                                          ▼
                       bayesian/ (Phase 5): fit thinning fn, estimate whole collection
```

## Key boundaries

- **Hardware behind interfaces.** `machine.capture.FrameSource` has a Pi
  (`PiCameraSource`) and a laptop (`FolderFrameSource`) implementation; the
  orchestrator depends only on iterating `Frame`s. Motors (Phase 2) will follow the
  same pattern. So the full pipeline runs and is tested off-Pi.
- **Capture is decoupled from classification.** A `BrickScan` is valid before it's
  classified. This is what enables deferred classification (capture on flaky host
  wifi; classify later at home) — see PROJECT_BRIEF.md §5.
- **The machine runtime never imports `bayesian/`.** The research model consumes the
  data the machine produces; it is not on the machine's critical path.

## Two cropping strategies, by stage

| Stage | Input | Strategy | Module |
|---|---|---|---|
| Phase 1 (still PoC) | one frame, brick on pale belt | colour distance from belt colour | `crop_by_belt_colour` |
| Phase 2 (conveyor) | stream of belt frames | MOG2 background subtraction | `MOG2Cropper` |
| Phase 5 (pile photo) | many pieces, one frame | trained object detector (the one place AI is needed) | `bayesian/` (TBD) |
