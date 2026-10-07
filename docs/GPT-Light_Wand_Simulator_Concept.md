# Light Wand Simulator / Live Flow Viewer Concept

## Purpose

Create a computer-side visual tool for the Light Wand that helps preview, explore, and capture what 100-pixel wand scripts will produce before using the physical wand and camera.

The tool should support two closely related modes built on the same 100-pixel frame stream:

1. **Image Paint Simulator** — estimate what a long-exposure photograph would look like under different wand orientations, sweep directions, speeds, and exposure times.
2. **Live Flow Viewer** — continuously visualize the evolving 100-pixel output of a wand script over time, making it easier to explore procedural systems such as smoke, flame, particles, cellular automata, noise fields, and other generative processes.

The goal is not only simulation. This can become a creative preview, exploration, and capture environment for the wand.

---

## Shared Core Concept

The existing Light Wand architecture already treats the wand as a one-dimensional display:

```text
Generator
   |
   v
100 RGB pixels per frame
   |
   +----> Simulator / Viewer
   |
   +----> Physical Wand via UDP
```

Each frame consists of the 100 RGB pixel values that would appear on the physical LED strip at one instant.

The same generator should be able to drive:

- the physical Light Wand
- the Image Paint Simulator
- the Live Flow Viewer
- any combination of the above

This avoids duplicating generator logic and allows a smoke, flame, particle, or automata script to work identically in simulation and on the real wand.

A useful frame structure could eventually contain:

- 100 RGB pixel values
- timestamp
- frame number
- brightness
- generator/script name
- generator parameters
- random seed
- optional motion metadata

---

# Mode 1 — Image Paint Simulator

## Goal

Estimate what the camera would record during a long-exposure light-painting sweep.

This is the more physically faithful simulation mode.

The simulator accumulates successive 100-pixel wand frames into a 2D canvas according to assumed wand movement.

## Example

For a vertical wand moving left to right:

```text
Frame 1   Frame 2   Frame 3   Frame 4 ...
   |         |         |         |
   v         v         v         v

   |         |         |         |
   |         |         |         |
   |         |         |         |
   |         |         |         |

        accumulated photograph
```

Each wand frame becomes a vertical slice of the final image.

For a horizontal wand moving upward, each frame becomes a horizontal slice.

---

## Initial Controls

The simulator should allow control of:

- **Wand orientation**
  - vertical
  - horizontal

- **Sweep direction**
  - left
  - right
  - up
  - down

- **Exposure duration**

- **Sweep speed**

- **Starting wand position**

- **Frame rate / slice rate**

- **Brightness**

- **LED diffusion / blur**

- **Frame spacing**
  - fixed
  - derived from simulated wand speed

---

## Motion Effects

Movement speed changes the spatial relationship between frames:

- **Slow movement** → slices overlap more densely
- **Fast movement** → slices are spaced farther apart
- **Pause** → repeated frames accumulate in nearly the same location and become brighter
- **Acceleration** → spacing gradually increases
- **Deceleration** → spacing gradually decreases

Future motion models could include:

- variable speed
- wobble
- rotation
- curved movement
- stop/start movement
- acceleration curves
- pendulum motion
- recorded IMU motion

These motion imperfections may ultimately be artistically useful rather than merely errors.

---

# Mode 2 — Live Flow Viewer

## Goal

Continuously visualize what a wand script is producing over time.

This mode is less about physically simulating a camera and more about making the evolving wand output visible as a scrolling field.

It is especially useful for procedural and continuously evolving systems such as:

- smoke
- flame
- particles
- cellular automata
- reaction-diffusion
- Perlin/noise fields
- wave systems
- music visualization
- other generative processes

---

## Basic Behavior

Assume the current wand occupies a fixed position on the screen.

For each frame:

1. Draw the new 100-pixel wand frame.
2. Shift the previous frames perpendicular to the wand orientation.
3. Repeat continuously.

For a vertical wand:

```text
older history  <----------------------  current wand

| | | | | | | | | | | | | | | | | |
                                  ^
                                  newest 100-pixel frame
```

The result becomes a scrolling history of the wand's output.

This effectively turns time into a second visual dimension.

---

## Important Distinction

If the physical wand is completely stationary in the real world, a camera would not see a wide scrolling field. The light would mostly accumulate in the same location.

Therefore, the Live Flow Viewer should be understood as a:

- **space-time visualizer**
- **strip-history display**
- **stream microscope**

rather than a literal camera simulation.

That distinction is useful because this mode is intended primarily for exploring the generator itself.

---

## Live Flow Controls

Possible controls include:

- wand orientation
- flow direction
- pixels shifted per frame
- simulated sweep speed
- frame rate
- history/trail length
- brightness
- blur / diffusion
- whether the wand is:
  - pinned to one side
  - centered
  - placed at a custom screen position

Initially, simulated wand motion can be zero.

Later, the viewer can optionally assume that the wand itself is moving continuously.

---

# Smoke / Flame Example

One of the main motivations for this tool is to create continuous animated effects such as smoke or fire.

A JavaScript or p5.js generator could simulate a full smoke field internally, then sample the appropriate 100-pixel slice for the wand.

```text
Smoke / Flame Simulation
          |
          v
   Sample 100-pixel slice
          |
          +------> Live Flow Viewer
          |
          +------> Image Paint Simulator
          |
          +------> Physical Wand
```

This makes it possible to explore effects such as luminous smoke or flame behind a person, tree, sculpture, or other photographic subject.

Instead of guessing how a continuously changing 1D LED strip will translate into a 2D result, the viewer makes that evolution visible immediately.

---

# Snapshot / Bookmark Concept

While watching a continuous generative stream, interesting moments may appear unexpectedly.

The viewer should eventually support a **Snapshot / Bookmark** function.

When something interesting appears, the user could capture:

- start time
- end time or duration
- frame range
- generator parameters
- random seed
- frame rate
- palette
- brightness
- other script-specific settings

That captured interval could then be sent to the Image Paint Simulator.

Example workflow:

```text
Run live smoke generator
        |
        v
Watch evolving flow
        |
        v
"That section looks interesting"
        |
        v
Bookmark / Snapshot
        |
        v
Replay captured frames
        |
        v
Simulate long-exposure painting
        |
        v
Send same sequence to physical wand
```

This creates a useful bridge between generative exploration and repeatable physical light painting.

---

# Two Complementary Questions

The two modes answer different questions.

### Live Flow Viewer

> What is the wand producing over time?

### Image Paint Simulator

> What would a camera see if the wand produced that output while moving?

The same underlying frame sequence can therefore be explored first as a temporal stream and later as a simulated photograph.

---

# Proposed Software Architecture

A simple modular structure could use three layers.

## A. Generator Layer

Produces:

```text
frame[100]
```

Examples:

- still-image slicer
- smoke generator
- flame generator
- particle system
- cellular automata
- noise field
- music analyzer
- existing p5.js sketches
- Python generative systems

---

## B. Output / Transport Layer

Receives the generated frame and routes it to one or more destinations:

```text
Generator
    |
    v
Frame Router
   / | \
  /  |  \
 v   v   v
Live   Paint   Physical
Flow   Sim     Wand
```

Destinations can be enabled independently.

---

## C. Viewer Layer

### Live Flow Viewer

Displays the evolving history of frames.

### Image Paint Simulator

Accumulates frames according to simulated wand motion and exposure.

---

# Future Motion Integration

A future IMU such as the planned BNO085/BNO086 could make the simulations substantially more realistic.

Instead of assuming motion, recorded or live motion data could determine:

- frame placement
- speed
- direction
- orientation
- acceleration
- pauses
- rotation

This would allow the simulator to replay an actual physical wand movement while changing only the LED content.

It could also allow frame playback to advance based on real distance traveled rather than elapsed time.

---

# Possible Development Sequence

## Phase 1 — Shared 100-Pixel Frame Engine

Create a simple generator that outputs 100 RGB pixels each frame.

Confirm that the same frame can be sent to multiple destinations.

---

## Phase 2 — Live Flow Viewer

Start with the simplest case:

- vertical wand
- fixed screen position
- new frames enter on one side
- old frames shift horizontally
- adjustable shift speed
- optional blur

Use a procedural smoke or noise generator as the first interesting test.

---

## Phase 3 — Image Paint Simulator

Add:

- vertical/horizontal orientation
- sweep direction
- exposure duration
- start position
- constant sweep speed
- frame accumulation
- blur/diffusion

---

## Phase 4 — Snapshot / Bookmark

Allow interesting intervals from the Live Flow Viewer to be saved and replayed.

Store:

- frame sequence
- timing
- parameters
- seed

---

## Phase 5 — Physical Wand Output

Route the same 100-pixel frames through UDP to the ESP32.

The display and physical wand can then run simultaneously.

---

## Phase 6 — Advanced Motion

Add:

- acceleration
- variable speed
- wobble
- rotation
- curved paths
- IMU-recorded motion

---

# Design Principle

The simulator should not become a separate system from the Light Wand software.

The strongest architecture is:

```text
             GENERATIVE SOURCE
                    |
                    v
              100-PIXEL FRAME
                    |
          +---------+---------+
          |         |         |
          v         v         v
      LIVE FLOW   PAINT     PHYSICAL
        VIEWER     SIM       WAND
```

The **100-pixel frame stream is the common language** between all parts of the system.

This keeps the project modular and makes every new generator automatically usable for:

- experimentation
- preview
- simulation
- recording
- real-world light painting

---

# Overall Direction

What began as a simple wand simulator could become a broader **creative preview and capture environment**.

It would allow a workflow of:

```text
Generate
   ↓
Observe
   ↓
Discover an interesting moment
   ↓
Capture it
   ↓
Simulate it
   ↓
Adjust motion / exposure
   ↓
Send it to the physical wand
   ↓
Photograph it
```

That fits naturally with the larger Light Wand idea: combining **code, light, motion, time, and photography** into a single experimental instrument.
