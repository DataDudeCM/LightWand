"""
Previews of what the wand will produce.

simulate_paint() estimates the long-exposure photo for a set of
frames: where each frame lands, the gaps between the 100 LEDs,
optional diffusion blur, and the photo's proportions.

simulate_flow() draws the flow view: the wand showing its newest
frame, with older frames scrolling away behind it.

No window or wand code here; paint.py and generate.py
are the viewers (window helpers in preview_window.py).

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


def simulate_flow(
    frames,
    tip="up",
    sweep="right",
    trail_frames=None,
    px_per_frame=2,
    led_size=8,
    led_gaps=True,
    led_dot_fraction=0.4,
    mark_start=None,
    mark_end=None
):
    """
    The flow viewer's picture: the wand at the leading edge
    (the SWEEP side) showing the newest frame, with older
    frames trailing behind it.

    frames:           oldest first, newest last.
    trail_frames:     frame slots in the trail. Older frames are
                      dropped; too few leave the far end dark.
                      None = len(frames).
    px_per_frame:     trail width of each frame (scroll speed).
    led_size:         pixels per LED along the wand.
    led_gaps:         draw each LED as a thin streak with dark gaps
                      between, like the wand itself. False = solid.
    led_dot_fraction: streak width as a fraction of led_size.
    mark_start,
    mark_end:         index (into frames) of a snapshot's first /
                      last frame, drawn as a thin white line at
                      that frame's outer edge. None = no line.

    Unlike simulate_paint, every frame and LED gets a whole number
    of pixels, so the picture is exact and fast enough to redraw
    at screen rate. Returns a PIL image as the camera sees it.
    """
    tip, sweep = check_orientation(tip, sweep)

    strip = np.asarray(list(frames), dtype=np.uint8)   # (frames, leds, 3)

    if trail_frames is None:
        trail_frames = len(strip)

    # Where frames[0] lands among the trail's slots.
    offset = trail_frames - len(strip)

    strip = strip[-trail_frames:]
    num_leds = strip.shape[1]

    # Not enough history yet: dark trail behind the wand.
    missing = trail_frames - len(strip)
    if missing > 0:
        strip = np.concatenate([
            np.zeros((missing, num_leds, 3), dtype=np.uint8),
            strip
        ])

    # Standard layout (tip up, sweep right): newest on the right.
    canvas = strip.transpose(1, 0, 2)                    # (leds, frames, 3)
    canvas = np.repeat(canvas, led_size, axis=0)
    canvas = np.repeat(canvas, px_per_frame, axis=1)

    if led_gaps:
        # The middle rows of each LED's cell are lit
        # (at least one).
        lit_rows = max(1, round(led_dot_fraction * led_size))
        first = (led_size - lit_rows) // 2

        lit = np.zeros(led_size, dtype=bool)
        lit[first:first + lit_rows] = True

        canvas = canvas * np.tile(lit, num_leds)[:, None, None]

    # Snapshot marks: start on the frame's first column,
    # end on its last, so the line sits outside the range.
    canvas = np.ascontiguousarray(canvas)

    for index, edge in ((mark_start, 0), (mark_end, px_per_frame - 1)):
        if index is None:
            continue

        slot = index + offset
        if 0 <= slot < trail_frames:
            canvas[:, slot * px_per_frame + edge] = 255

    image = Image.fromarray(canvas, "RGB")

    return unorient(image, tip, sweep)
