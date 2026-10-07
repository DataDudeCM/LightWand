"""
Paint preview: see roughly what the photo will look like before
shooting. No wand needed.

Keys:
    arrow keys   point the tip (TIP) up / down / left / right
    space        flip the sweep direction
    + / -        longer / shorter sweep (2 in steps)
    R            reset sweep to correct proportions
    G            LED gaps on / off
    B            diffusion blur on / off
    S            save the preview as a PNG (in ../previews/)
    Esc / Q      quit
"""

from pathlib import Path

import pygame
from PIL import Image

from image_frames import orient, to_frames, check_orientation
from sequence import FrameSequence
from preview import simulate_paint


# ============================================================
# EASY CONTROLS
# ============================================================

# An image, or a saved sequence (a .png strip with a .json next to it).
INPUT_FILE = "../images/jinx.jpg"

# For images: slices = EXPOSURE_SECONDS * FPS, as in image_paint.
EXPOSURE_SECONDS = 3
FPS = 100

TIP = "left"
SWEEP = "down"

# Length of the lit part of the wand (LED 1 to LED 100), in inches.
LIT_LENGTH_INCHES = 39

# How far the wand travels, in inches. None = correct proportions.
SWEEP_INCHES = None

PIXELS_PER_INCH = 15

LED_GAPS = True
LED_DOT_FRACTION = 0.4     # streak width as a fraction of LED spacing

BLUR_INCHES = 0.3          # used when blur is switched on (B)
BLUR_ON = False

GAIN = 1.0

NUM_LEDS = 100
SAVE_FOLDER = "../previews"


# ============================================================
# LOADING
# ============================================================

def load_input(path):
    """
    Returns (source_image, sequence). Exactly one is set:
    a plain image is oriented per render; a sequence is already
    in the standard layout.
    """
    path = Path(path)

    if path.with_suffix(".json").exists():
        return None, FrameSequence.load(path)

    return Image.open(path).convert("RGB"), None


def frames_and_ratio(source, sequence, tip, sweep):
    """
    Frames in playback order, plus the sweep/wand ratio that
    gives correct proportions.
    """
    if sequence is not None:
        return sequence.frames, len(sequence) / sequence.num_leds

    image = orient(source, tip, sweep)
    width, height = image.size
    num_slices = max(1, round(EXPOSURE_SECONDS * FPS))

    return to_frames(image, num_slices, NUM_LEDS), width / height


# ============================================================
# VIEWER
# ============================================================

PERPENDICULAR = {
    "up": ("right", "left"),
    "down": ("right", "left"),
    "left": ("down", "up"),
    "right": ("down", "up"),
}

ARROWS = {
    pygame.K_UP: "up",
    pygame.K_DOWN: "down",
    pygame.K_LEFT: "left",
    pygame.K_RIGHT: "right",
}


def main():
    source, sequence = load_input(INPUT_FILE)
    tip, sweep = check_orientation(TIP, SWEEP)

    sweep_in = SWEEP_INCHES          # None = auto
    gaps = LED_GAPS
    blur = BLUR_ON

    pygame.init()
    screen_info = pygame.display.Info()
    max_w = int(screen_info.current_w * 0.85)
    max_h = int(screen_info.current_h * 0.85)
    screen = pygame.display.set_mode((800, 600))

    def render():
        frames, ratio = frames_and_ratio(source, sequence, tip, sweep)
        actual_sweep = sweep_in if sweep_in else LIT_LENGTH_INCHES * ratio

        image = simulate_paint(
            frames,
            tip=tip,
            sweep=sweep,
            lit_length_in=LIT_LENGTH_INCHES,
            sweep_in=actual_sweep,
            px_per_inch=PIXELS_PER_INCH,
            led_gaps=gaps,
            led_dot_fraction=LED_DOT_FRACTION,
            blur_in=BLUR_INCHES if blur else 0.0,
            gain=GAIN
        )

        pygame.display.set_caption(
            f"Paint preview  |  TIP={tip} SWEEP={sweep}  |  "
            f"sweep {actual_sweep:.0f} in"
            f"{' (auto)' if not sweep_in else ''}  |  "
            f"gaps {'on' if gaps else 'off'}  blur {'on' if blur else 'off'}"
        )

        return image, actual_sweep

    def show(image):
        nonlocal screen
        scale = min(max_w / image.width, max_h / image.height, 1.0)
        size = (
            max(1, int(image.width * scale)),
            max(1, int(image.height * scale))
        )
        if screen.get_size() != size:
            screen = pygame.display.set_mode(size)

        shown = image.resize(size, Image.Resampling.LANCZOS)
        surface = pygame.image.fromstring(shown.tobytes(), size, "RGB")
        screen.blit(surface, (0, 0))
        pygame.display.flip()

    image, actual_sweep = render()
    show(image)

    running = True

    while running:
        event = pygame.event.wait()
        changed = False

        if event.type == pygame.QUIT:
            break

        if event.type == pygame.VIDEORESIZE or event.type == pygame.WINDOWEXPOSED:
            show(image)
            continue

        if event.type != pygame.KEYDOWN:
            continue

        key = event.key

        if key in (pygame.K_ESCAPE, pygame.K_q):
            running = False

        elif key in ARROWS:
            new_tip = ARROWS[key]
            if new_tip != tip:
                # Keep the sweep across the wand.
                if sweep not in PERPENDICULAR[new_tip]:
                    sweep = PERPENDICULAR[new_tip][0]
                tip = new_tip
                changed = True

        elif key == pygame.K_SPACE:
            a, b = PERPENDICULAR[tip]
            sweep = b if sweep == a else a
            changed = True

        elif key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            sweep_in = (sweep_in or actual_sweep) + 2
            changed = True

        elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            sweep_in = max(2, (sweep_in or actual_sweep) - 2)
            changed = True

        elif key == pygame.K_r:
            sweep_in = None
            changed = True

        elif key == pygame.K_g:
            gaps = not gaps
            changed = True

        elif key == pygame.K_b:
            blur = not blur
            changed = True

        elif key == pygame.K_s:
            folder = Path(SAVE_FOLDER)
            folder.mkdir(parents=True, exist_ok=True)
            name = (
                f"{Path(INPUT_FILE).stem}_{tip}_{sweep}_"
                f"{actual_sweep:.0f}in.png"
            )
            image.save(folder / name)
            print(f"Saved {folder / name}")

        if changed:
            image, actual_sweep = render()
            show(image)

    pygame.quit()


if __name__ == "__main__":
    main()
