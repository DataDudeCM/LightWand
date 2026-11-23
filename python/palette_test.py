"""Show a palette on the wand as a smooth gradient, and hold it.

    python palette_test.py                      # neonPortrait at 0.05
    python palette_test.py violetSmoke          # another palette
    python palette_test.py violetSmoke 0.2      # and a brightness (0-1)
    python palette_test.py violetSmoke --bands  # solid bands instead

Wings (Violet Smoke without its two lightest colors, the lightest of
the rest at the hand, dimmed to half there and full at the tip):

    python palette_test.py violetSmoke 0.6 --skip 2 --from-hand --hand-fade 0.5

The frame stays on until Ctrl+C, which blacks the wand out.
Pixel 0 is the tip; the hand (electronics) end is the last pixel.
"""
import argparse
import time

from lightwand import LightWand
from palette import PaletteLibrary


def gradient_pixels(colors, num_leds):
    """Blend colors evenly from pixel 0 (tip) to the last pixel."""
    segments = len(colors) - 1
    pixels = []
    for i in range(num_leds):
        scaled = i / max(1, num_leds - 1) * segments
        seg = min(int(scaled), segments - 1)
        t = scaled - seg
        c1, c2 = colors[seg], colors[seg + 1]
        pixels.append(tuple(a + (b - a) * t for a, b in zip(c1, c2)))
    return pixels


def hand_fade(pixels, hand_level, gamma):
    """
    Dim toward the hand end: hand_level at the last pixel (hand),
    full at pixel 0 (tip), changing evenly in between.

    hand_level is how bright it LOOKS (0.5 = looks half as bright).
    The wand applies gamma after this, so the color values are
    scaled by level ** (1 / gamma) to land on that visible level.
    """
    n = len(pixels)
    out = []
    for i, (r, g, b) in enumerate(pixels):
        u = i / max(1, n - 1)                 # 0 at tip, 1 at hand
        level = 1.0 + (hand_level - 1.0) * u
        k = level ** (1.0 / gamma)
        out.append((r * k, g * k, b * k))
    return out


palettes = PaletteLibrary()

parser = argparse.ArgumentParser(description="Show a palette on the wand.")
parser.add_argument("palette", nargs="?", default="neonPortrait",
                    help="palette key in palettes.json: " + ", ".join(palettes.keys()))
parser.add_argument("brightness", nargs="?", type=float, default=0.05,
                    help="0-1 (default 0.05)")
parser.add_argument("--bands", action="store_true",
                    help="solid color bands instead of a gradient")
parser.add_argument("--skip", type=int, default=0,
                    help="leave out the first N colors of the palette")
parser.add_argument("--from-hand", action="store_true",
                    help="start the palette at the hand end, not the tip")
parser.add_argument("--hand-fade", type=float, default=1.0,
                    help="how bright the hand end looks (0-1), ramping to "
                         "full at the tip (default 1 = no fade)")
args = parser.parse_args()

colors = palettes.rgb_colors(args.palette)
if not colors:
    parser.error(f"unknown palette '{args.palette}'. Choose from: "
                 + ", ".join(palettes.keys()))

colors = colors[args.skip:]
if len(colors) < 2 and not args.bands:
    parser.error(f"--skip {args.skip} leaves fewer than 2 colors for a gradient")
if not 0.0 <= args.hand_fade <= 1.0:
    parser.error("--hand-fade must be between 0 and 1")

# Pixel 0 is the tip, so "from the hand" means the palette runs backwards.
if args.from_hand:
    colors = colors[::-1]

wand = LightWand()
wand.blackout()
wand.set_brightness(args.brightness)

if args.bands:
    wand.bands(colors, show=False)
    pixels = list(wand.pixels)
else:
    pixels = gradient_pixels(colors, wand.num_leds)

if args.hand_fade < 1.0:
    pixels = hand_fade(pixels, args.hand_fade, wand.gamma)

wand.set_pixels(pixels)

print(f"{args.palette}: {len(colors)} colors, brightness {args.brightness}, "
      f"hand fade {args.hand_fade}. Ctrl+C to black out.")
try:
    # Resend now and then: one lost UDP packet would leave the wand dark.
    while True:
        wand.show()
        time.sleep(0.5)
except KeyboardInterrupt:
    pass
finally:
    wand.blackout()
    wand.show()
    print("Blacked out.")
