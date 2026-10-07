"""
Window helpers shared by the preview viewers
(paint.py and generate.py).
"""

import pygame
from PIL import Image


# The two sweep directions that go across the wand, for each TIP.
PERPENDICULAR = {
    "up": ("right", "left"),
    "down": ("right", "left"),
    "left": ("down", "up"),
    "right": ("down", "up"),
}

ARROWS = {
    pygame.K_UP: "up",
    pygame.K_DOWN: "down",
    pygame.K_LEFT: "left",
    pygame.K_RIGHT: "right",
}


def turn(key, tip, sweep):
    """
    Arrow keys point the tip, space flips the sweep.

    Returns the new (tip, sweep), or None if the key is
    neither. The sweep always stays across the wand.
    """
    if key in ARROWS:
        new_tip = ARROWS[key]

        if sweep not in PERPENDICULAR[new_tip]:
            sweep = PERPENDICULAR[new_tip][0]

        return new_tip, sweep

    if key == pygame.K_SPACE:
        a, b = PERPENDICULAR[tip]
        return tip, (b if sweep == a else a)

    return None


def screen_limits(fraction=0.85):
    """
    The largest window size to use, as a fraction of the screen.
    Call after pygame.init().
    """
    info = pygame.display.Info()

    return (
        int(info.current_w * fraction),
        int(info.current_h * fraction)
    )


def fit_size(width, height, max_w, max_h):
    """Shrink (never grow) width x height to fit inside max_w x max_h."""
    scale = min(max_w / width, max_h / height, 1.0)

    return (
        max(1, int(width * scale)),
        max(1, int(height * scale))
    )


def to_surface(image, size=None, resample=Image.Resampling.LANCZOS):
    """A PIL image as a pygame surface, resized to size if given."""
    if size is not None and image.size != tuple(size):
        image = image.resize(size, resample)

    return pygame.image.fromstring(image.tobytes(), image.size, "RGB")
