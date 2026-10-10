# Plan: light portraits (noise glow + palette tint)

**Status:** built (2026-10-09): `noise_glow`, `palette_tint`, `neonPortrait` palette, list
`MODE` and per-pass sparkles in `paint.py`. Not yet tried on the wand.

**Decisions:** new sparkles each repeat pass (`NEW_SPARKLES_EACH_PASS = True`); added a
`neonPortrait` palette (blue → violet → magenta → pink → pale pink, also in art's
`palette.js`); background removal stays in the photo editor for now.

**Findings from the first test portrait (simulated):** crop so the face fills most of the
100 LEDs (biggest improvement); the default glow is subtle, `base_level 0.5`,
`peak_level 1.5`, `sparkle_chance 0.2`, `sparkle_strength 0.75` gives clearer patches and
flecks; `palette_tint` suits natural-color / black-and-white portraits, not already
gradient-mapped ones.

## Goal

Paint my portrait photos with the wand: the subject floating on black, its own colors
dimmed slightly, with brighter patches and flickering sparkles where a noise field peaks,
and optionally a color grade (e.g. blue shadows, pink highlights). Reference: a light
portrait with streaky lines, pink/blue color and bright flecks around the eyes and
shoulders.

## How a portrait is painted

- **Vertically:** wand held horizontally, moved top to bottom: `TIP = "left"` (or
  `"right"`), `SWEEP = "down"` in `paint.py` (already the default). The 100 LEDs span the
  portrait's **width**; its height is the number of frames (`EXPOSURE_SECONDS * FPS`, e.g.
  3 s × 100 = 300 rows). `paint.py` prints how far to sweep for correct proportions.
- **Background:** removed before painting and made pure black, so the wand is dark there.
  Done outside this code (photo editor export, or the `rembg` Python tool). Not part of
  this plan.
- The streaky lines come for free from the LED gaps; hand wobble adds the waviness.

## 1. `noise_glow` effect (`frame_effects.py`)

A noise field over the portrait (frame index × LED). Everywhere, the portrait shows at
`base_level`; inside the noise peaks it brightens; within the peaks a random subset of
pixels sparkles.

| Setting | Default | Meaning |
|---|---|---|
| `base_level` | 0.6 | brightness of the portrait outside the peaks (leaves headroom: LEDs top out at 255) |
| `threshold` | 0.6 | noise height where peaks start (higher = fewer, smaller patches) |
| `soft_edge` | 0.08 | fade from base to peak brightness below the threshold |
| `blob_size` | 0.15 | size of the noise patches, as a fraction of the wand length |
| `peak_level` | 1.0 | brightness inside the peaks |
| `sparkle_chance` | 0.12 | share of peak pixels that sparkle |
| `sparkle_color` | `None` | `None` = the pixel's own color pushed toward white; or an RGB |
| `sparkle_strength` | 0.6 | how far toward white (or `sparkle_color`) a sparkle goes |
| `subject_threshold` | 10 | pixels darker than this count as background: never brightened or sparkled |
| `seed` | 7 | noise and sparkle pattern (reproducible) |

- **Round patches in the photo.** Frames and LEDs have different spacing in the photo,
  so the noise is scaled by the aspect (sweep length vs wand length). `paint.py` passes
  it in automatically.
- **Sparkles are deterministic:** a hash of (seed, frame, LED), so a shot can be repeated.
- **Background stays black:** a pixel at or below `subject_threshold` is left as is.

## 2. `palette_tint` effect (`frame_effects.py`, optional)

Recolor the portrait by brightness through a palette gradient (dark → first color,
bright → last), keeping each pixel's brightness, so black stays black.

| Setting | Default | Meaning |
|---|---|---|
| `palette` | `"duskSmoke"` | palette in `palettes.json` (a pink/blue one could be added) |
| `amount` | 0.7 | 0 = original colors, 1 = fully tinted |

## 3. `paint.py`

- `MODE` can be one mode or a list applied in order, e.g.
  `MODE = ["palette_tint", "noise_glow"]`. M still cycles single modes.
- `MODE CONTROLS` gets sections for both effects.
- The paint preview shows them, so a portrait can be tuned on screen before shooting.

## Testing (no wand)

- Background (black) pixels stay black with both effects.
- `base_level` dims the subject; peaks reach `peak_level`; sparkles only inside peaks and
  inside the subject; about `sparkle_chance` of peak pixels sparkle.
- Deterministic for a seed; a different seed gives different patches and sparkles.
- Patches come out round in the paint preview at a few sweep lengths.
- `palette_tint` keeps brightness and black; `amount` 0 = unchanged.
- Existing modes and `MODE` as a single name behave exactly as before.
- Preview renders on a test portrait with a black background.

## Open questions

1. Repeats: the same sparkles on every pass (`REPEATS_PER_MODE`), or new ones each pass?
2. A pink/blue palette for the tint (e.g. `neonPortrait`), or start with existing ones?
3. Background removal: a small `rembg` helper script later, or keep it in the photo editor?
