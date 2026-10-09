"""
Generate: run a generator (or loop a saved sequence) continuously,
on the screen, on the wand, or both. Runs until you stop it.

OUTPUT = "screen": the flow view. The wand sits at the leading
    edge of the window (the SWEEP side) and shows the newest frame;
    older frames scroll away behind it, so time becomes the second
    dimension. It's a view of the generator, not a photo: use
    paint.py for that.
OUTPUT = "wand": stream to the wand until Ctrl+C. No window.
OUTPUT = "both": the flow view, with every frame also sent to the
    wand. Pausing holds the current frame on the wand, and stepping
    sends the frame you step to. Screen drawing can delay a wand
    frame by a few ms: fine for watching; for photos, paint a
    saved sequence with paint.py.

Saving (screen / both): mark a start and an end, then S saves that
stretch as its own sequence (in ../sequences/), ready to preview or
paint. Marks go on the newest frame on screen, so pause and step to
the exact frame first. Both marked frames are included. S with no
marks saves everything played so far.

Keys (screen / both):
    arrow keys   point the tip (TIP) up / down / left / right
    space        flip the sweep direction
    P            pause / resume
    , / .        step one frame back / forward (while paused)
    + / -        faster / slower scroll (pixels per frame)
    G            LED gaps on / off
    [ / ]        mark snapshot start / end
    S            save the marked range (no marks: everything so far)
    O            open the last saved sequence in the paint preview
    Esc / Q      quit
"""

import importlib
import itertools
import subprocess
import sys
import time
from collections import deque
from pathlib import Path

import pygame

from image_frames import check_orientation
from sequence import FrameSequence
from lightwand import LightWand
from preview import simulate_flow
from preview_window import turn, screen_limits, to_surface


# ============================================================
# EASY CONTROLS
# ============================================================

# "screen", "wand" or "both"
OUTPUT = "screen"

# A saved sequence (.png strip with a .json next to it),
# or None to run GENERATOR live.
INPUT_FILE = None

# A module in generators/, and its settings.

'''
#Perlin Example
GENERATOR = "perlin"
GENERATOR_SETTINGS = {
    "seed": 42,
    "palette": "industrialSun",
    "x_scale": 0.01,
    "y_scale": 0.01,
}
'''

'''
#Particles Example  
GENERATOR = "particles"

GENERATOR_SETTINGS = {
    "seed": 42,

    "num_particles": 3,

    "braid_center": 0.1,
    "braid_radius": 0.1,
    "mirror": False,

    "period_frames": 20,
    "period_jitter": 0.0,
    "phase_spread": None,  # None = randomize each particle's phase
    "phase_jitter": 0.0,
    "amplitude_jitter": 0,

    "motion_mode": "sine", # use motion_mode when all particles use the same function
     #"particle_modes": ["sine", "harmonic", "modulated"], # use particle_modes when each particle can have a different function

    "harmonic_mix": 0.25,
    "harmonic_multiple": 3.0,

    "mod_amount": 0.50,
    "mod_multiple": 2.0,

    "flatten_power": 3.0,

    "secondary_amount": 0.0,
    "secondary_ratio": 2.0,

    "width": 3,
    "brightness": .5,
    "palette": "vividPrimary",
}

'''
'''
GENERATOR = "particles_physics"

GENERATOR_SETTINGS = {
    "seed": 42,

    "num_particles": 3,

    "braid_center": 0.25,
    "braid_radius": 0.2,

    "period_frames": 60,
    "period_jitter": 0.025,

    "anchor_strength": 0.06,

    "attraction_strength": 0.006,
    "repulsion_strength": 0.080,

    "interaction_distance": 0.10,
    "repulsion_distance": 0.035,

    "damping": 0.88,
    "max_speed": 0.02,

    "width": 10,
    "palette": "industrialSun",
}

'''

GENERATOR = "smoke"

GENERATOR_SETTINGS = {
    "seed": 42,

    "num_particles": 30,        # was 35

    "source_center": 0.22,
    "source_spread": 0.08,

    "upward_drift": 0.0025,
    "upward_bias": 0.00015,
    "turbulence": 0.3,          # was 0.55
    "curl_strength": 0.25,      # was 0.45
    "time_scale": 0.045,
    "spatial_scale": 8.0,
    "bounce": True,
    "drag": 0.15,               # 0 = no drag (the old, fast behavior)
    "max_speed": 0.03,

    "lifetime_frames": 120,
    "lifetime_jitter": 0.35,

    "width": 2.0,               # was 2.2
    "width_jitter": 0.35,
    "brightness": 0.55,         # was 0.35 (with blend "over" this is opacity)
    "brightness_jitter": 0.30,
    "speed_jitter": 0.35,
    "color_drift": 0.10,
    "color_mode": "age",        # was "position"; "age" = through the palette as particles age
    "age_color_span": 0.6,      # reach the palette's last color (grey) at 60% of life, then hold it
    "saturation": 1.0,          # 0 = grey ... 1 = full color (try 0.35 with "duskSmoke")
    "blend": "over",            # was "add": layers like smoke instead of adding up to glow

    # Wide, dim haze behind the wisps (0 = none)
    "haze_particles": 14,
    "haze_width": 9.0,
    "haze_brightness": 0.18,
    "haze_lifetime_scale": 2.0,
    "haze_spread_scale": 2.0,

    "palette": "ashSmoke",      # was "charcoalCoral"; also "duskSmoke", or "emberFire" for fire (with blend "add")
}

'''
#Ribbons Example: translucent veils with glowing edges (remove the quotes
#around this block, and add them around the smoke block above, to use it)
GENERATOR = "ribbons"

GENERATOR_SETTINGS = {
    "seed": 42,

    "num_ribbons": 5,
    "center": 0.5,
    "sway": 0.32,
    "ribbon_width": 0.14,
    "slowness": 2.0,            # higher = slower, bigger swoops
    "presence": 0.55,           # how often ribbons are visible

    "edge_width": 1.1,
    "edge_brightness": 1.0,
    "fill_brightness": 0.22,    # the see-through veil
    "fold_glow": 1.5,
    "glow": 1.6,

    "palette": None,            # None = rainbow, or e.g. "duskSmoke", "emberFire"
    "saturation": 0.75,
    "hue_drift": 0.0004,
}
'''

# Another example:
# GENERATOR = "automaton"
# GENERATOR_SETTINGS = {"seed": 42, "rule": 90, "initial": "center"}

# Generators only. Sequences play at their own fps.
FPS = 40

# ---- wand ("wand" / "both") ----

# None = find the wand on the network automatically.
WAND_IP = None

WAND_BRIGHTNESS = .5  # 0.0..1.0, 1.0 = full brightness

# LED gamma correction: 2.2 makes the wand's colors match the
# screen; 1.0 = off. See LightWand / DESIGN.md §5.3.
WAND_GAMMA = 2.2

# ---- screen ("screen" / "both") ----

TIP = "up"
SWEEP = "right"

# Pixels per LED along the wand (shrunk if the wand won't fit).
LED_SIZE = 8

# Draw the LEDs as streaks with dark gaps between them,
# like the wand itself. Toggle with G.
LED_GAPS = True
LED_DOT_FRACTION = 0.4     # streak width as a fraction of LED_SIZE

# Scroll speed: how far the trail moves per frame (simulated
# wand speed). Change with + / -.
PIXELS_PER_FRAME = 4

# Length of the window along the sweep, in pixels
# (shrunk to fit the screen). Trail seconds =
# TRAIL_PIXELS / PIXELS_PER_FRAME / fps.
TRAIL_PIXELS = 1200

NUM_LEDS = 100

SNAPSHOT_FOLDER = "../sequences"


# ============================================================
# SOURCE
# ============================================================

class Source:
    """
    Where the frames come from: an endless iterator plus what's
    needed to number them and to cut a snapshot.

    frames:  endless iterator of frames
    fps:     playback rate
    length:  sequence length (None for a generator)
    first:   number of the first frame
    name:    used in titles and snapshot file names
    """

    def __init__(self):
        if INPUT_FILE:
            self.sequence = FrameSequence.load(INPUT_FILE)
            self.frames = itertools.cycle(self.sequence.frames)
            self.fps = self.sequence.fps
            self.length = len(self.sequence)
            self.first = 0
            self.name = Path(INPUT_FILE).stem
            return

        self.sequence = None
        self.module = importlib.import_module(f"generators.{GENERATOR}")

        self.settings = dict(GENERATOR_SETTINGS)
        self.settings.setdefault("num_leds", NUM_LEDS)

        self.frames = self.module.frames(**self.settings)
        self.fps = FPS
        self.length = None
        self.first = self.settings.get("start", 0)
        self.name = GENERATOR

        seed = self.settings.get("seed")
        if seed is not None:
            self.name += f"_seed{seed}"

    def snapshot(self, start, end):
        """
        Frames start..end (both included) as a FrameSequence.

        A sequence is sliced (source points back to the file).
        A generator is re-run from its seed, so the range doesn't
        have to be in the viewer's memory and can be regenerated
        exactly from the JSON.
        """
        if self.sequence is not None:
            return self.sequence.slice(start, end + 1)

        settings = dict(self.settings, start=start)
        count = end + 1 - start

        frames = list(itertools.islice(
            self.module.frames(**settings),
            count
        ))

        params = {
            k: v for k, v in settings.items()
            if k not in ("seed", "start")
        }
        params["start"] = start
        params["end"] = end + 1

        return FrameSequence(
            frames,
            fps=self.fps,
            generator=GENERATOR,
            params=params,
            seed=settings.get("seed")
        )


# ============================================================
# WAND
# ============================================================

def make_wand():
    wand = LightWand(
        ip=WAND_IP,
        num_leds=NUM_LEDS,
        brightness=WAND_BRIGHTNESS,
        gamma=WAND_GAMMA
    )
    print(f"Sending to {wand.ip}:{wand.port}")
    return wand


def run_wand(source):
    """OUTPUT = "wand": stream until Ctrl+C, no window."""
    wand = make_wand()

    print(f"Running {source.name} at {source.fps} fps. Ctrl+C to stop.")

    def counted(frames):
        """Pass frames through, showing progress about once a second."""
        report_every = max(1, round(source.fps))

        for i, frame in enumerate(frames):
            if i % report_every == 0:
                number = (
                    i % source.length if source.length
                    else source.first + i
                )
                print(
                    f"\r  frame {number}   {i / source.fps:.0f} s ",
                    end="",
                    flush=True
                )
            yield frame

    try:
        wand.stream(counted(source.frames), fps=source.fps)

    except KeyboardInterrupt:
        print("\nStopping...")

    finally:
        wand.close()


# ============================================================
# VIEWER
# ============================================================

def main():
    source = Source()

    if OUTPUT == "wand":
        run_wand(source)
        return

    if OUTPUT not in ("screen", "both"):
        raise ValueError(f"Unknown OUTPUT: {OUTPUT}")

    wand = make_wand() if OUTPUT == "both" else None

    try:
        view(source, wand)

    except KeyboardInterrupt:
        print("\nStopping...")

    finally:
        pygame.quit()
        if wand is not None:
            wand.close()     # blacks out the wand


def view(source, wand):
    """The flow view; also sends each frame to wand if given."""
    fps = source.fps
    tip, sweep = check_orientation(TIP, SWEEP)

    px_per_frame = PIXELS_PER_FRAME
    gaps = LED_GAPS
    paused = False

    history = deque()   # (frame number, frame), oldest first
    taken = 0           # frames taken from the source so far
    back = 0            # frames stepped back while paused

    mark_in = None      # snapshot range, in frame numbers
    mark_out = None
    last_saved = None
    message = ""        # shown for a few seconds
    message_until = 0.0

    pygame.init()
    max_w, max_h = screen_limits()
    font = pygame.font.Font(None, 24)
    screen = None

    def layout():
        """LED size, trail length in frames, and window size."""
        vertical = tip in ("up", "down")
        wand_max, trail_max = (max_h, max_w) if vertical else (max_w, max_h)

        led_size = max(1, min(LED_SIZE, wand_max // NUM_LEDS))
        trail_frames = max(1, min(TRAIL_PIXELS, trail_max) // px_per_frame)

        wand_px = NUM_LEDS * led_size
        trail_px = trail_frames * px_per_frame
        size = (trail_px, wand_px) if vertical else (wand_px, trail_px)

        return led_size, trail_frames, size

    led_size, trail_frames, size = layout()

    def take():
        """Pull the next frame from the source."""
        nonlocal taken

        frame = next(source.frames)
        number = (
            taken % source.length if source.length
            else source.first + taken
        )
        history.append((number, frame))
        taken += 1
        send(frame)

        # Keep one extra screen of history for stepping back.
        while len(history) > 2 * trail_frames:
            history.popleft()

    def send(frame):
        """Show a frame on the wand, if there is one."""
        if wand is not None:
            wand.pixels = list(frame)
            wand.show()

    def current():
        """Number of the newest frame on screen."""
        return history[len(history) - 1 - back][0]

    def send_current():
        send(history[len(history) - 1 - back][1])

    def say(text):
        nonlocal message, message_until
        message = text
        message_until = time.perf_counter() + 4
        print(text)

    def save_snapshot():
        nonlocal last_saved

        if mark_in is None and mark_out is None:
            # No marks: everything played so far.
            start, end = source.first, current()

        elif mark_in is None or mark_out is None:
            say("Mark both a start [ and an end ] (or neither)")
            return

        else:
            start, end = mark_in, mark_out

        if end < start:
            say("End is before start: mark again")
            return

        snapshot = source.snapshot(start, end)
        path = Path(SNAPSHOT_FOLDER) / f"{source.name}_{start}-{end}"
        snapshot.save(path)

        last_saved = path
        say(f"Saved {path.name} ({len(snapshot)} frames)")

    def open_in_paint():
        if last_saved is None:
            say("Save a snapshot (S) first")
            return

        here = Path(__file__).resolve().parent
        subprocess.Popen(
            [sys.executable, "paint.py", str(last_saved.resolve()),
             "--output", "screen"],
            cwd=here
        )
        say(f"Opening {last_saved.name} in the paint preview")

    def mark_index(visible, number):
        """Index in visible of the newest frame with this number."""
        if number is None:
            return None

        for i in range(len(visible) - 1, -1, -1):
            if visible[i][0] == number:
                return i

        return None

    def draw_text(lines):
        y = 8
        for line in lines:
            text = font.render(line, True, (255, 255, 255))
            box = text.get_rect(topleft=(8, y)).inflate(10, 6)
            pygame.draw.rect(screen, (0, 0, 0), box)
            screen.blit(text, (8, y))
            y += text.get_height() + 8

    def draw():
        nonlocal screen

        if screen is None or screen.get_size() != size:
            screen = pygame.display.set_mode(size)

        visible = list(history)[:len(history) - back]

        image = simulate_flow(
            [frame for _, frame in visible],
            tip=tip,
            sweep=sweep,
            trail_frames=trail_frames,
            px_per_frame=px_per_frame,
            led_size=led_size,
            led_gaps=gaps,
            led_dot_fraction=LED_DOT_FRACTION,
            mark_start=mark_index(visible, mark_in),
            mark_end=mark_index(visible, mark_out)
        )
        screen.blit(to_surface(image), (0, 0))

        number = visible[-1][0]
        status = f"frame {number}"
        if source.length:
            status += f" / {source.length}"
        status += f"   {number / fps:.2f} s"
        if paused:
            status += "   PAUSED"
            if back:
                status += f" ({back} back)"

        lines = [status]

        if mark_in is not None or mark_out is not None:
            marks = (
                f"in {'-' if mark_in is None else mark_in}   "
                f"out {'-' if mark_out is None else mark_out}"
            )
            if mark_in is not None and mark_out is not None:
                count = mark_out + 1 - mark_in
                marks += f"   ({count} frames, {count / fps:.2f} s)"
            lines.append(marks)

        if message and time.perf_counter() < message_until:
            lines.append(message)

        draw_text(lines)

        pygame.display.set_caption(
            f"Flow{' + wand' if wand else ''}  |  {source.name}  |  "
            f"TIP={tip} SWEEP={sweep}  |  "
            f"{px_per_frame} px/frame, trail "
            f"{trail_frames / fps:.1f} s  |  {fps} fps  |  "
            f"gaps {'on' if gaps else 'off'}"
        )
        pygame.display.flip()

    # Same absolute clock as LightWand.play / stream: frame i
    # is due at start_time + i / fps.
    take()
    start_time = time.perf_counter()

    clock = pygame.time.Clock()
    dirty = True
    showing_message = False
    running = True

    while running:

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.WINDOWEXPOSED:
                dirty = True

            elif event.type == pygame.KEYDOWN:
                key = event.key
                new = turn(key, tip, sweep)

                if key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False

                elif new is not None:
                    tip, sweep = new

                elif key == pygame.K_p:
                    paused = not paused
                    if not paused:
                        back = 0
                        start_time = time.perf_counter() - (taken - 1) / fps

                elif key == pygame.K_PERIOD and paused:
                    if back > 0:
                        back -= 1
                        send_current()
                    else:
                        take()

                elif key == pygame.K_COMMA and paused:
                    back = min(back + 1, len(history) - 1)
                    send_current()

                elif key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    px_per_frame = min(32, px_per_frame + 1)

                elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    px_per_frame = max(1, px_per_frame - 1)

                elif key == pygame.K_g:
                    gaps = not gaps

                elif key == pygame.K_LEFTBRACKET:
                    mark_in = current()

                elif key == pygame.K_RIGHTBRACKET:
                    mark_out = current()

                elif key == pygame.K_s:
                    save_snapshot()

                elif key == pygame.K_o:
                    open_in_paint()

                led_size, trail_frames, size = layout()
                dirty = True

        if not paused:
            due = int((time.perf_counter() - start_time) * fps) + 1

            # A slow generator falls behind: slow down rather
            # than skip frames.
            if due - taken > fps:
                start_time = time.perf_counter() - (taken - 1) / fps
                due = taken + 1

            while taken < due:
                take()
                dirty = True

        # Redraw once when a message times out.
        message_on = bool(message) and time.perf_counter() < message_until
        if showing_message and not message_on:
            dirty = True
        showing_message = message_on

        if dirty:
            draw()
            dirty = False

        clock.tick(120)

    pygame.quit()


if __name__ == "__main__":
    main()
