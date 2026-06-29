"""Frame sources: a live Pi camera and a folder-replay source for dev."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator

import cv2

from .frame import Frame

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


class FrameSource(ABC):
    """Yields frames. Iterating is the only contract the orchestrator depends on."""

    @abstractmethod
    def __iter__(self) -> Iterator[Frame]: ...

    def close(self) -> None:  # optional cleanup hook
        pass


class FolderFrameSource(FrameSource):
    """Replay images from a directory — the laptop/dev source, no hardware needed.

    Files are yielded in sorted name order so runs are reproducible.
    """

    def __init__(self, folder: str | Path) -> None:
        self.folder = Path(folder)
        if not self.folder.is_dir():
            raise NotADirectoryError(f"Not a directory: {self.folder}")

    def _paths(self) -> list[Path]:
        return sorted(
            p for p in self.folder.iterdir() if p.suffix.lower() in _IMAGE_EXTS
        )

    def __iter__(self) -> Iterator[Frame]:
        for path in self._paths():
            image = cv2.imread(str(path))
            if image is None:
                continue  # skip unreadable files rather than crash a long run
            yield Frame(frame_id=path.stem, image=image, source_path=str(path))


class PiCameraSource(FrameSource):
    """Live Picamera2 capture (Raspberry Pi only).

    `picamera2` is imported lazily so importing this module never fails on a laptop.
    Yields frames indefinitely; pair it with an external trigger (Phase 2: blob-entry
    on the moving belt) or a manual loop (Phase 1: press-to-capture).
    """

    def __init__(self, resolution: tuple[int, int] = (2304, 1296), manual_trigger: bool = True) -> None:
        try:
            from picamera2 import Picamera2  # type: ignore
        except ImportError as e:  # pragma: no cover - hardware path
            raise RuntimeError(
                "picamera2 is not installed. Install the [pi] extra on the Raspberry Pi, "
                "or use --source folder for laptop development."
            ) from e

        self._picam = Picamera2()
        config = self._picam.create_still_configuration(main={"size": resolution})
        self._picam.configure(config)
        self._picam.start()
        self.manual_trigger = manual_trigger

    def _grab(self) -> Frame:
        rgb = self._picam.capture_array()  # Picamera2 returns RGB
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        return Frame(frame_id=uuid.uuid4().hex[:12], image=bgr)

    def __iter__(self) -> Iterator[Frame]:  # pragma: no cover - hardware path
        while True:
            if self.manual_trigger:
                try:
                    input("Place a brick on the belt, then press Enter (Ctrl-C to stop)... ")
                except (EOFError, KeyboardInterrupt):
                    return
            yield self._grab()

    def close(self) -> None:  # pragma: no cover - hardware path
        try:
            self._picam.stop()
        except Exception:
            pass


def make_source(kind: str, *, input_path: str | None = None) -> FrameSource:
    """Factory used by the CLI. `kind` is 'folder' or 'picamera'."""
    if kind == "folder":
        if not input_path:
            raise ValueError("--input is required for --source folder")
        return FolderFrameSource(input_path)
    if kind == "picamera":
        return PiCameraSource()
    raise ValueError(f"Unknown source kind: {kind!r} (expected 'folder' or 'picamera')")
