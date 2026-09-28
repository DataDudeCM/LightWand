import time
import math

from lightwand import LightWand
from palette import PaletteLibrary

wand = LightWand()
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

    wand.double_dot(
        phase,
        color1,
        color2,
        width=2
    )

    phase += 0.15

    time.sleep(0.02)