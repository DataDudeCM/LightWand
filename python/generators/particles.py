"""
Particle braid generator.

A set of particles move inside a localized braid zone on the wand.
Each particle follows a periodic motion function and is rendered as
a soft glowing strand. Over time, the changing 1D LED pattern becomes
a braided light painting when the wand is swept through space.

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


def motion_value(
    phase,
    mode="sine",
    harmonic_mix=0.30,
    harmonic_multiple=3.0,
    mod_amount=0.50,
    mod_multiple=2.0,
    flatten_power=3.0,
):
    """
    Return a motion value in the range approximately -1..1.

    Modes
    -----
    sine:
        A clean sine wave.

    harmonic:
        A weighted sum of a base sine plus a higher harmonic.

    modulated:
        A sine wave with phase modulation.

    flattened:
        A sine wave shaped to linger more around the center.
    """

    if mode == "sine":
        value = math.sin(phase)

    elif mode == "harmonic":
        # A richer periodic shape
        value = (
            (1.0 - harmonic_mix) * math.sin(phase)
            + harmonic_mix * math.sin(phase * harmonic_multiple)
        )

    elif mode == "modulated":
        # Phase-modulated sine
        value = math.sin(
            phase + mod_amount * math.sin(phase * mod_multiple)
        )

    elif mode == "flattened":
        # Same sign as sine, but flatter near 0 for odd powers > 1
        base = math.sin(phase)
        value = math.copysign(abs(base) ** flatten_power, base)

    else:
        raise ValueError(f"Unknown motion mode: {mode!r}")

    return clamp(value, -1.0, 1.0)


def frames(
    seed=42,

    # particle structure
    num_particles=3,

    # localized braid zone
    braid_center=0.18,      # 0..1 along wand; 0 = tip
    braid_radius=0.14,      # half-width of active braid zone
    mirror=False,           # flip braid to opposite end

    # base motion timing
    period_frames=100,
    period_jitter=0.08,
    phase_spread=None,
    phase_jitter=0.0,
    amplitude_jitter=0.05,

    # motion function controls
    motion_mode="sine",     # one mode for all particles
    particle_modes=None,    # optional list/tuple: one mode per particle

    harmonic_mix=0.30,
    harmonic_multiple=3.0,

    mod_amount=0.50,
    mod_multiple=2.0,

    flatten_power=3.0,

    # optional extra wobble applied after motion_value
    secondary_amount=0.0,
    secondary_ratio=2.0,

    # appearance
    width=2.5,
    brightness=1.0,
    palette="industrialSun",

    # standard generator interface
    num_leds=100,
    start=0
):
    """
    Yield frames forever.

    Notes
    -----
    - braid_center and braid_radius localize the braid to one part
      of the wand.
    - motion_mode defines the path function for all particles unless
      particle_modes is provided.
    - particle_modes can be a list like:
          ["sine", "harmonic", "modulated"]
      and will cycle if shorter than num_particles.
    """

    if num_particles < 1:
        raise ValueError("num_particles must be at least 1")

    if num_leds < 1:
        raise ValueError("num_leds must be at least 1")

    if period_frames <= 0:
        raise ValueError("period_frames must be greater than 0")

    if width < 0:
        raise ValueError("width must be >= 0")

    rng = random.Random(seed)

    colors = PaletteLibrary().rgb_colors(palette)
    if not colors:
        raise ValueError(f"Unknown or empty palette: {palette}")

    if phase_spread is None:
        phase_spread = (2.0 * math.pi) / num_particles

    if particle_modes is not None:
        if not isinstance(particle_modes, (list, tuple)):
            raise ValueError("particle_modes must be a list or tuple")
        if len(particle_modes) == 0:
            raise ValueError("particle_modes cannot be empty")

    effective_center = 1.0 - braid_center if mirror else braid_center

    zone_min = max(0.0, effective_center - braid_radius)
    zone_max = min(1.0, effective_center + braid_radius)

    zone_center = 0.5 * (zone_min + zone_max)
    zone_radius = 0.5 * (zone_max - zone_min)

    if zone_radius <= 0:
        raise ValueError("braid_radius is too small or the zone collapsed")

    particles = []

    for i in range(num_particles):
        particle_period = period_frames * (
            1.0 + rng.uniform(-period_jitter, period_jitter)
        )

        particle_phase = (
            i * phase_spread
            + rng.uniform(-phase_jitter, phase_jitter)
        )

        particle_amplitude = 1.0 + rng.uniform(
            -amplitude_jitter,
            amplitude_jitter
        )

        if particle_modes is None:
            mode = motion_mode
        else:
            mode = particle_modes[i % len(particle_modes)]

        color = tuple(colors[i % len(colors)])

        particles.append({
            "period": particle_period,
            "phase": particle_phase,
            "amplitude": particle_amplitude,
            "mode": mode,
            "color": color,
        })

    def blend_add(existing, color, amount):
        amount = max(0.0, amount)
        return tuple(
            min(255, existing[c] + round(color[c] * amount))
            for c in range(3)
        )

    def add_particle(frame, position, color):
        """
        Paint a particle into the frame using a soft cosine brush.
        """
        if width == 0:
            index = round(position)
            if 0 <= index < num_leds:
                frame[index] = blend_add(frame[index], color, brightness)
            return

        low = max(0, math.floor(position - width))
        high = min(num_leds - 1, math.ceil(position + width))

        for led in range(low, high + 1):
            distance = abs(led - position)
            if distance > width:
                continue

            # center = 1.0, edge = 0.0
            strength = 0.5 + 0.5 * math.cos(math.pi * distance / width)

            frame[led] = blend_add(
                frame[led],
                color,
                strength * brightness
            )

    frame_number = start

    while True:
        frame = [(0, 0, 0) for _ in range(num_leds)]

        for i, particle in enumerate(particles):
            phase = (
                2.0 * math.pi * frame_number / particle["period"]
                + particle["phase"]
            )

            value = motion_value(
                phase,
                mode=particle["mode"],
                harmonic_mix=harmonic_mix,
                harmonic_multiple=harmonic_multiple,
                mod_amount=mod_amount,
                mod_multiple=mod_multiple,
                flatten_power=flatten_power,
            )

            # Optional extra wobble layered on top
            if secondary_amount:
                secondary_phase = phase * secondary_ratio + i * 0.73
                value += secondary_amount * math.sin(secondary_phase)
                value /= (1.0 + abs(secondary_amount))

            local_value = clamp(
                value * particle["amplitude"],
                -1.0,
                1.0
            )

            position_normalized = zone_center + zone_radius * local_value
            position_normalized = clamp(position_normalized, 0.0, 1.0)

            position = position_normalized * (num_leds - 1)

            add_particle(frame, position, particle["color"])

        yield frame
        frame_number += 1