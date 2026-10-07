"""
Flow viewer: watch what the wand puts out over time. No wand needed.

The wand sits at the leading edge of the window (the SWEEP side)
and shows the newest frame. Older frames scroll away behind it,
so time becomes the second dimension. It's a view of the
generator, not a photo: use preview_paint.py for that.

Plays a saved sequence (looping) or a live generator.

Keys:
    arrow keys   point the tip (TIP) up / down / left / right
    space        flip the sweep direction
    P            pause / resume
    , / .        step one frame back / forward (while paused)
    + / -        faster / slower scroll (pixels per frame)
    G            LED gaps on / off
    Esc / Q      quit
"""

import importlib
import itertools
import time
from collections import deque
from pathlib import Path

import pygame

from image_frames import check_orientation
from sequence import FrameSequence
from preview import simulate_flow
from preview_window import turn, screen_limits, to_surface


# ============================================================
# EASY CONTROLS
# ============================================================

# A saved sequence (.png strip with a .json next to it),
# or None to run GENERATOR live.
INPUT_FILE = None

# A module in generators/, and its settings.
GENERATOR = "perlin"
GENERATOR_SETTINGS = {
    "seed": 42,
    "palette": "industrialSun",
    "x_scale": 0.01,
    "y_scale": 0.01,
}

# Generators only. Sequences play at their own fps.
FPS = 40

TIP = "up"
SWEEP = "right"

# Pixels per LED along the wand (shrunk if the wand won't fit).
LED_SIZE = 8

# Draw the LEDs as streaks with dark gaps between them,
# like the wand itself. Toggle with G.
LED_GAPS = True
LED_DOT_FRACTION = 0.4     # streak width as a fraction of LED_SIZE

# Scroll speed: how far the trail moves per frame (simulated
# wand speed). Change with + / -.
PIXELS_PER_FRAME = 2

# Length of the window along the sweep, in pixels
# (shrunk to fit the screen). Trail seconds =
# TRAIL_PIXELS / PIXELS_PER_FRAME / fps.
TRAIL_PIXELS = 1200

NUM_LEDS = 100


# ============================================================
# SOURCE
# ============================================================

def open_source():
    """
    Returns (frames, fps, length, first, name). frames is an
    endless iterator; length is the sequence length (None for
    a generator); first is the number of the first frame.
    """
    if INPUT_FILE:
        sequence = FrameSequence.load(INPUT_FILE)
        return (
            itertools.cycle(sequence.frames),
            sequence.fps,
            len(sequence),
            0,
            Path(INPUT_FILE).stem
        )

    module = importlib.import_module(f"generators.{GENERATOR}")

    settings = dict(GENERATOR_SETTINGS)
    settings.setdefault("num_leds", NUM_LEDS)

    return (
        module.frames(**settings),
        FPS,
        None,
        settings.get("start", 0),
        GENERATOR
    )


# ============================================================
# VIEWER
# ============================================================

def main():
    source, fps, length, first, name = open_source()
    tip, sweep = check_orientation(TIP, SWEEP)

    px_per_frame = PIXELS_PER_FRAME
    gaps = LED_GAPS
    paused = False

    history = deque()   # (frame number, frame), oldest first
    taken = 0           # frames taken from the source so far
    back = 0            # frames stepped back while paused

    pygame.init()
    max_w, max_h = screen_limits()
    font = pygame.font.Font(None, 24)
    screen = None

    def layout():
        """LED size, trail length in frames, and window size."""
        vertical = tip in ("up", "down")
        wand_max, trail_max = (max_h, max_w) if vertical else (max_w, max_h)

        led_size = max(1, min(LED_SIZE, wand_max // NUM_LEDS))
        trail_frames = max(1, min(TRAIL_PIXELS, trail_max) // px_per_frame)

        wand_px = NUM_LEDS * led_size
        trail_px = trail_frames * px_per_frame
        size = (trail_px, wand_px) if vertical else (wand_px, trail_px)

        return led_size, trail_frames, size

    led_size, trail_frames, size = layout()

    def take():
        """Pull the next frame from the source."""
        nonlocal taken

        frame = next(source)
        number = taken % length if length else first + taken
        history.append((number, frame))
        taken += 1

        # Keep one extra screen of history for stepping back.
        while len(history) > 2 * trail_frames:
            history.popleft()

    def draw():
        nonlocal screen

        if screen is None or screen.get_size() != size:
            screen = pygame.display.set_mode(size)

        visible = list(history)[:len(history) - back]

        image = simulate_flow(
            [frame for _, frame in visible],
            tip=tip,
            sweep=sweep,
            trail_frames=trail_frames,
            px_per_frame=px_per_frame,
            led_size=led_size,
            led_gaps=gaps,
            led_dot_fraction=LED_DOT_FRACTION
        )
        screen.blit(to_surface(image), (0, 0))

        number = visible[-1][0]
        label = f"frame {number}"
        if length:
            label += f" / {length}"
        label += f"   {number / fps:.2f} s"
        if paused:
            label += "   PAUSED"
            if back:
                label += f" ({back} back)"

        text = font.render(label, True, (255, 255, 255))
        box = text.get_rect(topleft=(8, 8)).inflate(10, 6)
        pygame.draw.rect(screen, (0, 0, 0), box)
        screen.blit(text, (8, 8))

        pygame.display.set_caption(
            f"Flow  |  {name}  |  TIP={tip} SWEEP={sweep}  |  "
            f"{px_per_frame} px/frame, trail "
            f"{trail_frames / fps:.1f} s  |  {fps} fps  |  "
            f"gaps {'on' if gaps else 'off'}"
        )
        pygame.display.flip()

    # Same absolute clock as LightWand.play / stream: frame i
    # is due at start_time + i / fps.
    take()
    start_time = time.perf_counter()

    clock = pygame.time.Clock()
    dirty = True
    running = True

    while running:

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.WINDOWEXPOSED:
                dirty = True

            elif event.type == pygame.KEYDOWN:
                key = event.key
                new = turn(key, tip, sweep)

                if key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False

                elif new is not None:
                    tip, sweep = new

                elif key == pygame.K_p:
                    paused = not paused
                    if not paused:
                        back = 0
                        start_time = time.perf_counter() - (taken - 1) / fps

                elif key == pygame.K_PERIOD and paused:
                    if back > 0:
                        back -= 1
                    else:
                        take()

                elif key == pygame.K_COMMA and paused:
                    back = min(back + 1, len(history) - 1)

                elif key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    px_per_frame = min(32, px_per_frame + 1)

                elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    px_per_frame = max(1, px_per_frame - 1)

                elif key == pygame.K_g:
                    gaps = not gaps

                led_size, trail_frames, size = layout()
                dirty = True

        if not paused:
            due = int((time.perf_counter() - start_time) * fps) + 1

            # A slow generator falls behind: slow down rather
            # than skip frames.
            if due - taken > fps:
                start_time = time.perf_counter() - (taken - 1) / fps
                due = taken + 1

            while taken < due:
                take()
                dirty = True

        if dirty:
            draw()
            dirty = False

        clock.tick(120)

    pygame.quit()


if __name__ == "__main__":
    main()
