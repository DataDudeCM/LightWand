"""
Turn a picture into wand frames, for any way the wand is held.

Pixel 0 is at the TIP of the wand (the end away from the electronics).

Directions are always as seen by the CAMERA, in the final photo:

    TIP    where the tip (pixel 0) points:  "up", "down", "left", "right"
    SWEEP  which way the wand moves:        "right", "left", "down", "up"

SWEEP must be perpendicular to TIP. If it isn't, we fall back to
TIP="up", SWEEP="right" and print a warning.

Usage:

    image = Image.open("photo.jpg").convert("RGB")
    image = orient(image, tip="left", sweep="down")
    frames = to_frames(image, num_slices=350, num_leds=100)

Call this once, before the exposure. The display loop then just
plays the frames in order.
"""

from PIL import Image


DEFAULT_TIP = "up"
DEFAULT_SWEEP = "right"

# Each operation turns the source image into the standard layout:
# tip up, sweep right. Row 0 -> pixel 0, column 0 -> first frame.
ORIENTATIONS = {
    ("up", "right"): None,
    ("up", "left"): Image.Transpose.FLIP_LEFT_RIGHT,
    ("down", "right"): Image.Transpose.FLIP_TOP_BOTTOM,
    ("down", "left"): Image.Transpose.ROTATE_180,
    ("left", "down"): Image.Transpose.TRANSPOSE,
    ("left", "up"): Image.Transpose.ROTATE_270,
    ("right", "down"): Image.Transpose.ROTATE_90,
    ("right", "up"): Image.Transpose.TRANSVERSE,
}


def check_orientation(tip, sweep):
    """
    Return a valid (tip, sweep) pair.

    Falls back to the defaults, with a warning, if the pair
    doesn't fit together (or has a typo).
    """
    key = (str(tip).lower(), str(sweep).lower())

    if key in ORIENTATIONS:
        return key

    print(
        f"WARNING: TIP={tip!r} and SWEEP={sweep!r} don't fit together. "
        f"SWEEP must be across the wand, not along it. "
        f"Using TIP={DEFAULT_TIP!r}, SWEEP={DEFAULT_SWEEP!r}."
    )

    return (DEFAULT_TIP, DEFAULT_SWEEP)


def orient(image, tip=DEFAULT_TIP, sweep=DEFAULT_SWEEP):
    """
    Rotate / flip the image into the standard layout
    (tip up, sweep right).
    """
    key = check_orientation(tip, sweep)
    operation = ORIENTATIONS[key]

    if operation is None:
        return image

    return image.transpose(operation)


def unorient(image, tip=DEFAULT_TIP, sweep=DEFAULT_SWEEP):
    """
    The reverse of orient(): turn an image in the standard
    layout back into how it appears in the photo.
    """
    key = check_orientation(tip, sweep)
    operation = ORIENTATIONS[key]

    if operation is None:
        return image

    # Every operation is its own inverse except the two quarter turns.
    inverse = {
        Image.Transpose.ROTATE_90: Image.Transpose.ROTATE_270,
        Image.Transpose.ROTATE_270: Image.Transpose.ROTATE_90,
    }.get(operation, operation)

    return image.transpose(inverse)


def to_frames(image, num_slices, num_leds):
    """
    Resize an oriented image and slice it into frames.

    Returns a list of num_slices frames.
    Each frame is a list of num_leds (r, g, b) tuples,
    starting at pixel 0 (the tip).
    """
    image = image.convert("RGB").resize(
        (num_slices, num_leds),
        Image.Resampling.LANCZOS
    )

    frames = []

    for x in range(num_slices):
        frame = [
            image.getpixel((x, y))
            for y in range(num_leds)
        ]
        frames.append(frame)

    return frames
