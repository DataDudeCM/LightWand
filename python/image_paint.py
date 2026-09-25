from PIL import Image
from lightwand import LightWand
import time
import math
import random


# ============================================================
# EASY CONTROLS
# ============================================================

IMAGE_FILE = "../images/jinx.jpg"

EXPOSURE_SECONDS = 3.5
DELAY_BEFORE_START_SECONDS = 12.5

# Number of image slices shown each second.
FPS = 100

REVERSE = False

# One mode at a time:
#   "full_field"
#   "sparse_random"
#   "sparse_noise"
#   "bands"
MODE = "sparse_noise"

REPEATS_PER_MODE = 3
PAUSE_BETWEEN_PASSES = 1.0

# If True, send black between passes.
BLANK_BETWEEN_PASSES = True

# Wand output brightness
WAND_BRIGHTNESS = 0.3


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
# HELPERS
# ============================================================

def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def scale_color(rgb, scale):
    return (
        int(clamp(rgb[0] * scale, 0, 255)),
        int(clamp(rgb[1] * scale, 0, 255)),
        int(clamp(rgb[2] * scale, 0, 255)),
    )


def add_colors(c1, c2):
    return (
        int(clamp(c1[0] + c2[0], 0, 255)),
        int(clamp(c1[1] + c2[1], 0, 255)),
        int(clamp(c1[2] + c2[2], 0, 255)),
    )


# ============================================================
# SIMPLE SMOOTH VALUE NOISE
# ============================================================

def smoothstep(t):
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def hash01(ix, iy, seed=0):
    n = ix * 374761393 + iy * 668265263 + seed * 1447
    n = (n ^ (n >> 13)) * 1274126177
    n = n ^ (n >> 16)
    return (n & 0xFFFFFFFF) / 0xFFFFFFFF


def value_noise_2d(x, y, seed=0):
    x0 = math.floor(x)
    y0 = math.floor(y)
    x1 = x0 + 1
    y1 = y0 + 1

    sx = smoothstep(x - x0)
    sy = smoothstep(y - y0)

    n00 = hash01(x0, y0, seed)
    n10 = hash01(x1, y0, seed)
    n01 = hash01(x0, y1, seed)
    n11 = hash01(x1, y1, seed)

    ix0 = lerp(n00, n10, sx)
    ix1 = lerp(n01, n11, sx)

    return lerp(ix0, ix1, sy)


# ============================================================
# IMAGE PREP
# ============================================================

def prepare_image(filename, exposure, fps):

    image = Image.open(filename).convert("RGB")

    # Every vertical slice must contain exactly
    # one pixel for every LED.
    target_height = wand.num_leds

    # Number of temporal slices we'll display.
    num_slices = max(
        1,
        round(exposure * fps)
    )

    image = image.resize(
        (num_slices, target_height),
        Image.Resampling.LANCZOS
    )

    return image


def get_column_pixels(image, x, reverse=False):
    width, height = image.size

    source_x = (
        width - 1 - x
        if reverse
        else x
    )

    pixels = []

    for y in range(height):
        r, g, b = image.getpixel((source_x, y))
        pixels.append((r, g, b))

    return pixels


# ============================================================
# MODE PROCESSING
# ============================================================

def apply_full_field(source_pixels, x, width):
    return source_pixels


def apply_sparse_random(source_pixels, x, width):
    frame = [(0, 0, 0)] * len(source_pixels)

    rng = random.Random(SPARSE_RANDOM_SEED + x)

    min_count = max(1, int(len(source_pixels) * SPARSE_RANDOM_MIN_PERCENT))
    max_count = max(min_count, int(len(source_pixels) * SPARSE_RANDOM_MAX_PERCENT))
    active_count = rng.randint(min_count, max_count)

    active_indices = rng.sample(range(len(source_pixels)), active_count)

    for y in active_indices:
        frame[y] = source_pixels[y]

    return frame


def apply_sparse_noise(source_pixels, x, width):
    frame = []

    nx = x * NOISE_X_SCALE

    for y, pixel in enumerate(source_pixels):
        ny = y * NOISE_Y_SCALE
        n = value_noise_2d(nx, ny, seed=NOISE_SEED)

        if n >= NOISE_THRESHOLD:
            strength = 0.45 + 0.55 * (
                (n - NOISE_THRESHOLD) /
                max(1e-6, (1.0 - NOISE_THRESHOLD))
            )
            frame.append(scale_color(pixel, strength))

        elif n >= (NOISE_THRESHOLD - NOISE_SOFT_EDGE):
            halo = (
                (n - (NOISE_THRESHOLD - NOISE_SOFT_EDGE)) /
                NOISE_SOFT_EDGE
            )
            frame.append(scale_color(pixel, 0.18 * halo))

        else:
            frame.append((0, 0, 0))

    return frame


def apply_bands(source_pixels, x, width):
    frame = []

    # normalized position through the image, 0..1
    t = 0.0 if width <= 1 else x / (width - 1)

    centers = [
        20 + 12 * math.sin((2 * math.pi * BAND_CYCLE_1 * t) + 0.0),
        50 + 16 * math.sin((2 * math.pi * BAND_CYCLE_2 * t) + 1.9),
        78 + 10 * math.sin((2 * math.pi * BAND_CYCLE_3 * t) + 3.7),
    ]

    centers = centers[:BAND_COUNT]

    for y, pixel in enumerate(source_pixels):
        strength = 0.0

        for c in centers:
            d = abs(y - c)
            s = max(0.0, 1.0 - (d / BAND_HALF_WIDTH))
            strength = max(strength, s)

        base = scale_color(pixel, BAND_BACKGROUND)

        if strength > 0:
            band_pixel = scale_color(pixel, strength)
            frame.append(add_colors(base, band_pixel))
        else:
            frame.append(base)

    return frame


def apply_mode(source_pixels, x, width, mode):
    if mode == "full_field":
        return apply_full_field(source_pixels, x, width)

    elif mode == "sparse_random":
        return apply_sparse_random(source_pixels, x, width)

    elif mode == "sparse_noise":
        return apply_sparse_noise(source_pixels, x, width)

    elif mode == "bands":
        return apply_bands(source_pixels, x, width)

    else:
        raise ValueError(f"Unknown MODE: {mode}")


# ============================================================
# DISPLAY
# ============================================================

def display_image(image, exposure, mode):

    width, height = image.size

    print(f"Image size: {width} x {height}")
    print(f"Exposure: {exposure:.2f} seconds")
    print(f"Slices: {width}")
    print(f"Slice rate: {width / exposure:.1f} fps")
    print(f"Mode: {mode}")
    print(f"Repeats: {REPEATS_PER_MODE}")
    print(f"Pause between passes: {PAUSE_BETWEEN_PASSES:.2f} sec")
    print(f"Blank between passes: {BLANK_BETWEEN_PASSES}")

    for repeat_index in range(REPEATS_PER_MODE):

        print(f"\nPass {repeat_index + 1} / {REPEATS_PER_MODE}")

        start_time = time.perf_counter()

        for x in range(width):

            source_pixels = get_column_pixels(
                image,
                x,
                reverse=REVERSE
            )

            pixels = apply_mode(
                source_pixels,
                x,
                width,
                mode
            )

            wand.pixels = pixels
            wand.show()

            # Absolute timing prevents accumulated
            # sleep errors from stretching the sequence.
            target_time = (
                start_time +
                ((x + 1) / width) * exposure
            )

            remaining = (
                target_time -
                time.perf_counter()
            )

            if remaining > 0:
                time.sleep(remaining)

        actual_time = (
            time.perf_counter() -
            start_time
        )

        print(f"Completed in {actual_time:.3f} sec")

        # Between-pass behavior
        if repeat_index < (REPEATS_PER_MODE - 1):
            if BLANK_BETWEEN_PASSES:
                wand.blackout()

            if PAUSE_BETWEEN_PASSES > 0:
                time.sleep(PAUSE_BETWEEN_PASSES)

    wand.blackout()


# ============================================================
# MAIN
# ============================================================

try:

    image = prepare_image(
        IMAGE_FILE,
        EXPOSURE_SECONDS,
        FPS
    )

    print()
    print("Ready.")
    print(
        f"Mode: {MODE}"
    )
    print(
        f"Open shutter and move wand "
        f"A → B in {EXPOSURE_SECONDS} seconds."
    )
    print(
        f"Camera should be set for "
        f"{REPEATS_PER_MODE} shots."
    )

    input("Press ENTER to start...")
    time.sleep(DELAY_BEFORE_START_SECONDS)

    display_image(
        image,
        EXPOSURE_SECONDS,
        MODE
    )

finally:

    wand.close()