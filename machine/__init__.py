"""Pi-side runtime: capture, vision, motors, orchestration.

Hardware-touching modules (`picamera2`, `buildhat`) are imported lazily so that the
non-hardware code in this package runs and is testable on a laptop.
"""
