from noise import pnoise2
from lightwand import LightWand
from palette import PaletteLibrary

pixels = []

# ---- sparse_noise ----
NOISE_THRESHOLD = 0.55             # higher = sparser
NOISE_SOFT_EDGE = 0.08             # dim halo below threshold
NOISE_X_SCALE = 0.08
NOISE_Y_SCALE = 0.14
NOISE_SEED = 999

wand = LightWand()

wand.blackout()
wand.set_brightness(.2)

palettes = PaletteLibrary()

colors = palettes.rgb_colors("industrialSun")

x += speed

for y in range(100):
    n = pnoise2(x * NOISE_X_SCALE,
               y * NOISE_Y_SCALE)

    pixels[y] = palette(n)

wand.send(pixels)