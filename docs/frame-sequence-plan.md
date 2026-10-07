# Plan: frame sequences, previews, and generators

**Status:** steps 1–5 done (sequence format + `wand.play`; paint simulator
`preview.py` + viewer `preview_paint.py`; perlin generator + `wand.stream`;
flow viewer `preview_flow.py`; snapshots in the flow viewer). Step 3 live mode
not yet tried on the wand. Next: step 6, p5 `wand-capture.js`, once the first
*Nature of Code* sketch is picked.
**Date:** 2026-10-07

## Goal

Make it easy to create, preview, and play wand content of any kind: photos, text,
procedural effects (perlin, smoke, flame, automata), and *Nature of Code* sketches.

- **Pre-generate on the laptop by default.** Then optionally send the result to the wand,
  either painted once (like `image_paint` today) or looped continuously.
- **Live generation still works** for Python generators (endless smoke, flame, etc.).
- **Preview before shooting:**
  - a paint simulator: "what will the photo look like?"
  - a flow viewer: "what is the wand putting out over time?"
- **Snapshots:** spot a good moment in a flow and turn exactly that stretch into a painting.

Origin: discussion in the ChatGPT "Light Wand Improvements" thread (two-mode preview
idea), plus the decision to center everything on pre-generated sequences.

## Core idea: a frame sequence is an image

A sequence of 100-pixel frames is an image that is 100 pixels tall, with one column per frame.
This is the same "tip up, sweep right" layout that `image_frames` already produces.

A **FrameSequence** is saved as two files:

- `name.png`: the strip (100 px tall, N frames wide). It opens in any image viewer.
  A minute at 100 fps is 6,000 × 100 px, which is small.
- `name.json`: metadata, for example:

```json
{
  "fps": 100,
  "generator": "perlin",
  "params": {"x_scale": 0.08, "palette": "ember"},
  "seed": 999,
  "source": null,
  "notes": ""
}
```

Because the format is just a file, generators can be written in **Python or p5.js**.
Everything downstream (previews, wand playback) reads the same files.

## Architecture

```
Sources                      Artifact                   Outputs
───────                      ────────                   ───────
photo / text ─┐                                     ┌─ paint simulator
Python gen   ─┼─► FrameSequence (PNG + JSON) ───────┼─ flow viewer
p5.js sketch ─┘   (or a live frame iterator)        ├─ wand: paint once
                                                    └─ wand: loop / live
```

Rules:

- **Generators** produce frames and know nothing about the wand, timing, or orientation.
  Python generators are iterators that yield frames one at a time. The same code can fill a
  list for saving or drive the wand live. They must be deterministic given a seed.
- **Sequences** are always stored in the standard layout. Orientation (`TIP`/`SWEEP`)
  is applied at paint time by `image_frames.orient`, as it is today.
- **Playback** lives in `LightWand.play(frames, seconds, loop=False)`. This is the
  "extract on second use" step from the orientation plan, and this work is that second use.
- **Shoot setup** (countdown beeps, repeats, sweep printout) stays in the painting script.
- **Modes** (`bands`, `sparse_noise`, …) move to a shared `frame_effects` module. They
  transform a sequence, so they apply to any source.

## Where code goes

| Piece | Language | Location |
|---|---|---|
| FrameSequence (save/load/slice) | Python | `python/sequence.py` |
| Wand playback (`play`) | Python | `python/lightwand.py` |
| Picture → frames | Python | `python/image_frames.py` (unchanged) |
| Frame effects (modes) | Python | `python/frame_effects.py` |
| Python generators | Python | `python/generators/` |
| Paint simulator + flow viewer | Python | `python/preview.py` (or split later) |
| p5 capture helper | JS | `p5/wand-capture.js` |
| p5 generator sketches | JS | `p5/<sketch>/` |
| Painting script | Python | `python/image_paint.py`, slimmed to: load sequence/image → orient → play |

The p5 helper could move to `art/common/js/` later if art sketches start using it.
That's a cross-project decision, not part of this plan.

## Language decision

- **Python core:** sequences, playback, previews. These drive the wand and reuse
  `image_frames`, so they belong in one process with no bridge.
- **p5.js for *Nature of Code* generators:** stay close to the book, tweak live in the
  browser, and reuse `art/common/js/palette.js` and the Live Server workflow.
- **Python for other generators:** existing scripts are Python, and numpy is plenty for 100 px.

### How a p5 generator makes wand frames

Run the full 2D simulation on the canvas as usual. Each simulation step, sample **one
line of pixels** (for example a row across the canvas), resize it to 100 px, and append
it as a frame. `wand-capture.js` collects the frames and saves the PNG strip + JSON.

- Capture **one frame per simulation step**, not per wall-clock tick. Combined with
  `randomSeed`/`noiseSeed`, the output is then deterministic and snapshots are reproducible.
- Browser saves go to the Downloads folder. A sequences folder in the repo (or a
  gitignored `sequences/`) is where they should end up. To be decided in step 6.

### Live vs pre-generated

| | Python generator | p5 generator |
|---|---|---|
| Pre-generate → paint once / loop | yes | yes |
| Live, endless | yes (iterator → `play`) | needs a bridge (browser → websocket → Python → UDP). Later, only if needed |

## Previews

### Paint simulator

Places each frame where it would land in the photo, given:

- `TIP` / `SWEEP` (reuses the orientation logic)
- exposure length, sweep distance (`LIT_LENGTH_INCHES`)
- optional: LED spacing/gaps, diffusion blur, brightness accumulation, uneven speed

The orientation test from the previous plan already did the core placement. This step
grows it into a real tool that outputs a preview image.

Later additions (wanted, not in step 2):

- **Speed profiles:** uneven sweep speed (slow start, acceleration, pauses), e.g. to
  reproduce the squeezed top seen in real photos.
- **Preview from `image_paint`:** a `PREVIEW = True` setting that shows the simulated
  photo before shooting.

### Flow viewer

A window that shows the newest frame at the "wand" edge and scrolls older frames away
across the screen.

- Settings: scroll direction (follows `TIP`/`SWEEP`), pixels per frame (simulated speed),
  history length, blur.
- Plays a saved sequence or a live Python generator.
- Shows the current frame number / time so it's clear where you are.

### Snapshots

While watching a flow, press a key to mark a start and an end. The result:

- a slice of the sequence saved as a new strip + JSON (with `source` pointing to the
  original, the frame range, and the seed/params), and
- optionally opened in the paint simulator.

## Build order

1. **Sequence format + `wand.play`.** Save/load/slice, paint-once and loop playback.
   Refactor `image_paint` to use them (behavior unchanged).
2. **Paint simulator.**
3. **First Python generator.** Port `perlin_effect.py` to the generator interface.
4. **Flow viewer.**
5. **Snapshots.**
6. **p5 `wand-capture.js`**, once the first *Nature of Code* sketch is picked.
7. *(Optional, later)* p5 live bridge.
8. *(Optional, later)* upload a sequence to the ESP32 and play it from its own memory
   (works without the laptop, no Wi-Fi timing jitter). The file format shouldn't block this.

Each step should be usable on its own, and each gets its own small plan or commit.

**When the plan is done:** write a short "how to use" summary (generate, save, preview,
paint, stream) for the README.

## Decisions

- **Saved sequences** go in `sequences/` at the repo root, which is **gitignored**.
  They can be regenerated from the seed. A favorite can still be committed deliberately.
- **Timing:** one fps per sequence (stored in the JSON). Playback can stretch or
  compress to a chosen exposure length. Per-frame timing isn't needed for now.
- **Loop playback** runs until Ctrl+C, with an optional limit (loop count or seconds).
- **Viewer toolkit:** pygame (already installed, also used in `art/python/`). The paint
  simulator and the flow viewer share window code.

## Open questions

- Should LED brightness/gamma be modeled in the simulator so previews match photos?

## Not changing

- Firmware and the UDP frame protocol.
- `image_frames.py` and the `TIP`/`SWEEP` design.
- Brightness approach (DESIGN.md §5.3).
