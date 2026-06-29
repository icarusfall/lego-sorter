"""Build HAT motor control — belt, feeder, diverter (Phase 2+).

Stub for now. Will wrap the `buildhat` library (Pi-only, imported lazily) behind a
small interface (`Belt.run()`, `Feeder.pulse()`, `Diverter.route(bucket)`) with a
no-hardware fake so the orchestrator state machine is testable off-Pi, mirroring the
camera-source pattern in `machine.capture`.
"""
