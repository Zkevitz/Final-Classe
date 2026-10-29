"""Briques d'effets visuels de Final Classe (game feel).

Tout est piloté par `dt` (secondes). Un effet expose `update(dt) -> bool`
(False = terminé) et `draw(surface, layer)`. Calques : "back" (derrière les
sprites), "front" (devant), "overlay" (au-dessus de l'interface).

Le `FxManager` tient la liste des effets ; la scène appelle `update(dt)`, puis
`draw(surface, layer)` pour chaque calque, et ajoute `fx.shake_offset` au
décalage de sa caméra. `fx.hide_ui` est vrai pendant les invocations.

Les lueurs sont pré-calculées (numpy) et mises en cache ; on les dessine en
`BLEND_ADD`. Aucune Surface n'est créée par particule et par image.
"""
from __future__ import annotations

import math
import random
from typing import Callable, Iterable, Sequence

import numpy as np
import pygame
from pygame import Vector2

Color = tuple[int, int, int]

# ----------------------------------------------------------------- palette (DA §4)
WHITE: Color = (255, 255, 255)
BLACK: Color = (0, 0, 0)
GOLD: Color = (242, 193, 78)
FIRE: Color = (255, 107, 45)
ICE: Color = (127, 216, 255)
THUNDER: Color = (255, 233, 74)
HOLY: Color = (200, 162, 255)
GREEN: Color = (74, 222, 128)
BLUE: Color = (96, 165, 250)
RED: Color = (239, 68, 68)
PALE: Color = (232, 236, 248)
STEEL: Color = (169, 180, 216)
NAVY: Color = (36, 53, 140)
POISON: Color = (150, 120, 210)

# ----------------------------------------------------------------- easing


def _out_back(t: float) -> float:
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def _in_back(t: float) -> float:
    c1 = 1.70158
    return (c1 + 1) * t ** 3 - c1 * t ** 2


def _out_elastic(t: float) -> float:
    if t in (0.0, 1.0):
        return t
    return 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi / 3)) + 1


def _out_bounce(t: float) -> float:
    n, d = 7.5625, 2.75
    if t < 1 / d:
        return n * t * t
    if t < 2 / d:
        t -= 1.5 / d
        return n * t * t + 0.75
    if t < 2.5 / d:
        t -= 2.25 / d
        return n * t * t + 0.9375
    t -= 2.625 / d
    return n * t * t + 0.984375


EASE: dict[str, Callable[[float], float]] = {
    "linear": lambda t: t,
    "in_quad": lambda t: t * t,
    "out_quad": lambda t: 1 - (1 - t) * (1 - t),
    "in_out_quad": lambda t: 2 * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 2 / 2,
    "in_cubic": lambda t: t ** 3,
    "out_cubic": lambda t: 1 - (1 - t) ** 3,
    "in_out_cubic": lambda t: 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2,
    "in_out_sine": lambda t: -(math.cos(math.pi * t) - 1) / 2,
    "out_expo": lambda t: 1.0 if t >= 1 else 1 - 2 ** (-10 * t),
    "in_expo": lambda t: 0.0 if t <= 0 else 2 ** (10 * t - 10),
    "out_back": _out_back,
    "in_back": _in_back,
    "out_elastic": _out_elastic,
    "out_bounce": _out_bounce,
}


def ease(spec: str | Callable[[float], float], t: float) -> float:
    """Applique une courbe (nom ou fonction) à t borné dans [0, 1]."""
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    fn = EASE[spec] if isinstance(spec, str) else spec
    return fn(t)


def lerp(a, b, t: float):
    """Interpolation linéaire de nombres, Vector2 ou tuples."""
    if isinstance(a, Vector2):
        return a + (Vector2(b) - a) * t
    if isinstance(a, (tuple, list)):
        return tuple(x + (y - x) * t for x, y in zip(a, b))
    return a + (b - a) * t


def clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def scaled(color: Sequence[int], k: float) -> Color:
    """Couleur multipliée par k (0..1) : fondu vers le noir."""
    k = clamp01(k)
    return (int(color[0] * k), int(color[1] * k), int(color[2] * k))


def mix(a: Sequence[int], b: Sequence[int], t: float) -> Color:
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def polar(angle_deg: float, length: float = 1.0) -> Vector2:
    a = math.radians(angle_deg)
    return Vector2(math.cos(a) * length, math.sin(a) * length)


# ----------------------------------------------------------------- base


class Effect:
    """Base d'un effet : `layer` = calque, `dead` = arrêt demandé, `tag` = nom optionnel."""

    layer = "front"
    dead = False
    tag: str | None = None

    def update(self, dt: float) -> bool:
        return False

    def render(self, surface: pygame.Surface) -> None:
        pass

    def draw(self, surface: pygame.Surface, layer: str) -> None:
        if layer == self.layer:
            self.render(surface)

    def kill(self) -> None:
        self.dead = True


class Tween(Effect):
    """Interpolation dans le temps : `value`, `on_update(value)`, `on_done()`."""

    def __init__(self, start, end, duration: float, easing="out_quad",
                 on_update: Callable | None = None, on_done: Callable | None = None,
                 delay: float = 0.0) -> None:
        self.start, self.end = start, end
        self.duration = max(1e-6, duration)
        self.easing = easing
        self.on_update, self.on_done = on_update, on_done
        self.t = -delay
        self.value = start

    @property
    def progress(self) -> float:
        return clamp01(self.t / self.duration)

    def update(self, dt: float) -> bool:
        self.t += dt
        if self.t < 0:
            return True
        self.value = lerp(self.start, self.end, ease(self.easing, self.progress))
        if self.on_update:
            self.on_update(self.value)
        if self.t >= self.duration:
            if self.on_done:
                self.on_done()
            return False
        return True


# ----------------------------------------------------------------- textures en cache

_GLOW: dict[tuple, pygame.Surface] = {}
_SCRATCH: dict[tuple, pygame.Surface] = {}
_FONTS: dict[tuple, pygame.font.Font] = {}
_TEXT: dict[tuple, pygame.Surface] = {}
FONT_NAMES = ["Segoe UI Semibold", "Segoe UI", "Trebuchet MS", "Arial"]


def font(size: int, bold: bool = True) -> pygame.font.Font:
    key = (size, bold)
    if key not in _FONTS:
        if not pygame.font.get_init():
            pygame.font.init()
        _FONTS[key] = pygame.font.SysFont(FONT_NAMES, size, bold=bold)
    return _FONTS[key]


def glow(radius: float, color: Sequence[int] = WHITE, a: float = 1.0) -> pygame.Surface:
    """Disque lumineux (RGB, à dessiner en BLEND_ADD), mis en cache.

    `a` (0..1) est quantifié sur 8 paliers pour limiter le cache.
    """
    r = max(2, int(radius))
    q = 1 if r < 14 else 2 if r < 32 else 4 if r < 80 else 8 if r < 160 else 16 if r < 320 else 32  # rayon quantifié
    r = max(2, int(round(r / q)) * q)
    b = max(1, min(8, int(a * 8 + 0.5)))
    key = (r, (int(color[0]) >> 4 << 4 | 8, int(color[1]) >> 4 << 4 | 8, int(color[2]) >> 4 << 4 | 8), b)
    surf = _GLOW.get(key)
    if surf is None:
        if len(_GLOW) > 2500:  # cache borné : on évince les plus anciennes entrées
            for k in list(_GLOW)[:800]:
                del _GLOW[k]
        rr = r // 2 if r >= 64 else r  # grandes lueurs : calcul en demi-résolution puis agrandissement
        n = rr * 2
        ax = np.arange(n) - rr + 0.5
        d = np.sqrt(ax[:, None] ** 2 + ax[None, :] ** 2) / rr
        v = np.clip(1 - d, 0, 1)
        prof = v ** 2 * 0.8 + np.clip(1 - d * 2.4, 0, 1) ** 2 * 0.7
        col = np.array(key[1], dtype=np.float32)
        rgb = prof[..., None] * (col * 0.9 + 25) * (b / 8)
        surf = pygame.surfarray.make_surface(np.clip(rgb, 0, 255).astype(np.uint8))
        if rr != r:
            surf = pygame.transform.smoothscale(surf, (r * 2, r * 2))
        _GLOW[key] = surf
    return surf


def blit_glow(surface: pygame.Surface, pos, radius: float, color: Sequence[int] = WHITE,
              a: float = 1.0) -> None:
    if a <= 0.03 or radius < 1:
        return
    g = glow(radius, color, a)
    surface.blit(g, (pos[0] - g.get_width() // 2, pos[1] - g.get_height() // 2),
                 special_flags=pygame.BLEND_ADD)


def scratch(size: tuple[int, int], name: str = "full") -> pygame.Surface:
    """Surface RGBA partagée (pour les voiles plein écran)."""
    key = (name, size)
    s = _SCRATCH.get(key)
    if s is None:
        s = pygame.Surface(size, pygame.SRCALPHA)
        _SCRATCH[key] = s
    return s


def veil(surface: pygame.Surface, color: Sequence[int], alpha: float,
         additive: bool = False, rect: pygame.Rect | None = None) -> None:
    """Voile coloré semi-transparent sur toute la surface (ou un rectangle)."""
    if alpha <= 0.004:
        return
    if additive:
        k = scaled(color, alpha)
        surface.fill(k, rect, special_flags=pygame.BLEND_ADD)
        return
    size = rect.size if rect else surface.get_size()
    s = scratch(size, "veil")
    s.fill((color[0], color[1], color[2], int(255 * clamp01(alpha))))
    surface.blit(s, rect.topleft if rect else (0, 0))


def text_surface(text: str, size: int, color: Sequence[int], outline: int = 2) -> pygame.Surface:
    """Texte avec contour noir, mis en cache."""
    key = (text, size, tuple(color), outline)
    s = _TEXT.get(key)
    if s is None:
        if len(_TEXT) > 400:
            _TEXT.clear()
        f = font(size)
        body = f.render(text, True, color)
        edge = f.render(text, True, (0, 0, 0))
        s = pygame.Surface((body.get_width() + outline * 2, body.get_height() + outline * 2),
                           pygame.SRCALPHA)
        for dx in range(-outline, outline + 1):
            for dy in range(-outline, outline + 1):
                if dx or dy:
                    s.blit(edge, (outline + dx, outline + dy))
        s.blit(body, (outline, outline))
        _TEXT[key] = s
    return s


# ----------------------------------------------------------------- particules

PRESETS: dict[str, dict] = {
    "fire": dict(colors=[FIRE, (255, 170, 60), (255, 233, 120)], speed=(40, 190), life=(0.4, 1.0),
                 size=(5, 13), gravity=-110, drag=1.0, kind="glow", angle=-90, spread=80, shrink=1.0),
    "ice": dict(colors=[ICE, (220, 245, 255), WHITE], speed=(50, 230), life=(0.5, 1.1),
                size=(3, 8), gravity=160, drag=0.8, kind="shard", angle=-90, spread=360, shrink=0.5),
    "thunder": dict(colors=[THUNDER, WHITE, (255, 250, 170)], speed=(150, 520), life=(0.15, 0.4),
                    size=(2, 4), gravity=0, drag=2.0, kind="streak", angle=-90, spread=360, shrink=0.6),
    "holy": dict(colors=[HOLY, (255, 244, 200), GOLD], speed=(15, 90), life=(0.8, 1.6),
                 size=(4, 10), gravity=-70, drag=0.8, kind="glow", angle=-90, spread=120, shrink=0.7),
    "heal": dict(colors=[GREEN, (190, 255, 210), WHITE], speed=(10, 60), life=(0.9, 1.7),
                 size=(4, 9), gravity=-90, drag=0.5, kind="glow", angle=-90, spread=60, shrink=0.6),
    "dust": dict(colors=[STEEL, (111, 128, 200), PALE], speed=(30, 170), life=(0.4, 0.9),
                 size=(3, 8), gravity=60, drag=3.0, kind="dot", angle=-90, spread=160, shrink=0.8),
    "sparkle": dict(colors=[WHITE, GOLD, (255, 244, 200)], speed=(20, 140), life=(0.4, 1.0),
                    size=(3, 8), gravity=40, drag=1.5, kind="star", angle=-90, spread=360, shrink=1.0),
    "coins": dict(colors=[GOLD, (255, 220, 120)], speed=(180, 420), life=(0.9, 1.3),
                  size=(5, 7), gravity=900, drag=0.2, kind="dot", angle=-90, spread=110, shrink=0.0),
    "poison": dict(colors=[(95, 190, 120), POISON, (120, 90, 170)], speed=(20, 90), life=(0.9, 1.8),
                   size=(10, 26), gravity=-30, drag=1.0, kind="glow", angle=-90, spread=360, shrink=-0.6),
}


class _P:
    __slots__ = ("x", "y", "vx", "vy", "life", "age", "size", "color", "rot", "vrot")


class ParticleEmitter(Effect):
    """Émetteur de particules : rafale (`count`) et/ou flux (`rate`/s pendant `duration`).

    `preset` : fire, ice, thunder, holy, heal, dust, sparkle, coins, poison.
    `angle`/`spread` : direction et ouverture en degrés ; `radius` : zone d'apparition ;
    `speed`, `size`, `life` : multiplicateurs ; `attract` : point qui aspire les particules ;
    `follow` : fonction renvoyant la position de l'émetteur.
    """

    def __init__(self, pos, preset: str = "fire", count: int = 0, rate: float = 0.0,
                 duration: float = 0.0, radius: float = 0.0, angle: float | None = None,
                 spread: float | None = None, speed: float = 1.0, size: float = 1.0,
                 life: float = 1.0, colors: Sequence[Color] | None = None,
                 gravity: float | None = None, attract=None, attract_force: float = 600.0,
                 follow: Callable[[], Vector2] | None = None, layer: str = "front",
                 delay: float = 0.0, additive: bool | None = None) -> None:
        p = PRESETS[preset]
        self.cfg = p
        self.pos = Vector2(pos)
        self.layer = layer
        self.rate, self.duration, self.radius = rate, duration, radius
        self.angle = p["angle"] if angle is None else angle
        self.spread = p["spread"] if spread is None else spread
        self.speed, self.size_k, self.life_k = speed, size, life
        self.colors = list(colors or p["colors"])
        self.gravity = p["gravity"] if gravity is None else gravity
        self.attract = Vector2(attract) if attract is not None else None
        self.attract_force = attract_force
        self.follow = follow
        self.additive = (p["kind"] in ("glow", "star")) if additive is None else additive
        self.parts: list[_P] = []
        self.t = -delay
        self.pending = count
        self.acc = 0.0

    def emit(self, n: int) -> None:
        p = self.cfg
        for _ in range(n):
            q = _P()
            a = math.radians(self.angle + random.uniform(-self.spread / 2, self.spread / 2))
            sp = random.uniform(*p["speed"]) * self.speed
            r = self.radius
            if r:
                ang, d = random.uniform(0, math.tau), r * math.sqrt(random.random())
                q.x, q.y = self.pos.x + math.cos(ang) * d, self.pos.y + math.sin(ang) * d
            else:
                q.x, q.y = self.pos.x, self.pos.y
            q.vx, q.vy = math.cos(a) * sp, math.sin(a) * sp
            q.life = random.uniform(*p["life"]) * self.life_k
            q.age = 0.0
            q.size = random.uniform(*p["size"]) * self.size_k
            q.color = random.choice(self.colors)
            q.rot = random.uniform(0, math.tau)
            q.vrot = random.uniform(-6, 6)
            self.parts.append(q)

    def update(self, dt: float) -> bool:
        if self.follow:
            self.pos = Vector2(self.follow())
        self.t += dt
        if self.t >= 0:
            if self.pending:
                self.emit(self.pending)
                self.pending = 0
            if self.rate and self.t <= self.duration + dt:
                self.acc += self.rate * dt
                n = int(self.acc)
                self.acc -= n
                self.emit(n)
        drag = self.cfg["drag"]
        g = self.gravity
        att = self.attract
        keep = []
        for q in self.parts:
            q.age += dt
            if q.age >= q.life:
                continue
            if att is not None:
                dx, dy = att.x - q.x, att.y - q.y
                d = math.hypot(dx, dy) or 1.0
                q.vx += dx / d * self.attract_force * dt
                q.vy += dy / d * self.attract_force * dt
                if d < 8:
                    continue
            q.vy += g * dt
            k = max(0.0, 1 - drag * dt)
            q.vx *= k
            q.vy *= k
            q.x += q.vx * dt
            q.y += q.vy * dt
            q.rot += q.vrot * dt
            keep.append(q)
        self.parts = keep
        return bool(keep) or self.pending > 0 or self.t < 0 or (self.rate and self.t <= self.duration)

    def render(self, surface: pygame.Surface) -> None:
        kind = self.cfg["kind"]
        shrink = self.cfg["shrink"]
        add = self.additive
        for q in self.parts:
            t = q.age / q.life
            a = 1 - t * t
            s = q.size * (1 - t * shrink) if shrink >= 0 else q.size * (1 - shrink * t)
            if s < 1:
                continue
            if kind == "glow":
                blit_glow(surface, (q.x, q.y), s, q.color, a)
            elif kind == "dot":
                col = scaled(q.color, a) if add else q.color
                pygame.draw.circle(surface, col, (int(q.x), int(q.y)), max(1, int(s)))
            elif kind == "streak":
                col = scaled(q.color, a)
                pygame.draw.line(surface, col, (q.x, q.y), (q.x - q.vx * 0.04, q.y - q.vy * 0.04),
                                 max(1, int(s)))
            elif kind == "star":
                col = scaled(q.color, a)
                x, y = q.x, q.y
                pygame.draw.line(surface, col, (x - s, y), (x + s, y), 2)
                pygame.draw.line(surface, col, (x, y - s), (x, y + s), 2)
                blit_glow(surface, (x, y), s * 1.6, q.color, a * 0.6)
            else:  # shard : losange tournant
                col = scaled(q.color, 0.35 + 0.65 * a)
                c, sn = math.cos(q.rot) * s, math.sin(q.rot) * s
                x, y = q.x, q.y
                pygame.draw.polygon(surface, col, [(x + c * 1.6, y + sn * 1.6), (x - sn * 0.6, y + c * 0.6),
                                                   (x - c * 1.6, y - sn * 1.6), (x + sn * 0.6, y - c * 0.6)])


# ----------------------------------------------------------------- texte flottant


class FloatingText(Effect):
    """Chiffre ou texte flottant. `kind` : damage (rebondit), heal, mp, free."""

    layer = "front"

    def __init__(self, text: str, pos, color: Color = WHITE, size: int = 34, crit: bool = False,
                 kind: str = "damage", delay: float = 0.0, life: float = 1.3) -> None:
        if crit:
            color, size = GOLD, int(size * 1.45)
        self.text, self.size, self.color, self.crit = str(text), size, color, crit
        self.pos0 = Vector2(pos)
        self.kind, self.life = kind, life
        self.t = -delay
        self.vy = -380.0
        self.dy = 0.0
        self.bounced = False

    def update(self, dt: float) -> bool:
        self.t += dt
        if self.t < 0:
            return True
        if self.kind == "damage":
            self.vy += 1500 * dt
            self.dy += self.vy * dt
            if self.dy > 0 and self.vy > 0 and not self.bounced:
                self.dy, self.vy, self.bounced = 0.0, -self.vy * 0.33, True
            elif self.dy > 0 and self.bounced:
                self.dy, self.vy = 0.0, 0.0
        else:
            self.dy = -70 * ease("out_cubic", self.t / 0.9)
        return self.t < self.life

    def render(self, surface: pygame.Surface) -> None:
        if self.t < 0:
            return
        s = text_surface(self.text, self.size, self.color)
        pop = ease("out_back", self.t / 0.18)
        k = (1.0 + (0.5 if self.crit else 0.2) * (1 - pop)) * (0.4 + 0.6 * pop)
        if abs(k - 1) > 0.04:
            k = round(k * 20) / 20
            s = pygame.transform.smoothscale(s, (max(1, int(s.get_width() * k)), max(1, int(s.get_height() * k))))
        fade = clamp01((self.life - self.t) / 0.35)
        if fade < 1:
            s = s.copy()
            s.set_alpha(int(255 * fade))
        surface.blit(s, (self.pos0.x - s.get_width() / 2, self.pos0.y + self.dy - s.get_height() / 2))


# ----------------------------------------------------------------- écran


class ScreenShake(Effect):
    """Tremblement d'écran : le `FxManager` additionne les `offset` dans `shake_offset`."""

    layer = "none"

    def __init__(self, amplitude: float = 8.0, duration: float = 0.3, decay: bool = True) -> None:
        self.amp, self.duration, self.decay = amplitude, max(1e-3, duration), decay
        self.t = 0.0
        self.offset = Vector2()

    def update(self, dt: float) -> bool:
        self.t += dt
        k = (1 - self.t / self.duration) if self.decay else 1.0
        a = self.amp * max(0.0, k)
        self.offset = Vector2(random.uniform(-a, a), random.uniform(-a, a))
        return self.t < self.duration


class Flash(Effect):
    """Flash plein écran (ou limité à `rect`) qui s'estompe."""

    def __init__(self, color: Color = WHITE, duration: float = 0.25, peak: float = 1.0,
                 attack: float = 0.0, layer: str = "overlay", rect: pygame.Rect | None = None,
                 additive: bool = False) -> None:
        self.color, self.duration, self.peak, self.attack = color, max(1e-3, duration), peak, attack
        self.layer, self.rect, self.additive = layer, rect, additive
        self.t = 0.0

    def update(self, dt: float) -> bool:
        self.t += dt
        return self.t < self.duration + self.attack

    def alpha(self) -> float:
        if self.t < self.attack:
            return self.peak * self.t / self.attack
        return self.peak * clamp01(1 - (self.t - self.attack) / self.duration)

    def render(self, surface: pygame.Surface) -> None:
        veil(surface, self.color, self.alpha(), self.additive, self.rect)


class ScreenTint(Effect):
    """Assombrit ou teinte l'écran : fondu entrant, maintien, fondu sortant."""

    def __init__(self, color: Color = BLACK, alpha: float = 0.6, fade_in: float = 0.3,
                 hold: float = 1.0, fade_out: float = 0.4, layer: str = "overlay",
                 additive: bool = False) -> None:
        self.color, self.peak = color, alpha
        self.fi, self.hold, self.fo = max(1e-3, fade_in), hold, max(1e-3, fade_out)
        self.layer, self.additive = layer, additive
        self.t = 0.0
        self.releasing = False

    def release(self) -> None:
        """Termine le maintien tout de suite (fondu sortant)."""
        self.t = max(self.t, self.fi + self.hold)

    def update(self, dt: float) -> bool:
        self.t += dt
        return self.t < self.fi + self.hold + self.fo

    def alpha(self) -> float:
        if self.t < self.fi:
            return self.peak * self.t / self.fi
        if self.t < self.fi + self.hold:
            return self.peak
        return self.peak * clamp01(1 - (self.t - self.fi - self.hold) / self.fo)

    def render(self, surface: pygame.Surface) -> None:
        veil(surface, self.color, self.alpha(), self.additive)


class Fade(Effect):
    """Fondu d'une couleur (noir par défaut) de `a0` à `a1` en `duration`, puis `hold`."""

    def __init__(self, a0: float = 0.0, a1: float = 1.0, duration: float = 0.5, color: Color = BLACK,
                 hold: float = 0.0, easing="in_out_quad") -> None:
        self.a0, self.a1, self.duration, self.color = a0, a1, max(1e-3, duration), color
        self.hold, self.easing = hold, easing
        self.layer = "overlay"
        self.t = 0.0

    def update(self, dt: float) -> bool:
        self.t += dt
        return self.t < self.duration + self.hold

    @property
    def alpha(self) -> float:
        return lerp(self.a0, self.a1, ease(self.easing, self.t / self.duration))

    def render(self, surface: pygame.Surface) -> None:
        veil(surface, self.color, self.alpha)


# ----------------------------------------------------------------- traînées


class Trail(Effect):
    """Traînée effilée (arme, projectile). Ajouter des points avec `add`, ou `follow=fonction`.

    Se termine après `stop()` quand tous les points ont vieilli (`life` secondes).
    """

    def __init__(self, points: Iterable = (), color: Color = WHITE, width: float = 12.0,
                 life: float = 0.3, follow: Callable[[], Vector2] | None = None,
                 core: Color | None = WHITE, layer: str = "front", glow_color: Color | None = None) -> None:
        self.pts: list[list[float]] = [[p[0], p[1], 0.0] for p in points]
        self.color, self.width, self.life, self.follow = color, width, life, follow
        self.core, self.layer, self.glow_color = core, layer, glow_color
        self.open = follow is not None or not self.pts

    def add(self, p) -> None:
        self.pts.append([p[0], p[1], 0.0])

    def stop(self) -> None:
        self.follow = None
        self.open = False

    def update(self, dt: float) -> bool:
        for p in self.pts:
            p[2] += dt
        while self.pts and self.pts[0][2] > self.life:
            self.pts.pop(0)
        if self.follow is not None:
            self.add(self.follow())
        return bool(self.pts) or self.open

    def _strip(self, scale: float):
        pts = self.pts
        n = len(pts)
        left, right = [], []
        for i, p in enumerate(pts):
            a = pts[max(0, i - 1)]
            b = pts[min(n - 1, i + 1)]
            dx, dy = b[0] - a[0], b[1] - a[1]
            d = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / d, dx / d
            age = clamp01(p[2] / self.life)
            w = self.width * scale * (1 - age) * (0.35 + 0.65 * (i + 1) / n) * 0.5
            left.append((p[0] + nx * w, p[1] + ny * w))
            right.append((p[0] - nx * w, p[1] - ny * w))
        return left + right[::-1]

    def render(self, surface: pygame.Surface) -> None:
        if len(self.pts) < 2:
            return
        age = clamp01(self.pts[-1][2] / self.life)
        k = 1 - age * 0.6
        col = self.glow_color or self.color
        pygame.draw.polygon(surface, scaled(col, 0.55 * k), self._strip(1.6))
        pygame.draw.polygon(surface, scaled(self.color, k), self._strip(1.0))
        if self.core:
            pygame.draw.polygon(surface, scaled(self.core, k), self._strip(0.45))


class Slash(Effect):
    """Coup d'arme : une traînée qui suit `path(t)` (t de 0 à 1) en `duration` secondes."""

    def __init__(self, path: Callable[[float], Vector2], duration: float = 0.18, color: Color = WHITE,
                 width: float = 18.0, life: float = 0.3, core: Color | None = WHITE,
                 glow_color: Color | None = None, delay: float = 0.0, layer: str = "front") -> None:
        self.path, self.duration, self.t = path, max(1e-3, duration), -delay
        self.trail = Trail((), color, width, life, core=core, glow_color=glow_color)
        self.trail.open = False
        self.layer = layer

    @classmethod
    def arc(cls, center, radius: float, a0: float, a1: float, ry: float | None = None, **kw) -> "Slash":
        c = Vector2(center)
        ry = radius if ry is None else ry

        def path(t: float) -> Vector2:
            a = math.radians(lerp(a0, a1, t))
            return Vector2(c.x + math.cos(a) * radius, c.y + math.sin(a) * ry)
        return cls(path, **kw)

    @classmethod
    def line(cls, p0, p1, bulge: float = 0.0, **kw) -> "Slash":
        a, b = Vector2(p0), Vector2(p1)
        d = b - a
        nrm = Vector2(-d.y, d.x).normalize() * bulge if d.length() else Vector2()

        def path(t: float) -> Vector2:
            return a.lerp(b, t) + nrm * math.sin(math.pi * t)
        return cls(path, **kw)

    def update(self, dt: float) -> bool:
        self.t += dt
        if self.t >= 0 and self.t < self.duration + dt:
            # sous-échantillonne pour une courbe lisse même à gros dt
            steps = 4
            prev = self.t - dt
            for i in range(1, steps + 1):
                tt = prev + dt * i / steps
                if 0 <= tt <= self.duration:
                    self.trail.add(self.path(tt / self.duration))
        return self.trail.update(dt) or self.t < self.duration

    def render(self, surface: pygame.Surface) -> None:
        self.trail.render(surface)


class AfterImage(Effect):
    """Image rémanente : silhouette colorée (ellipse de `rect`, ou masque d'`image`) qui s'estompe."""

    def __init__(self, rect: pygame.Rect, color: Color = ICE, life: float = 0.35, alpha: int = 170,
                 image: pygame.Surface | None = None, additive: bool = True, layer: str = "front",
                 drift: Sequence[float] = (0, 0)) -> None:
        self.rect = pygame.Rect(rect)
        self.life, self.alpha0, self.additive, self.layer = life, alpha, additive, layer
        self.drift = Vector2(drift)
        self.t = 0.0
        if image is not None:
            m = pygame.mask.from_surface(image)
            self.surf = m.to_surface(setcolor=color + (255,), unsetcolor=(0, 0, 0, 0))
            self.rect = image.get_rect(midbottom=self.rect.midbottom)
        else:
            w, h = max(2, self.rect.w), max(2, self.rect.h)
            self.surf = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.ellipse(self.surf, color + (255,), (w * 0.15, 0, w * 0.7, h * 0.55))
            pygame.draw.rect(self.surf, color + (255,), (w * 0.2, h * 0.3, w * 0.6, h * 0.7), border_radius=int(w * 0.2))

    @classmethod
    def of(cls, actor, **kw) -> "AfterImage":
        return cls(actor.rect, image=getattr(actor, "image", None), **kw)

    def update(self, dt: float) -> bool:
        self.t += dt
        return self.t < self.life

    def render(self, surface: pygame.Surface) -> None:
        k = 1 - self.t / self.life
        self.surf.set_alpha(int(self.alpha0 * k))
        pos = self.rect.topleft + self.drift * self.t
        surface.blit(self.surf, pos)


# ----------------------------------------------------------------- éclairs


def lightning_points(p0, p1, jag: float = 0.18, depth: int = 6) -> list[Vector2]:
    """Polyligne d'éclair par déplacement du point milieu (différente à chaque appel)."""
    pts = [Vector2(p0), Vector2(p1)]
    off = (pts[1] - pts[0]).length() * jag
    for _ in range(depth):
        nxt = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            m = (a + b) / 2
            d = b - a
            if d.length():
                nrm = Vector2(-d.y, d.x).normalize()
                m = m + nrm * random.uniform(-off, off)
            nxt += [m, b]
        pts = nxt
        off *= 0.52
    return pts


class Lightning(Effect):
    """Éclair ramifié procédural, qui scintille puis s'éteint."""

    def __init__(self, start, end, color: Color = THUNDER, width: float = 5.0, life: float = 0.4,
                 branches: int = 3, jag: float = 0.18, delay: float = 0.0, layer: str = "front") -> None:
        self.color, self.width, self.life, self.t = color, width, life, -delay
        self.layer = layer
        self.end = Vector2(end)
        self.bolts: list[tuple[list[Vector2], float]] = [(lightning_points(start, end, jag), 1.0)]
        main = self.bolts[0][0]
        for _ in range(branches):
            i = random.randint(len(main) // 6, len(main) * 3 // 4)
            d = (Vector2(end) - Vector2(start)).rotate(random.uniform(-50, 50)) * random.uniform(0.2, 0.4)
            self.bolts.append((lightning_points(main[i], main[i] + d, jag, 5), 0.5))

    def update(self, dt: float) -> bool:
        self.t += dt
        return self.t < self.life

    def render(self, surface: pygame.Surface) -> None:
        if self.t < 0:
            return
        k = clamp01(1 - self.t / self.life)
        flick = 1.0 if int(self.t * 40) % 3 else 0.55
        a = k * flick
        for pts, w in self.bolts:
            pl = [(p.x, p.y) for p in pts]
            pygame.draw.lines(surface, scaled(self.color, a * 0.6), False, pl, max(1, int(self.width * w * 2.2)))
            pygame.draw.lines(surface, scaled(WHITE, a), False, pl, max(1, int(self.width * w * 0.8)))
        blit_glow(surface, self.end, 70 * k + 20, self.color, a)


# ----------------------------------------------------------------- formes magiques


def _ell(c: Vector2, rx: float, ry: float, a_deg: float) -> tuple[float, float]:
    a = math.radians(a_deg)
    return c.x + math.cos(a) * rx, c.y + math.sin(a) * ry


class MagicCircle(Effect):
    """Cercle magique au sol (ellipse aplatie) : anneaux, étoile, runes qui tournent."""

    layer = "back"

    def __init__(self, center, radius: float = 110.0, color: Color = FIRE, life: float = 1.2,
                 squash: float = 0.32, points: int = 6, spin: float = 50.0, delay: float = 0.0,
                 appear: float = 0.25, fade: float = 0.3) -> None:
        self.c, self.r, self.color, self.life = Vector2(center), radius, color, life
        self.squash, self.n, self.spin, self.t = squash, points, spin, -delay
        self.appear, self.fade = appear, fade

    def update(self, dt: float) -> bool:
        self.t += dt
        return self.t < self.life

    def render(self, surface: pygame.Surface) -> None:
        if self.t < 0:
            return
        k = ease("out_back", self.t / self.appear)
        a = clamp01(self.t / 0.12) * clamp01((self.life - self.t) / self.fade)
        if a <= 0:
            return
        r, sq = self.r * k, self.squash
        col = scaled(self.color, a)
        bright = scaled(mix(self.color, WHITE, 0.6), a)
        rot = self.t * self.spin
        c = self.c
        blit_glow(surface, (c.x, c.y), r * 1.15, self.color, a * 0.45)
        for rr, w, cc in ((1.0, 3, bright), (0.82, 2, col), (0.45, 2, col)):
            pygame.draw.ellipse(surface, cc, (c.x - r * rr, c.y - r * rr * sq, 2 * r * rr, 2 * r * rr * sq), w)
        n = self.n
        verts = [_ell(c, r * 0.82, r * 0.82 * sq, rot + i * 360 / n) for i in range(n)]
        step = 2 if n >= 5 else 1
        for i in range(n):
            pygame.draw.line(surface, col, verts[i], verts[(i + step) % n], 2)
        for i in range(16):  # runes : petits traits sur l'anneau extérieur
            ang = -rot * 0.7 + i * 22.5
            p0 = _ell(c, r * 0.9, r * 0.9 * sq, ang)
            p1 = _ell(c, r * 0.98, r * 0.98 * sq, ang + (3 if i % 2 else 0))
            pygame.draw.line(surface, bright if i % 4 == 0 else col, p0, p1, 2)


class Shockwave(Effect):
    """Onde de choc : anneau qui grossit (`squash` < 1 pour une onde au sol)."""

    def __init__(self, center, color: Color = WHITE, r0: float = 10.0, r1: float = 160.0,
                 life: float = 0.4, width: int = 8, squash: float = 1.0, delay: float = 0.0,
                 easing="out_cubic", layer: str = "front", glow_on: bool = True) -> None:
        self.c, self.color, self.r0, self.r1 = Vector2(center), color, r0, r1
        self.life, self.width, self.squash, self.t = life, width, squash, -delay
        self.easing, self.layer, self.glow_on = easing, layer, glow_on

    def update(self, dt: float) -> bool:
        self.t += dt
        return self.t < self.life

    def render(self, surface: pygame.Surface) -> None:
        if self.t < 0:
            return
        p = clamp01(self.t / self.life)
        r = lerp(self.r0, self.r1, ease(self.easing, p))
        a = 1 - p
        w = max(1, int(self.width * a))
        c = self.c
        rect = pygame.Rect(c.x - r, c.y - r * self.squash, 2 * r, 2 * r * self.squash)
        if rect.h < 2:
            return
        # dessin additif (lumineux, jamais de contour sombre) : sur un calque temporaire noir, puis BLEND_ADD
        pad = w * 2 + 4
        area = rect.inflate(pad * 2, pad * 2).clip(surface.get_rect())
        if area.w < 2 or area.h < 2:
            return
        tmp = scratch(surface.get_size(), "shockwave")
        tmp.fill((0, 0, 0, 255), area)
        local = rect
        if self.glow_on:
            pygame.draw.ellipse(tmp, scaled(self.color, a * 0.5), local.inflate(w, w * self.squash), w * 2)
        pygame.draw.ellipse(tmp, scaled(mix(self.color, WHITE, 0.5), a), local, w)
        surface.blit(tmp, area.topleft, area, special_flags=pygame.BLEND_ADD)


class Beam(Effect):
    """Rayon lumineux de `start` à `end` (modifiables), qui gonfle puis se resserre."""

    def __init__(self, start, end, color: Color = WHITE, width: float = 40.0, life: float = 0.6,
                 delay: float = 0.0, attack: float = 0.15, layer: str = "front") -> None:
        self.start, self.end = Vector2(start), Vector2(end)
        self.color, self.width, self.life, self.t = color, width, life, -delay
        self.attack, self.layer = attack, layer

    def update(self, dt: float) -> bool:
        self.t += dt
        return self.t < self.life

    def render(self, surface: pygame.Surface) -> None:
        if self.t < 0:
            return
        k = clamp01(self.t / self.attack) * clamp01((self.life - self.t) / (self.life * 0.45))
        if k <= 0:
            return
        w = self.width * k * (1 + 0.08 * math.sin(self.t * 60))
        s, e = (self.start.x, self.start.y), (self.end.x, self.end.y)
        pygame.draw.line(surface, scaled(self.color, 0.35 * k), s, e, int(w * 2.2))
        pygame.draw.line(surface, scaled(self.color, 0.8 * k), s, e, int(w * 1.3))
        pygame.draw.line(surface, scaled(WHITE, k), s, e, max(1, int(w * 0.6)))
        blit_glow(surface, s, w * 1.8, self.color, k)
        blit_glow(surface, e, w * 2.2, self.color, k)


class EnergyOrb(Effect):
    """Boule d'énergie pulsante. `pos`, `radius` modifiables ; `kill()` ou `life` pour l'éteindre."""

    def __init__(self, pos, radius: float = 40.0, color: Color = WHITE, life: float | None = None,
                 follow: Callable[[], Vector2] | None = None, layer: str = "front",
                 grow: float = 0.0) -> None:
        self.pos, self.radius, self.color, self.life = Vector2(pos), radius, color, life
        self.follow, self.layer, self.t, self.grow = follow, layer, 0.0, grow

    def update(self, dt: float) -> bool:
        self.t += dt
        self.radius += self.grow * dt
        if self.follow:
            self.pos = Vector2(self.follow())
        return not self.dead and (self.life is None or self.t < self.life)

    def render(self, surface: pygame.Surface) -> None:
        r = self.radius * (1 + 0.07 * math.sin(self.t * 22))
        blit_glow(surface, self.pos, r * 2.2, self.color, 0.55)
        blit_glow(surface, self.pos, r * 1.3, mix(self.color, WHITE, 0.4), 0.9)
        blit_glow(surface, self.pos, r * 0.6, WHITE, 1.0)


class Projectile(Effect):
    """Projectile (`orb`, `arrow`, `shuriken`, `bolt`) avec traînée, arc et spirale.

    `on_arrive()` est appelé à l'arrivée ; `arc` = hauteur de la courbe (px) ;
    `wobble=(amplitude, tours)` ajoute une spirale qui se resserre.
    """

    def __init__(self, start, end, duration: float = 0.4, kind: str = "orb", color: Color = FIRE,
                 size: float = 14.0, arc: float = 0.0, wobble: tuple[float, float] = (0.0, 0.0),
                 easing="in_quad", on_arrive: Callable[[], None] | None = None, trail: bool = True,
                 spin: float = 20.0, delay: float = 0.0, layer: str = "front") -> None:
        self.p0, self.p1 = Vector2(start), Vector2(end)
        self.duration, self.kind, self.color, self.size = max(1e-3, duration), kind, color, size
        self.arc, self.wobble, self.easing, self.on_arrive = arc, wobble, easing, on_arrive
        self.spin, self.t, self.layer = spin, -delay, layer
        self.pos = Vector2(start)
        self.heading = (self.p1 - self.p0).normalize() if self.p1 != self.p0 else Vector2(1, 0)
        self.trail = Trail((), color, size * 1.1, 0.28, core=WHITE) if trail else None
        if self.trail:
            self.trail.open = True
        self.arrived = False

    def _at(self, p: float) -> Vector2:
        pos = self.p0 + (self.p1 - self.p0) * ease(self.easing, p)
        nrm = Vector2(-self.heading.y, self.heading.x)
        off = -self.arc * math.sin(math.pi * p) * (1 if nrm.y < 0 else -1) if self.arc else 0.0
        amp, turns = self.wobble
        if amp:
            off += amp * (1 - p) * math.sin(p * turns * math.tau)
        return pos + nrm * off

    def update(self, dt: float) -> bool:
        self.t += dt
        if self.arrived:
            return self.trail.update(dt) if self.trail else False
        if self.t < 0:
            return True
        p = clamp01(self.t / self.duration)
        old = self.pos
        self.pos = self._at(p)
        if (self.pos - old).length_squared() > 0.5:
            self.heading = (self.pos - old).normalize()
        if self.trail:
            self.trail.add(self.pos)
            self.trail.update(dt)
        if p >= 1:
            self.arrived = True
            if self.trail:
                self.trail.open = False
            if self.on_arrive:
                self.on_arrive()
            return bool(self.trail and self.trail.pts)
        return True

    def render(self, surface: pygame.Surface) -> None:
        if self.t < 0:
            return
        if self.trail:
            self.trail.render(surface)
        if self.arrived:
            return
        x, y = self.pos
        s, h = self.size, self.heading
        if self.kind == "orb":
            blit_glow(surface, self.pos, s * 2.4, self.color, 0.8)
            blit_glow(surface, self.pos, s * 1.0, WHITE, 1.0)
        elif self.kind == "arrow":
            tail = self.pos - h * 46
            pygame.draw.line(surface, PALE, tail, self.pos, 3)
            n = Vector2(-h.y, h.x)
            pygame.draw.polygon(surface, WHITE, [self.pos + h * 10, self.pos - h * 4 + n * 6, self.pos - h * 4 - n * 6])
            pygame.draw.line(surface, self.color, tail, tail - h * 8 + n * 6, 2)
            pygame.draw.line(surface, self.color, tail, tail - h * 8 - n * 6, 2)
            blit_glow(surface, self.pos, s * 1.6, self.color, 0.5)
        elif self.kind == "shuriken":
            a = self.t * self.spin
            pts = []
            for i in range(8):
                r = s * (1.4 if i % 2 == 0 else 0.5)
                pts.append((x + math.cos(a + i * math.pi / 4) * r, y + math.sin(a + i * math.pi / 4) * r))
            pygame.draw.polygon(surface, PALE, pts)
            pygame.draw.polygon(surface, STEEL, pts, 2)
            pygame.draw.circle(surface, NAVY, (int(x), int(y)), max(2, int(s * 0.25)))
        else:  # bolt
            pygame.draw.line(surface, self.color, self.pos - h * s * 2, self.pos, max(2, int(s * 0.4)))
            blit_glow(surface, self.pos, s * 1.5, self.color, 0.8)


class GlassShards(Effect):
    """Éclats (verre, glace, métal) projetés depuis `center`, avec gravité et rotation."""

    def __init__(self, center, count: int = 24, colors: Sequence[Color] = (PALE, ICE, WHITE),
                 size: tuple[float, float] = (6, 18), speed: tuple[float, float] = (150, 520),
                 life: float = 1.0, gravity: float = 900.0, angle: float = -90, spread: float = 360,
                 radius: float = 0.0, delay: float = 0.0, layer: str = "front") -> None:
        self.life, self.g, self.t, self.layer = life, gravity, -delay, layer
        self.sh = []
        for _ in range(count):
            a = math.radians(angle + random.uniform(-spread / 2, spread / 2))
            sp = random.uniform(*speed)
            ox, oy = (random.uniform(-radius, radius), random.uniform(-radius, radius)) if radius else (0, 0)
            self.sh.append([center[0] + ox, center[1] + oy, math.cos(a) * sp, math.sin(a) * sp,
                            random.uniform(*size), random.choice(colors), random.uniform(0, math.tau),
                            random.uniform(-9, 9), random.uniform(0.7, 1.0) * life, random.random() < 0.5])

    def update(self, dt: float) -> bool:
        self.t += dt
        if self.t < 0:
            return True
        for s in self.sh:
            s[3] += self.g * dt
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            s[6] += s[7] * dt
        return self.t < self.life

    def render(self, surface: pygame.Surface) -> None:
        if self.t < 0:
            return
        for x, y, _, _, sz, col, rot, _, life, tri in self.sh:
            k = clamp01(1 - self.t / life)
            if k <= 0:
                continue
            c = scaled(col, 0.3 + 0.7 * k)
            r = sz * (0.5 + 0.5 * k)
            pts = [(x + math.cos(rot + i * (2.4 if tri else 1.57)) * r * (1.0 if i != 1 else 0.45),
                    y + math.sin(rot + i * (2.4 if tri else 1.57)) * r * (1.0 if i != 1 else 0.45))
                   for i in range(3 if tri else 4)]
            pygame.draw.polygon(surface, c, pts)


class LightColumn(Effect):
    """Colonne de lumière verticale (niveau, soin, jugement) : jaillit puis s'amincit."""

    _tex: dict[Color, pygame.Surface] = {}

    def __init__(self, x: float, y_bottom: float, height: float = 420.0, width: float = 90.0,
                 color: Color = GOLD, life: float = 0.9, delay: float = 0.0, layer: str = "front") -> None:
        self.x, self.yb, self.h, self.w, self.color = x, y_bottom, height, width, color
        self.life, self.t, self.layer = life, -delay, layer
        if color not in self._tex:
            xs = np.abs(np.linspace(-1, 1, 64))[:, None]
            ys = np.linspace(1, 0.0, 128)[None, :] ** 0.6
            v = np.clip(1 - xs, 0, 1) ** 1.6 * ys
            core = np.clip(1 - xs * 3, 0, 1) * ys
            rgb = v[..., None] * np.array(color) * 0.9 + core[..., None] * 150
            self._tex[color] = pygame.surfarray.make_surface(np.clip(rgb, 0, 255).astype(np.uint8))

    def update(self, dt: float) -> bool:
        self.t += dt
        return self.t < self.life

    def render(self, surface: pygame.Surface) -> None:
        if self.t < 0:
            return
        p = self.t / self.life
        grow = ease("out_cubic", p * 4)
        w = max(2, int(self.w * (1 - ease("in_quad", p)) * (0.6 + 0.4 * grow)))
        h = max(2, int(self.h * grow))
        img = pygame.transform.scale(self._tex[self.color], (w, h))
        surface.blit(img, (self.x - w // 2, self.yb - h), special_flags=pygame.BLEND_ADD)


class HexShield(Effect):
    """Bulle hexagonale qui scintille autour d'un acteur, jusqu'à `kill()` (garde `tag`)."""

    def __init__(self, actor, color: Color = ICE, tag: str | None = None) -> None:
        self.actor, self.color, self.tag, self.t = actor, color, tag, 0.0
        r = int(max(actor.rect.w, actor.rect.h) * 0.62) + 8
        self.r = r
        s = pygame.Surface((2 * r + 6, 2 * r + 6), pygame.SRCALPHA)
        c = Vector2(r + 3, r + 3)
        hexp = lambda ctr, rad: [(ctr.x + math.cos(math.radians(60 * i + 30)) * rad,
                                  ctr.y + math.sin(math.radians(60 * i + 30)) * rad) for i in range(6)]
        pygame.draw.polygon(s, color + (45,), hexp(c, r))
        sm = r / 2.6
        for i in range(-1, 2):
            for j in range(-1, 2):
                ctr = Vector2(c.x + (i * 1.74 + j * 0.87) * sm, c.y + j * 1.5 * sm)
                if (ctr - c).length() < r - sm * 0.6:
                    pygame.draw.polygon(s, color + (110,), hexp(ctr, sm * 0.98), 1)
        pygame.draw.polygon(s, PALE + (230,), hexp(c, r), 3)
        self.base = s
        self.verts = hexp(c, r)

    def update(self, dt: float) -> bool:
        self.t += dt
        return not self.dead

    def render(self, surface: pygame.Surface) -> None:
        k = ease("out_back", self.t / 0.35)
        s = self.base
        if k < 0.99:
            sz = max(2, int(s.get_width() * k))
            s = pygame.transform.smoothscale(s, (sz, sz))
        s.set_alpha(int(190 + 50 * math.sin(self.t * 6)))
        cx, cy = self.actor.rect.center
        cy -= self.actor.rect.h * 0.05
        surface.blit(s, (cx - s.get_width() / 2, cy - s.get_height() / 2))
        if self.t > 0.35:
            sw = (self.t * 1.3) % 1.0  # reflet qui balaie la bulle
            vx, vy = self.verts[int(self.t * 3) % 6]
            off = (self.r + 3)
            blit_glow(surface, (cx + vx - off, cy + vy - off), 10 + 5 * math.sin(self.t * 12), WHITE, 0.4 + 0.5 * sw)


# ----------------------------------------------------------------- transitions


class BattleTransition(Effect):
    """Entrée en combat : `kind` = "spiral" ou "shards". `reverse=True` pour révéler la scène.

    `progress` va de 0 à 1 (inversé si reverse) ; `hold` secondes de plein noir à la fin.
    """

    layer = "overlay"

    def __init__(self, kind: str = "spiral", duration: float = 0.9, reverse: bool = False,
                 color: Color = BLACK, hold: float = 0.0, seed: int = 1) -> None:
        self.kind, self.duration, self.reverse, self.color, self.hold = kind, max(1e-3, duration), reverse, color, hold
        self.t = 0.0
        rng = random.Random(seed)
        self.cells = [(i, j, rng.random() * 0.55, rng.uniform(-1.2, 1.2)) for i in range(17) for j in range(10)]

    @property
    def progress(self) -> float:
        p = clamp01(self.t / self.duration)
        return 1 - p if self.reverse else p

    def update(self, dt: float) -> bool:
        self.t += dt
        return self.t < self.duration + self.hold

    def render(self, surface: pygame.Surface) -> None:
        p = self.progress
        if p <= 0:
            return
        w, h = surface.get_size()
        if p >= 0.999:
            surface.fill(self.color)
            return
        if self.kind == "spiral":
            n = 14
            cx, cy = w / 2, h / 2
            R = math.hypot(w, h)
            e = ease("in_out_quad", p)
            width = math.tau / n * 1.25 * e
            twist = e * 2.4
            reach = R * clamp01(e * 1.4)
            for i in range(n):
                a = i * math.tau / n + twist
                pts = [(cx, cy)]
                for k in range(5):
                    aa = a + width * (k / 4 - 0.5)
                    pts.append((cx + math.cos(aa) * reach, cy + math.sin(aa) * reach))
                pygame.draw.polygon(surface, self.color, pts)
            if e > 0.55:
                pygame.draw.circle(surface, self.color, (int(cx), int(cy)), int(reach * (e - 0.55) / 0.45 * 0.6))
        else:
            cw, ch = w / 17 + 1, h / 10 + 1
            for i, j, d, rot in self.cells:
                k = clamp01((p - d) / 0.45)
                if k <= 0:
                    continue
                cx, cy = (i + 0.5) * w / 17, (j + 0.5) * h / 10
                s = ease("out_quad", k) * 1.45
                a = (1 - k) * rot
                pts = [(cx + math.cos(a + q) * cw * 0.72 * s, cy + math.sin(a + q) * ch * 0.72 * s)
                       for q in (0.78, 2.36, 3.93, 5.5)]
                pygame.draw.polygon(surface, self.color, pts)


# ----------------------------------------------------------------- gestionnaire


class FxManager:
    """Tient les effets actifs et les dessine par calque. Aussi une fabrique de raccourcis."""

    LAYERS = ("back", "front", "overlay")

    def __init__(self) -> None:
        self.effects: list[Effect] = []
        self.shake_offset = Vector2()
        self.hide_ui = False

    # --- cycle de vie
    def add(self, effect: Effect, layer: str | None = None, tag: str | None = None) -> Effect:
        if layer:
            effect.layer = layer
        if tag:
            effect.tag = tag
        self.effects.append(effect)
        return effect

    def update(self, dt: float) -> None:
        cur, self.effects = self.effects, []  # les ajouts pendant la mise à jour vont dans la nouvelle liste
        alive = [e for e in cur if not e.dead and e.update(dt)]
        self.effects = alive + self.effects
        off = Vector2()
        for e in self.effects:
            if isinstance(e, ScreenShake):
                off += e.offset
        self.shake_offset = off

    def draw(self, surface: pygame.Surface, layer: str) -> None:
        for e in self.effects:
            if not getattr(e, "top", False):
                e.draw(surface, layer)
        for e in self.effects:  # effets « au-dessus de tout » du calque (bandes de cinéma)
            if getattr(e, "top", False):
                e.draw(surface, layer)

    def clear(self) -> None:
        self.effects.clear()
        self.shake_offset = Vector2()
        self.hide_ui = False

    def kill(self, tag: str) -> None:
        for e in self.effects:
            if e.tag == tag:
                e.dead = True

    @property
    def busy(self) -> bool:
        return any(not e.dead for e in self.effects)

    # --- raccourcis
    def burst(self, preset: str, pos, count: int = 20, **kw) -> ParticleEmitter:
        return self.add(ParticleEmitter(pos, preset, count=count, **kw))

    def emitter(self, preset: str, pos, rate: float, duration: float, **kw) -> ParticleEmitter:
        return self.add(ParticleEmitter(pos, preset, rate=rate, duration=duration, **kw))

    def text(self, text, pos, color: Color = WHITE, **kw) -> FloatingText:
        return self.add(FloatingText(text, pos, color, **kw))

    def shake(self, amplitude: float = 8.0, duration: float = 0.3) -> ScreenShake:
        return self.add(ScreenShake(amplitude, duration))

    def flash(self, color: Color = WHITE, duration: float = 0.25, **kw) -> Flash:
        return self.add(Flash(color, duration, **kw))

    def tint(self, color: Color = BLACK, alpha: float = 0.6, **kw) -> ScreenTint:
        return self.add(ScreenTint(color, alpha, **kw))

    def ring(self, center, color: Color = WHITE, **kw) -> Shockwave:
        return self.add(Shockwave(center, color, **kw))
