from palette import PaletteLibrary

palettes = PaletteLibrary()

print(palettes.keys())

print(palettes.colors("industrialSun"))

print(palettes.rgb_colors("industrialSun"))

print(
    palettes.rgb_by_role(
        "industrialSun",
        "warm"
    )
)