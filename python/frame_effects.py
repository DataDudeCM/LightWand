"""
Frame effects ("modes"): transform a whole list of frames.

Each effect takes frames (lists of num_leds (r, g, b), pixel 0 =
tip, in playback order) and returns new frames. They depend only
on each frame and its position, so they work on any source:
images, generator output, snapshots.

Usage:

    frames = frame_effects.apply(frames, "bands", count=2)

The defaults are the values image_paint has always used.
"""

import math
import random


MODES = ("full_field", "sparse_random", "sparse_noise", "bands")


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
# EFFECTS
# ============================================================

def full_field(frames):
    """Every pixel, unchanged."""
    return [list(frame) for frame in frames]


def sparse_random(
    frames,
    min_percent=0.10,
    max_percent=0.25,
    seed=12345
):
    """
    Each frame lights a random 10-25% of its pixels.
    Deterministic: the same seed gives the same pixels.
    """
    result = []

    for x, pixels in enumerate(frames):
        frame = [(0, 0, 0)] * len(pixels)

        rng = random.Random(seed + x)

        min_count = max(1, int(len(pixels) * min_percent))
        max_count = max(min_count, int(len(pixels) * max_percent))
        active_count = rng.randint(min_count, max_count)

        active_indices = rng.sample(range(len(pixels)), active_count)

        for y in active_indices:
            frame[y] = pixels[y]

        result.append(frame)

    return result


def sparse_noise(
    frames,
    threshold=0.55,
    soft_edge=0.08,
    x_scale=0.08,
    y_scale=0.14,
    seed=999
):
    """
    Pixels show only where a noise field is above threshold
    (higher = sparser), with a dim halo soft_edge below it.
    """
    result = []

    for x, pixels in enumerate(frames):
        frame = []

        nx = x * x_scale

        for y, pixel in enumerate(pixels):
            ny = y * y_scale
            n = value_noise_2d(nx, ny, seed=seed)

            if n >= threshold:
                strength = 0.45 + 0.55 * (
                    (n - threshold) /
                    max(1e-6, (1.0 - threshold))
                )
                frame.append(scale_color(pixel, strength))

            elif n >= (threshold - soft_edge):
                halo = (
                    (n - (threshold - soft_edge)) /
                    soft_edge
                )
                frame.append(scale_color(pixel, 0.18 * halo))

            else:
                frame.append((0, 0, 0))

        result.append(frame)

    return result


def bands(
    frames,
    count=3,
    half_width=2.5,
    background=0.0,
    cycles=(1.30, 0.90, 1.70)
):
    """
    Up to three bands that wave along the wand over the sweep.

    background: 0.0 = only bands, 0.1 = faint full image behind.
    cycles:     how many wave cycles each band makes across
                the whole sweep.
    """
    width = len(frames)
    result = []

    for x, pixels in enumerate(frames):
        frame = []

        # normalized position through the sweep, 0..1
        t = 0.0 if width <= 1 else x / (width - 1)

        centers = [
            20 + 12 * math.sin((2 * math.pi * cycles[0] * t) + 0.0),
            50 + 16 * math.sin((2 * math.pi * cycles[1] * t) + 1.9),
            78 + 10 * math.sin((2 * math.pi * cycles[2] * t) + 3.7),
        ]

        centers = centers[:count]

        for y, pixel in enumerate(pixels):
            strength = 0.0

            for c in centers:
                d = abs(y - c)
                s = max(0.0, 1.0 - (d / half_width))
                strength = max(strength, s)

            base = scale_color(pixel, background)

            if strength > 0:
                band_pixel = scale_color(pixel, strength)
                frame.append(add_colors(base, band_pixel))
            else:
                frame.append(base)

        result.append(frame)

    return result


EFFECTS = {
    "full_field": full_field,
    "sparse_random": sparse_random,
    "sparse_noise": sparse_noise,
    "bands": bands,
}


def apply(frames, mode="full_field", **settings):
    """Run the named effect on frames, with optional settings."""
    if mode not in EFFECTS:
        raise ValueError(
            f"Unknown MODE: {mode}. Choose from {', '.join(MODES)}"
        )

    return EFFECTS[mode](frames, **settings)
