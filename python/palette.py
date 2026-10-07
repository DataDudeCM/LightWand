import json
import random
from pathlib import Path


class PaletteLibrary:
    """
    Loads and provides access to the shared palettes.json file.

    palettes.json remains the canonical palette source.
    Colors remain stored as hex in JSON and are converted
    to RGB only when needed by Python/LightWand.
    """

    def __init__(self, filename=None):

        if filename is None:
            # palette.py is in /python
            # palettes.json is one directory above it
            filename = (
                Path(__file__).resolve().parent.parent
                / "palettes.json"
            )

        self.filename = Path(filename)

        with open(self.filename, "r", encoding="utf-8") as f:
            self.palettes = json.load(f)

    # --------------------------------------------------
    # Palette access
    # --------------------------------------------------

    def get(self, key):
        """
        Return the complete palette dictionary.

        Example:
            palette = palettes.get("industrialSun")
        """
        return self.palettes.get(key)

    def keys(self):
        """
        Return all palette keys.
        """
        return list(self.palettes.keys())

    def names(self):
        """
        Return all human-readable palette names.
        """
        return [
            palette.get("name", key)
            for key, palette in self.palettes.items()
        ]

    # --------------------------------------------------
    # Colors
    # --------------------------------------------------

    def colors(self, key):
        """
        Return all colors as hex strings.

        Example:
            [
                "#272727",
                "#fed766",
                ...
            ]
        """
        palette = self.get(key)

        if palette is None:
            return []

        return [
            color["hex"]
            for color in palette.get("colors", [])
        ]

    def rgb_colors(self, key):
        """
        Return all palette colors as RGB tuples.

        This format can be handed directly to LightWand
        effects and pixel-generation code.
        """
        return [
            self.hex_to_rgb(color)
            for color in self.colors(key)
        ]

    # --------------------------------------------------
    # Roles
    # --------------------------------------------------

    def colors_by_role(self, key, role):
        """
        Return all hex colors matching a semantic role.

        Example:
            palettes.colors_by_role(
                "industrialSun",
                "warm"
            )
        """
        palette = self.get(key)

        if palette is None:
            return []

        return [
            color["hex"]
            for color in palette.get("colors", [])
            if color.get("role") == role
        ]

    def color_by_role(
        self,
        key,
        role,
        fallback_to_random=True
    ):
        """
        Return one hex color matching a role.
        """
        matches = self.colors_by_role(key, role)

        if matches:
            return random.choice(matches)

        if fallback_to_random:
            return self.random_color(key)

        return None

    def rgb_by_role(
        self,
        key,
        role,
        fallback_to_random=True
    ):
        """
        Return one RGB tuple matching a role.
        """
        color = self.color_by_role(
            key,
            role,
            fallback_to_random
        )

        if color is None:
            return None

        return self.hex_to_rgb(color)

    # --------------------------------------------------
    # Tags
    # --------------------------------------------------

    def palettes_by_tag(self, tag):
        """
        Return palette keys containing a given tag.
        """
        return [
            key
            for key, palette in self.palettes.items()
            if tag in palette.get("tags", [])
        ]

    def random_palette(self, tag=None):
        """
        Return a random palette key.

        Optionally restrict selection by tag.
        """
        if tag is None:
            choices = self.keys()
        else:
            choices = self.palettes_by_tag(tag)

        if not choices:
            return None

        return random.choice(choices)

    # --------------------------------------------------
    # Random colors
    # --------------------------------------------------

    def random_color(self, key):
        """
        Return a random palette color as hex.
        """
        colors = self.colors(key)

        if not colors:
            return None

        return random.choice(colors)

    def random_rgb(self, key):
        """
        Return a random palette color as an RGB tuple.
        """
        color = self.random_color(key)

        if color is None:
            return None

        return self.hex_to_rgb(color)

    # --------------------------------------------------
    # Reserved semantic colors
    # --------------------------------------------------

    def reserved_color(self, key, name):
        """
        Return a top-level reserved color such as 'ink'.
        """
        palette = self.get(key)

        if palette is None:
            return None

        return palette.get(name)

    def ink(self, key):
        """
        Return the palette's explicit ink color.

        If no ink is defined, fall back to dark,
        then shadow, then a random palette color.
        """
        explicit = self.reserved_color(key, "ink")

        if explicit:
            return explicit

        return (
            self.color_by_role(
                key,
                "dark",
                fallback_to_random=False
            )
            or self.color_by_role(
                key,
                "shadow",
                fallback_to_random=False
            )
            or self.random_color(key)
        )

    def ink_rgb(self, key):
        color = self.ink(key)

        if color is None:
            return None

        return self.hex_to_rgb(color)

    # --------------------------------------------------
    # Conversion
    # --------------------------------------------------

    @staticmethod
    def hex_to_rgb(hex_color):
        """
        Convert '#fed766' -> (254, 215, 102)
        """
        value = hex_color.lstrip("#")

        if len(value) != 6:
            raise ValueError(
                f"Expected 6-digit hex color, got: {hex_color}"
            )

        return tuple(
            int(value[i:i + 2], 16)
            for i in (0, 2, 4)
        )

# --------------------------------------------------
# Smooth palette blend
# --------------------------------------------------

def palette_color(value, colors):
    """
    Turn a 0..1 value into a color, blending smoothly
    between neighboring palette colors.

    colors is a list of RGB tuples, e.g. from
    PaletteLibrary.rgb_colors(). Values outside 0..1
    are clamped.

    Example:
        colors = PaletteLibrary().rgb_colors("industrialSun")
        palette_color(0.5, colors)
    """
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
