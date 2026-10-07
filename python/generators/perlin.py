"""
Perlin noise field (OpenSimplex), one column per frame.

The field is a 2D noise image: x runs along time (one step
per frame), y runs along the wand. Each noise value is mapped
through the palette with a smooth blend.

Example:
    from generators import perlin

    for frame in perlin.frames(seed=42):
        ...
"""

import itertools

from opensimplex import OpenSimplex

from palette import PaletteLibrary, palette_color


def frames(
    seed=42,
    x_scale=0.01,
    y_scale=0.01,
    palette="industrialSun",
    num_leds=100,
    start=0
):
    """
    Yield frames forever, starting at frame `start`.

    x_scale, y_scale: field scale. Smaller = larger/smoother
                      features, larger = smaller/busier.
    palette:          a key in palettes.json.
    """
    noise = OpenSimplex(seed=seed)

    colors = PaletteLibrary().rgb_colors(palette)

    if not colors:
        raise ValueError(f"Unknown or empty palette: {palette}")

    for column in itertools.count(start):

        x = column * x_scale

        frame = []

        for y in range(num_leds):
            n = noise.noise2(
                x,
                y * y_scale
            )

            # OpenSimplex is roughly -1..1
            value = (n + 1.0) / 2.0

            frame.append(
                palette_color(value, colors)
            )

        yield frame
