from PIL import Image
from lightwand import LightWand
import time


IMAGE_FILE = "images/antelope.jpg"

EXPOSURE_SECONDS = 3.5
DELAY_BEFORE_START_SECONDS = 12.5

# Number of image slices shown each second.
# 100 fps gives 300 slices during a 3-second exposure.
FPS = 100

REVERSE = False

wand = LightWand(
    ip="192.168.1.8",
    port=7777,
    num_leds=100,
    brightness = .4
)


def prepare_image(filename, exposure, fps):

    image = Image.open(filename).convert("RGB")

    # Every vertical slice must contain exactly
    # one pixel for every LED.
    target_height = wand.num_leds

    # Number of temporal slices we'll display.
    num_slices = max(
        1,
        round(exposure * fps)
    )

    image = image.resize(
        (num_slices, target_height),
        Image.Resampling.LANCZOS
    )

    return image


def display_image(image, exposure):

    width, height = image.size

    print(f"Image size: {width} x {height}")
    print(f"Exposure: {exposure:.2f} seconds")
    print(f"Slices: {width}")
    print(
        f"Slice rate: "
        f"{width / exposure:.1f} fps"
    )

    start_time = time.perf_counter()

    for x in range(width):

        source_x = (
            width - 1 - x
            if REVERSE
            else x
        )

        pixels = []

        for y in range(height):

            r, g, b = image.getpixel(
                (source_x, y)
            )

            pixels.append((r, g, b))

        wand.pixels = pixels
        wand.show()

        # Absolute timing prevents accumulated
        # sleep errors from stretching the sequence.
        target_time = (
            start_time +
            ((x + 1) / width) * exposure
        )

        remaining = (
            target_time -
            time.perf_counter()
        )

        if remaining > 0:
            time.sleep(remaining)

    wand.clear()

    actual_time = (
        time.perf_counter() -
        start_time
    )

    print(
        f"Completed in {actual_time:.3f} sec"
    )


try:

    image = prepare_image(
        IMAGE_FILE,
        EXPOSURE_SECONDS,
        FPS
    )

    print()
    print("Ready.")
    print(
        f"Open shutter and move wand "
        f"A → B in {EXPOSURE_SECONDS} seconds."
    )

    input("Press ENTER to start...")
    time.sleep(DELAY_BEFORE_START_SECONDS)

    display_image(
        image,
        EXPOSURE_SECONDS
    )

finally:

    wand.close()