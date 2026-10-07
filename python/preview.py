"""
Previews of what the wand will produce.

simulate_paint() estimates the long-exposure photo for a set of
frames: where each frame lands, the gaps between the 100 LEDs,
optional diffusion blur, and the photo's proportions.

No window or wand code here; preview_paint.py is the viewer.

Usage:

    image = simulate_paint(frames, tip="left", sweep="down",
                           lit_length_in=39, sweep_in=28)
    image.save("preview.png")
"""

import numpy as np
from PIL import Image, ImageFilter

from image_frames import check_orientation, unorient


def simulate_paint(
    frames,
    tip="up",
    sweep="right",
    lit_length_in=39,
    sweep_in=None,
    px_per_inch=15,
    led_gaps=True,
    led_dot_fraction=0.4,
    blur_in=0.0,
    gain=1.0
):
    """
    Simulate the photo of `frames` being painted.

    frames:           list of frames, each a list of (r, g, b),
                      pixel 0 = tip, in playback order.
    tip, sweep:       as seen by the camera (see image_frames).
    lit_length_in:    LED 1 to LED 100, in inches.
    sweep_in:         how far the wand travels during the exposure.
                      None = same proportions as the frame strip.
    px_per_inch:      preview resolution.
    led_gaps:         draw each LED as a thin streak with dark gaps
                      between, like the real photos. False = solid.
    led_dot_fraction: streak width as a fraction of the LED spacing.
    blur_in:          diffusion blur radius, in inches (0 = none).
    gain:             exposure brightness multiplier.

    The sweep is assumed to be at steady speed, so every frame
    gets the same width. Returns a PIL image as the camera sees it.
    """
    tip, sweep = check_orientation(tip, sweep)

    strip = np.asarray(frames, dtype=np.float32)   # (frames, leds, 3)
    num_frames, num_leds = strip.shape[0], strip.shape[1]

    if sweep_in is None:
        sweep_in = lit_length_in * num_frames / num_leds

    # Build in the standard layout (tip up, sweep right),
    # then turn it into the camera's view at the end.
    pitch = lit_length_in * px_per_inch / max(1, num_leds - 1)
    height = max(1, round(num_leds * pitch))
    width = max(1, round(sweep_in * px_per_inch))

    # Steady speed: column x shows the frame that was lit
    # while the wand passed that spot.
    cols = np.arange(width)
    frame_at_col = np.minimum(cols * num_frames // width, num_frames - 1)

    # Each row belongs to the nearest LED.
    rows = np.arange(height)
    led_at_row = np.minimum((rows / pitch).astype(int), num_leds - 1)

    canvas = strip[frame_at_col][:, led_at_row]    # (width, height, 3)
    canvas = canvas.transpose(1, 0, 2)              # (height, width, 3)

    if led_gaps:
        # Distance from each row's centre to its LED's centre.
        row_centres = rows + 0.5
        led_centres = (led_at_row + 0.5) * pitch
        lit = np.abs(row_centres - led_centres) <= (
            led_dot_fraction * pitch / 2
        )
        canvas = canvas * lit[:, None, None]

    canvas = np.clip(canvas * gain, 0, 255).astype(np.uint8)
    image = Image.fromarray(canvas, "RGB")

    if blur_in > 0:
        image = image.filter(
            ImageFilter.GaussianBlur(blur_in * px_per_inch)
        )

    return unorient(image, tip, sweep)
