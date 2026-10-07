"""
Paint: one fixed-length exposure of an image or a saved sequence,
for a long-exposure photo. On the screen, on the wand, or both.

OUTPUT = "screen": preview the photo. A simulated long exposure
    (LED gaps, sweep length, mode) to adjust before shooting.
    No wand needed.
OUTPUT = "wand": paint it. Prints the setup, waits for ENTER,
    then counts down with beeps and plays REPEATS_PER_MODE passes
    in sync with the camera.
OUTPUT = "both": preview first. Adjust TIP / SWEEP / mode / sweep
    length with the keys, then press ENTER in the window to paint
    exactly that. The window closes while painting and comes back
    afterwards, to adjust and shoot again.

    python paint.py                          uses INPUT_FILE and OUTPUT below
    python paint.py path/to/file             that image or sequence instead
    python paint.py ... --output screen      override OUTPUT

Keys (screen / both):
    arrow keys   point the tip (TIP) up / down / left / right
    space        flip the sweep direction
    + / -        longer / shorter sweep (2 in steps)
    R            reset sweep to correct proportions
    G            LED gaps on / off
    B            diffusion blur on / off
    M            next mode (full_field, sparse_random, sparse_noise, bands)
    S            save the preview as a PNG (in ../previews/)
    ENTER        paint it (both only)
    Esc / Q      quit
"""

import argparse
import threading
import time
from pathlib import Path

import pygame

import frame_effects
from image_frames import check_orientation, load_input, input_frames
from lightwand import LightWand
from preview import simulate_paint
from preview_window import turn, screen_limits, fit_size, to_surface

try:
    import winsound
except ImportError:
    winsound = None  # not on Windows: countdown prints only


# ============================================================
# EASY CONTROLS
# ============================================================

# "screen", "wand" or "both"
OUTPUT = "screen"

# An image, or a saved sequence (a .png strip with a .json next to it,
# e.g. a snapshot from generate.py). Sequences are painted as-is:
# they're already wand frames, so TIP / SWEEP don't change them.
INPUT_FILE = "../images/jinx.jpg"

# Images: always a number.
# Sequences: None = the sequence's own length (frames / its fps);
# a number stretches or squeezes it to that many seconds.
EXPOSURE_SECONDS = 3

# Number of image slices shown each second (images only).
FPS = 100

# How the wand is held and moved, as seen by the CAMERA.
#   TIP:   where the tip (pixel 0) points  - "up", "down", "left", "right"
#   SWEEP: which way the wand moves        - "right", "left", "down", "up"
# SWEEP must be across the wand. Examples:
#   vertical wand:   TIP = "up",   SWEEP = "right"  (old REVERSE = False)
#                    TIP = "up",   SWEEP = "left"   (old REVERSE = True)
#   horizontal wand: TIP = "left", SWEEP = "down"
TIP = "left"
SWEEP = "down"

# Length of the lit part of the wand (LED 1 to LED 100), in inches.
# Used to print how far to sweep for correct proportions.
LIT_LENGTH_INCHES = 39

# One mode at a time (see frame_effects.py and MODE CONTROLS below):
#   "full_field"
#   "sparse_random"
#   "sparse_noise"
#   "bands"
MODE = "full_field"

# ---- shoot (wand / both) ----

DELAY_BEFORE_START_SECONDS = 12.5

REPEATS_PER_MODE = 3

# Match the camera's interval between shots.
PAUSE_BETWEEN_PASSES = 1.0

# Countdown beeps: short beeps at 3, 2, 1, then a long "go" beep.
# Start moving on "go". Beeps never shift the frame timing, so the
# passes stay in sync with the camera. Beeps that don't fit in the
# pause are skipped (a 1 s pause gets only "go").
BEEP_COUNTDOWN = True
COUNTDOWN_BEEPS = 3

# How long before the first frame "go" sounds, so the wand is already
# moving when the image starts. Top of image squeezed -> increase.
# Top of image missing -> decrease.
LEAD_IN_SECONDS = 0.8

# If True, send black between passes.
BLANK_BETWEEN_PASSES = True

# ---- wand (wand / both) ----

# None = find the wand on the network automatically.
WAND_IP = None

# Wand output brightness (0.0 - 1.0).
# Keep this high and dim the photo with aperture / ISO / ND filter.
# Low values leave only a few color levels per LED: gradients get
# steppy, hues shift, and at very low values (~0.1) you get banding.
WAND_BRIGHTNESS = 0.25

# LED gamma correction: 2.2 makes the photo's colors match the
# source image (and the preview); 1.0 = off. Gamma also squeezes
# the dark levels, which adds to the low-brightness problem above:
# at 0.25 with gamma 2.2 each channel has far fewer levels. Next
# shoot: compare against a higher WAND_BRIGHTNESS with the camera
# stopped down. See DESIGN.md §5.3.
WAND_GAMMA = 2.2

# ---- preview (screen / both) ----

# How far the wand travels, in inches. None = correct proportions.
# In "both", a sweep set with + / - is the distance printed for the shoot.
SWEEP_INCHES = None

PIXELS_PER_INCH = 15

LED_GAPS = True
LED_DOT_FRACTION = 0.4     # streak width as a fraction of LED spacing

BLUR_INCHES = 0.3          # used when blur is switched on (B)
BLUR_ON = False

GAIN = 1.0

SAVE_FOLDER = "../previews"

NUM_LEDS = 100


# ============================================================
# MODE CONTROLS
# ============================================================

# ---- sparse_random ----
SPARSE_RANDOM_MIN_PERCENT = 0.10   # 10%
SPARSE_RANDOM_MAX_PERCENT = 0.25   # 25%
SPARSE_RANDOM_SEED = 12345         # deterministic across repeats

# ---- sparse_noise ----
NOISE_THRESHOLD = 0.55             # higher = sparser
NOISE_SOFT_EDGE = 0.08             # dim halo below threshold
NOISE_X_SCALE = 0.08
NOISE_Y_SCALE = 0.14
NOISE_SEED = 999

# ---- bands ----
BAND_COUNT = 3
BAND_HALF_WIDTH = 2.5
BAND_BACKGROUND = 0.00             # 0.0 = only bands, 0.1 = faint full image behind
BAND_CYCLE_1 = 1.30                # how many wave cycles across the full image
BAND_CYCLE_2 = 0.90
BAND_CYCLE_3 = 1.70


# ============================================================
# FRAMES
# ============================================================

def mode_settings(mode):
    """Settings for a mode, from MODE CONTROLS above."""
    return {
        "sparse_random": dict(
            min_percent=SPARSE_RANDOM_MIN_PERCENT,
            max_percent=SPARSE_RANDOM_MAX_PERCENT,
            seed=SPARSE_RANDOM_SEED,
        ),
        "sparse_noise": dict(
            threshold=NOISE_THRESHOLD,
            soft_edge=NOISE_SOFT_EDGE,
            x_scale=NOISE_X_SCALE,
            y_scale=NOISE_Y_SCALE,
            seed=NOISE_SEED,
        ),
        "bands": dict(
            count=BAND_COUNT,
            half_width=BAND_HALF_WIDTH,
            background=BAND_BACKGROUND,
            cycles=(BAND_CYCLE_1, BAND_CYCLE_2, BAND_CYCLE_3),
        ),
    }.get(mode, {})


def apply_mode(frames, mode):
    # Each mode depends only on the frame and its position,
    # so apply it to every frame up front.
    return frame_effects.apply(frames, mode, **mode_settings(mode))


def exposure_for(sequence):
    """
    EXPOSURE_SECONDS, or for a sequence with None, its own
    length (frames / its fps).
    """
    if sequence is not None and EXPOSURE_SECONDS is None:
        return sequence.duration

    if EXPOSURE_SECONDS is None:
        raise ValueError("EXPOSURE_SECONDS must be a number for an image")

    return EXPOSURE_SECONDS


def prepare_frames(image, sequence, exposure, tip, sweep):
    """
    Frames from an image or a saved sequence (no mode applied),
    plus the sweep/wand ratio that gives correct proportions.
    """
    # Images: one frame per slice. Sequences keep their frames.
    num_slices = max(
        1,
        round(exposure * FPS)
    )

    return input_frames(
        image,
        sequence,
        tip,
        sweep,
        num_slices,
        NUM_LEDS
    )


# ============================================================
# COUNTDOWN
# ============================================================

def sleep_until(target_time):
    remaining = target_time - time.perf_counter()

    if remaining > 0:
        time.sleep(remaining)


def beep(frequency, duration_ms):
    if winsound is None:
        return

    # winsound.Beep blocks, so play it in the background
    # to keep the countdown and frame timing exact.
    threading.Thread(
        target=winsound.Beep,
        args=(frequency, duration_ms),
        daemon=True
    ).start()


def wait_for_start(start_time):
    """
    Wait until start_time (the first frame), beeping a
    countdown before it. "Go" sounds LEAD_IN_SECONDS early.
    start_time itself never moves, so camera sync is kept.
    """
    if BEEP_COUNTDOWN:
        go_time = start_time - LEAD_IN_SECONDS

        for count in range(COUNTDOWN_BEEPS, 0, -1):
            beep_time = go_time - count

            # Not enough time left for this beep: skip it.
            if beep_time < time.perf_counter():
                continue

            sleep_until(beep_time)
            beep(880, 150)
            print(f"{count}...")

        if go_time >= time.perf_counter():
            sleep_until(go_time)
            beep(1320, 500)
            print("GO")

    sleep_until(start_time)


# ============================================================
# SHOOT (wand)
# ============================================================

def display_frames(wand, frames, exposure, mode, start_delay):

    width = len(frames)
    height = len(frames[0])

    print(f"Image size: {width} x {height}")
    print(f"Exposure: {exposure:.2f} seconds")
    print(f"Slices: {width}")
    print(f"Slice rate: {width / exposure:.1f} fps")
    print(f"Mode: {mode}")
    print(f"Repeats: {REPEATS_PER_MODE}")
    print(f"Pause between passes: {PAUSE_BETWEEN_PASSES:.2f} sec")
    print(f"Blank between passes: {BLANK_BETWEEN_PASSES}")

    frames = apply_mode(frames, mode)

    for repeat_index in range(REPEATS_PER_MODE):

        print(f"\nPass {repeat_index + 1} / {REPEATS_PER_MODE}")

        delay = (
            start_delay
            if repeat_index == 0
            else PAUSE_BETWEEN_PASSES
        )

        wait_for_start(time.perf_counter() + delay)

        actual_time = wand.play(frames, seconds=exposure)

        print(f"Completed in {actual_time:.3f} sec")

        # Between-pass behavior. The pause itself happens
        # in wait_for_start at the start of the next pass.
        if repeat_index < (REPEATS_PER_MODE - 1):
            if BLANK_BETWEEN_PASSES:
                wand.blackout()

    wand.blackout()


def shoot(wand, image, sequence, exposure, view, ask_enter):
    """
    Print the setup, optionally wait for ENTER, then paint.
    view holds tip, sweep, mode and sweep_in (None = proportions).
    """
    tip, sweep, mode = view["tip"], view["sweep"], view["mode"]

    frames, sweep_ratio = prepare_frames(image, sequence, exposure, tip, sweep)

    sweep_inches = view["sweep_in"] or LIT_LENGTH_INCHES * sweep_ratio
    proportions = (
        "for correct proportions." if not view["sweep_in"]
        else "(as set in the preview)."
    )

    print()
    print("Ready.")
    print(
        f"Mode: {mode}"
    )
    print(
        f"Hold the wand with the tip pointing {tip} "
        f"(as seen by the camera)."
    )
    print(
        f"Open shutter and move wand "
        f"{sweep} in {exposure} seconds."
    )
    print(
        f"Sweep about {sweep_inches:.0f} in "
        f"(~{sweep_inches / exposure:.1f} in/s) "
        f"{proportions}"
    )
    print(
        f"Camera should be set for "
        f"{REPEATS_PER_MODE} shots."
    )

    if ask_enter:
        input("Press ENTER to start...")

    display_frames(
        wand,
        frames,
        exposure,
        mode,
        DELAY_BEFORE_START_SECONDS
    )


# ============================================================
# PREVIEW (screen)
# ============================================================

def preview(image, sequence, exposure, input_file, view, allow_paint):
    """
    The paint preview window. Changes to tip / sweep / mode /
    sweep length / gaps / blur are kept in view. Returns
    "paint" (ENTER, only if allow_paint) or "quit".
    """
    pygame.init()
    max_w, max_h = screen_limits()
    screen = pygame.display.set_mode((800, 600))

    def render():
        frames, ratio = prepare_frames(
            image, sequence, exposure, view["tip"], view["sweep"]
        )
        frames = apply_mode(frames, view["mode"])

        sweep_in = view["sweep_in"]
        actual_sweep = sweep_in if sweep_in else LIT_LENGTH_INCHES * ratio

        rendered = simulate_paint(
            frames,
            tip=view["tip"],
            sweep=view["sweep"],
            lit_length_in=LIT_LENGTH_INCHES,
            sweep_in=actual_sweep,
            px_per_inch=PIXELS_PER_INCH,
            led_gaps=view["gaps"],
            led_dot_fraction=LED_DOT_FRACTION,
            blur_in=BLUR_INCHES if view["blur"] else 0.0,
            gain=GAIN
        )

        pygame.display.set_caption(
            f"Paint preview  |  TIP={view['tip']} SWEEP={view['sweep']}  |  "
            f"sweep {actual_sweep:.0f} in"
            f"{' (auto)' if not sweep_in else ''}  |  "
            f"gaps {'on' if view['gaps'] else 'off'}  "
            f"blur {'on' if view['blur'] else 'off'}  |  "
            f"mode {view['mode']}"
            f"{'  |  ENTER = paint' if allow_paint else ''}"
        )

        return rendered, actual_sweep

    def show(rendered):
        nonlocal screen
        size = fit_size(rendered.width, rendered.height, max_w, max_h)
        if screen.get_size() != size:
            screen = pygame.display.set_mode(size)

        screen.blit(to_surface(rendered, size), (0, 0))
        pygame.display.flip()

    rendered, actual_sweep = render()
    show(rendered)

    action = "quit"

    while True:
        event = pygame.event.wait()
        changed = False

        if event.type == pygame.QUIT:
            break

        if event.type == pygame.VIDEORESIZE or event.type == pygame.WINDOWEXPOSED:
            show(rendered)
            continue

        if event.type != pygame.KEYDOWN:
            continue

        key = event.key

        if key in (pygame.K_ESCAPE, pygame.K_q):
            break

        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER) and allow_paint:
            action = "paint"
            break

        elif turn(key, view["tip"], view["sweep"]) is not None:
            new = turn(key, view["tip"], view["sweep"])
            changed = new != (view["tip"], view["sweep"])
            view["tip"], view["sweep"] = new

        elif key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            view["sweep_in"] = (view["sweep_in"] or actual_sweep) + 2
            changed = True

        elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            view["sweep_in"] = max(2, (view["sweep_in"] or actual_sweep) - 2)
            changed = True

        elif key == pygame.K_r:
            view["sweep_in"] = None
            changed = True

        elif key == pygame.K_g:
            view["gaps"] = not view["gaps"]
            changed = True

        elif key == pygame.K_b:
            view["blur"] = not view["blur"]
            changed = True

        elif key == pygame.K_m:
            modes = frame_effects.MODES
            view["mode"] = modes[(modes.index(view["mode"]) + 1) % len(modes)]
            changed = True

        elif key == pygame.K_s:
            folder = Path(SAVE_FOLDER)
            folder.mkdir(parents=True, exist_ok=True)
            name = (
                f"{Path(input_file).stem}_{view['tip']}_{view['sweep']}_"
                f"{actual_sweep:.0f}in"
                f"{'' if view['mode'] == 'full_field' else '_' + view['mode']}.png"
            )
            rendered.save(folder / name)
            print(f"Saved {folder / name}")

        if changed:
            rendered, actual_sweep = render()
            show(rendered)

    # Close the window: painting blocks for the whole countdown
    # and exposure, and a window that doesn't respond that long
    # gets marked "Not responding".
    pygame.quit()

    return action


# ============================================================
# MAIN
# ============================================================

def main(argv=None):
    parser = argparse.ArgumentParser(description="Paint an image or sequence.")
    parser.add_argument("path", nargs="?", default=None,
                        help="image or sequence (default: INPUT_FILE)")
    parser.add_argument("--output", choices=("screen", "wand", "both"),
                        default=None, help="override OUTPUT")
    args = parser.parse_args(argv)

    input_file = args.path or INPUT_FILE
    output = args.output or OUTPUT

    if output not in ("screen", "wand", "both"):
        raise ValueError(f"Unknown OUTPUT: {output}")

    image, sequence = load_input(input_file)
    exposure = exposure_for(sequence)

    tip, sweep = check_orientation(TIP, SWEEP)

    view = {
        "tip": tip,
        "sweep": sweep,
        "mode": MODE,
        "sweep_in": SWEEP_INCHES,
        "gaps": LED_GAPS,
        "blur": BLUR_ON,
    }

    if output == "screen":
        preview(image, sequence, exposure, input_file, view, allow_paint=False)
        return

    wand = LightWand(
        ip=WAND_IP,
        num_leds=NUM_LEDS,
        brightness=WAND_BRIGHTNESS,
        gamma=WAND_GAMMA
    )

    try:
        if output == "wand":
            shoot(wand, image, sequence, exposure, view, ask_enter=True)
            return

        # both: preview, paint on ENTER, back to the preview.
        while preview(
            image, sequence, exposure, input_file, view, allow_paint=True
        ) == "paint":
            shoot(wand, image, sequence, exposure, view, ask_enter=False)
            print("\nBack to the preview (Esc to quit).")

    except KeyboardInterrupt:
        print("\nStopping...")

    finally:
        wand.close()


if __name__ == "__main__":
    main()
