"""
Particle braid with attraction and repulsion.

Each particle has:
- a sine-wave target position
- position and velocity
- attraction / repulsion forces from other particles

The sine wave provides structure.
The particle physics introduces organic deviation.

Deterministic for the same seed/settings.

Note:
Because this generator is stateful, start=N is reproduced by
simulating frames 0..N internally before yielding frame N.
"""

import math
import random

from palette import PaletteLibrary


def frames(
    seed=42,
    num_particles=3,

    # braid location
    braid_center=0.18,
    braid_radius=0.14,
    mirror=False,

    # underlying sine motion
    period_frames=100,
    period_jitter=0.03,
    phase_spread=None,

    # particle physics
    anchor_strength=0.08,
    attraction_strength=0.015,
    repulsion_strength=0.20,
    interaction_distance=0.10,
    repulsion_distance=0.035,
    damping=0.90,
    max_speed=0.025,

    # appearance
    width=2.5,
    brightness=1.0,
    palette="industrialSun",

    # generator interface
    num_leds=100,
    start=0
):
    """
    Yield frames forever.

    Positions and distances are normalized to 0..1 across the wand.

    anchor_strength:
        Pull toward each particle's underlying sine-wave path.

    attraction_strength:
        Pull particles toward one another at medium range.

    repulsion_strength:
        Push particles apart when they get too close.

    interaction_distance:
        Maximum distance at which attraction operates.

    repulsion_distance:
        Distance inside which repulsion becomes active.

    damping:
        Velocity retained each frame.
        Smaller = calmer / less momentum.
        Larger = more fluid / springy.

    max_speed:
        Maximum position change per frame.
    """

    if num_particles < 1:
        raise ValueError("num_particles must be at least 1")

    rng = random.Random(seed)

    colors = PaletteLibrary().rgb_colors(palette)

    if not colors:
        raise ValueError(f"Unknown or empty palette: {palette}")

    if phase_spread is None:
        phase_spread = 2.0 * math.pi / num_particles

    center = 1.0 - braid_center if mirror else braid_center

    zone_min = max(0.0, center - braid_radius)
    zone_max = min(1.0, center + braid_radius)

    zone_center = (zone_min + zone_max) / 2.0
    zone_radius = (zone_max - zone_min) / 2.0

    particles = []

    # --------------------------------------------------------
    # Create particles
    # --------------------------------------------------------

    for i in range(num_particles):

        period = period_frames * (
            1.0 + rng.uniform(-period_jitter, period_jitter)
        )

        phase = i * phase_spread

        # Start each particle directly on its sine path.
        value = math.sin(phase)

        position = zone_center + zone_radius * value

        particles.append({
            "position": position,
            "velocity": 0.0,
            "period": period,
            "phase": phase,
            "color": tuple(colors[i % len(colors)])
        })

    # --------------------------------------------------------
    # Rendering helpers
    # --------------------------------------------------------

    def blend_add(existing, color, amount):

        return tuple(
            min(
                255,
                existing[channel]
                + round(color[channel] * amount)
            )
            for channel in range(3)
        )

    def add_particle(frame, position, color):

        led_position = position * (num_leds - 1)

        low = max(
            0,
            math.floor(led_position - width)
        )

        high = min(
            num_leds - 1,
            math.ceil(led_position + width)
        )

        for led in range(low, high + 1):

            distance = abs(led - led_position)

            if distance > width:
                continue

            strength = (
                0.5
                + 0.5
                * math.cos(
                    math.pi * distance / width
                )
            )

            frame[led] = blend_add(
                frame[led],
                color,
                strength * brightness
            )

    # --------------------------------------------------------
    # Physics
    # --------------------------------------------------------

    def step(frame_number):

        accelerations = [0.0] * num_particles

        # --------------------------------
        # Sine-wave anchor force
        # --------------------------------

        for i, p in enumerate(particles):

            phase = (
                2.0
                * math.pi
                * frame_number
                / p["period"]
                + p["phase"]
            )

            target = (
                zone_center
                + zone_radius * math.sin(phase)
            )

            # Spring force toward the ideal sine path
            accelerations[i] += (
                target - p["position"]
            ) * anchor_strength

        # --------------------------------
        # Particle-particle interaction
        # --------------------------------

        for i in range(num_particles):

            for j in range(i + 1, num_particles):

                a = particles[i]
                b = particles[j]

                delta = (
                    b["position"]
                    - a["position"]
                )

                distance = abs(delta)

                if distance < 0.000001:
                    # deterministic tiny separation
                    direction = 1.0 if i < j else -1.0
                    distance = 0.000001

                else:
                    direction = (
                        1.0 if delta > 0 else -1.0
                    )

                # ------------------------
                # REPULSION
                # ------------------------

                if distance < repulsion_distance:

                    strength = (
                        1.0
                        - distance / repulsion_distance
                    )

                    force = (
                        repulsion_strength
                        * strength
                    )

                    accelerations[i] -= (
                        direction * force
                    )

                    accelerations[j] += (
                        direction * force
                    )

                # ------------------------
                # ATTRACTION
                # ------------------------

                elif distance < interaction_distance:

                    # strongest around the middle
                    # of the attraction zone

                    normalized = (
                        distance - repulsion_distance
                    ) / (
                        interaction_distance
                        - repulsion_distance
                    )

                    force = (
                        attraction_strength
                        * math.sin(
                            math.pi * normalized
                        )
                    )

                    accelerations[i] += (
                        direction * force
                    )

                    accelerations[j] -= (
                        direction * force
                    )

        # --------------------------------
        # Integrate movement
        # --------------------------------

        for i, p in enumerate(particles):

            p["velocity"] += accelerations[i]

            p["velocity"] *= damping

            p["velocity"] = max(
                -max_speed,
                min(
                    max_speed,
                    p["velocity"]
                )
            )

            p["position"] += p["velocity"]

            # Keep particles inside braid zone.
            # Bounce softly off boundaries.

            if p["position"] < zone_min:

                p["position"] = zone_min
                p["velocity"] *= -0.5

            elif p["position"] > zone_max:

                p["position"] = zone_max
                p["velocity"] *= -0.5

    # --------------------------------------------------------
    # Advance to requested start frame
    # --------------------------------------------------------

    frame_number = 0

    while frame_number < start:

        step(frame_number)

        frame_number += 1

    # --------------------------------------------------------
    # Generate
    # --------------------------------------------------------

    while True:

        step(frame_number)

        frame = [
            (0, 0, 0)
            for _ in range(num_leds)
        ]

        for particle in particles:

            add_particle(
                frame,
                particle["position"],
                particle["color"]
            )

        yield frame

        frame_number += 1