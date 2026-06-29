"""Image capture: a `Frame` type and pluggable `FrameSource`s.

`PiCameraSource` uses Picamera2 (Pi-only, imported lazily). `FolderFrameSource`
replays a directory of images so the whole capture -> crop -> classify pipeline runs
on a laptop with no hardware. Both yield `Frame`s, so the orchestrator is identical
in dev and on the machine.
"""

from .frame import Frame
from .sources import FolderFrameSource, FrameSource, make_source

__all__ = ["Frame", "FrameSource", "FolderFrameSource", "make_source"]
