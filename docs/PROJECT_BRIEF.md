# LEGO Sorter & Collection-Estimator — Project Brief / Handover

> **For Claude Code:** This is the founding brief for the project. Treat the decisions in it as settled (the rationale is included so you don't need to relitigate them — if you think a decision is wrong, flag it explicitly rather than quietly diverging). Suggested first action: save this as `docs/PROJECT_BRIEF.md`, then generate a root `CLAUDE.md` summarising the stack, conventions, and current phase.

---

## 1. What we're building (two goals, one machine)

**Goal A — the machine (fun build, with kids).** A transportable Lego-brick sorting machine: tip a jumbled pile into a hopper, it singulates pieces onto a conveyor, a camera photographs each one, an AI identifies it, and (optionally) a diverter routes it into one of several buckets.

**Goal B — the research (the real prize).** Build a dataset of *(photo of a jumbled pile → true part-by-part inventory)* pairs, and from it a **Bayesian model that estimates the composition of someone's whole Lego collection from a single photo** of the jumbled pile.

**The key insight linking them:** the machine is a *ground-truth label generator* for the model. Photograph a pile from above **before** sorting, then let the machine produce the exact inventory. Every run yields one labelled example. Nobody else has this data because every existing tool (Brickit etc.) sidesteps the hard problem by requiring bricks spread in a single visible layer.

---

## 2. Hardware (purchased / decided — do not re-spec)

**Bought (from The Pi Hut unless noted):**
- Raspberry Pi 5 **8GB** + Active Cooler + official 27W USB-C PSU
- **64GB** SanDisk microSD (Amazon; A1 or A2 both fine — class is irrelevant here)
- **Camera Module 3 (standard, 75°)** — autofocus is the reason; ships with the Pi 5 (22-pin) cable
- **Build HAT** + **1× Standard motor (88013)** + **1× Angular motor (88017)**
- **Build HAT 8V power supply** (required to drive motors; USB power alone only reads encoders)

> Note on the 8GB Pi: identification runs on a cloud API, so 4GB would have sufficed, but 2/4GB were out of stock and 8GB is useful for general projects and for running local object-detection later (see §7).

**To source cheaply:**
- Technic structural parts (beams, pins, axles, bushes, **gears**) — existing collection + an eBay "Technic joblot/bundle" (sold-by-weight lots are best value) + targeted BrickLink top-ups for specific gears.

**Deliberately NOT buying:**
- **LEGO Education SPIKE Prime set** — its cost is dominated by the programmable hub (the Build HAT *is* our controller, so the hub is redundant) and motors (already bought). ~£470 inc VAT at Hope Education for mostly-redundant kit.
- **SPIKE colour/distance sensors (45605/45604)** — optional. The camera already sees colour; "piece arrived" / "hopper empty" can be detected for free in OpenCV. If wanted later, buy *used* on BrickLink, and only LPF2 type (SPIKE/Robot Inventor) — **not** EV3/NXT, which use an incompatible RJ12 plug.

**Power topology:** Pi 5 on its own 27W USB-C; Build HAT on the 8V supply for the motors. (Don't try to run the Pi 5 off the Build HAT supply — risk of brownout.)

---

## 3. Software stack (decided)

| Concern | Choice | Notes |
|---|---|---|
| Part identification | **Brickognize API** (free) | brickognize.com; REST at `api.brickognize.com/docs`; one part per image; returns BrickLink/Rebrickable/BrickOwl IDs. **No custom model training.** An MCP server exists. |
| Image cropping | **OpenCV background subtraction (MOG2)** — *not* AI | Conveyor case only: plain non-Lego belt + one moving blob. Free, runs on the Pi. |
| Image capture | **Picamera2** | |
| Motor control | **Build HAT Python library** | |
| Metadata / valuation / build suggestions | **Rebrickable + BrickLink** | For the host catalogue (see §6). |
| Bayesian model | **PyMC** (or Stan) | Separate research module (§7). |

**Cropping detail worth stealing from Daniel West:** make the belt a **pale pastel (e.g. pale pink) paper** — a colour no Lego brick is — so nothing is lost against the background, and **boost image saturation before background subtraction** so white/grey pieces don't vanish.

---

## 4. Physical architecture — modular & transportable

The machine must disassemble, pack into a Ford Galaxy, and re-set-up at people's houses in **≤ ~10 minutes**. Module boundaries follow the functional stages anyway, so the design *wants* to be modular.

**Four modules, each on its own rigid sub-base (plywood/laser-cut — not flexing Lego baseplate):**
1. **Feeder / singulation** — hopper, belt(s), vibration feeder. Bulky, noisy, the hard part.
2. **Capture chamber** — short belt past camera + LED, enclosed. Small but precision-critical. **Transport assembled, padded, never broken down** (focus/angle/lighting/belt-distance are what accuracy depends on).
3. **Distribution** — diverter + buckets. **Optional / bolt-on** (see §5). Bulkiest, fiddliest to calibrate.
4. **Brain** — Pi, Build HAT, PSUs, wiring.

**Transport principles to bake in from the start:**
- **Self-aligning inter-module joins** — Technic-axle "dowels" into matching holes, or tongue-and-groove lips — so modules re-register *identically* each setup with no re-tuning. This single thing makes or breaks fast setup.
- **Wiring stays within modules.** At teardown the *only* disconnects are the ~4 module-boundary connectors + 2 PSU leads. Use the Build HAT's quick LPF2 plugs.
- **`systemd` service** auto-runs the software on boot → setup is "place modules, click together, power on."
- One labelled **stackable crate per module** (capture-chamber crate padded). **Bring your own folding table** for a guaranteed flat, known-height surface.
- Build in **lips/walls + a catch tray** to contain flung bricks in someone's home.
- **Feeder noise** matters — a vibration feeder running an hour in a living room is grating. Prototype damping or a gentler singulation method.

---

## 5. Operating modes (central design decision)

Scanning and bucketing **share the whole front end** (singulate → convey → photograph → classify). Bucketing only adds a routing stage — but that stage has a **hard real-time deadline** (the brick arrives whether or not the diverter is ready), and that deadline is what costs throughput and reliability.

| | Scan-only (1 tub) | Binary extract (2-way gate) | Full 6-way bucketing |
|---|---|---|---|
| Cycle/brick | ~2s (feeder-bound) | ~2–2.3s | ~3–4s |
| Net bricks / 40-min live window | **~900–1,100** | ~800–1,000 | **~400–650** |
| Stoppage frequency | low | medium | high |
| Host-wifi tolerance | **high** (can defer classification entirely) | medium | **low** (round-trip on critical path) |
| Diverter module needed? | **no** | tiny gate | yes (bulkiest) |
| Labelled bricks/visit (data yield) | **highest** | high | lowest |

**Why scanning wins for the data goal:**
- In scan mode the photo is captured with a frame ID and the brick drops into the tub immediately; the Brickognize result is **joined to that frame in software later**. API latency never touches the mechanical cycle.
- This enables **deferred classification**: store timestamped photos to the SD card, drive home, classify that evening on *your* connection. Immune to flaky host wifi and API rate limits.
- Bucketing can't defer — the diverter needs the answer *before* the brick arrives — so variable wifi becomes belt stalls/misroutes.
- 6-way throughput also depends on the *sequence* of destinations (a far-bin sweep makes the belt wait), so it's worse and less predictable than cycle time suggests — and the extra mechanism motion produces **no extra label**.

**Conclusion:** for the dataset, bucketing is *strictly dominated* (same label type, fewer of them, more risk). Its only justification is the physical sort.

**Design rule that gives all three modes from one machine:** a brick must **exit straight off the belt-end into a tub when no diverter is fitted**, and the gate/diverter seats at *that same exit point* when it is. Make that exit a clean module boundary.

**Road default:** scan-only with deferred classification. **Diverter:** optional bolt-on. **For a crowd-pleasing physical result on a visit:** run a **binary extraction** of one high-value category, not a six-way split. **Full 6-way:** home demo only, where stoppages cost nothing.

---

## 6. The visit / value proposition

- **Max 1-hour visits. No unattended running in v1** (would need a huge hopper, jam auto-recovery, remote alerting, and host trust — that's a v2 research rig and inverts effort-to-payoff). Cover the collection by **sampling + extrapolation** (that's literally what the Bayesian model is for), not machine-hours.
- **Throughput reality:** ~1 brick/2s tuned (West's benchmark, after 2.5 yrs); v1 slower. Collections are 10k–50k+ pieces, so one visit touches **1–10%**. *Never promise "we'll sort your Lego."*
- **The keepsake is information, not tidiness.** Hand the host a **catalogue**: estimated total count, breakdown by type & colour, a BrickLink-based **valuation**, and a Rebrickable **"sets you could build from what you own"** list. Nobody has this for their pile.
- **Elegant bit:** that catalogue *is* the research output — you scan a sample, the model extrapolates to the whole collection, and the extrapolation is the gift. Same artefact, both purposes.
- **Physical sorting = the entertainment** (a Lego robot sorting Lego, kids feeding the hopper — the social engine of the visit) **+ a targeted high-value extraction** (e.g. "every minifig/minifig part", "all the Technic", or binary "in *this* set / not" against a Rebrickable BOM). Selective extraction is useful even at low volume; a generic colour split of 300 bricks helps nobody.

---

## 7. The Bayesian model (research goal)

**Target:** P(true collection composition | one top-down photo of the jumbled pile).

**Why it's hard (and original):** the photo shows only the **surface**, which is a *biased* sample of the interior because of (a) **occlusion** and (b) **granular size-segregation — the Brazil-nut effect** (shaking lifts large pieces, sinks small ones), so the surface systematically over-represents big parts. The bias is physical, hence *modellable* rather than mere noise.

**Approach:**
- Hierarchical model with a **Dirichlet–multinomial** prior over true part-type proportions.
- Observation layer maps true composition → *visible-surface* composition via a per-part **visibility/thinning function** of piece size, height, colour-contrast.
- **Calibrate the thinning function empirically from the machine's ground truth** — the labelled runs give exactly this.
- Total count scale from pile volume/mass; proportions from the bias-corrected surface read.
- Closed loop: sorter labels → fit model → predictions re-checkable against the sorter.

**Note:** for the *pile* photo (many pieces in one frame) you **do** need AI object-detection to separate pieces — unlike the conveyor case, where OpenCV background-subtraction suffices. This is the one place a trained detector earns its keep.

---

## 8. Suggested repo structure

```
lego-sorter/
├── CLAUDE.md                  # generated from this brief
├── docs/
│   ├── PROJECT_BRIEF.md       # this file
│   ├── architecture.md
│   └── decisions/             # ADRs for notable choices
├── machine/                   # Pi-side runtime
│   ├── capture/               # Picamera2 capture, frame IDs, timestamping
│   ├── vision/                # OpenCV crop / background subtraction
│   ├── motors/                # Build HAT control (belt, feeder, diverter)
│   └── orchestrator/          # mode state machine: scan | extract | sort
├── classification/
│   ├── brickognize_client/    # API client + retry/rate-limit handling
│   └── batch/                 # deferred (at-home) classification pipeline
├── catalogue/                 # Rebrickable/BrickLink enrichment, valuation, build-suggestions, report gen
├── bayesian/                  # research model (PyMC), separate from machine runtime
├── data/                      # schemas only — raw images/data NOT committed
└── scripts/
```

**Data schema to define early** (per scanned brick): `frame_id`, `timestamp`, `image_path`, `session_id`, `host_id`, `declared_partition`, `brickognize_result` (raw), `resolved_part_id`, `resolved_colour`, `confidence`. Plus a per-session `pile_photo` (the before shot) linked to the resulting inventory — that join is the Bayesian training pair.

---

## 9. Build phases

1. **Capture PoC** — Pi + camera + Brickognize. Hold a brick under the camera, print the identification. (First win; hooks the kids.)
2. **Conveyor** — Build HAT + Lego belt moves one brick past the camera; OpenCV crop on the moving belt; capture triggered on blob entry.
3. **Singulation + diverter** — vibration feeder + v-channel; binary gate at the belt exit. (The long slog — expect many iterations.)
4. **Data flywheel** — add the before-sorting pile photo + structured logging; start collecting (pile → inventory) pairs.
5. **Bayesian model** — once a few dozen labelled piles exist, fit and validate.

---

## 10. Immediate next actions for Claude Code

1. Scaffold the repo (§8), init git, push to GitHub.
2. Generate `CLAUDE.md` (stack, conventions, current phase = Phase 1).
3. **Phase 1 capture script:** Picamera2 grab → OpenCV crop against pale background → POST to Brickognize → print part ID + confidence. Make the belt/background colour and saturation-boost configurable.
4. Define the data schema (§8) as code (e.g. a pydantic model + a SQLite or JSONL store for v1).

---

## 11. Open questions / TODO

- **Quieter singulation** — vibration-feeder noise in homes; evaluate damping vs. alternative singulation.
- **Deferred-classification logistics** — capture format, photos-per-visit, SD capacity headroom, at-home batch pipeline throughput against Brickognize rate limits.
- **Module interface scheme** — concrete locating features + the 4 boundary connectors.
- **Diverter mechanism** — single servo-driven swivel chute over a bin turntable is far simpler than West's 18 gates; start 4–6 bins, but road kit uses binary gate only.
- **Belt material** — pale pink paper (West) vs. printable alternative; must be uniform and non-Lego-coloured.

---

## 12. Reference builds & docs

- **BrickSortingMachine** — `https://bricksortingmachine.com` — closest thing to a buildable blueprint; open-source code + (Sept 2025) **Lego build instructions & BrickLink Studio plans**. Design write-up: `https://medium.com/@bricksortingmachine/diy-lego-sorting-machine-a4227e61221d`
- **Daniel West — CV pipeline** (background subtraction, belt colour, saturation trick): `https://medium.com/data-science/a-high-speed-computer-vision-pipeline-for-the-universal-lego-sorting-machine-253f5a690ef4` (companion article on synthetic training data from same author).
- **Brickognize** — `https://brickognize.com`, API docs `https://api.brickognize.com/docs`.
- **awesome-lego-machine-learning** (Piotr Rybak) — master index of builds, datasets, ML approaches. Search GitHub for the repo name.
- **Build HAT** docs (Raspberry Pi), **Picamera2** docs, **Rebrickable API** docs.

---

*Stack summary for CLAUDE.md: Python on Raspberry Pi 5 (Picamera2, OpenCV, Build HAT lib) for the machine; Brickognize REST API for identification; Rebrickable/BrickLink for catalogue enrichment; PyMC for the Bayesian estimator. Modular, transportable hardware. Current phase: 1 (capture PoC).*
