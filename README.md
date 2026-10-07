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
* Save, preview and paint frame sequences from images, Python generators or p5 sketches
* Preview on screen without the wand: a scrolling flow view and a simulated photo
* Adjust playback timing to match camera exposure and physical wand movement
* OTA ESP32 firmware updates over Wi-Fi
* Fully untethered operation during photography

## Python Setup

The scripts in `python/` use a virtual environment in `.venv/` (not committed). One-time setup from the repo root, using Python 3.12:

```text
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

Run scripts from `python/` with the venv's Python, e.g. `..\.venv\Scripts\python paint.py`, or select `.venv` as the interpreter in VS Code (the workspace file already points to it).

## How to Use

Each script has its settings at the top (`EASY CONTROLS`): edit them, then run the script from `python/`.

Content for the wand is a **frame sequence**: a PNG strip (one column per frame, 100 px tall, top row = the tip) plus a JSON with the fps and how it was made. Sequences live in `sequences/` (gitignored, since they can be regenerated). Images work too, anywhere a sequence does.

The usual flow is **make → watch → preview the photo → paint**.

### 1. Make content

| Source | How |
|---|---|
| Image | Nothing to do: use the image's path as `INPUT_FILE` below. |
| Python generator | Run it in `generate.py` (below) and press `S` to save. Built in: `perlin` (noise field), `automaton` (1D cellular automaton, e.g. rule 30 or 90), `particles` (strands braiding in one zone of the wand, with several motion shapes) and `particles_physics` (the same braid with attraction, repulsion and momentum). Example settings for each are in `generate.py`. New generators go in `python/generators/`: a module with `frames(seed, ..., start=0)` that yields frames forever, the same frames for the same seed, beginning at frame `start`. |
| p5 sketch | In the art repo, use `common/js/wand-capture.js` (see `art/docs/wand-capture.md`). Move the PNG + JSON from Downloads into `sequences/`. |

### 2. Watch it or run it live: `generate.py`

Runs a generator continuously (or loops a saved sequence) until you stop it. Set `GENERATOR` and `GENERATOR_SETTINGS`, or `INPUT_FILE` for a sequence.

- `OUTPUT = "screen"`: the flow view. The newest frame is at the edge and older frames scroll away. No wand needed.
- `OUTPUT = "wand"`: streams to the wand until Ctrl+C (which blacks it out). No window.
- `OUTPUT = "both"`: the flow view, with the wand showing the same frames. Pausing holds the frame on the wand; stepping sends the one you step to. For photos, save and use `paint.py`, which has exact timing.

Keys: arrows / space = orientation, `P` pause, `,` `.` step, `+` `-` speed, `G` LED gaps.
**Saving:** `[` mark start, `]` mark end, `S` save the range to `sequences/` (with no marks, `S` saves everything played so far), `O` open it in the paint preview.

### 3. Preview and paint it: `paint.py`

One fixed-length exposure of an image or a sequence.

- `OUTPUT = "screen"`: a simulated photo to adjust before shooting. No wand needed.
- `OUTPUT = "wand"`: paint it. Press ENTER, then follow the countdown beeps and start moving on "go".
- `OUTPUT = "both"`: preview first, adjust with the keys, then press ENTER in the window to paint exactly that. The window comes back afterwards for another shot.

```text
..\.venv\Scripts\python paint.py                                uses INPUT_FILE and OUTPUT
..\.venv\Scripts\python paint.py ..\sequences\NAME              any image or sequence
..\.venv\Scripts\python paint.py ..\sequences\NAME --output both
```

Settings:

- `INPUT_FILE`: an image or a sequence.
- `EXPOSURE_SECONDS`: for a sequence, `None` plays it at its own length; a number stretches it.
- `TIP` / `SWEEP`: where the tip points and which way you move, **as seen by the camera**. The script prints how far to sweep.
- `MODE`: `full_field`, `sparse_random`, `sparse_noise` or `bands` (from `frame_effects.py`), tuned in `MODE CONTROLS`.

Keys: arrows / space = orientation, `+` `-` sweep length, `R` reset, `G` gaps, `B` blur, `M` next mode, `S` save a PNG to `previews/`, `ENTER` paint (both).

The wand is found automatically on the network; set `WAND_IP` if that fails.

### Settings worth knowing

- **`WAND_GAMMA = 2.2`** (default): makes the wand's colors match the previews. `1.0` turns it off.
- **`WAND_BRIGHTNESS`**: keep it high and dim the photo with the camera (aperture / ISO / ND). Low values make gradients steppy. See `docs/DESIGN.md` §5.3.

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
