from lightwand import LightWand
from image_frames import check_orientation, load_input, input_frames
import frame_effects
import time
import threading

try:
    import winsound
except ImportError:
    winsound = None  # not on Windows: countdown prints only


# ============================================================
# EASY CONTROLS
# ============================================================

# An image, or a saved sequence (a .png strip with a .json next to it,
# e.g. a snapshot from preview_flow). Sequences are painted as-is:
# they're already wand frames, so TIP / SWEEP don't change them.
INPUT_FILE = "../images/jinx.jpg"

# Images: always a number.
# Sequences: None = the sequence's own length (frames / its fps);
# a number stretches or squeezes it to that many seconds.
EXPOSURE_SECONDS = 3
DELAY_BEFORE_START_SECONDS = 12.5

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

# One mode at a time (see frame_effects.py):
#   "full_field"
#   "sparse_random"
#   "sparse_noise"
#   "bands"
MODE = "full_field"

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

# Wand output brightness (0.0 - 1.0).
# Keep this high and dim the photo with aperture / ISO / ND filter.
# Low values leave only a few color levels per LED: gradients get
# steppy, hues shift, and at very low values (~0.1) you get banding.
WAND_BRIGHTNESS = 0.25


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
# WAND SETUP
# ============================================================

wand = LightWand(
    ip="192.168.1.8",
    port=7777,
    num_leds=100,
    brightness=WAND_BRIGHTNESS
)


# ============================================================
# FRAMES
# ============================================================

# Settings for each mode, from MODE CONTROLS above.
MODE_SETTINGS = {
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
}


def prepare_frames(filename, exposure, fps, tip, sweep):
    """
    Frames from an image or a saved sequence.

    Returns (frames, sweep_ratio, exposure). For a sequence,
    exposure None means its own length (frames / its fps).
    """
    image, sequence = load_input(filename)

    if sequence is not None and exposure is None:
        exposure = sequence.duration

    if exposure is None:
        raise ValueError("EXPOSURE_SECONDS must be a number for an image")

    # Images: one frame per slice. Sequences keep their frames.
    num_slices = max(
        1,
        round(exposure * fps)
    )

    frames, sweep_ratio = input_frames(
        image,
        sequence,
        tip,
        sweep,
        num_slices,
        wand.num_leds
    )

    return frames, sweep_ratio, exposure


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
# DISPLAY
# ============================================================

def display_frames(frames, exposure, mode, start_delay):

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

    # Each mode depends only on the frame and its position,
    # so apply it to every frame up front.
    frames = frame_effects.apply(
        frames,
        mode,
        **MODE_SETTINGS.get(mode, {})
    )

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


# ============================================================
# MAIN
# ============================================================

try:

    tip, sweep = check_orientation(TIP, SWEEP)

    frames, sweep_ratio, exposure = prepare_frames(
        INPUT_FILE,
        EXPOSURE_SECONDS,
        FPS,
        tip,
        sweep
    )

    sweep_inches = LIT_LENGTH_INCHES * sweep_ratio

    print()
    print("Ready.")
    print(
        f"Mode: {MODE}"
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
        f"for correct proportions."
    )
    print(
        f"Camera should be set for "
        f"{REPEATS_PER_MODE} shots."
    )

    input("Press ENTER to start...")

    display_frames(
        frames,
        exposure,
        MODE,
        DELAY_BEFORE_START_SECONDS
    )

finally:

    wand.close()