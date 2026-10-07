"""
A frame sequence: frames for the wand, plus how to play them and
where they came from.

Saved as two files:

    name.png    the strip: one column per frame, num_leds pixels tall
                (standard layout: row 0 = pixel 0 = tip, column 0 = first frame)
    name.json   fps and metadata (generator, params, seed, source, notes)

Usage:

    seq = FrameSequence(frames, fps=100, generator="perlin", seed=999)
    seq.save("../sequences/perlin_test")

    seq = FrameSequence.load("../sequences/perlin_test")
    wand.play(seq.frames, seconds=3)

A strip is just an image, so it opens in any image viewer.
paint.py and generate.py take a sequence as INPUT_FILE; paint.py
uses its frames as-is (no orienting or resizing).
"""

import json
from pathlib import Path

from PIL import Image


class FrameSequence:

    def __init__(
        self,
        frames,
        fps=100,
        generator=None,
        params=None,
        seed=None,
        source=None,
        notes=""
    ):
        self.frames = [list(frame) for frame in frames]
        self.fps = fps
        self.generator = generator
        self.params = params or {}
        self.seed = seed
        self.source = source
        self.notes = notes

        # Set by save() / load(), so slices can point back to the file.
        self.path = None

    def __len__(self):
        return len(self.frames)

    @property
    def num_leds(self):
        return len(self.frames[0]) if self.frames else 0

    @property
    def duration(self):
        """Length in seconds when played at its own fps."""
        return len(self.frames) / self.fps

    # -----------------------------------------------------
    # Image conversion
    # -----------------------------------------------------

    def to_image(self):
        """The strip as a PIL image (frames left to right)."""
        image = Image.new("RGB", (len(self.frames), self.num_leds))

        for x, frame in enumerate(self.frames):
            for y, rgb in enumerate(frame):
                image.putpixel((x, y), tuple(rgb))

        return image

    @classmethod
    def from_image(cls, image, fps=100, **metadata):
        """
        Make a sequence from a strip image that is already
        in the standard layout (e.g. the output of image_frames).
        """
        image = image.convert("RGB")
        width, height = image.size

        frames = [
            [image.getpixel((x, y)) for y in range(height)]
            for x in range(width)
        ]

        return cls(frames, fps=fps, **metadata)

    # -----------------------------------------------------
    # Save / load
    # -----------------------------------------------------

    def metadata(self):
        return {
            "fps": self.fps,
            "frames": len(self.frames),
            "num_leds": self.num_leds,
            "generator": self.generator,
            "params": self.params,
            "seed": self.seed,
            "source": self.source,
            "notes": self.notes,
        }

    def save(self, path):
        """
        Save as path.png + path.json. Any extension on path
        is ignored. Creates the folder if needed.
        """
        path = Path(path).with_suffix("")
        path.parent.mkdir(parents=True, exist_ok=True)

        self.to_image().save(path.with_suffix(".png"))

        with open(path.with_suffix(".json"), "w", encoding="utf-8") as f:
            json.dump(self.metadata(), f, indent=2)

        self.path = path

    @classmethod
    def load(cls, path):
        """
        Load path.png + path.json. If there's no .json,
        loads the strip at 100 fps with no metadata.
        """
        path = Path(path).with_suffix("")
        meta = {}

        json_path = path.with_suffix(".json")
        if json_path.exists():
            with open(json_path, encoding="utf-8") as f:
                meta = json.load(f)

        image = Image.open(path.with_suffix(".png"))

        seq = cls.from_image(
            image,
            fps=meta.get("fps", 100),
            generator=meta.get("generator"),
            params=meta.get("params"),
            seed=meta.get("seed"),
            source=meta.get("source"),
            notes=meta.get("notes", "")
        )
        seq.path = path

        return seq

    # -----------------------------------------------------
    # Slicing
    # -----------------------------------------------------

    def slice(self, start, end):
        """
        Frames start..end-1 as a new sequence. Records where
        it came from in `source`, so a snapshot can be traced
        back (and regenerated from the seed).
        """
        return FrameSequence(
            self.frames[start:end],
            fps=self.fps,
            generator=self.generator,
            params=self.params,
            seed=self.seed,
            source={
                "from": str(self.path) if self.path else self.source,
                "start": start,
                "end": end,
            },
            notes=self.notes
        )
