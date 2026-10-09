"""
Smoke generator.

A 1D particle system designed specifically for the light wand.

Particles live on the wand's vertical LED slice, drift over time,
fade as they age, and are continuously respawned. When the wand is
swept through space, the temporal evolution of the 1D slice becomes
a smoke-like 2D light painting.

Deterministic:
    same seed + settings + start frame = same output

Generator contract:
    frames(..., start=N) yields frames forever
    each frame is a list of num_leds (r, g, b) tuples
    pixel 0 = physical tip of the wand
"""

import math
import random

from palette import PaletteLibrary


def clamp(value, low, high):
    return max(low, min(high, value))


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(edge0, edge1, x):
    if edge0 == edge1:
        return 0.0
    t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def blend_add(existing, color, amount):
    amount = max(0.0, amount)
    return tuple(
        min(255, existing[i] + round(color[i] * amount))
        for i in range(3)
    )


def blend_over(existing, color, amount):
    """
    Paint over what's there at partial opacity (amount 0..1).
    Dense smoke tends toward its color instead of adding up to white.
    """
    amount = clamp(amount, 0.0, 1.0)
    return tuple(
        round(existing[i] + (color[i] - existing[i]) * amount)
        for i in range(3)
    )


BLENDS = {"add": blend_add, "over": blend_over}


def desaturate(color, saturation):
    """Mix a color toward its grey: 0 = grey, 1 = unchanged."""
    if saturation == 1.0:
        return color
    grey = 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]
    return tuple(
        round(clamp(grey + (c - grey) * saturation, 0, 255))
        for c in color
    )


def sample_palette_gradient(colors, t):
    """
    Sample smoothly between palette colors.
    t expected in 0..1
    """
    if not colors:
        return (255, 255, 255)

    if len(colors) == 1:
        return tuple(colors[0])

    t = clamp(t, 0.0, 1.0)
    scaled = t * (len(colors) - 1)
    i0 = int(math.floor(scaled))
    i1 = min(i0 + 1, len(colors) - 1)
    f = scaled - i0

    c0 = colors[i0]
    c1 = colors[i1]

    return tuple(
        round(lerp(c0[ch], c1[ch], f))
        for ch in range(3)
    )


def value_noise_1d(x, seed_offset=0):
    """
    Cheap deterministic smooth-ish 1D value noise in approximately -1..1.
    """
    x0 = math.floor(x)
    x1 = x0 + 1

    def rand_at(i):
        # integer hash -> deterministic pseudorandom 0..1
        n = i * 374761393 + seed_offset * 668265263
        n = (n ^ (n >> 13)) * 1274126177
        n = n ^ (n >> 16)
        return (n & 0xFFFFFFFF) / 0xFFFFFFFF

    v0 = rand_at(x0)
    v1 = rand_at(x1)

    f = x - x0
    f = f * f * (3.0 - 2.0 * f)  # smooth interpolation

    value = lerp(v0, v1, f)
    return value * 2.0 - 1.0


def flow_noise(y_norm, frame_number, time_scale, spatial_scale, seed):
    """
    Smooth field varying over position and time.
    """
    x = y_norm * spatial_scale + frame_number * time_scale
    n1 = value_noise_1d(x, seed_offset=seed + 11)
    n2 = value_noise_1d(x * 1.91 + 17.3, seed_offset=seed + 29)
    n3 = value_noise_1d(x * 3.73 - 9.4, seed_offset=seed + 53)

    # weighted sum, still roughly -1..1
    return (0.55 * n1 + 0.30 * n2 + 0.15 * n3)


def make_particle(
    rng,
    colors,
    frame_number,
    source_center,
    source_spread,
    upward_drift,
    turbulence,
    lifetime_frames,
    lifetime_jitter,
    speed_jitter,
    width,
    width_jitter,
    brightness,
    brightness_jitter,
    color_drift,
):
    """
    Create one particle.
    All particle values are normalized to 0..1 in vertical position space.
    """

    position = clamp(
        rng.gauss(source_center, source_spread),
        0.0,
        1.0
    )

    # Upward drift in normalized wand units per frame
    velocity = upward_drift * (1.0 + rng.uniform(-speed_jitter, speed_jitter))

    lifetime = max(
        2,
        round(lifetime_frames * (1.0 + rng.uniform(-lifetime_jitter, lifetime_jitter)))
    )

    particle_width = max(
        0.25,
        width * (1.0 + rng.uniform(-width_jitter, width_jitter))
    )

    particle_brightness = max(
        0.0,
        brightness * (1.0 + rng.uniform(-brightness_jitter, brightness_jitter))
    )

    color_anchor = clamp(
        position + rng.uniform(-color_drift, color_drift),
        0.0,
        1.0
    )

    color = sample_palette_gradient(colors, color_anchor)

    return {
        "birth": frame_number,
        "age": 0,
        "lifetime": lifetime,
        "y": position,
        "vy": velocity,
        "width": particle_width,
        "brightness": particle_brightness,
        "color": color,
        # Per-particle shift used by color_mode="age" (same spread as
        # color_drift, no extra random draws so "position" output is unchanged).
        "color_offset": color_anchor - position,
        "turbulence_scale": turbulence * rng.uniform(0.8, 1.2),
        "noise_offset": rng.uniform(0.0, 1000.0),
    }


def respawn_particle(
    particle,
    rng,
    colors,
    frame_number,
    source_center,
    source_spread,
    upward_drift,
    turbulence,
    lifetime_frames,
    lifetime_jitter,
    speed_jitter,
    width,
    width_jitter,
    brightness,
    brightness_jitter,
    color_drift,
):
    new_particle = make_particle(
        rng=rng,
        colors=colors,
        frame_number=frame_number,
        source_center=source_center,
        source_spread=source_spread,
        upward_drift=upward_drift,
        turbulence=turbulence,
        lifetime_frames=lifetime_frames,
        lifetime_jitter=lifetime_jitter,
        speed_jitter=speed_jitter,
        width=width,
        width_jitter=width_jitter,
        brightness=brightness,
        brightness_jitter=brightness_jitter,
        color_drift=color_drift,
    )
    particle.clear()
    particle.update(new_particle)


def particle_opacity(particle):
    """
    Fade in briefly, then fade out over lifetime.
    """
    age = particle["age"]
    life = particle["lifetime"]

    # short fade-in (haze: a long one, so wide blobs don't pop in)
    if particle.get("soft_fade"):
        fade_in_frames = max(1, life // 4)
    else:
        fade_in_frames = min(5, max(1, life // 8))
    fade_in = smoothstep(0, fade_in_frames, age)

    # longer fade-out
    remaining = life - age
    fade_out_frames = min(max(8, life // 3), life)
    fade_out = smoothstep(0, fade_out_frames, remaining)

    return fade_in * fade_out


def particle_color(particle, colors, color_mode, saturation=1.0, age_color_span=1.0):
    """
    "position": the color picked at birth from where the particle
                was born along the wand (first palette colors near
                the tip).
    "age":      moves through the palette as the particle ages:
                first color when born, last color after
                age_color_span of its life (1.0 = as it dies; lower
                reaches the last color sooner and holds it while
                the particle fades, e.g. fire ending as grey smoke).
    """
    if color_mode == "position":
        color = particle["color"]
    else:
        t = (
            particle["age"] / (particle["lifetime"] * age_color_span)
            + particle["color_offset"]
        )
        color = sample_palette_gradient(colors, t)

    return desaturate(color, saturation)


def add_particle(
    frame,
    particle,
    num_leds,
    colors=None,
    color_mode="position",
    blend="add",
    saturation=1.0,
    age_color_span=1.0,
    boost=1.0,
):
    """
    Paint one particle into the frame with a soft cosine brush.
    boost multiplies its brightness (highlights).
    """
    y = particle["y"] * (num_leds - 1)
    width = particle["width"]
    color = particle_color(particle, colors, color_mode, saturation, age_color_span)
    blend_fn = BLENDS[blend]
    opacity = particle_opacity(particle) * particle["brightness"] * boost

    if opacity <= 0:
        return

    low = max(0, math.floor(y - width))
    high = min(num_leds - 1, math.ceil(y + width))

    for led in range(low, high + 1):
        distance = abs(led - y)
        if distance > width:
            continue

        if width <= 0:
            strength = 1.0
        else:
            strength = 0.5 + 0.5 * math.cos(math.pi * distance / width)

        frame[led] = blend_fn(frame[led], color, strength * opacity)


def update_particle(
    particle,
    frame_number,
    upward_bias,
    turbulence,
    curl_strength,
    time_scale,
    spatial_scale,
    bounce,
    noise_seed,
    drag=0.0,
    max_speed=0.03,
):
    """
    Advance one particle by one frame.

    drag:      fraction of the velocity lost each frame. Without it,
               forces pile up in the velocity and particles keep
               speeding up; with it they settle at a steady drift
               (about upward_bias / drag).
    max_speed: hard limit on speed, in wand lengths per frame.
    """
    y = particle["y"]

    # Two related noise samples, offset in space/time, act like
    # a crude flow field and keep nearby particles somewhat correlated.
    n1 = flow_noise(
        y + particle["noise_offset"] * 0.001,
        frame_number,
        time_scale=time_scale,
        spatial_scale=spatial_scale,
        seed=noise_seed
    )
    n2 = flow_noise(
        y + 0.37 + particle["noise_offset"] * 0.001,
        frame_number + 17,
        time_scale=time_scale * 0.83,
        spatial_scale=spatial_scale * 1.17,
        seed=noise_seed + 101
    )

    # Noise influences velocity; second field adds curl-ish wobble
    accel = upward_bias
    accel += n1 * particle["turbulence_scale"] * 0.0035
    accel += n2 * curl_strength * 0.0020

    particle["vy"] = particle["vy"] * (1.0 - drag) + accel
    particle["vy"] = clamp(particle["vy"], -max_speed, max_speed)

    particle["y"] += particle["vy"]

    # soft bounce / containment so particles can curl back instead
    # of instantly dying at boundaries
    if bounce:
        if particle["y"] < 0.0:
            particle["y"] = -particle["y"]
            particle["vy"] *= -0.45
        elif particle["y"] > 1.0:
            particle["y"] = 2.0 - particle["y"]
            particle["vy"] *= -0.45
    else:
        particle["y"] = clamp(particle["y"], 0.0, 1.0)

    particle["age"] += 1


def frames(
    seed=42,

    # particle structure
    num_particles=45,

    # where particles are born, 0..1 along wand; 0 = tip
    source_center=0.22,
    source_spread=0.08,

    # motion
    upward_drift=0.0025,      # starting upward velocity
    upward_bias=0.00015,      # constant acceleration bias
    turbulence=1.0,           # overall turbulence amount
    curl_strength=0.8,        # secondary correlated wobble
    time_scale=0.045,         # noise time scale
    spatial_scale=8.0,        # noise spatial scale
    bounce=True,              # bounce at ends instead of hard clipping
    drag=0.15,                # velocity lost per frame: higher = slower, lazier smoke
    max_speed=0.03,           # speed limit, wand lengths per frame

    # lifespan
    lifetime_frames=90,
    lifetime_jitter=0.35,

    # appearance
    width=2.8,
    width_jitter=0.35,
    brightness=0.55,
    brightness_jitter=0.30,
    speed_jitter=0.35,
    color_drift=0.10,
    color_mode="position",    # "position" (by birth place) or "age" (through the palette as it ages)
    age_color_span=1.0,       # "age" mode: share of life to reach the last color (0.6 = hold it while fading)
    saturation=1.0,           # 0 = grey, 1 = full palette color
    blend="add",              # "add" (light adds up, glows) or "over" (smoke layers, never blows out)

    # haze: an optional second set of wide, dim, longer-lived particles
    # behind the wisps (0 = none). Uses its own random stream, so the
    # wisps are the same with or without it.
    haze_particles=0,
    haze_width=8.0,
    haze_brightness=0.15,
    haze_lifetime_scale=2.0,  # haze lives this many times longer
    haze_spread_scale=2.0,    # and is born over a wider area

    # highlights: a share of the wisps glow much brighter, drawn last
    # with "add" blending so they shine through the smoke (0 = none)
    highlight_fraction=0.0,
    highlight_boost=2.5,      # how much brighter a highlight wisp is
    palette="industrialSun",

    # standard generator interface
    num_leds=100,
    start=0
):
    """
    Yield frames forever.

    Conceptually:
        - particles are born in a localized source region
        - they drift and wobble along the 1D wand
        - they fade in and out over time
        - dead particles respawn
        - the resulting 1D slice can be swept through space to create
          smoke-like photographic forms

    Notes
    -----
    - `start` is supported by simulating forward from frame 0 so saved
      snapshots can be regenerated exactly.
    - horizontal structure in the final photograph comes from time and
      your physical wand movement, not from an x coordinate in code.
    """

    if num_particles < 1:
        raise ValueError("num_particles must be at least 1")

    if num_leds < 1:
        raise ValueError("num_leds must be at least 1")

    if lifetime_frames < 2:
        raise ValueError("lifetime_frames must be at least 2")

    if width < 0:
        raise ValueError("width must be >= 0")

    if color_mode not in ("position", "age"):
        raise ValueError(f"color_mode must be 'position' or 'age', got {color_mode!r}")

    if not 0.0 < age_color_span <= 1.0:
        raise ValueError("age_color_span must be in 0..1 (and above 0)")

    if not 0.0 <= highlight_fraction <= 1.0:
        raise ValueError("highlight_fraction must be in 0..1")

    if blend not in BLENDS:
        raise ValueError(f"blend must be one of {sorted(BLENDS)}, got {blend!r}")

    if haze_particles < 0:
        raise ValueError("haze_particles must be >= 0")

    if not 0.0 <= drag < 1.0:
        raise ValueError("drag must be in 0..1 (0 = none)")

    rng = random.Random(seed)

    colors = PaletteLibrary().rgb_colors(palette)
    if not colors:
        raise ValueError(f"Unknown or empty palette: {palette}")

    # How each group is born: the wisps use the main settings; the
    # haze is wider, dimmer, longer-lived and born over a wider area.
    wisp_spawn = dict(
        colors=colors,
        source_center=source_center,
        source_spread=source_spread,
        upward_drift=upward_drift,
        turbulence=turbulence,
        lifetime_frames=lifetime_frames,
        lifetime_jitter=lifetime_jitter,
        speed_jitter=speed_jitter,
        width=width,
        width_jitter=width_jitter,
        brightness=brightness,
        brightness_jitter=brightness_jitter,
        color_drift=color_drift,
    )
    haze_spawn = dict(
        wisp_spawn,
        source_spread=source_spread * haze_spread_scale,
        lifetime_frames=max(2, round(lifetime_frames * haze_lifetime_scale)),
        width=haze_width,
        brightness=haze_brightness,
    )

    wisps = [
        make_particle(rng=rng, frame_number=0, **wisp_spawn)
        for _ in range(num_particles)
    ]

    haze_rng = random.Random(f"{seed}-haze")
    haze = [
        make_particle(rng=haze_rng, frame_number=0, **haze_spawn)
        for _ in range(haze_particles)
    ]

    for particle in haze:
        particle["soft_fade"] = True

    # (particles, their random stream, how they're born)
    groups = [(haze, haze_rng, haze_spawn), (wisps, rng, wisp_spawn)]

    def step(frame_number):
        for particles, group_rng, spawn in groups:
            for particle in particles:
                update_particle(
                    particle=particle,
                    frame_number=frame_number,
                    upward_bias=upward_bias,
                    turbulence=turbulence,
                    curl_strength=curl_strength,
                    time_scale=time_scale,
                    spatial_scale=spatial_scale,
                    bounce=bounce,
                    noise_seed=seed,
                    drag=drag,
                    max_speed=max_speed,
                )

                expired = particle["age"] >= particle["lifetime"]
                faded_out = (not bounce) and (
                    particle["y"] <= 0.0 or particle["y"] >= 1.0
                )

                if expired or faded_out:
                    respawn_particle(
                        particle=particle,
                        rng=group_rng,
                        frame_number=frame_number,
                        **spawn
                    )
                    if particles is haze:
                        particle["soft_fade"] = True

    def is_highlight(particle):
        """
        About highlight_fraction of the wisps, picked from a value each
        particle already has (no extra random draws, so output with
        highlights off is unchanged). A new pick on every respawn.
        """
        return (particle["noise_offset"] * 7.919) % 1.0 < highlight_fraction

    # Advance to requested start frame so snapshots regenerate correctly.
    frame_number = 0
    while frame_number < start:
        step(frame_number)
        frame_number += 1

    while True:
        frame = [(0, 0, 0) for _ in range(num_leds)]

        # Haze first, so the wisps are painted over it; highlights last,
        # glowing on top of everything.
        highlights = []

        for particles, _, _ in groups:
            for particle in particles:
                if particles is wisps and is_highlight(particle):
                    highlights.append(particle)
                    continue

                add_particle(
                    frame, particle, num_leds,
                    colors, color_mode, blend, saturation,
                    age_color_span
                )

        for particle in highlights:
            add_particle(
                frame, particle, num_leds,
                colors, color_mode, "add", saturation,
                age_color_span, boost=highlight_boost
            )

        yield frame

        step(frame_number)
        frame_number += 1
