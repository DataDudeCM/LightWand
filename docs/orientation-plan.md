# Plan: wand orientation (TIP / SWEEP)

**Status:** done. The orientation table passed a simulation of all 8 combinations
and worked on camera (`TIP="left", SWEEP="down"`). Decisions are recorded in DESIGN.md §10.1
and §15. The banding seen during testing was low LED brightness + dithering, not
orientation (see DESIGN.md §5.3). The out-of-scope items below are still open.
**Date:** 2026-10-06

## Goal

Paint an image (or, later, text) with the wand held either way:

- vertical, swept sideways (what the scripts assume today)
- horizontal, swept up or down

The result should come out upright in the photo either way.

## Key facts

- **Pixel 0 is at the tip** (the far end from the electronics). See DESIGN.md §7.1.
- Today `image_paint.py` sends image row 0 (the top of the image) to pixel 0. Held
  vertically with the tip up, that's already correct, so no flip is needed in the base class.
- What actually changes between setups is **how the wand is held and moved**,
  not the wiring.

## Settings

Two settings, both described **as seen by the camera** (in the final photo):

| Setting | Values | Meaning |
|---|---|---|
| `TIP` | `"up"`, `"down"`, `"left"`, `"right"` | where the tip (pixel 0) points in the photo |
| `SWEEP` | `"right"`, `"left"`, `"down"`, `"up"` | which way the wand moves across the photo |

- `SWEEP` must be perpendicular to `TIP`. Sweeping along the wand's own axis is an error.
- That gives 8 valid combinations.
- The "camera's view" rule matters. If you face the camera, *your* right is the
  camera's left. With text, getting this wrong mirrors the letters.
- Today's behavior (`REVERSE = False`) = `TIP="up", SWEEP="right"`.
  `REVERSE = True` = `TIP="up", SWEEP="left"`.

## How it works

Turn the source image into one standard layout ("tip up, sweep right") first. Then slice
it exactly as the code does now: one column per frame, left to right, row 0 → pixel 0.

| TIP | SWEEP | PIL operation on the source image |
|---|---|---|
| up | right | none |
| up | left | `FLIP_LEFT_RIGHT` |
| down | right | `FLIP_TOP_BOTTOM` |
| down | left | `ROTATE_180` |
| left | down | `TRANSPOSE` |
| left | up | `ROTATE_270` |
| right | down | `ROTATE_90` |
| right | up | `TRANSVERSE` |

The table above is worked out on paper. The test image step below confirms it.

The resize to `(num_slices, num_leds)` happens **after** this step, so the LED axis
always gets 100 pixels whichever way the image was turned.

## File changes

1. **New `python/image_frames.py`**: a shared helper with no wand or network code.
   - `orient(image, tip, sweep)`: checks the combination, applies the operation from the table.
   - `to_frames(image, num_slices, num_leds)`: resizes and returns a list of frames
     (each a list of 100 `(r, g, b)`).
   - Takes a **PIL image, not a filename**, so a future text script can render words
     in memory and use the same path.
2. **`python/image_paint.py`**
   - Replace `REVERSE` with `TIP` / `SWEEP` in EASY CONTROLS (default `"up"` / `"right"`).
   - `prepare_image` loads the file, then calls `orient` and `to_frames`.
   - `get_column_pixels` and its `reverse` argument go away. The display loop
     iterates over the frame list. The modes (`bands`, `sparse_noise`, etc.) are
     unchanged, since they already work per slice.
3. **`python/lightwand.py`**: comment only. State that pixel 0 is at the tip.
   No `flip` option for now. Add it only if the strip is ever rewired.
4. **`python/image_paint_v0.py`**: not changed. It's being removed.
5. **After it works:** add the decisions to DESIGN.md §15. In §10 note that
   "vertical slices" are now just the default layout. Update the README if it
   describes `REVERSE`.

## Testing

1. Make a test image of a large letter **F** (it shows both rotation and
   mirroring), plus a color mark in one corner.
2. Dry run without the wand: have the helper save the oriented image for each
   of the 8 combinations, and check that each one looks right.
3. On camera: shoot at least the combinations you'll really use
   (`up/right`, `left/down` or `right/down`). The F should read correctly in the photo.

## Out of scope (later)

- **Aspect ratio.** Stroke length and exposure time decide whether the image
  is squashed. A vertical sweep is usually shorter than a sideways walk. A
  target-aspect or stroke-length setting is a separate step.
- **Text painting script.** It renders text to an image and then uses `image_frames`.
- **Move shared code out when a second script needs it** (probably the text script).
  Until then it stays in `image_paint.py`:
  - **Timed playback** (the frame loop with absolute timing in `display_frames`) →
    a `LightWand` method, e.g. `wand.play(frames, seconds)`. It drives the LEDs and
    has no image knowledge. Repeats, pauses, blanking and printouts stay in each script.
  - **Modes** (`apply_mode` and the `apply_*` functions) → a shared `frame_effects` module.
  - **Color / noise helpers** (`clamp`, `scale_color`, `value_noise_2d`, ...) also look
    duplicated in `wand_variations.py`. They could become a shared module too.
  - Keep `image_frames` pure: picture → frames, with no wand, timing or file loading.
- **Procedural scripts** (perlin, double_helix, wand_variations) have no source
  image. Holding the wand differently simply rotates them. Revisit only if one
  needs a fixed "up."

## When the helper is used

- **Use it for content that starts as a whole picture:** images, text, anything you can
  render to an image before the exposure starts.
- **It's called once, during setup, before the exposure.** It's not called on every frame.
  The display loop just plays the frame list on the timer.
- **Live effects** (`test_effects.py`, perlin, etc.) build frames one at a time and don't
  use it. If one needs a fixed direction:
  - along the wand: flip the pixel order in each frame (works live)
  - along the sweep: generate all frames first, stack them into an image
    (one column per frame), then put that image through the helper

## Decisions

- `image_paint_v0.py` is being removed, so it isn't changed.
- If `TIP` and `SWEEP` don't fit together, fall back to `TIP="up", SWEEP="right"`
  and print a warning.
- Modes (`bands`, `sparse_noise`, ...) run **after** orientation, so they follow the wand,
  not the picture. That's intended: wavy bands always run along the sweep.
