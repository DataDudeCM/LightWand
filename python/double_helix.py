import time
import math

from lightwand import LightWand
from palette import PaletteLibrary

wand = LightWand()
wand.set_brightness(.1)
palettes = PaletteLibrary()

color1 = palettes.rgb_by_role(
    "industrialSun",
    "warm"
)

color2 = palettes.rgb_by_role(
    "industrialSun",
    "cool"
)

phase = 0

while True:

    # Move toward each other
    for pos in range(wand.num_leds):
        wand.double_dot(
            pos,
            color1,
            color2,
            width=2
        )

        time.sleep(0.02)

    # Move away from each other
    for pos in range(wand.num_leds - 1, -1, -1):
        wand.double_dot(
            pos,
            color1,
            color2,
            width=2
        )

        time.sleep(0.02)