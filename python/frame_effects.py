"""
Frame effects ("modes"): transform a whole list of frames.

Each effect takes frames (lists of num_leds (r, g, b), pixel 0 =
tip, in playback order) and returns new frames. They depend only
on each frame and its position, so they work on any source:
images, generator output, snapshots.

Usage:

    frames = frame_effects.apply(frames, "bands", count=2)

The defaults of the first four are the values image_paint (now
paint.py) has always used. noise_glow and palette_tint are for light
portraits (see docs/portrait-effects-plan.md).
"""

import math
import random

from opensimplex import OpenSimplex

from palette import PaletteLibrary, palette_color


MODES = (
    "full_field", "sparse_random", "sparse_noise", "bands",
    "noise_glow", "palette_tint",
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


def luminance(rgb):
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def noise_glow(
    frames,
    base_level=0.6,
    threshold=0.6,
    soft_edge=0.08,
    blob_size=0.15,
    peak_level=1.0,
    sparkle_chance=0.12,
    sparkle_color=None,
    sparkle_strength=0.6,
    subject_threshold=10,
    seed=7,
    sweep_ratio=None,
    pass_index=0,
):
    """
    Light-portrait glow: the image dimmed to base_level, brighter
    patches where a smooth noise field peaks, and sparkles inside them.

    base_level:        brightness outside the peaks (headroom: LEDs
                       top out at 255, so the peaks need room above).
    threshold:         noise height (0..1) where peaks start; higher =
                       fewer, smaller patches.
    soft_edge:         fade from base to peak below the threshold.
    blob_size:         patch size as a fraction of the wand length.
    peak_level:        brightness inside the peaks (above 1 = brighter
                       than the original, clipped at 255).
    sparkle_chance:    share of peak pixels that sparkle.
    sparkle_color:     None = the pixel's own color at full strength,
                       pushed toward white; or an (r, g, b).
    sparkle_strength:  how far toward white / sparkle_color.
    subject_threshold: pixels with brightness at or below this are
                       background: left as they are.
    sweep_ratio:       sweep length / wand length in the photo, so the
                       patches come out round (None = one frame per
                       LED spacing). paint.py passes it in.
    pass_index:        changes only the sparkles, e.g. per repeat pass.
    """
    num_frames = len(frames)
    if num_frames == 0:
        return []

    num_leds = len(frames[0])
    noise = OpenSimplex(seed=seed)

    # Photo distance per frame and per LED, in wand lengths.
    led_step = 1.0 / max(1, num_leds - 1)
    if sweep_ratio is None:
        frame_step = led_step
    else:
        frame_step = sweep_ratio / max(1, num_frames - 1)

    sparkle_seed = seed * 1009 + 31 + pass_index * 7919
    result = []

    for x, pixels in enumerate(frames):
        frame = []
        nx = x * frame_step / blob_size

        for y, pixel in enumerate(pixels):
            if luminance(pixel) <= subject_threshold:
                frame.append(tuple(pixel))
                continue

            n = (noise.noise2(nx, y * led_step / blob_size) + 1.0) / 2.0

            # 0 below the soft edge, 1 at and above the threshold.
            if soft_edge > 0:
                p = clamp((n - (threshold - soft_edge)) / soft_edge, 0.0, 1.0)
                p = smoothstep(p)
            else:
                p = 1.0 if n >= threshold else 0.0

            level = base_level + (peak_level - base_level) * p
            out = scale_color(pixel, level)

            if p >= 0.999 and hash01(x, y, sparkle_seed) < sparkle_chance:
                if sparkle_color is None:
                    peak = max(pixel)
                    target = (255, 255, 255)
                    full = scale_color(pixel, 255.0 / peak) if peak else out
                else:
                    target = tuple(sparkle_color)
                    full = out
                out = tuple(
                    int(clamp(lerp(full[c], target[c], sparkle_strength), 0, 255))
                    for c in range(3)
                )

            frame.append(out)

        result.append(frame)

    return result


def palette_tint(frames, palette="neonPortrait", amount=0.7):
    """
    Recolor by brightness through a palette gradient (dark -> first
    color, bright -> last), keeping each pixel's brightness, so black
    stays black. amount: 0 = original colors, 1 = fully tinted.
    """
    colors = PaletteLibrary().rgb_colors(palette)
    if not colors:
        raise ValueError(f"Unknown or empty palette: {palette}")

    result = []

    for pixels in frames:
        frame = []

        for pixel in pixels:
            lum = luminance(pixel)
            if lum <= 0:
                frame.append(tuple(pixel))
                continue

            tint = palette_color(lum / 255.0, colors)
            tint_lum = luminance(tint)
            if tint_lum > 0:
                tint = scale_color(tint, lum / tint_lum)

            frame.append(tuple(
                int(clamp(lerp(pixel[c], tint[c], amount), 0, 255))
                for c in range(3)
            ))

        result.append(frame)

    return result


EFFECTS = {
    "full_field": full_field,
    "sparse_random": sparse_random,
    "sparse_noise": sparse_noise,
    "bands": bands,
    "noise_glow": noise_glow,
    "palette_tint": palette_tint,
}


def apply(frames, mode="full_field", **settings):
    """Run the named effect on frames, with optional settings."""
    if mode not in EFFECTS:
        raise ValueError(
            f"Unknown MODE: {mode}. Choose from {', '.join(MODES)}"
        )

    return EFFECTS[mode](frames, **settings)
