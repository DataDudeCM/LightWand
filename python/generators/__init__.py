"""
Frame generators.

Each generator is a module with a frames(seed, **settings)
function that yields frames (lists of num_leds (r, g, b),
pixel 0 = tip) one at a time, forever. No wand or timing code:
the same frames can be streamed live (wand.stream), saved as a
FrameSequence, or previewed.

frames(..., start=N) begins at frame N, so a saved range can be
regenerated exactly from the seed and settings.
"""
