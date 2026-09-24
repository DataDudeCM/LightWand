import time
from lightwand import LightWand

wand = LightWand(
    ip="192.168.1.8",
    port=7777,
    num_leds=100,
    brightness=0.5
  
)

print("Starting LightWand effects test...")
print(f"Sending to {wand.ip}:{wand.port}")
print(f"LED count: {wand.num_leds}")

try:
    # --------------------------------------------------
    # Solid colors
    # --------------------------------------------------

    print("Red")
    wand.solid(255, 0, 0)
    time.sleep(1)

    print("Green")
    wand.solid(0, 255, 0)
    time.sleep(1)

    print("Blue")
    wand.solid(0, 0, 255)
    time.sleep(1)

    # --------------------------------------------------
    # Gradient
    # --------------------------------------------------

    print("Red to blue gradient")
    wand.gradient(
        (255, 0, 0),
        (0, 0, 255)
    )

    time.sleep(2)

    # --------------------------------------------------
    # Animated rainbow
    # --------------------------------------------------

    print("Rainbow")

    for step in range(150):
        wand.rainbow(
            offset=step * 0.01
        )

        time.sleep(0.025)

    # --------------------------------------------------
    # Moving dot with fading trail
    # --------------------------------------------------

    print("Moving dot with trail")

    wand.clear()

    for _ in range(3):
        for pos in range(wand.num_leds):

            wand.fade(0.82)

            wand.set_pixel(
                pos,
                255,
                255,
                255
            )

            wand.show()

            time.sleep(0.02)

    # --------------------------------------------------
    # Bouncing dot
    # --------------------------------------------------

    print("Bouncing dot")

    for _ in range(3):

        for pos in range(wand.num_leds):

            wand.fade(0.75)
            wand.set_pixel(pos, 0, 255, 255)
            wand.show()

            time.sleep(0.015)

        for pos in range(wand.num_leds - 1, -1, -1):

            wand.fade(0.75)
            wand.set_pixel(pos, 255, 0, 255)
            wand.show()

            time.sleep(0.015)

    # --------------------------------------------------
    # Finish
    # --------------------------------------------------

    print("Done")

    wand.clear()

finally:
    wand.close()