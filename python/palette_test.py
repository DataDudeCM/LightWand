from lightwand import LightWand
from palette import PaletteLibrary

wand = LightWand()

wand.blackout()
wand.set_brightness(.2)

palettes = PaletteLibrary()

colors = palettes.rgb_colors("industrialSun")

wand.bands(colors)
wand.palette(colors)