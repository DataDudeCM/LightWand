import socket
import time
import math
import random

# ============================================================
# EASY CONTROLS
# ============================================================

WAND_IP = "192.168.1.123"   # <-- change this
UDP_PORT = 7777

NUM_LEDS = 100
FPS = 60
PASS_SECONDS = 3.0          # how long one full image/effect pass lasts
GLOBAL_BRIGHTNESS = 0.18    # 0.0 to 1.0

# Determines how many seconds to wait after pressing ENTER
# -gives time to push the shutter release button on the camera
DELAY_BEFORE_START = 2.5

# Which mode to run:
#   "full_field"
#   "sparse_random"
#   "sparse_noise"
#   "bands"
#   "all"
MODE = "all"

# Repeat each mode this many times before moving to the next one.
# Great for multiple camera attempts.
REPEATS_PER_MODE = 3

# Delay between repeated passes of the same mode
INTER_PASS_DELAY = 0.25

# If True, briefly blank the wand between repeated passes
BLANK_BETWEEN_PASSES = True
BLANK_TIME = 0.08

# If MODE == "all", this controls the order
MODE_ORDER = ["full_field", "sparse_random", "sparse_noise", "bands"]

# ============================================================
# MODE-SPECIFIC CONTROLS
# ============================================================

# ---- sparse_random ----
RANDOM_ACTIVE_MIN = 10
RANDOM_ACTIVE_MAX = 25

# ---- sparse_noise ----
NOISE_THRESHOLD = 0.78      # higher = fewer LEDs on
NOISE_SOFT_EDGE = 0.08      # soft halo below threshold
NOISE_X_SCALE = 0.10
NOISE_Y_SCALE = 0.14

# ---- full_field ----
FULL_X_SCALE = 0.08
FULL_Y_SCALE = 0.10

# ---- moving bands ----
BAND_HALF_WIDTH = 2.2
BAND_SPEED_1 = 0.11
BAND_SPEED_2 = 0.07
BAND_SPEED_3 = 0.15

# ============================================================
# LOW-LEVEL HELPERS
# ============================================================

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def lerp(a, b, t):
    return a + (b - a) * t

def lerp_color(c1, c2, t):
    return (
        int(lerp(c1[0], c2[0], t)),
        int(lerp(c1[1], c2[1], t)),
        int(lerp(c1[2], c2[2], t)),
    )

def scale_color(rgb, scale):
    return tuple(int(clamp(c * scale, 0, 255)) for c in rgb)

def add_colors(c1, c2):
    return (
        int(clamp(c1[0] + c2[0], 0, 255)),
        int(clamp(c1[1] + c2[1], 0, 255)),
        int(clamp(c1[2] + c2[2], 0, 255)),
    )

def finalize_color(rgb, local_scale=1.0):
    return scale_color(rgb, GLOBAL_BRIGHTNESS * local_scale)

def black_frame():
    return [(0, 0, 0)] * NUM_LEDS

def send_frame(frame):
    """
    Frame is a list of (r,g,b) tuples of length NUM_LEDS.
    Sends raw RGB bytes in LED order.
    """
    payload = bytearray()
    for r, g, b in frame:
        payload.extend((r, g, b))
    sock.sendto(payload, (WAND_IP, UDP_PORT))

# ============================================================
# PALETTE
# ============================================================

def cool_palette(t):
    """
    t in [0,1]
    Blue -> purple -> near-white
    Similar to the feel of your recent image.
    """
    t = clamp(t, 0.0, 1.0)

    c_blue   = (40, 140, 255)
    c_purple = (170, 80, 255)
    c_white  = (255, 245, 255)

    if t < 0.55:
        u = t / 0.55
        return lerp_color(c_blue, c_purple, u)
    else:
        u = (t - 0.55) / 0.45
        return lerp_color(c_purple, c_white, u)

# ============================================================
# SIMPLE SMOOTH VALUE NOISE (Perlin-like without extra package)
# ============================================================

def smoothstep(t):
    return t * t * (3 - 2 * t)

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
# FRAME GENERATORS
# ============================================================

def frame_full_field(frame_idx, total_frames):
    """
    Dense field: almost all LEDs lit.
    Organic / curtain-like / topographic feel.
    """
    frame = []
    x = frame_idx * FULL_X_SCALE

    for y in range(NUM_LEDS):
        yy = y * FULL_Y_SCALE

        n1 = value_noise_2d(x, yy, seed=1)
        n2 = value_noise_2d(x * 1.9 + 50.0, yy * 2.2 + 100.0, seed=2)

        v = 0.72 * n1 + 0.28 * n2
        color = cool_palette(v)
        frame.append(finalize_color(color, 1.0))

    return frame

def frame_sparse_random(frame_idx, total_frames):
    """
    Random 10-25 LEDs active each slice.
    Chaotic / sparkly / glitchier.
    """
    frame = black_frame()

    rng = random.Random(1000 + frame_idx)  # deterministic per frame
    active_count = rng.randint(RANDOM_ACTIVE_MIN, RANDOM_ACTIVE_MAX)
    active_indices = rng.sample(range(NUM_LEDS), active_count)

    for y in active_indices:
        v = value_noise_2d(frame_idx * 0.13, y * 0.20, seed=5)
        local_scale = 0.65 + 0.35 * v
        frame[y] = finalize_color(cool_palette(v), local_scale)

    return frame

def frame_sparse_noise(frame_idx, total_frames):
    """
    Thresholded smooth noise:
    coherent drifting islands / filaments / clusters.
    This is likely the most interesting sparse mode.
    """
    frame = []

    x = frame_idx * NOISE_X_SCALE

    for y in range(NUM_LEDS):
        yy = y * NOISE_Y_SCALE
        n = value_noise_2d(x, yy, seed=9)

        if n >= NOISE_THRESHOLD:
            # Bright core above threshold
            local = 0.45 + 0.55 * ((n - NOISE_THRESHOLD) / max(1e-6, (1.0 - NOISE_THRESHOLD)))
            frame.append(finalize_color(cool_palette(n), local))
        elif n >= (NOISE_THRESHOLD - NOISE_SOFT_EDGE):
            # Dim halo just below threshold
            halo = (n - (NOISE_THRESHOLD - NOISE_SOFT_EDGE)) / NOISE_SOFT_EDGE
            frame.append(finalize_color(cool_palette(n), 0.15 * halo))
        else:
            frame.append((0, 0, 0))

    return frame

def frame_bands(frame_idx, total_frames):
    """
    Three drifting bands.
    More deliberate / graphic / wireframe-like.
    """
    frame = []

    p1 = 22 + 10 * math.sin(frame_idx * BAND_SPEED_1)
    p2 = 52 + 14 * math.sin(frame_idx * BAND_SPEED_2 + 1.7)
    p3 = 78 +  9 * math.sin(frame_idx * BAND_SPEED_3 + 3.0)

    band_colors = [
        cool_palette(0.20),   # blue
        cool_palette(0.55),   # purple
        cool_palette(0.95),   # near-white
    ]
    band_positions = [p1, p2, p3]

    for y in range(NUM_LEDS):
        accum = (0, 0, 0)

        for pos, base_color in zip(band_positions, band_colors):
            d = abs(y - pos)
            strength = max(0.0, 1.0 - (d / BAND_HALF_WIDTH))
            if strength > 0:
                accum = add_colors(accum, scale_color(base_color, strength))

        # Slight dim background from a weak field helps continuity
        bg = value_noise_2d(frame_idx * 0.05, y * 0.08, seed=13)
        bg_color = finalize_color(cool_palette(bg), 0.08)

        accum = add_colors(accum, bg_color)
        frame.append(finalize_color(accum, 1.0 / max(GLOBAL_BRIGHTNESS, 1e-6)))

    return frame

def generate_frame(mode_name, frame_idx, total_frames):
    if mode_name == "full_field":
        return frame_full_field(frame_idx, total_frames)
    elif mode_name == "sparse_random":
        return frame_sparse_random(frame_idx, total_frames)
    elif mode_name == "sparse_noise":
        return frame_sparse_noise(frame_idx, total_frames)
    elif mode_name == "bands":
        return frame_bands(frame_idx, total_frames)
    else:
        raise ValueError(f"Unknown mode: {mode_name}")

# ============================================================
# RUN LOGIC
# ============================================================

def run_mode(mode_name):
    frames_per_pass = max(1, int(PASS_SECONDS * FPS))
    print(f"\nMode: {mode_name}")
    print(f"  pass length: {PASS_SECONDS:.2f}s")
    print(f"  fps: {FPS}")
    print(f"  repeats: {REPEATS_PER_MODE}")
    print(f"  brightness: {GLOBAL_BRIGHTNESS}")

    for repeat_idx in range(REPEATS_PER_MODE):
        print(f"  repeat {repeat_idx + 1}/{REPEATS_PER_MODE}")

        start = time.perf_counter()

        for frame_idx in range(frames_per_pass):
            frame = generate_frame(mode_name, frame_idx, frames_per_pass)
            send_frame(frame)

            next_time = start + ((frame_idx + 1) / FPS)
            sleep_time = next_time - time.perf_counter()
            if sleep_time > 0:
                time.sleep(sleep_time)

        if repeat_idx < REPEATS_PER_MODE - 1:
            if BLANK_BETWEEN_PASSES:
                send_frame(black_frame())
                time.sleep(BLANK_TIME)
            if INTER_PASS_DELAY > 0:
                time.sleep(INTER_PASS_DELAY)

def main():
    if MODE == "all":
        modes = MODE_ORDER
    else:
        modes = [MODE]

    print("Starting wand variations...")
    print(f"Target: {WAND_IP}:{UDP_PORT}")
    print(f"LEDs: {NUM_LEDS}")
    print(f"Mode selection: {modes}")

    try:
        time.sleep(DELAY_BEFORE_START)
        for mode_name in modes:
            run_mode(mode_name)

    except KeyboardInterrupt:
        print("\nStopped by user.")

    finally:
        # turn off at the end
        send_frame(black_frame())
        print("Wand off.")

if __name__ == "__main__":
    main()