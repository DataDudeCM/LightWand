import socket
import time
import colorsys
import random


class LightWand:

    DISCOVERY_MESSAGE = b"LIGHTWAND_DISCOVER"
    DISCOVERY_RESPONSE = b"LIGHTWAND_HERE"
    DISCOVERY_BROADCASTS = [
        "255.255.255.255",
        "192.168.137.255",  # laptop hotspot
        "192.168.1.255",    # home Wi-Fi
    ]

    def __init__(
        self,
        ip=None,
        port=7777,
        num_leds=100,
        brightness=1.0
    ):
        self.port = port
        self.num_leds = num_leds
        self.brightness = brightness

        self.sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )

        if ip is None:
            self.ip = self.discover()
        else:
            self.ip = ip

        self.pixels = [(0, 0, 0)] * self.num_leds

    # -----------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------

    @staticmethod
    def _clamp(value):
        return max(0, min(255, int(value)))

    @classmethod
    def _color(cls, r, g, b):
        return (
            cls._clamp(r),
            cls._clamp(g),
            cls._clamp(b)
        )

    # -----------------------------------------------------
    # Discover IP
    # -----------------------------------------------------

    def discover(self, timeout=3.0):

        print("Looking for Light Wand...")

        self.sock.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_BROADCAST,
            1
        )

        self.sock.settimeout(timeout)

        try:
            for broadcast_ip in self.DISCOVERY_BROADCASTS:
                self.sock.sendto(
                    self.DISCOVERY_MESSAGE,
                    (broadcast_ip, self.port)
                )

            while True:

                data, address = self.sock.recvfrom(1024)

                if data == self.DISCOVERY_RESPONSE:

                    wand_ip = address[0]

                    print(
                        f"Light Wand found at "
                        f"{wand_ip}:{self.port}"
                    )

                    return wand_ip

        except socket.timeout:

            raise RuntimeError(
                "Light Wand not found. "
                "Make sure the wand and computer "
                "are on the same Wi-Fi network."
            )

        finally:
            self.sock.settimeout(None)

    # -----------------------------------------------------
    # Core pixel operations
    # -----------------------------------------------------

    def set_pixel(self, index, r, g, b):
        if 0 <= index < self.num_leds:
            self.pixels[index] = self._color(r, g, b)

    def fill(self, r, g, b):
        color = self._color(r, g, b)
        self.pixels = [color] * self.num_leds

    def show(self):
        frame = bytearray()

        for r, g, b in self.pixels:
            frame.extend((
                int(r * self.brightness),
                int(g * self.brightness),
                int(b * self.brightness)
            ))

        self.sock.sendto(
            frame,
            (self.ip, self.port)
        )

    def blackout(self, show=True):
        """
        Immediately turn every LED off.

        Essentially:
            fill(0, 0, 0)
            show()

        """
        self.fill(0, 0, 0)

        if show:
            self.show()

    def solid(self, r, g, b):
        self.fill(r, g, b)
        self.show()


    # -----------------------------------------------------
    # Brightness control
    # -----------------------------------------------------

    def set_brightness(self, brightness):
        """
        Set the global software brightness multiplier.

        Example:
            wand.set_brightness(0.4)

        Useful because brightness is something you'll likely
        want to adjust dynamically from experiment scripts
        without recreating the LightWand object.
        """


    # -----------------------------------------------------
    # Replace entire LED frame
    # -----------------------------------------------------

    def set_pixels(self, pixels):
        """
        Replace the complete internal pixel buffer.

        pixels should be a list of RGB tuples:
            [(255, 0, 0), (0, 255, 0), ...]

        This is probably the MOST useful addition.

        Image slicing, generative algorithms, audio analysis,
        procedural patterns, etc. can all produce a list of
        100 RGB values and hand it directly to the wand.

        Example:
            colors = generate_something()
            wand.set_pixels(colors)
            wand.show()
        """


    # -----------------------------------------------------
    # Read one pixel
    # -----------------------------------------------------

    def get_pixel(self, index):
        """
        Return the RGB value currently stored at one LED.

        Example:
            r, g, b = wand.get_pixel(42)

        Useful when an algorithm wants to examine or modify
        the existing frame rather than rebuild it from scratch.
        """


    # -----------------------------------------------------
    # Reverse current frame
    # -----------------------------------------------------

    def reverse(self, show=True):
        """
        Reverse the order of the current LED pixels.

        LED 0 becomes LED 99, LED 1 becomes LED 98, etc.

        Very useful for changing physical drawing direction
        without rewriting the pattern-generation algorithm.

        Example:
            wand.reverse()
        """


    # -----------------------------------------------------
    # Shift current pixels
    # -----------------------------------------------------

    def shift(self, amount=1, wrap=True, show=False):
        """
        Move the current pixels along the strip.

        Positive amount:
            move toward higher LED numbers

        Negative amount:
            move toward lower LED numbers

        wrap=True:
            pixels leaving one end reappear at the other

        wrap=False:
            empty positions become black

        Useful for:
            scrolling
            trails
            moving textures
            cellular automata
            evolving patterns
        """


    # -----------------------------------------------------
    # Scale current pixel intensities
    # -----------------------------------------------------

    def scale_brightness(self, amount, show=False):
        """
        Multiply the brightness of the EXISTING pixels.

        Example:
            wand.scale_brightness(0.8)

        Unlike set_brightness(), this permanently modifies
        the pixel data itself.

        IDEALLY the fade() function below would call this once this is built

        Useful for:
            fades
            decay
            trails
            feedback effects
        """


    # -----------------------------------------------------
    # Draw a range of LEDs
    # -----------------------------------------------------

    def band(self, start, end, color, show=False):
        """
        Fill only a section of the strip with one color.

        Example:
            wand.band(20, 40, (255, 0, 0))

        Useful as a simple drawing primitive for composing
        more complex frames.
        """


    # -----------------------------------------------------
    # Draw a point or small group of LEDs
    # -----------------------------------------------------

    def dot(self, position, color, width=1, show=False):
        """
        Draw a point centered around a given LED position.

        width=1:
            one LED

        width=5:
            a small five-pixel mark

        Useful for:
            particles
            moving marks
            position indicators
            music visualization
            motion-reactive effects
        """


    # -----------------------------------------------------
    # Mirror part of a pattern
    # -----------------------------------------------------

    def mirror(self, show=False):
        """
        Mirror one half of the current pixel buffer onto
        the other half.

        Useful for symmetrical effects and especially handy
        for music/audio visualization.
        """


    # -----------------------------------------------------
    # Apply a pixel mask
    # -----------------------------------------------------

    def mask(self, mask_values, show=False):
        """
        Control which LEDs are visible without rebuilding
        the original frame.

        mask_values could contain numbers from 0.0 to 1.0.

        Example:
            1.0 = fully visible
            0.5 = half intensity
            0.0 = off

        This opens up a lot of interesting compositing ideas.
        """


    # -----------------------------------------------------
    # Add random variation
    # -----------------------------------------------------

    def noise(self, amount=0.1, show=False):
        """
        Add controlled random variation to the current colors.

        Useful for making generated imagery less mechanically
        perfect and introducing texture into light paintings.
        """

    # -----------------------------------------------------
    # Gradient
    # -----------------------------------------------------

    def gradient(self, color1, color2):

        r1, g1, b1 = color1
        r2, g2, b2 = color2

        for i in range(self.num_leds):

            t = i / max(1, self.num_leds - 1)

            self.set_pixel(
                i,
                r1 + (r2 - r1) * t,
                g1 + (g2 - g1) * t,
                b1 + (b2 - b1) * t
            )

        self.show()

    # -----------------------------------------------------
    # Rainbow
    # -----------------------------------------------------

    def rainbow(self, offset=0.0):

        for i in range(self.num_leds):

            hue = (
                i / self.num_leds + offset
            ) % 1.0

            r, g, b = colorsys.hsv_to_rgb(
                hue,
                1.0,
                1.0
            )

            self.set_pixel(
                i,
                r * 255,
                g * 255,
                b * 255
            )

        self.show()

    # -----------------------------------------------------
    # Fade existing pixels
    # -----------------------------------------------------

    def fade(self, amount=0.9):

        self.pixels = [
            (
                int(r * amount),
                int(g * amount),
                int(b * amount)
            )
            for r, g, b in self.pixels
        ]

    # -----------------------------------------------------
    # Wave
    # -----------------------------------------------------

    def wave(
        self,
        phase=0.0,
        color=(255, 255, 255),
        wavelength=20,
        background=(0, 0, 0)
    ):

        import math

        cr, cg, cb = color
        br, bg, bb = background

        for i in range(self.num_leds):

            value = (
                math.sin(
                    (i / wavelength) *
                    math.tau +
                    phase
                ) + 1
            ) / 2

            self.set_pixel(
                i,
                br + (cr - br) * value,
                bg + (cg - bg) * value,
                bb + (cb - bb) * value
            )

        self.show()

    # -----------------------------------------------------
    # Comet
    # -----------------------------------------------------

    def comet(
        self,
        position,
        color=(255, 255, 255),
        tail=15,
        fade_power=2.0
    ):

        self.blackout(show=False)

        for distance in range(tail):

            index = position - distance

            if 0 <= index < self.num_leds:

                brightness = (
                    1 - distance / tail
                ) ** fade_power

                r, g, b = color

                self.set_pixel(
                    index,
                    r * brightness,
                    g * brightness,
                    b * brightness
                )

        self.show()

    # -----------------------------------------------------
    # Sparkle
    # -----------------------------------------------------

    def sparkle(
        self,
        count=5,
        color=(255, 255, 255),
        fade_amount=0.8
    ):

        self.fade(fade_amount)

        for _ in range(count):

            index = random.randrange(
                self.num_leds
            )

            self.set_pixel(
                index,
                *color
            )

        self.show()

    # -----------------------------------------------------
    # Palette mapping
    # -----------------------------------------------------

    def palette(self, colors):

        if len(colors) < 2:
            raise ValueError(
                "Palette requires at least 2 colors"
            )

        segments = len(colors) - 1

        for i in range(self.num_leds):

            normalized = (
                i / max(1, self.num_leds - 1)
            )

            scaled = normalized * segments

            segment = min(
                int(scaled),
                segments - 1
            )

            local_t = scaled - segment

            c1 = colors[segment]
            c2 = colors[segment + 1]

            r = c1[0] + (
                c2[0] - c1[0]
            ) * local_t

            g = c1[1] + (
                c2[1] - c1[1]
            ) * local_t

            b = c1[2] + (
                c2[2] - c1[2]
            ) * local_t

            self.set_pixel(i, r, g, b)

        self.show()

    # -----------------------------------------------------
    # Cleanup
    # -----------------------------------------------------

    def close(self):
        try:
            self.blackout()
        finally:
            self.sock.close()

