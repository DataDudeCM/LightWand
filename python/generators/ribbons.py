"""
Ribbons: translucent veils of light, like colored smoke ribbons.

At any moment a ribbon is an interval along the wand: two glowing
edges with a faint, see-through fill between them. The edges drift
slowly and smoothly, so as the wand sweeps they trace swooping
curves. When a ribbon twists, its edges cross: that fold glows
brighter. Ribbons drift in and out like smoke, and where they
overlap their light adds up toward white.

Stateless: every frame is computed straight from the frame number
(sums of slow sine waves with seeded random periods and phases), so
start=N is instant and snapshots are exact.

Deterministic:
    same seed + settings + start frame = same output

Generator contract:
    frames(..., start=N) yields frames forever
    each frame is a list of num_leds (r, g, b) tuples
    pixel 0 = physical tip of the wand
"""

import colorsys
import itertools
import math
import random

from palette import PaletteLibrary, palette_color


def smooth_signal(rng, periods, amplitudes):
    """
    A smooth wandering value: a sum of sine waves with the given
    periods (in frames) and amplitudes, at random phases.
    """
    waves = [
        (2.0 * math.pi / period, rng.uniform(0.0, 2.0 * math.pi), amplitude)
        for period, amplitude in zip(periods, amplitudes)
    ]

    def value(t):
        return sum(
            amplitude * math.sin(speed * t + phase)
            for speed, phase, amplitude in waves
        )

    return value


def desaturate(rgb, saturation):
    """Mix a 0..1 color toward its grey: 0 = grey, 1 = unchanged."""
    if saturation == 1.0:
        return rgb
    grey = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
    return tuple(grey + (c - grey) * saturation for c in rgb)


def ping_pong(x):
    """0..1..0 over each unit of x, so palette drift never jumps."""
    x = x % 2.0
    return x if x <= 1.0 else 2.0 - x


def frames(
    seed=42,

    # shape and motion (positions are 0..1 along the wand, 0 = tip)
    num_ribbons=5,
    center=0.5,             # where the ribbons gather
    sway=0.32,              # how far ribbon centers swing from there
    ribbon_width=0.14,      # typical half-width; edges can cross (a fold)
    slowness=2.0,           # 1 = brisk, higher = slower, bigger swoops
    presence=0.55,          # how much of the time ribbons are visible (fade in/out like smoke)

    # look
    edge_width=1.1,         # softness of the glowing edges, in LEDs
    edge_brightness=1.0,
    fill_brightness=0.22,   # the see-through veil between the edges
    fold_glow=1.5,          # extra glow where a ribbon's edges meet
    glow=1.6,               # how quickly overlaps brighten toward white
    brightness=1.0,

    # color
    palette=None,           # None = rainbow; or a palette name, e.g. "duskSmoke"
    saturation=0.75,
    hue_drift=0.0004,       # color change per frame (rainbow: hue; palette: along it)

    # standard generator interface
    num_leds=100,
    start=0
):
    """
    Yield frames forever, starting at frame `start`.
    """
    if num_ribbons < 1:
        raise ValueError("num_ribbons must be at least 1")

    if slowness <= 0:
        raise ValueError("slowness must be greater than 0")

    if edge_width <= 0:
        raise ValueError("edge_width must be greater than 0")

    colors = None
    if palette is not None:
        colors = PaletteLibrary().rgb_colors(palette)
        if not colors:
            raise ValueError(f"Unknown or empty palette: {palette}")

    rng = random.Random(seed)
    s = slowness

    ribbons = []
    for i in range(num_ribbons):
        ribbons.append({
            # center wanders: a big slow swing plus smaller, quicker ones
            "center": smooth_signal(
                rng,
                [s * rng.uniform(260, 520), s * rng.uniform(120, 220), s * rng.uniform(60, 100)],
                [sway * 0.65, sway * 0.30, sway * 0.12],
            ),
            # half-width breathes, and goes negative now and then: a twist
            "width": smooth_signal(
                rng,
                [s * rng.uniform(180, 360), s * rng.uniform(70, 130)],
                [ribbon_width * 1.4, ribbon_width * 0.5],
            ),
            # fades in and out like smoke
            "envelope": smooth_signal(
                rng,
                [s * rng.uniform(200, 400), s * rng.uniform(90, 150)],
                [0.8, 0.3],
            ),
            # spread around the color wheel (or along the palette)
            "hue": (i / num_ribbons + rng.uniform(-0.04, 0.04)) % 1.0,
        })

    last_led = num_leds - 1
    reach = 4.0 * edge_width    # beyond this an edge's glow is negligible

    def ribbon_rgb(ribbon, t):
        """The ribbon's color now, 0..1 per channel."""
        position = ribbon["hue"] + hue_drift * t

        if colors is None:
            rgb = colorsys.hsv_to_rgb(position % 1.0, 1.0, 1.0)
        else:
            rgb = tuple(
                c / 255.0
                for c in palette_color(ping_pong(position), colors)
            )

        return desaturate(rgb, saturation)

    for t in itertools.count(start):
        light = [[0.0, 0.0, 0.0] for _ in range(num_leds)]

        for ribbon in ribbons:
            amount = min(1.0, presence + ribbon["envelope"](t)) * brightness
            if amount <= 0:
                continue

            middle = center + ribbon["center"](t)
            half = ribbon["width"](t) + ribbon_width * 0.4

            edge_a = (middle - half) * last_led
            edge_b = (middle + half) * last_led
            low, high = min(edge_a, edge_b), max(edge_a, edge_b)

            # A fold (edges close together) glows brighter.
            fold = 1.0 + fold_glow * math.exp(-((high - low) / 3.0) ** 2)

            rgb = ribbon_rgb(ribbon, t)

            first = max(0, math.floor(low - reach))
            last = min(last_led, math.ceil(high + reach))

            for led in range(first, last + 1):
                value = fill_brightness if low <= led <= high else 0.0

                for edge in (edge_a, edge_b):
                    d = (led - edge) / edge_width
                    if abs(d) < 4.0:
                        value += edge_brightness * fold * math.exp(-0.5 * d * d)

                if value:
                    value *= amount
                    pixel = light[led]
                    for channel in range(3):
                        pixel[channel] += rgb[channel] * value

        # Overlaps brighten smoothly toward white instead of clipping.
        yield [
            tuple(round(255 * (1.0 - math.exp(-glow * x))) for x in pixel)
            for pixel in light
        ]
