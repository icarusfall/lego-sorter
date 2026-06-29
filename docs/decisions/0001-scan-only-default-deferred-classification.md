# ADR 0001 — Scan-only is the road default; classification is deferred

Status: Accepted (carried over from PROJECT_BRIEF.md §5)

## Context

The machine can run scan-only (one tub), binary extraction (2-way gate), or full
6-way bucketing. The research goal (Goal B) wants the maximum number of *labelled*
bricks per visit. Bucketing adds a routing stage with a hard real-time deadline: the
brick arrives whether or not the diverter is ready, so the Brickognize round-trip
lands on the mechanical critical path, and host wifi variance turns into belt stalls
and misroutes.

## Decision

On the road, default to **scan-only with deferred classification**:

- Capture the crop with a `frame_id` and drop the brick into the tub immediately.
- Persist the crop + a `BrickScan` row now; leave `brickognize_result` empty.
- Classify later (`classification.batch`) on our own connection.

The diverter is an optional bolt-on. For a crowd-pleasing physical result on a visit,
run a *binary* extraction of one high-value category — never a generic colour split.

## Consequences

- API latency and flaky host wifi never touch the mechanical cycle → higher, more
  predictable throughput and the highest label yield per visit.
- Requires the schema to treat classification as optional/late-bound (it does:
  `BrickScan.brickognize_result` is nullable, filled by a batch pass).
- Needs SD-card capacity headroom for a visit's worth of crops (tracked in
  PROJECT_BRIEF.md §11, deferred-classification logistics).
- Bucketing is not removed — the belt exit is a clean module boundary so a gate can
  seat there — but it is justified only by the physical sort, not the data.
