from lightwand import LightWand
from palette import PaletteLibrary

wand = LightWand()

wand.blackout()

palettes = PaletteLibrary()

colors = palettes.rgb_colors("vividPrimary")

wand.bands(colors)