#!/usr/bin/env python3
"""Winding the Sun — an ukiyo-e poster drawn procedurally, stdlib only.

A giant clockwork sun hangs in a deep navy night sky. A small clockmaker in a
dark-blue kimono stands on a tall bamboo ladder and turns the huge brass
winding key at the sun's centre. Hokusai-style waves roll along the bottom,
flat red clouds drift, stars speckle the sky.

Reads nothing. Writes /output/entry.png (1024x768, <= 1 MiB).
Deterministic: one fixed seed, no time, no network, no machine dependence.
Standard library only (zlib + struct for the PNG encoder).
"""

import math
import os
import random
import struct
import zlib

W, H = 1024, 768
SEED = 20261113

# ---------------------------------------------------------------- palette
NAVY = (14, 30, 58)        # deep night sky, top
NAVY2 = (24, 44, 82)       # sky near the horizon
GOLD = (232, 182, 76)
GOLD_L = (255, 211, 77)
GOLD_PALE = (255, 224, 138)
GOLD_D = (166, 124, 46)    # brass / gear teeth
BRASS_D = (140, 102, 34)
CREAM = (245, 234, 208)
RED = (192, 57, 43)
TURQ = (46, 196, 182)
INK = (10, 18, 38)         # outlines
SKIN = (232, 195, 154)
KIMONO = (31, 58, 95)
KIMONO_D = (22, 44, 74)
BAMBOO = (200, 154, 85)
BAMBOO_D = (146, 104, 52)
WAVE_A = (18, 63, 87)
WAVE_B = (23, 90, 117)
WAVE_C = (27, 107, 130)
WHITE = (250, 248, 240)

SUN_CX, SUN_CY = 688, 248
SUN_R = 186


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.buf = bytearray(w * h * 3)

    def hline(self, x0, x1, y, c):
        if y < 0 or y >= self.h:
            return
        x0 = max(0, int(x0))
        x1 = min(self.w - 1, int(x1))
        if x1 < x0:
            return
        i = (y * self.w + x0) * 3
        self.buf[i:i + (x1 - x0 + 1) * 3] = bytes(c) * (x1 - x0 + 1)

    def fill_rect(self, x0, y0, x1, y1, c):
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        for y in range(max(0, y0), min(self.h, y1)):
            self.hline(x0, x1 - 1, y, c)

    def fill_circle(self, cx, cy, r, c):
        r = float(r)
        for y in range(int(cy - r) - 1, int(cy + r) + 2):
            dy = y - cy
            if abs(dy) > r:
                continue
            dx = math.sqrt(max(0.0, r * r - dy * dy))
            self.hline(cx - dx, cx + dx, y, c)

    def ring(self, cx, cy, r, c, w):
        """Stroke a circle: annulus of width w centred on radius r."""
        r1 = r + w / 2.0
        r0 = r - w / 2.0
        for y in range(int(cy - r1) - 1, int(cy + r1) + 2):
            dy = y - cy
            if abs(dy) >= r1:
                continue
            xo = math.sqrt(max(0.0, r1 * r1 - dy * dy))
            xi = math.sqrt(max(0.0, r0 * r0 - dy * dy)) if abs(dy) < r0 else 0.0
            self.hline(cx - xo, cx - xi, y, c)
            self.hline(cx + xi, cx + xo, y, c)

    def fill_poly(self, pts, c):
        ys = [p[1] for p in pts]
        y0 = max(0, int(math.ceil(min(ys))))
        y1 = min(self.h - 1, int(math.floor(max(ys))))
        n = len(pts)
        for y in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x0, y0p = pts[i]
                x1, y1p = pts[(i + 1) % n]
                if (y0p <= y < y1p) or (y1p <= y < y0p):
                    t = (y - y0p) / (y1p - y0p)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.hline(math.ceil(xs[i]), math.floor(xs[i + 1]), y, c)

    def stroke_poly(self, pts, c, w):
        n = len(pts)
        for i in range(n):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % n]
            self.thick_line(x0, y0, x1, y1, c, w)

    def thick_line(self, x0, y0, x1, y1, c, w):
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy)
        if length < 0.001:
            self.fill_circle(x0, y0, w / 2.0, c)
            return
        nx, ny = -dy / length * w / 2.0, dx / length * w / 2.0
        self.fill_poly([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny),
                        (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)], c)
        self.fill_circle(x0, y0, w / 2.0, c)
        self.fill_circle(x1, y1, w / 2.0, c)

    def bezier(self, p0, p1, p2, p3, c, w, steps=40):
        pts = []
        for i in range(steps + 1):
            t = i / steps
            mt = 1 - t
            x = (mt ** 3 * p0[0] + 3 * mt * mt * t * p1[0]
                 + 3 * mt * t * t * p2[0] + t ** 3 * p3[0])
            y = (mt ** 3 * p0[1] + 3 * mt * mt * t * p1[1]
                 + 3 * mt * t * t * p2[1] + t ** 3 * p3[1])
            pts.append((x, y))
        for i in range(len(pts) - 1):
            self.thick_line(pts[i][0], pts[i][1], pts[i + 1][0],
                            pts[i + 1][1], c, w)

    def arc(self, cx, cy, r, a0, a1, c, w, steps=24):
        """Stroke a circular arc (angles in radians, screen coords)."""
        pts = []
        for i in range(steps + 1):
            a = a0 + (a1 - a0) * i / steps
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        for i in range(len(pts) - 1):
            self.thick_line(pts[i][0], pts[i][1], pts[i + 1][0],
                            pts[i + 1][1], c, w)

    def ellipse(self, cx, cy, rx, ry, c):
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            dy = (y - cy) / float(ry)
            if abs(dy) > 1:
                continue
            dx = rx * math.sqrt(max(0.0, 1 - dy * dy))
            self.hline(cx - dx, cx + dx, y, c)


# ---------------------------------------------------------------- shapes
def cloud(cv, cx, cy, w, h, c, outline=INK):
    """Flat-bottomed woodblock cloud: a smooth triple-hump silhouette."""
    pts = []
    for k in range(41):
        x = cx - w / 2.0 + w * k / 40.0
        u = (x - cx) / (w / 2.0)  # -1 .. 1
        bump = (0.62 * math.exp(-((u + 0.62) ** 2) / (2 * 0.20 ** 2))
                + 0.90 * math.exp(-(u ** 2) / (2 * 0.20 ** 2))
                + 0.62 * math.exp(-((u - 0.62) ** 2) / (2 * 0.20 ** 2)))
        pts.append((x, cy + h * 0.30 - h * bump))
    # gently curved base: sags a little in the middle, lifts at the ends
    for k in range(40, -1, -1):
        x = cx - w / 2.0 + w * k / 40.0
        u = (x - cx) / (w / 2.0)
        pts.append((x, cy + h * 0.30 + h * 0.10 * math.sin(math.pi * (k / 40.0))))
    cv.fill_poly(pts, c)
    cv.stroke_poly(pts, outline, 4)


def cloud_band(cv, cx, cy, w, h, c, outline=INK):
    """Ukiyo-e cloud band: scalloped round top, flat bottom, woodblock style."""
    bumps = max(3, int(w // 46))
    seg = w / bumps
    r = seg / 2.0
    pts = []
    for i in range(bumps):
        bx = cx - w / 2.0 + i * seg + r
        for k in range(9):
            a = math.pi * (1 - k / 8.0)
            pts.append((bx + r * math.cos(a), cy - r * math.sin(a)))
    pts.append((cx + w / 2.0, cy + h * 0.35))
    pts.append((cx - w / 2.0, cy + h * 0.35))
    cv.fill_poly(pts, c)
    cv.stroke_poly(pts, outline, 4)


def puff_cloud(cv, cx, cy, c, outline=INK):
    """A round puff cloud: a cluster of overlapping circles, no flat base."""
    blobs = [(0, 0, 26), (-26, 8, 20), (26, 8, 20), (-12, -14, 18), (14, -12, 18)]
    for dx, dy, r in blobs:
        cv.fill_circle(cx + dx, cy + dy, r + 2, outline)
    for dx, dy, r in blobs:
        cv.fill_circle(cx + dx, cy + dy, r, c)


def curl_wave(cv):
    """One large Hokusai-style curling crest on the left side."""
    p0, p1, p2, p3 = (55, 705), (85, 590), (185, 535), (258, 600)
    cv.bezier(p0, p1, p2, p3, WHITE, 54)
    cv.bezier(p0, p1, p2, p3, WAVE_B, 46)
    cv.bezier((70, 700), (100, 610), (180, 565), (245, 605), TURQ, 3)
    cv.bezier((75, 640), (110, 575), (190, 550), (250, 595), WHITE, 5)
    cv.arc(250, 610, 26, math.radians(200), math.radians(470), WHITE, 6)
    cv.arc(250, 610, 18, math.radians(200), math.radians(430), TURQ, 3)
    for (x, y, r) in ((120, 585, 5), (160, 560, 6), (205, 560, 5), (235, 580, 4)):
        cv.fill_circle(x, y, r, WHITE)


def boat(cv, cx, cy):
    """Tiny fishing boat with a warm lantern, riding the front wave."""
    hull = [(cx - 56, cy), (cx + 56, cy), (cx + 40, cy + 20), (cx - 40, cy + 20)]
    cv.fill_poly(hull, (96, 58, 32))
    cv.stroke_poly(hull, INK, 3)
    cv.thick_line(cx, cy, cx, cy - 56, INK, 6)
    cv.thick_line(cx, cy, cx, cy - 56, BAMBOO_D, 3)
    # small red flag at the mast top
    cv.fill_poly([(cx, cy - 56), (cx + 18, cy - 50), (cx, cy - 44)], RED)
    cv.thick_line(cx, cy - 56, cx + 18, cy - 50, INK, 2)
    cv.thick_line(cx + 18, cy - 50, cx, cy - 44, INK, 2)
    # lantern glow + lantern
    cv.fill_circle(cx + 18, cy - 42, 18, GOLD_PALE)
    cv.fill_circle(cx + 18, cy - 42, 11, GOLD_L)
    cv.fill_circle(cx + 18, cy - 42, 5, INK)
    cv.hline(cx - 34, cx + 34, cy + 27, GOLD_L)
    cv.hline(cx - 22, cx + 22, cy + 33, GOLD_D)


def wave_layer(cv, top_y, color, crest_r, spacing, offset):
    cv.fill_rect(0, top_y, W, H, color)
    x = offset
    while x < W + spacing:
        cv.fill_circle(x, top_y, crest_r, color)
        x += spacing


def gear_teeth(cv, cx, cy, r_in, r_out, teeth, c, outline=INK):
    pitch = 2 * math.pi / teeth
    for i in range(teeth):
        a = i * pitch
        a0, a1 = a - pitch * 0.28, a + pitch * 0.28
        a2, a3 = a - pitch * 0.16, a + pitch * 0.16
        pts = [(cx + r_in * math.cos(a0), cy + r_in * math.sin(a0)),
               (cx + r_out * math.cos(a2), cy + r_out * math.sin(a2)),
               (cx + r_out * math.cos(a3), cy + r_out * math.sin(a3)),
               (cx + r_in * math.cos(a1), cy + r_in * math.sin(a1))]
        cv.fill_poly(pts, c)
        cv.stroke_poly(pts, outline, 3)


def ladder(cv, base_l, top_l, base_r, top_r, rungs=8):
    """Bamboo ladder between two rails; rungs spaced along the rails."""
    cv.thick_line(*base_l, *top_l, INK, 11)
    cv.thick_line(*base_r, *top_r, INK, 11)
    cv.thick_line(*base_l, *top_l, BAMBOO, 7)
    cv.thick_line(*base_r, *top_r, BAMBOO, 7)
    for i in range(1, rungs):
        t = i / float(rungs)
        lx = base_l[0] + (top_l[0] - base_l[0]) * t
        ly = base_l[1] + (top_l[1] - base_l[1]) * t
        rx = base_r[0] + (top_r[0] - base_r[0]) * t
        ry = base_r[1] + (top_r[1] - base_r[1]) * t
        cv.thick_line(lx, ly, rx, ry, INK, 7)
        cv.thick_line(lx, ly, rx, ry, BAMBOO_D, 4)


def figure(cv):
    """Clockmaker in a dark-blue kimono, enlarged, both hands on the key ring."""
    # both arms reach up to the key ring (drawn first, behind the body)
    cv.thick_line(548, 384, 512, 306, INK, 17)
    cv.thick_line(548, 384, 512, 306, KIMONO, 12)
    cv.fill_circle(510, 302, 9, SKIN)
    cv.thick_line(594, 386, 608, 294, INK, 17)
    cv.thick_line(594, 386, 608, 294, KIMONO, 12)
    cv.fill_circle(611, 290, 9, SKIN)
    # legs + feet
    cv.fill_rect(552, 468, 565, 500, INK)
    cv.fill_rect(577, 468, 590, 500, INK)
    cv.ellipse(560, 502, 11, 5, INK)
    cv.ellipse(585, 502, 11, 5, INK)
    # kimono body: flared trapezoid
    body = [(542, 370), (598, 372), (613, 473), (527, 473)]
    cv.fill_poly(body, KIMONO)
    cv.stroke_poly(body, INK, 4)
    # cream collar V
    cv.fill_poly([(560, 372), (580, 372), (570, 415)], CREAM)
    cv.thick_line(560, 372, 570, 415, INK, 2)
    cv.thick_line(580, 372, 570, 415, INK, 2)
    # red sash
    cv.fill_poly([(534, 412), (606, 412), (608, 434), (532, 434)], RED)
    cv.thick_line(534, 412, 606, 412, INK, 2)
    cv.thick_line(532, 434, 608, 434, INK, 2)
    # head: hair cap, face, topknot
    cv.fill_circle(570, 335, 20, INK)
    cv.fill_circle(571, 343, 17, SKIN)
    cv.fill_circle(570, 312, 8, INK)
    cv.thick_line(570, 319, 570, 327, RED, 3)
    cv.fill_circle(564, 342, 2, INK)
    cv.fill_circle(577, 342, 2, INK)


def apprentice(cv):
    """Small apprentice at the ladder's base, holding a lantern up to the
    clockmaker. Clearly smaller than the clockmaker; simpler dark kimono."""
    # raised arm (toward the ladder) holding the lantern
    cv.thick_line(430, 694, 452, 668, INK, 11)
    cv.thick_line(430, 694, 452, 668, KIMONO_D, 7)
    cv.fill_circle(453, 666, 4, SKIN)
    # lantern glow + lantern
    cv.fill_circle(458, 652, 12, GOLD_PALE)
    cv.fill_circle(458, 652, 7, GOLD_L)
    cv.fill_circle(458, 652, 3, INK)
    # other arm hanging at the side
    cv.thick_line(400, 694, 394, 716, INK, 11)
    cv.thick_line(400, 694, 394, 716, KIMONO_D, 7)
    cv.fill_circle(394, 718, 4, SKIN)
    # legs + feet
    cv.fill_rect(404, 720, 412, 756, INK)
    cv.fill_rect(418, 720, 426, 756, INK)
    cv.ellipse(408, 758, 7, 4, INK)
    cv.ellipse(422, 758, 7, 4, INK)
    # simple dark kimono, no sash
    body = [(398, 690), (432, 690), (440, 724), (390, 724)]
    cv.fill_poly(body, KIMONO_D)
    cv.stroke_poly(body, INK, 3)
    # head: hair cap, face, small topknot, eyes looking up
    cv.fill_circle(415, 672, 11, INK)
    cv.fill_circle(416, 677, 9, SKIN)
    cv.fill_circle(415, 659, 4, INK)
    cv.fill_circle(412, 676, 1, INK)
    cv.fill_circle(420, 676, 1, INK)


# ---------------------------------------------------------------- drawing
def draw():
    rng = random.Random(SEED)
    cv = Canvas(W, H)

    # sky: vertical gradient
    for y in range(0, 570):
        t = y / 570.0
        cv.hline(0, W - 1, y, lerp(NAVY, NAVY2, t))

    # stars (skip the sun disc and the clouds)
    for _ in range(150):
        x = rng.randint(4, W - 4)
        y = rng.randint(4, 540)
        if math.hypot(x - SUN_CX, y - SUN_CY) < 250:
            continue
        if 60 < x < 300 and 130 < y < 260:
            continue
        if 800 < x < 1000 and 400 < y < 520:
            continue
        if 95 < x < 210 and 395 < y < 470:
            continue
        r = rng.choice([1, 1, 1, 2])
        c = rng.choice([WHITE, WHITE, CREAM, GOLD_L])
        cv.fill_circle(x, y, r, c)
        if rng.random() < 0.12:
            cv.thick_line(x - 5, y, x + 5, y, c, 1)
            cv.thick_line(x, y - 5, x, y + 5, c, 1)

    # extra sparkle stars in the top-left corner so it is not dead space
    for (x, y) in ((40, 40), (90, 70), (150, 35), (210, 80), (260, 45),
                   (60, 120), (130, 105), (300, 110), (180, 130), (35, 170)):
        c = WHITE if (x + y) % 3 else GOLD_L
        cv.thick_line(x - 6, y, x + 6, y, c, 1)
        cv.thick_line(x, y - 6, x, y + 6, c, 1)
        cv.fill_circle(x, y, 2, c)

    # woodblock grain in the sky: sparse speckles
    for _ in range(2200):
        x = rng.randint(0, W - 1)
        y = rng.randint(0, 560)
        c = (18, 38, 72) if rng.random() < 0.5 else (10, 24, 48)
        cv.hline(x, x, y, c)

    # --- the clockwork sun ---
    gear_teeth(cv, SUN_CX, SUN_CY, SUN_R - 4, SUN_R + 28, 26, GOLD_D)
    cv.fill_circle(SUN_CX, SUN_CY, SUN_R + 7, INK)          # dark rim
    cv.fill_circle(SUN_CX, SUN_CY, SUN_R, GOLD)             # disc
    cv.fill_circle(SUN_CX, SUN_CY, 128, GOLD_L)             # inner glow
    cv.fill_circle(SUN_CX, SUN_CY, 70, GOLD_PALE)           # hot centre
    cv.ring(SUN_CX, SUN_CY, 150, INK, 3)                    # engraved ring
    cv.ring(SUN_CX, SUN_CY, 96, BRASS_D, 3)
    # speckles on the disc
    for _ in range(320):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0, SUN_R - 8)
        x = SUN_CX + r * math.cos(a)
        y = SUN_CY + r * math.sin(a)
        c = (210, 160, 60) if rng.random() < 0.5 else (255, 222, 120)
        cv.hline(int(x), int(x), int(y), c)

    # winding key: stem from the sun's centre to one big ring bow
    cv.thick_line(SUN_CX, SUN_CY, 606, 292, INK, 20)
    cv.thick_line(SUN_CX, SUN_CY, 606, 292, GOLD_D, 13)
    cv.fill_circle(SUN_CX, SUN_CY, 30, INK)                 # hub
    cv.fill_circle(SUN_CX, SUN_CY, 24, GOLD_D)
    cv.fill_circle(SUN_CX, SUN_CY, 7, INK)
    # one large round bow: dark rim, brass ring, pale highlight (bolder: +15%)
    cv.ring(556, 290, 53, INK, 20)
    cv.ring(556, 290, 53, GOLD_D, 13)
    cv.ring(556, 290, 53, GOLD_L, 5)

    # --- secondary gear meshing with the sun's lower-left rim ---
    gear_teeth(cv, 448, 368, 52, 66, 12, GOLD_D)
    cv.fill_circle(448, 368, 56, INK)
    cv.fill_circle(448, 368, 52, GOLD)
    cv.fill_circle(448, 368, 40, GOLD_L)
    cv.ring(448, 368, 30, BRASS_D, 3)
    cv.fill_circle(448, 368, 12, INK)
    cv.fill_circle(448, 368, 8, GOLD_D)

    # --- clouds: cream/gold ukiyo-e bands + one small red puff ---
    cloud_band(cv, 175, 195, 230, 64, CREAM)
    cloud_band(cv, 905, 462, 170, 48, GOLD_PALE)
    puff_cloud(cv, 150, 430, RED)

    # --- waves ---
    wave_layer(cv, 566, WAVE_A, 55, 112, 20)
    wave_layer(cv, 628, WAVE_B, 48, 98, 64)
    wave_layer(cv, 688, WAVE_C, 42, 86, 30)
    # foam: white arcs tracing some crest tops (every other crest on the
    # middle layer, every crest on the front layer, thinner there)
    for top_y, crest_r, spacing, off, step, wdt in ((628, 48, 98, 64, 2, 4),
                                                    (688, 42, 86, 30, 1, 3)):
        x = off
        n = 0
        while x < W + spacing:
            if n % step == 0:
                cv.arc(x, top_y, crest_r - 6, math.radians(205),
                       math.radians(335), WHITE, wdt)
            x += spacing
            n += 1
    # big foam curl (Hokusai hook) on the front wave, right side
    cv.bezier((830, 700), (880, 640), (940, 640), (950, 700), WHITE, 6)
    cv.bezier((830, 700), (875, 655), (925, 655), (938, 700), TURQ, 3)

    # one large curling crest on the left + a tiny lantern boat
    curl_wave(cv)
    boat(cv, 150, 690)

    # --- ladder + clockmaker (in front of the waves) ---
    ladder(cv, (455, 768), (585, 395), (525, 768), (640, 400), rungs=7)
    figure(cv)
    apprentice(cv)

    # --- frame ---
    cv.fill_rect(0, 0, W, 9, INK)
    cv.fill_rect(0, H - 9, W, H, INK)
    cv.fill_rect(0, 0, 9, H, INK)
    cv.fill_rect(W - 9, 0, W, H, INK)
    cv.fill_rect(12, 12, W - 12, 14, GOLD_D)
    cv.fill_rect(12, H - 14, W - 12, H - 12, GOLD_D)
    cv.fill_rect(12, 12, 14, H - 12, GOLD_D)
    cv.fill_rect(W - 14, 12, W - 12, H - 12, GOLD_D)

    return cv


# ---------------------------------------------------------------- PNG
def write_png(path, cv):
    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)  # filter: none
        raw += cv.buf[y * cv.w * 3:(y + 1) * cv.w * 3]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        return out + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", comp) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    cv = draw()
    write_png(os.path.join(out_dir, "entry.png"), cv)


if __name__ == "__main__":
    main()
