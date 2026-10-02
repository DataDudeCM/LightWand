import time

from opensimplex import OpenSimplex

from lightwand import LightWand
from palette import PaletteLibrary


# --------------------------------------------------
# Settings
# --------------------------------------------------

FPS = 40
FRAME_TIME = 1.0 / FPS

PALETTE_NAME = "industrialSun"

# Perlin field scale
#
# Smaller = larger/smoother features
# Larger  = smaller/busier features
X_SCALE = 0.01
Y_SCALE = 0.01

noise = OpenSimplex(seed=42)


# --------------------------------------------------
# Palette setup
# --------------------------------------------------

palettes = PaletteLibrary()

colors = palettes.rgb_colors(
    PALETTE_NAME
)


# --------------------------------------------------
# Convert 0..1 value into a smoothly interpolated
# palette color
# --------------------------------------------------

def palette_color(value, colors):

    value = max(
        0.0,
        min(1.0, value)
    )

    position = value * (
        len(colors) - 1
    )

    index = int(position)
    fraction = position - index

    # Last palette color
    if index >= len(colors) - 1:
        return colors[-1]

    color1 = colors[index]
    color2 = colors[index + 1]

    return tuple(
        int(
            color1[channel]
            + (
                color2[channel]
                - color1[channel]
            ) * fraction
        )
        for channel in range(3)
    )


# --------------------------------------------------
# Generate one 100-pixel Perlin column
# --------------------------------------------------

def generate_perlin_column(column, num_leds):
    pixels = []

    x = column * X_SCALE

    for y in range(num_leds):
        n = noise.noise2(
            x,
            y * Y_SCALE
        )

        # OpenSimplex is roughly -1..1
        value = (n + 1.0) / 2.0

        pixels.append(
            palette_color(value, colors)
        )

    return pixels


# --------------------------------------------------
# Wand
# --------------------------------------------------

wand = LightWand(
    num_leds=100,
    brightness=1
)

print("Starting Perlin noise field...")
print(f"Sending to {wand.ip}:{wand.port}")
print(f"Palette: {PALETTE_NAME}")
print(f"FPS: {FPS}")


# --------------------------------------------------
# Animation
# --------------------------------------------------

column = 0

try:

    while True:

        pixels = generate_perlin_column(
            column,
            wand.num_leds
        )

        wand.set_pixels(pixels)
        wand.show()

        column += 1

        time.sleep(FRAME_TIME)

except KeyboardInterrupt:

    print("Stopping Perlin effect...")

finally:

    wand.close()