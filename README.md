# Winding the Sun

Entry for make.fun bounty **"Make the coolest art"** (coolest-art-01).

A giant clockwork sun hangs in a deep navy night sky. A small clockmaker in
a dark-blue kimono stands on a tall bamboo ladder and turns the huge brass
winding key at the sun's centre. Hokusai-style waves roll along the bottom,
flat red clouds drift, stars speckle the sky.

## Run

```sh
python3 main.py            # writes /output/entry.png
MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Python 3.13, standard library only. The program draws the poster
procedurally (filled polygons, circles, bezier curves, seeded-random
texture) and encodes the PNG itself with `zlib` + `struct` — no image
packages, no fonts, no text, no files read.

Deterministic: one fixed seed, so two runs produce byte-identical PNGs.
Output is 1024x768, under 1 MiB.
