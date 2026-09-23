# Light Wand

A programmable LED light-painting system combining Python, Wi-Fi, an ESP32, and a 100-pixel WS2812B LED strip.

The Light Wand is an experimental photographic instrument. Instead of treating the LEDs simply as an animated light source, the system treats the wand as a moving one-dimensional display.

Python generates a sequence of 100-pixel RGB frames and streams them over Wi-Fi to an ESP32. The ESP32 displays those frames on the LED strip while the wand is physically moved through space.

During a long-exposure photograph, that movement supplies the second spatial dimension and turns the changing LED patterns into a two-dimensional image.

## Architecture

```text
Python
   |
   | Wi-Fi / UDP
   v
ESP32
   |
   | GPIO 27
   v
100-pixel WS2812B LED strip
   |
   | physical movement
   v
Long-exposure photograph
```

## Current Hardware

* ESP32 development board
* 100 WS2812B individually addressable LEDs
* GPIO 27 LED data output
* ~330 ohm data-line resistor
* 5V USB-C power system
* Portable battery-powered construction
* Black wooden wand support

## Current Capabilities

* Control all 100 LEDs individually
* Stream RGB frames from Python over Wi-Fi using UDP
* Generate animated LED effects
* Stream image slices for persistence-of-vision/light-painting photography
* Adjust playback timing to match camera exposure and physical wand movement
* OTA ESP32 firmware updates over Wi-Fi
* Fully untethered operation during photography

## Image Painting

An image can be resized to match the 100-pixel height of the wand and divided into vertical slices.

Each slice becomes one LED frame:

```text
Image

| slice 1 |
| slice 2 |
| slice 3 |
|   ...   |
| slice N |
```

Python transmits the slices sequentially while the wand moves across the camera's field of view.

For example, a 3-second exposure using 100 slices requires approximately:

```text
3 seconds / 100 slices = 30 ms per slice
```

Physical movement, timing, rotation, acceleration, and imperfections can intentionally become part of the resulting image.

## Creative Direction

The goal isn't merely to reproduce images accurately.

The wand is intended as an experimental instrument combining:

**code + light + motion + time + photography**

Possible experiments include:

* Image painting
* Procedural and generative imagery
* Abstract light painting
* Music visualization
* Motion-reactive patterns
* Multiple-pass compositions
* Pendulum painting
* Geometric light structures
* Intentional image distortion
* Algorithmic patterns generated live in Python

Future versions may incorporate an IMU so actual wand movement can influence or synchronize the generated imagery.

## Wi-Fi Configuration

Wi-Fi credentials are intentionally excluded from the repository.

Copy:

```text
secrets.example.h
```

to:

```text
secrets.h
```

and enter the local Wi-Fi credentials there.

`secrets.h` is excluded through `.gitignore`.

## Status

Working prototype.

The full 100-LED wand can currently receive RGB frames from Python over Wi-Fi and operate untethered.

The next phase is less about adding hardware and more about discovering what kinds of images emerge from the interaction between software and physical movement.
