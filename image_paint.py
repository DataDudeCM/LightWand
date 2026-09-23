import socket
import time
import math
import random
from PIL import Image

# ============================================================
# EASY CONTROLS
# ============================================================

WAND_IP = "192.168.1.123"   # <-- CHANGE THIS
UDP_PORT = 7777

IMAGE_PATH = "my_image.jpg"  # <-- CHANGE THIS
NUM_LEDS = 100

# Playback timing
EXPOSURE_SECONDS = 3.0       # how long one full image pass lasts
FPS = 60                     # slices per second
INITIAL_DELAY = 2.0          # seconds before playback starts
PAUSE_BETWEEN_PASSES = 0.75  # pause between repeats of the same mode
BLANK_BETWEEN_PASSES = True
BLANK_TIME = 0.0            # brief blank before next repeat - not really needed

# Brightness
GLOBAL_BRIGHTNESS = 0.20     # 0.0 to 1.0

# Mode options:
#   "full_field"
#   "sparse_random"
#   "sparse_noise"
#   "bands"
#   "all"
MODE = "all"

# If MODE="all", this is the order
MODE_ORDER = ["full_field", "sparse_random", "sparse_noise", "bands"]

# Number of times to repeat each mode
REPEATS_PER_MODE = 3

# Set True to keep cycling until Ctrl+C
LOOP_FOREVER = False

# ============================================================
# MODE-SPECIFIC CONTROLS
# ============================================================

# ---- sparse_random ----
SPARSE_RANDOM_MIN_PERCENT = 0.10   # 10%
SPARSE_RANDOM_MAX_PERCENT = 0.25   # 25%
SPARSE_RANDOM_SEED = 12345         # deterministic across repeats

# ---- sparse_noise ----
NOISE_THRESHOLD = 0.78             # higher = fewer pixels shown
NOISE_SOFT_EDGE = 0.08             # dim halo below threshold
NOISE_X_SCALE = 0.08
NOISE_Y_SCALE = 0.14
NOISE_SEED = 999

# ---- bands ----
BAND_COUNT = 3
BAND_HALF_WIDTH = 2.5
BAND_SPEED_1 = 0.18
BAND_SPEED_2 = 0.11
BAND_SPEED_3 = 0.23
BAND_BACKGROUND = 0.00             # faint source image behind bands (0.0 = none)

# ============================================================
# LOW-LEVEL HELPERS
# ============================================================

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

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

def apply_brightness(rgb, local_scale=1.0):
    return scale_color(rgb, GLOBAL_BRIGHTNESS * local_scale)

def send_frame(frame):
    """
    frame = list of (r,g,b) tuples, length NUM_LEDS
    Sends raw RGB bytes in LED order.
    """
    payload = bytearray()
    for r, g, b in frame:
        payload.extend((r, g, b))
    sock.sendto(payload, (WAND_IP, UDP_PORT))

def black_frame():
    return [(0, 0, 0)] * NUM_LEDS

def blank_wand(duration=0.0):
    send_frame(black_frame())
    if duration > 0:
        time.sleep(duration)

# ============================================================
# SIMPLE SMOOTH VALUE NOISE (no extra dependencies required)
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
# IMAGE LOADING / PREP
# ============================================================

def load_and_prepare_image(path, num_leds, width):
    img = Image.open(path).convert("RGB")

    # resize to (playback_width, NUM_LEDS)
    try:
        resample = Image.Resampling.LANCZOS
    except AttributeError:
        resample = Image.LANCZOS

    img = img.resize((width, num_leds), resample)
    return img

def get_column_pixels(img, x):
    """
    Returns one image column as a list of (r,g,b), top-to-bottom.
    """
    frame = []
    for y in range(NUM_LEDS):
        frame.append(img.getpixel((x, y)))
    return frame

# ============================================================
# FRAME MODES
# ============================================================

def frame_full_field(img, x):
    """
    Original image-paint behavior: show every pixel in the column.
    """
    source = get_column_pixels(img, x)
    return [apply_brightness(pixel, 1.0) for pixel in source]

def frame_sparse_random(img, x):
    """
    Keep only 10-25% of LEDs from this column.
    Deterministic per column, so repeats look the same.
    """
    source = get_column_pixels(img, x)
    frame = [(0, 0, 0)] * NUM_LEDS

    rng = random.Random(SPARSE_RANDOM_SEED + x)

    min_count = max(1, int(NUM_LEDS * SPARSE_RANDOM_MIN_PERCENT))
    max_count = max(min_count, int(NUM_LEDS * SPARSE_RANDOM_MAX_PERCENT))
    active_count = rng.randint(min_count, max_count)

    active_indices = rng.sample(range(NUM_LEDS), active_count)

    for y in active_indices:
        pixel = source[y]
        frame[y] = apply_brightness(pixel, 1.0)

    return frame

def frame_sparse_noise(img, x):
    """
    Use coherent noise as a mask to reveal only parts of the column.
    This tends to produce drifting islands/filaments/clusters.
    """
    source = get_column_pixels(img, x)
    frame = []

    nx = x * NOISE_X_SCALE

    for y in range(NUM_LEDS):
        ny = y * NOISE_Y_SCALE
        n = value_noise_2d(nx, ny, seed=NOISE_SEED)

        if n >= NOISE_THRESHOLD:
            # fully reveal source pixel
            strength = 0.45 + 0.55 * ((n - NOISE_THRESHOLD) / max(1e-6, (1.0 - NOISE_THRESHOLD)))
            frame.append(apply_brightness(source[y], strength))
        elif n >= (NOISE_THRESHOLD - NOISE_SOFT_EDGE):
            # dim halo
            halo = (n - (NOISE_THRESHOLD - NOISE_SOFT_EDGE)) / NOISE_SOFT_EDGE
            frame.append(apply_brightness(source[y], 0.18 * halo))
        else:
            frame.append((0, 0, 0))

    return frame

def frame_bands(img, x):
    """
    Reveal only portions of the source image through drifting horizontal bands.
    """
    source = get_column_pixels(img, x)
    frame = []

    # Moving band centers as a function of x
    centers = []
    centers.append(20 + 12 * math.sin(x * BAND_SPEED_1))
    centers.append(50 + 16 * math.sin(x * BAND_SPEED_2 + 1.9))
    centers.append(78 + 10 * math.sin(x * BAND_SPEED_3 + 3.7))

    # Use as many centers as BAND_COUNT requests
    centers = centers[:BAND_COUNT]

    for y in range(NUM_LEDS):
        strength = 0.0

        for c in centers:
            d = abs(y - c)
            s = max(0.0, 1.0 - (d / BAND_HALF_WIDTH))
            strength = max(strength, s)

        # Optional faint background
        base = apply_brightness(source[y], BAND_BACKGROUND)

        if strength > 0:
            band_pixel = apply_brightness(source[y], strength)
            frame.append(add_colors(base, band_pixel))
        else:
            frame.append(base)

    return frame

def generate_frame(img, x, mode_name):
    if mode_name == "full_field":
        return frame_full_field(img, x)
    elif mode_name == "sparse_random":
        return frame_sparse_random(img, x)
    elif mode_name == "sparse_noise":
        return frame_sparse_noise(img, x)
    elif mode_name == "bands":
        return frame_bands(img, x)
    else:
        raise ValueError(f"Unknown mode: {mode_name}")

# ============================================================
# PLAYBACK
# ============================================================

def play_mode(img, mode_name):
    width = img.width

    print(f"\nMode: {mode_name}")
    print(f"  columns / frames: {width}")
    print(f"  pass duration: {EXPOSURE_SECONDS:.2f}s")
    print(f"  fps: {FPS}")
    print(f"  repeats: {REPEATS_PER_MODE}")
    print(f"  brightness: {GLOBAL_BRIGHTNESS}")

    input(f"\nReady for mode '{mode_name}'. Press Enter to start...")
    if INITIAL_DELAY > 0:
        print(f"Waiting {INITIAL_DELAY:.1f}s...")
        time.sleep(INITIAL_DELAY)

    for repeat_idx in range(REPEATS_PER_MODE):
        print(f"  pass {repeat_idx + 1}/{REPEATS_PER_MODE}")

        start = time.perf_counter()

        for x in range(width):
            frame = generate_frame(img, x, mode_name)
            send_frame(frame)

            next_time = start + ((x + 1) / FPS)
            sleep_time = next_time - time.perf_counter()
            if sleep_time > 0:
                time.sleep(sleep_time)

        if repeat_idx < REPEATS_PER_MODE - 1:
            if BLANK_BETWEEN_PASSES:
                blank_wand(BLANK_TIME)
            if PAUSE_BETWEEN_PASSES > 0:
                time.sleep(PAUSE_BETWEEN_PASSES)

def get_modes_to_run():
    if MODE == "all":
        return MODE_ORDER
    return [MODE]

# ============================================================
# MAIN
# ============================================================

def main():
    total_columns = max(1, int(EXPOSURE_SECONDS * FPS))
    img = load_and_prepare_image(IMAGE_PATH, NUM_LEDS, total_columns)

    print("Starting image_paint.py")
    print(f"Target: {WAND_IP}:{UDP_PORT}")
    print(f"Image: {IMAGE_PATH}")
    print(f"Prepared image size: {img.width} x {img.height}")
    print(f"Mode setting: {MODE}")

    try:
        if LOOP_FOREVER:
            while True:
                for mode_name in get_modes_to_run():
                    play_mode(img, mode_name)
                    blank_wand(0.15)
        else:
            for mode_name in get_modes_to_run():
                play_mode(img, mode_name)
                blank_wand(0.15)

    except KeyboardInterrupt:
        print("\nStopped by user.")

    finally:
        blank_wand()
        print("Wand off.")

if __name__ == "__main__":
    main()