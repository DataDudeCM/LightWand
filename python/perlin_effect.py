"""
Perlin noise field on the wand.

RUN = "live":  stream to the wand until Ctrl+C.
RUN = "save":  save SAVE_SECONDS of frames to ../sequences/
               (no wand needed). Open the result with
               preview_paint.py, or paint it with image_paint.
"""

import itertools
from pathlib import Path

from generators import perlin
from lightwand import LightWand
from sequence import FrameSequence


# ============================================================
# EASY CONTROLS
# ============================================================

# "live" or "save"
RUN = "live"

FPS = 40

SEED = 42

PALETTE_NAME = "industrialSun"

# Perlin field scale
#
# Smaller = larger/smoother features
# Larger  = smaller/busier features
X_SCALE = 0.01
Y_SCALE = 0.01

# First frame. Lets a saved range be regenerated exactly
# (e.g. START_FRAME = 1440 with SAVE_SECONDS = 7.5 at 40 fps
# gives frames 1440-1740).
START_FRAME = 0

# ---- save ----
SAVE_SECONDS = 10
SAVE_FOLDER = "../sequences"

# ---- live ----
WAND_BRIGHTNESS = 1

# LED gamma correction: 2.2 makes the wand's colors match the
# screen previews; 1.0 = off. See LightWand / DESIGN.md §5.3.
WAND_GAMMA = 2.2

NUM_LEDS = 100


# ============================================================
# RUN
# ============================================================

def make_frames():
    return perlin.frames(
        seed=SEED,
        x_scale=X_SCALE,
        y_scale=Y_SCALE,
        palette=PALETTE_NAME,
        num_leds=NUM_LEDS,
        start=START_FRAME
    )


def run_live():
    wand = LightWand(
        num_leds=NUM_LEDS,
        brightness=WAND_BRIGHTNESS,
        gamma=WAND_GAMMA
    )

    print("Starting Perlin noise field...")
    print(f"Sending to {wand.ip}:{wand.port}")
    print(f"Palette: {PALETTE_NAME}")
    print(f"FPS: {FPS}")
    print(f"Gamma: {WAND_GAMMA}")

    try:
        wand.stream(make_frames(), fps=FPS)

    except KeyboardInterrupt:
        print("Stopping Perlin effect...")

    finally:
        wand.close()


def run_save():
    count = max(1, round(SAVE_SECONDS * FPS))

    frames = list(itertools.islice(make_frames(), count))

    sequence = FrameSequence(
        frames,
        fps=FPS,
        generator="perlin",
        params={
            "x_scale": X_SCALE,
            "y_scale": Y_SCALE,
            "palette": PALETTE_NAME,
            "start": START_FRAME,
            "end": START_FRAME + count,
        },
        seed=SEED
    )

    path = Path(SAVE_FOLDER) / f"perlin_seed{SEED}"
    sequence.save(path)

    print(f"Saved {count} frames ({sequence.duration:.1f} s at {FPS} fps)")
    print(f"  {path.with_suffix('.png')}")
    print(f"  {path.with_suffix('.json')}")


if __name__ == "__main__":
    if RUN == "live":
        run_live()
    elif RUN == "save":
        run_save()
    else:
        raise ValueError(f"Unknown RUN: {RUN}")
