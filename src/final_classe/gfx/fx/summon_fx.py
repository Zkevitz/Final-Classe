"""Briques du grand spectacle des invocations (utilisées par `choreo/summons.py`).

`Stage` (suivi des effets créés), `Letterbox` (bandes de cinéma), `ImpactWarp` (zoom + aberration
chromatique plein écran), `Rays` (rayons de lumière additifs), `Inflow` (particules qui spiralent vers
un point), `Aurora`, `Rain`, `anchor_top` / `anchor_bright` (points d'ancrage trouvés dans l'image,
indépendants de son orientation).
"""
from __future__ import annotations

import math
import random

import numpy as np
import pygame
from pygame import Vector2

from . import (Effect, Flash, ScreenShake, blit_glow, clamp01, mix, scaled,
               BLACK, ICE, WHITE)

# ----------------------------------------------------------------- suivi des effets


class Stage:
    """Garde la liste des effets créés par une chorégraphie et les tue à la fin (ou au `skip()`)."""

    def __init__(self, c) -> None:
        self.c = c
        self.items: list[Effect] = []
        c.on_end(self.clear)

    def spawn(self, effect: Effect, layer: str | None = None) -> Effect:
        self.c.spawn(effect, layer)
        self.items.append(effect)
        return effect

    def add(self, effect: Effect, layer: str | None = None):
        """Étape de séquence qui crée l'effet au moment voulu."""
        from .choreo import Call
        return Call(self.spawn, effect, layer)

    def clear(self) -> None:
        for e in self.items:
            e.kill()
        self.items.clear()


# ----------------------------------------------------------------- cinéma


class Letterbox(Effect):
    """Bandes noires haut et bas (`k` de 0 à 1)."""

    layer = "overlay"
    top = True  # dessiné après tous les autres effets du calque (au-dessus des lueurs additives)

    def __init__(self, size: float = 62.0) -> None:
        self.size, self.k = size, 0.0

    def update(self, dt: float) -> bool:
        return not self.dead

    def render(self, surface: pygame.Surface) -> None:
        bh = int(self.size * clamp01(self.k))
        if bh <= 0:
            return
        w, h = surface.get_size()
        surface.fill(BLACK, (0, 0, w, bh))
        surface.fill(BLACK, (0, h - bh, w, bh))


class ImpactWarp(Effect):
    """Coup de zoom radial + aberration chromatique sur l'image déjà dessinée (court : 0,2 à 0,6 s)."""

    layer = "overlay"

    def __init__(self, life: float = 0.35, zoom: float = 0.06, split: float = 7.0, center=None,
                 delay: float = 0.0) -> None:
        self.life, self.zoom, self.split, self.center, self.t = life, zoom, split, center, -delay

    def update(self, dt: float) -> bool:
        self.t += dt
        return self.t < self.life and not self.dead

    def render(self, surface: pygame.Surface) -> None:
        if self.t < 0:
            return
        k = (1 - clamp01(self.t / self.life)) ** 2
        if k < 0.03:
            return
        w, h = surface.get_size()
        cx, cy = self.center if self.center is not None else (w / 2, h / 2)
        if self.zoom > 0:
            z = 1 + self.zoom * k
            big = pygame.transform.scale(surface, (int(w * z), int(h * z)))
            surface.blit(big, (int(cx - cx * z), int(cy - cy * z)))
        dx = int(self.split * k)
        if dx >= 1:
            r = surface.copy()
            b = surface.copy()
            r.fill((255, 0, 0), special_flags=pygame.BLEND_MULT)
            b.fill((0, 0, 255), special_flags=pygame.BLEND_MULT)
            surface.fill((0, 255, 0), special_flags=pygame.BLEND_MULT)
            surface.blit(r, (-dx, 0), special_flags=pygame.BLEND_ADD)
            surface.blit(b, (dx, 0), special_flags=pygame.BLEND_ADD)


# ----------------------------------------------------------------- lumière

_RAYS: dict = {}
_RAY_CACHE: dict = {}  # images déjà tournées/agrandies (borné)


def _ray_tex(color) -> pygame.Surface:
    key = tuple(color)
    tex = _RAYS.get(key)
    if tex is None:
        n = 256
        ax = (np.arange(n) - n / 2 + 0.5) / (n / 2)
        yy, xx = ax[:, None], ax[None, :]
        d = np.sqrt(xx ** 2 + yy ** 2)
        ang = np.arctan2(yy, xx)
        pat = (0.5 + 0.5 * np.cos(11 * ang + 2.2 * np.sin(3 * ang) + 0.8 * np.cos(5 * ang))) ** 5
        prof = np.clip(1 - d, 0, 1) ** 1.2 * np.clip(d * 6, 0, 1)
        v = (pat * 0.85 + 0.15) * prof
        rgb = v[..., None] * np.array(color, dtype=np.float32)[None, None, :]
        tex = pygame.surfarray.make_surface(np.clip(rgb, 0, 255).astype(np.uint8).transpose(1, 0, 2))
        _RAYS[key] = tex
    return tex


class Rays(Effect):
    """Rayons de lumière additifs qui tournent autour de `pos` (rayon `r`, intensité `k`)."""

    layer = "back"

    def __init__(self, pos, r: float = 520.0, color=WHITE, spin: float = 14.0, layer: str = "back") -> None:
        self.pos, self.r, self.color, self.spin, self.layer = Vector2(pos), r, color, spin, layer
        self.k, self.angle, self.follow = 0.0, random.uniform(0, 360), None

    def update(self, dt: float) -> bool:
        self.angle += self.spin * dt
        if self.follow:
            self.pos = Vector2(self.follow())
        return not self.dead

    def render(self, surface: pygame.Surface) -> None:
        if self.k <= 0.03 or self.r < 20:
            return
        s = max(16, int(round(self.r / 24)) * 48)
        kq = max(1, int(clamp01(self.k) * 6 + 0.5))
        step = 1 if abs(self.spin) <= 12 else 2 if abs(self.spin) <= 20 else 3  # pas adapté à la vitesse
        key = (tuple(self.color), int(self.angle // step * step) % 360, s, kq)
        img = _RAY_CACHE.get(key)
        if img is None:
            rot = pygame.transform.rotozoom(_ray_tex(self.color), key[1], 1.0)
            rot.fill(scaled(WHITE, kq / 6), special_flags=pygame.BLEND_MULT)
            img = pygame.transform.scale(rot, (s, s))
            _RAY_CACHE[key] = img
            while len(_RAY_CACHE) > 24:
                del _RAY_CACHE[next(iter(_RAY_CACHE))]
        surface.blit(img, (self.pos.x - s / 2, self.pos.y - s / 2), special_flags=pygame.BLEND_ADD)


class Inflow(Effect):
    """Particules qui spiralent vers `pos` (aspiration). `k` = visibilité, `pull` = vitesse d'aspiration 0..1."""

    layer = "overlay"

    def __init__(self, pos, count: int = 220, r_out: float = 430.0, r_in: float = 24.0,
                 colors=(WHITE, ICE), layer: str = "overlay", seed: int = 5) -> None:
        self.pos, self.r_out, self.r_in, self.layer = Vector2(pos), r_out, r_in, layer
        rng = random.Random(seed)
        self.colors = list(colors)
        self.k = self.pull = 0.0
        self.follow = None
        self.p = [[rng.uniform(0, math.tau), rng.uniform(r_in, r_out), rng.uniform(70, 230),
                   rng.choice((5, 8, 12)), rng.randrange(len(self.colors)), rng.uniform(0.6, 1.8) * rng.choice((1, 1, -1))]
                  for _ in range(count)]

    def update(self, dt: float) -> bool:
        if self.follow:
            self.pos = Vector2(self.follow())
        sp = 0.25 + 2.4 * clamp01(self.pull) ** 1.5
        for q in self.p:
            q[1] -= q[2] * sp * dt * (0.5 + q[1] / self.r_out)
            q[0] += q[5] * dt * (0.4 + 2.5 * clamp01(self.pull)) * (1.3 - 0.9 * q[1] / self.r_out)
            if q[1] < self.r_in:
                q[1] = self.r_out * random.uniform(0.7, 1.15)
                q[0] = random.uniform(0, math.tau)
        return not self.dead

    def render(self, surface: pygame.Surface) -> None:
        if self.k <= 0.03:
            return
        px, py = self.pos
        for a, d, sp, size, ci, _ in self.p:
            x, y = px + math.cos(a) * d, py + math.sin(a) * d * 0.9
            k = clamp01(self.k * min(1.0, (d - self.r_in) / 60.0) * (0.45 + 0.55 * (1 - d / self.r_out)))
            if k <= 0.04:
                continue
            col = self.colors[ci]
            blit_glow(surface, (x, y), size, col, k)
            if self.pull > 0.25:
                n = min(40.0, 6 + sp * self.pull * 0.12)
                pygame.draw.line(surface, scaled(col, k * 0.7), (x, y),
                                 (x + math.cos(a) * n, y + math.sin(a) * n * 0.9), 1)


class Aurora(Effect):
    """Rubans de lumière froide qui ondulent en haut de l'écran."""

    layer = "back"

    def __init__(self, colors=(ICE, (140, 230, 200), (160, 140, 255))) -> None:
        self.colors, self.k, self.t = list(colors), 0.0, 0.0

    def update(self, dt: float) -> bool:
        self.t += dt
        return not self.dead

    def render(self, surface: pygame.Surface) -> None:
        if self.k <= 0.03:
            return
        w, h = surface.get_size()
        for i, col in enumerate(self.colors):
            base = h * (0.12 + 0.07 * i)
            for x in range(-40, w + 80, 70):
                y = base + math.sin(x * 0.006 + self.t * (0.7 + 0.3 * i) + i * 2) * 46 + math.sin(x * 0.015 - self.t) * 16
                a = self.k * (0.3 + 0.2 * math.sin(x * 0.01 + self.t * 1.3 + i))
                blit_glow(surface, (x, y), 90, col, a)
                blit_glow(surface, (x, y + 70), 60, col, a * 0.5)


class Rain(Effect):
    """Pluie battante en diagonale (`k` = visibilité)."""

    layer = "overlay"

    def __init__(self, count: int = 170, seed: int = 9, color=(150, 175, 230)) -> None:
        rng = random.Random(seed)
        self.d = [[rng.random(), rng.random(), rng.uniform(900, 1500), rng.uniform(14, 30)] for _ in range(count)]
        self.k, self.color = 0.0, color

    def update(self, dt: float) -> bool:
        for d in self.d:
            d[1] = (d[1] + d[2] * dt / 720.0) % 1.0
            d[0] = (d[0] - d[2] * 0.18 * dt / 1280.0) % 1.0
        return not self.dead

    def render(self, surface: pygame.Surface) -> None:
        if self.k <= 0.03:
            return
        w, h = surface.get_size()
        col = scaled(self.color, clamp01(self.k) * 0.8)
        for x, y, sp, ln in self.d:
            px, py = x * w, y * h
            pygame.draw.line(surface, col, (px, py), (px - ln * 0.18, py + ln), 1)


# ----------------------------------------------------------------- ancres dans l'image


def anchor_head(img: pygame.Surface, mouth=(0.74, 0.26)) -> tuple[float, float]:
    """Position de la gueule d'un dragon, quel que soit son sens : la queue (partie basse la plus étirée)
    est du côté opposé à la tête. `mouth` = position quand la tête est à droite."""
    try:
        al = pygame.surfarray.array_alpha(img)
    except (pygame.error, ValueError):
        return mouth
    w, h = al.shape
    low = al[:, int(h * 0.6):] > 60
    xs = np.where(low.any(axis=1))[0]
    if not len(xs):
        return mouth
    m = (al > 60).sum(axis=1).astype(float)
    cx = float((m * np.arange(w)).sum() / max(1.0, m.sum()))
    head_right = (cx - xs[0]) >= (xs[-1] - cx)
    return (mouth[0] if head_right else 1 - mouth[0]), mouth[1]


def anchor_top(img: pygame.Surface, depth: int = 10) -> tuple[float, float]:
    """(fx, fy) du point le plus haut de l'image (bout du bâton), en fractions de la taille de l'image."""
    try:
        al = pygame.surfarray.array_alpha(img)  # (w, h)
    except (pygame.error, ValueError):
        return 0.5, 0.1
    rows = np.where((al > 60).any(axis=0))[0]
    if not len(rows):
        return 0.5, 0.1
    y0 = int(rows[0])
    xs = np.where((al[:, y0:y0 + depth] > 60).any(axis=1))[0]
    return float(xs.mean() / img.get_width()), float((y0 + depth * 0.6) / img.get_height())


def anchor_bright(img: pygame.Surface, default=(0.74, 0.26)) -> tuple[float, float]:
    """(fx, fy) du foyer le plus lumineux (blanc-bleuté : orbe dans la gueule), sinon `default`."""
    try:
        rgb = pygame.surfarray.array3d(img).astype(np.int16)
        al = pygame.surfarray.array_alpha(img)
    except (pygame.error, ValueError):
        return default
    m = (rgb.min(axis=2) > 205) & (al > 200)
    if int(m.sum()) < 25:
        return default
    xs, ys = np.where(m)
    # amas le plus dense : médiane (robuste aux reflets isolés)
    return float(np.median(xs) / img.get_width()), float(np.median(ys) / img.get_height())


__all__ = ["Stage", "Letterbox", "ImpactWarp", "Rays", "Inflow", "Aurora", "Rain", "anchor_top",
           "anchor_head", "anchor_bright", "Flash", "ScreenShake", "mix"]
