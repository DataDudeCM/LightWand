"""
1D cellular automaton (Wolfram's elementary rules), one
generation per frame. Each cell is one LED.

Rule 90 from a single center cell draws a Sierpinski triangle;
rule 30 is chaotic; rule 110 grows complex structures.
(Nature of Code, chapter 7.)

Example:
    from generators import automaton

    for frame in automaton.frames(rule=30):
        ...
"""

import random


def frames(
    seed=42,
    rule=90,
    num_leds=100,
    start=0,
    initial="center",
    edges="wrap",
    on_color=(255, 255, 255),
    off_color=(0, 0, 0)
):
    """
    Yield frames forever, starting at generation `start`.

    rule:      0-255, Wolfram numbering.
    initial:   "center" (one live cell in the middle) or
               "random" (from the seed).
    edges:     "wrap" (the ends are neighbors), "off" (cells
               beyond the ends are always dead), or "fixed" (the
               two end cells never change, as in Nature of Code
               and the p5 sketch in art/generative/cellularAutomata).
    on_color,
    off_color: colors of live and dead cells.
    """
    if not 0 <= rule <= 255:
        raise ValueError(f"rule must be 0-255, got {rule}")

    if edges not in ("wrap", "off", "fixed"):
        raise ValueError(
            f"edges must be 'wrap', 'off' or 'fixed', got {edges!r}"
        )

    if initial == "center":
        cells = [0] * num_leds
        cells[num_leds // 2] = 1
    elif initial == "random":
        rng = random.Random(seed)
        cells = [rng.randint(0, 1) for _ in range(num_leds)]
    else:
        raise ValueError(
            f"initial must be 'center' or 'random', got {initial!r}"
        )

    # New state for each neighborhood (left, self, right) read
    # as a 3-bit number: bit n of the rule.
    table = [(rule >> n) & 1 for n in range(8)]

    def step(cells):
        n = len(cells)
        new = list(cells)

        # "fixed": the end cells keep their state.
        inner = range(1, n - 1) if edges == "fixed" else range(n)

        for i in inner:
            if edges == "wrap":
                left = cells[i - 1]
                right = cells[(i + 1) % n]
            else:
                left = cells[i - 1] if i > 0 else 0
                right = cells[i + 1] if i < n - 1 else 0

            new[i] = table[(left << 2) | (cells[i] << 1) | right]

        return new

    for _ in range(start):
        cells = step(cells)

    on = tuple(on_color)
    off = tuple(off_color)

    while True:
        yield [on if cell else off for cell in cells]
        cells = step(cells)
