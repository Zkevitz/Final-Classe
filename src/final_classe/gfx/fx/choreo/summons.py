"""Invocations : Ifrit, Shiva, Ramuh, Bahamut (4 à 7 s, interface cachée, `skippable`).

Mise en scène en actes (ambiance, apparition, montée en tension, frappe, déflagration, retombée) ;
briques de spectacle dans `fx/summon_fx.py`.
Briques locales (partagées avec `monsters.py`) : `Starfield`, `EdgeGlow`, `Apparition`,
`Snow`, `StormClouds`, `Crackle`, `LavaCracks`, `IcePillar`, `soft`.
Les voiles sombres vont sur le calque "back" (le décor s'assombrit, pas les sprites ni les chiffres) ;
seuls les écrans noirs (Bahamut, Supernova) et les flashs passent par "overlay".
"""
from __future__ import annotations

import math
import random

import numpy as np
import pygame
from pygame import Vector2

from . import Anim, Call, Par, Seq, scripted
from ..summon_fx import (Aurora, ImpactWarp, Inflow, Letterbox, Rain, Rays, Stage, anchor_head, anchor_top)
from .. import (Effect, EnergyOrb, Flash, GlassShards, LightColumn, Lightning, MagicCircle,
                ParticleEmitter, Projectile, ScreenShake, scratch, ScreenTint, Shockwave, blit_glow, clamp01,
                ease, lightning_points, mix, polar, scaled, veil,
                BLACK, BLUE, FIRE, GOLD, HOLY, ICE, NAVY, PALE, RED, THUNDER, WHITE)

# ----------------------------------------------------------------- utilitaires


def _screen(c) -> tuple[int, int]:
    return tuple(c.ctx.extra.get("screen", (1280, 720)))


def soft(surface: pygame.Surface, pos, r: float, color, a: float = 1.0) -> None:
    """Lueur dont le rayon est quantifié (évite de créer une texture par image)."""
    if a <= 0.03 or r < 2:
        return
    q = 6 if r < 80 else 16
    rr = max(q, int(round(min(r, 460) / q)) * q)
    blit_glow(surface, pos, rr, color, a)


def _image(c, ident: str, color) -> pygame.Surface:
    """Image d'invocation (placeholder du moteur si absente, disque lumineux si pas d'assets)."""
    img = None
    try:
        if c.ctx.assets is not None:
            img = c.ctx.assets.image(ident)
    except Exception:  # noqa: BLE001
        img = None
    if img is None:
        img = pygame.Surface((256, 256), pygame.SRCALPHA)
        pygame.draw.circle(img, color, (128, 128), 110)
        pygame.draw.circle(img, WHITE, (128, 128), 110, 4)
    try:
        img = img.convert_alpha()
    except pygame.error:
        pass
    return img


_STAR_COLORS = [WHITE, WHITE, PALE, ICE, GOLD, HOLY]

# ----------------------------------------------------------------- briques


class Starfield(Effect):
    """Écran noir (`bg`) + champ d'étoiles ("drift" qui tombe, "stream" qui défile), nébuleuses."""

    layer = "overlay"

    def __init__(self, bg: float = 0.0, mode: str = "drift", count: int = 200, speed: float = 1.0,
                 nebula=None, seed: int = 7) -> None:
        rng = random.Random(seed)
        self.stars = [[rng.random(), rng.random(), rng.uniform(0.15, 1.0), rng.uniform(0, 6.28),
                       rng.choice(_STAR_COLORS)] for _ in range(count)]
        self.bg, self.mode, self.speed, self.a = bg, mode, speed, 1.0
        self.nebula = nebula or []  # (x%, y%, rayon, couleur, force)
        self.pos = self.t = 0.0

    def update(self, dt: float) -> bool:
        self.t += dt
        self.pos += self.speed * dt
        return not self.dead

    def render(self, surface: pygame.Surface) -> None:
        w, h = surface.get_size()
        veil(surface, BLACK, self.bg)
        vis = self.bg * self.a
        if vis <= 0.02:
            return
        for nx, ny, r, col, st in self.nebula:
            soft(surface, (nx * w, ny * h), r, col, st * vis)
        stream = self.mode == "stream"
        for sx, sy, z, ph, col in self.stars:
            if stream:
                x, y = (sx * w - self.pos * z * 420) % w, sy * h
            else:
                x, y = sx * w, (sy * h + self.pos * z * 45) % h
            k = vis * (0.4 + 0.6 * z) * (0.7 + 0.3 * math.sin(self.t * 3 + ph))
            col0, col = col, scaled(col, k)
            if stream:
                ln = max(1.0, z * self.speed * 22)
                pygame.draw.line(surface, col, (x, y), (x + ln, y), max(1, int(z * 2.4)))
            elif z > 0.82:
                pygame.draw.line(surface, col, (x - 4, y), (x + 4, y), 1)
                pygame.draw.line(surface, col, (x, y - 4), (x, y + 4), 1)
                blit_glow(surface, (x, y), 9, col0, 0.7 * clamp01(k))
            else:
                surface.fill(col, (int(x), int(y), 2 if z > 0.5 else 1, 2 if z > 0.5 else 1))


_EDGE: dict = {}


def _edge_tex(size, color) -> pygame.Surface:
    key = (size, tuple(color))
    tex = _EDGE.get(key)
    if tex is None:
        sw, sh = 160, 90
        ys, xs = np.mgrid[0:sh, 0:sw]
        nx, ny = xs / (sw - 1) * 2 - 1, ys / (sh - 1) * 2 - 1
        d = np.sqrt(nx ** 2 * 0.7 + ny ** 2)
        edge = np.clip((d - 0.62) / 0.5, 0, 1) ** 1.7
        g = pygame.Surface((12, 7))
        gp = pygame.surfarray.pixels3d(g)
        gp[:] = (np.random.default_rng(3).random((12, 7, 1)) * 255).astype(np.uint8)
        del gp
        g = pygame.transform.smoothscale(g, (sw, sh))
        noise = pygame.surfarray.array3d(g)[..., 0].T / 255.0
        al = np.clip(edge * (0.5 + 0.9 * noise), 0, 1) * 225
        small = pygame.Surface((sw, sh), pygame.SRCALPHA)
        px = pygame.surfarray.pixels3d(small)
        px[:] = color
        del px
        pa = pygame.surfarray.pixels_alpha(small)
        pa[:] = al.T.astype(np.uint8)
        del pa
        tex = pygame.transform.smoothscale(small, size)
        _EDGE[key] = tex
    return tex


class EdgeGlow(Effect):
    """Givre / chaleur / poison qui envahit les bords de l'écran (`k` de 0 à 1, `pulse` = respiration)."""

    layer = "overlay"

    def __init__(self, color=ICE, pulse: float = 0.0) -> None:
        self.color, self.pulse, self.k, self.t = color, pulse, 0.0, 0.0

    def update(self, dt: float) -> bool:
        self.t += dt
        return not self.dead

    def render(self, surface: pygame.Surface) -> None:
        k = self.k * (1 + self.pulse * math.sin(self.t * 4))
        if k <= 0.02:
            return
        tex = _edge_tex(surface.get_size(), self.color)
        tex.set_alpha(int(255 * clamp01(k)))
        surface.blit(tex, (0, 0))


class Apparition(Effect):
    """Image de l'invocation (ancrée en bas-milieu) : `pos`, `k` (échelle), `a` (opacité), `jit`, aura colorée."""

    def __init__(self, image: pygame.Surface, pos, height: float, color, layer: str = "back") -> None:
        self.src, self.pos, self.h, self.color, self.layer = image, Vector2(pos), height, color, layer
        self.a, self.k, self.aura, self.jit, self.bob, self.t = 0.0, 1.0, 1.0, 0.0, 6.0, 0.0
        self.bright, self.bright_color, self.drift = 0.0, WHITE, 0.0  # silhouette lumineuse additive, dérive d'échelle/s
        self._cache: tuple | None = None
        self._prem: pygame.Surface | None = None  # image prémultipliée par l'alpha (pour la lueur additive)
        self._pcache: tuple | None = None
        self._pbase: pygame.Surface | None = None

    def mouth(self, f: float = 0.3) -> Vector2:
        """Point situé à la fraction `f` de la hauteur en partant du haut."""
        return Vector2(self.pos.x, self.pos.y - self.h * self.k * (1 - f))

    def point(self, fx: float, fy: float, pos=None) -> Vector2:
        """Point de l'image (fractions de largeur/hauteur depuis le coin haut-gauche), à l'échelle actuelle."""
        h = self.h * self.k
        w = h * self.src.get_width() / self.src.get_height()
        p = Vector2(pos) if pos is not None else self.pos
        return Vector2(p.x + (fx - 0.5) * w, p.y - h * (1 - fy))

    def update(self, dt: float) -> bool:
        self.t += dt
        self.k += self.drift * dt
        return not self.dead

    def _premul(self) -> pygame.Surface:
        if self._prem is None:
            rgb = pygame.surfarray.array3d(self.src).astype(np.float32)
            try:
                al = pygame.surfarray.array_alpha(self.src).astype(np.float32) / 255.0
            except (pygame.error, ValueError):
                al = np.ones(rgb.shape[:2], np.float32)
            self._prem = pygame.surfarray.make_surface((rgb * al[..., None]).astype(np.uint8))
        return self._prem

    def render(self, surface: pygame.Surface) -> None:
        if self.a <= 0.01:
            return
        h = max(8, int(self.h * self.k))
        w = max(8, int(self.src.get_width() * h / self.src.get_height()))
        if self._cache is None or self._cache[0] != (w, h):
            self._cache = ((w, h), pygame.transform.smoothscale(self.src, (w, h)))
        img = self._cache[1]
        x = self.pos.x + random.uniform(-self.jit, self.jit)
        y = self.pos.y + math.sin(self.t * 2.1) * self.bob + random.uniform(-self.jit, self.jit)
        soft(surface, (x, y - h * 0.55), h * 0.85 * self.aura, self.color, 0.5 * self.a)
        img.set_alpha(int(255 * clamp01(self.a)))
        surface.blit(img, (x - w / 2, y - h))
        if self.bright > 0.02:
            bq = int(clamp01(self.bright) * clamp01(self.a) * 24 + 0.5)  # recopie seulement si la lueur a changé
            if bq > 0:
                key = (w, h, bq)
                if self._pcache is None or self._pcache[0] != key:
                    if self._pcache is None or self._pcache[0][:2] != (w, h):
                        self._pbase = pygame.transform.smoothscale(self._premul(), (w, h))
                    g = self._pbase.copy()
                    g.fill(scaled(self.bright_color, bq / 24), special_flags=pygame.BLEND_MULT)
                    self._pcache = (key, g)
                surface.blit(self._pcache[1], (x - w / 2, y - h), special_flags=pygame.BLEND_ADD)


class Snow(Effect):
    """Flocons qui tombent sur tout l'écran (`k` = visibilité)."""

    layer = "overlay"

    def __init__(self, count: int = 130, seed: int = 4) -> None:
        rng = random.Random(seed)
        self.f = [[rng.random(), rng.random(), rng.uniform(40, 130), rng.uniform(0, 6.28),
                   rng.uniform(1.0, 4.2)] for _ in range(count)]
        self.k = self.t = 0.0

    def update(self, dt: float) -> bool:
        self.t += dt
        for f in self.f:
            f[1] = (f[1] + f[2] * dt / 720.0) % 1.0
        return not self.dead

    def render(self, surface: pygame.Surface) -> None:
        if self.k <= 0.02:
            return
        w, h = surface.get_size()
        for x, y, _, ph, s in self.f:
            px, py = x * w + math.sin(self.t * 1.3 + ph) * 26, y * h
            col = scaled(WHITE if s > 2.4 else ICE, self.k * (0.5 + 0.1 * s))
            if s > 3.0:
                for i in range(3):
                    a = i * math.pi / 3 + self.t * 0.4
                    dx, dy = math.cos(a) * s * 2, math.sin(a) * s * 2
                    pygame.draw.line(surface, col, (px - dx, py - dy), (px + dx, py + dy), 1)
            else:
                pygame.draw.circle(surface, col, (int(px), int(py)), max(1, int(s * 0.7)))


_PUFF: dict = {}


def _puff(size: int) -> pygame.Surface:
    s = _PUFF.get(size)
    if s is None:
        ax = (np.arange(size) - size / 2 + 0.5) / (size / 2)
        d = np.sqrt(ax[:, None] ** 2 + ax[None, :] ** 2)
        al = np.clip(1 - d, 0, 1) ** 1.4 * 235
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        px = pygame.surfarray.pixels3d(s)
        px[:] = mix(NAVY, BLACK, 0.72)
        del px
        pa = pygame.surfarray.pixels_alpha(s)
        pa[:] = al.astype(np.uint8)
        del pa
        _PUFF[size] = s
    return s


class StormClouds(Effect):
    """Nuages d'orage sombres en haut de l'écran, avec éclairs de chaleur dans la masse."""

    layer = "back"

    def __init__(self, seed: int = 11) -> None:
        rng = random.Random(seed)
        self.puffs = [[rng.uniform(-0.1, 1.1), rng.uniform(-0.02, 0.3), rng.choice((200, 290, 380)),
                       rng.uniform(4, 14) * rng.choice((-1, 1))] for _ in range(26)]
        self.k, self.t, self.lit, self.next_flash, self.fpos = 0.0, 0.0, 0.0, 0.5, (0.5, 0.15)

    def flash(self) -> None:
        self.lit = 1.0
        self.fpos = (random.uniform(0.15, 0.85), random.uniform(0.05, 0.22))

    def update(self, dt: float) -> bool:
        self.t += dt
        self.lit = max(0.0, self.lit - dt * 4.5)
        self.next_flash -= dt
        if self.next_flash <= 0 and self.k > 0.4:
            self.flash()
            self.next_flash = random.uniform(0.5, 1.2)
        return not self.dead

    def render(self, surface: pygame.Surface) -> None:
        if self.k <= 0.02:
            return
        w, h = surface.get_size()
        for size in (200, 290, 380):
            _puff(size).set_alpha(int(255 * clamp01(self.k)))
        for x, y, size, sp in self.puffs:
            px = (x * w + self.t * sp) % (w + 400) - 200
            s = _puff(size)
            surface.blit(s, (px - size / 2, y * h * 1.0 - size / 2 + 30))
        if self.lit > 0:
            soft(surface, (self.fpos[0] * w, self.fpos[1] * h), 300, mix(THUNDER, WHITE, 0.5), 0.8 * self.lit * self.k)


class Crackle(Effect):
    """Sphère d'énergie crépitante au bout du bâton (`r`, `k`)."""

    layer = "front"

    def __init__(self, pos) -> None:
        self.pos, self.r, self.k, self.t, self.bolts, self.timer = Vector2(pos), 4.0, 1.0, 0.0, [], 0.0

    def update(self, dt: float) -> bool:
        self.t += dt
        self.timer -= dt
        if self.timer <= 0:
            self.timer = 0.07
            self.bolts = [lightning_points(self.pos, self.pos + polar(random.uniform(0, 360), self.r * random.uniform(1.3, 2.6)),
                                           0.3, 4) for _ in range(4)]
        return not self.dead

    def render(self, surface: pygame.Surface) -> None:
        k = clamp01(self.k)
        r = self.r * (1 + 0.12 * math.sin(self.t * 30))
        soft(surface, self.pos, r * 2.6, THUNDER, 0.6 * k)
        soft(surface, self.pos, r * 1.2, WHITE, 0.9 * k)
        for pts in self.bolts:
            pl = [(p.x, p.y) for p in pts]
            pygame.draw.lines(surface, scaled(THUNDER, k), False, pl, 3)
            pygame.draw.lines(surface, scaled(WHITE, k), False, pl, 1)


class LavaCracks(Effect):
    """Fissures de lave au sol (réseau procédural, `p` = progression 0..1, `k` = opacité)."""

    layer = "back"

    def __init__(self, origin, reach: float = 620.0) -> None:
        o = Vector2(origin)
        self.o, self.p, self.k, self.t, self.lines = o, 0.0, 1.0, 0.0, []
        n = 11
        for i in range(n):
            ang = i * math.tau / n + random.uniform(-0.2, 0.2)
            end = o + Vector2(math.cos(ang) * reach * random.uniform(0.45, 1.0),
                              math.sin(ang) * reach * 0.27 * random.uniform(0.6, 1.0))
            pts = lightning_points(o, end, 0.16, 4)
            delay = random.uniform(0.0, 0.3)
            self.lines.append((pts, 5, delay))
            j = random.randint(len(pts) // 4, len(pts) * 3 // 4)
            br = pts[j] + Vector2(random.uniform(-160, 160), random.uniform(-40, 50))
            self.lines.append((lightning_points(pts[j], br, 0.2, 3), 3, delay + 0.25))

    def update(self, dt: float) -> bool:
        self.t += dt
        return not self.dead

    def render(self, surface: pygame.Surface) -> None:
        if self.p <= 0.01 or self.k <= 0.02:
            return
        k = clamp01(self.k)
        flick = 0.85 + 0.15 * math.sin(self.t * 11)
        soft(surface, self.o, 250 * clamp01(self.p * 1.5), FIRE, 0.45 * k * flick)
        for pts, w, d in self.lines:
            q = clamp01((self.p - d) / max(0.2, 1 - d))
            n = int(len(pts) * q)
            if n < 2:
                continue
            pl = [(p.x, p.y) for p in pts[:n]]
            pygame.draw.lines(surface, scaled(RED, 0.55 * k), False, pl, w + 6)
            pygame.draw.lines(surface, scaled(FIRE, k * flick), False, pl, w + 2)
            pygame.draw.lines(surface, scaled(GOLD, k), False, pl, max(1, w - 2))
            soft(surface, pl[-1], 38, FIRE, 0.7 * k * flick)


class MegaBeam(Effect):
    """Rayon effilé (étroit à la source, évasé vers la cible) : polygones emboîtés + lueurs diffuses."""

    layer = "overlay"

    def __init__(self, start, end, color=ICE, width: float = 120.0, life: float = 1.4, attack: float = 0.25,
                 delay: float = 0.0, layer: str = "overlay") -> None:
        self.a, self.b, self.color, self.width, self.life, self.attack = Vector2(start), Vector2(end), color, width, life, attack
        self.t, self.layer = -delay, layer

    def update(self, dt: float) -> bool:
        self.t += dt
        return self.t < self.life

    def render(self, surface: pygame.Surface) -> None:
        if self.t < 0:
            return
        k = clamp01(self.t / self.attack) * clamp01((self.life - self.t) / (self.life * 0.4))
        if k <= 0.01:
            return
        d = self.b - self.a
        n = Vector2(-d.y, d.x)
        if not n.length():
            return
        n = n.normalize()
        wob = 1 + 0.06 * math.sin(self.t * 55)
        tmp = scratch(surface.get_size(), "megabeam")
        tmp.fill((0, 0, 0, 255))
        w0, w1 = self.width * 0.22 * k * wob, self.width * k * wob
        for sc, col, kk in ((1.0, mix(self.color, BLACK, 0.45), 0.55), (0.72, self.color, 0.85),
                            (0.42, mix(self.color, WHITE, 0.6), 1.0), (0.2, WHITE, 1.0)):
            pts = [self.a + n * w0 * sc, self.b + n * w1 * sc, self.b - n * w1 * sc, self.a - n * w0 * sc]
            pygame.draw.polygon(tmp, scaled(col, kk), pts)
        surface.blit(tmp, (0, 0), special_flags=pygame.BLEND_ADD)  # additif : jamais de bord sombre
        steps = max(3, int(d.length() / 55))
        for i in range(steps + 1):
            u = i / steps
            soft(surface, self.a + d * u, lerp_(w0, w1, u) * 1.5, self.color, 0.45 * k)
        soft(surface, self.a, w0 * 4, WHITE, 0.9 * k)
        soft(surface, self.b, w1 * 2.6, WHITE, 0.9 * k)


def lerp_(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


class IcePillar(Effect):
    """Pilier de glace facetté qui jaillit sous un ennemi (reste jusqu'à `kill()`)."""

    layer = "front"

    def __init__(self, base, width: float, height: float, delay: float = 0.0, grow: float = 0.55) -> None:
        self.base, self.w, self.h = Vector2(base), int(width), int(height)
        self.t, self.grow = -delay, grow
        w, h = self.w, self.h
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        body = [(0.06 * w, h), (0.0, 0.3 * h), (0.5 * w, 0), (w, 0.3 * h), (0.94 * w, h)]
        pygame.draw.polygon(s, ICE + (120,), body)
        pygame.draw.polygon(s, PALE + (150,), [(0.06 * w, h), (0, 0.3 * h), (0.5 * w, 0), (0.42 * w, h)])
        pygame.draw.polygon(s, WHITE + (80,), [(0.5 * w, 0), (0.62 * w, 0.28 * h), (0.55 * w, h), (0.42 * w, h)])
        pygame.draw.polygon(s, BLUE + (90,), [(w, 0.3 * h), (0.5 * w, 0), (0.62 * w, 0.28 * h), (0.94 * w, h), (0.7 * w, h)])
        for a, b in (((0.5 * w, 0), (0.42 * w, h)), ((0.0, 0.3 * h), (0.5 * w, 0.34 * h)), ((w, 0.3 * h), (0.5 * w, 0.34 * h))):
            pygame.draw.line(s, WHITE + (200,), a, b, 2)
        pygame.draw.polygon(s, WHITE + (235,), body, 3)
        self.surf = s

    def update(self, dt: float) -> bool:
        self.t += dt
        return not self.dead

    def render(self, surface: pygame.Surface) -> None:
        if self.t < 0:
            return
        g = clamp01(ease("out_back", self.t / self.grow))
        g = min(g, 1.0)
        hh = max(2, int(self.h * g))
        soft(surface, self.base, self.w * 0.9, ICE, 0.5 * clamp01(self.t * 3))
        surface.blit(self.surf, (self.base.x - self.w / 2, self.base.y - hh), (0, self.h - hh, self.w, hh))
        if self.t > self.grow:  # scintillement
            ph = self.t * 5
            soft(surface, (self.base.x + math.sin(ph) * self.w * 0.25, self.base.y - self.h * (0.25 + 0.5 * ((ph * 0.4) % 1))),
                 14, WHITE, 0.7 + 0.3 * math.sin(ph * 3))


# ----------------------------------------------------------------- aides de mise en scène


def _duck(c, level: float, seconds: float):
    """Baisse la musique pendant le spectacle (sans effet s'il n'y a pas d'audio)."""
    def f() -> None:
        try:
            if c.audio is not None:
                c.audio.duck(level, seconds)
        except Exception:  # noqa: BLE001
            pass

    def restore() -> None:  # fin ou skip : la musique revient tout de suite
        try:
            if c.audio is not None:
                c.audio.duck(1.0, 0.0)
        except Exception:  # noqa: BLE001
            pass
    c.on_end(restore)
    return Call(f)


def _pose(actor, pose: str) -> None:
    try:
        actor.set_pose(pose)
    except Exception:  # noqa: BLE001
        pass


def _cast(c):
    """Le lanceur passe en `cast` pendant l'invocation et revient à `idle` à la fin (ou au skip)."""
    c.on_end(lambda: _pose(c.caster, "idle"))
    return Call(_pose, c.caster, "cast")


def _set(obj, attr: str, value):
    return Call(setattr, obj, attr, value)


def _pulse(obj, attr: str, peak: float, seconds: float):
    """Saute à `peak` puis redescend à 0 (pulsation de lueur)."""
    return Seq(_set(obj, attr, peak), Anim(obj, attr, 0.0, seconds, "out_quad"))


# ----------------------------------------------------------------- Ifrit


@scripted("summon.ifrit", skippable=True)
def ifrit(c):
    """Ifrit (~6 s) : fournaise (sol qui se fissure) / surgit du sol en silhouette incandescente /
    rugit (ondes, souffle) / météores sur chaque ennemi, secousses graduées / se consume."""
    W, H = _screen(c)
    cx, gy = W * 0.58, H * 0.80
    st, n = Stage(c), max(1, len(c.targets))
    tint = ScreenTint(scaled(RED, 0.5), 0.74, 0.8, 4.4, 0.9, layer="back")
    edge, bars = EdgeGlow(FIRE, pulse=0.15), Letterbox()
    cracks = LavaCracks((cx - 60, gy + 10), 700)
    rays = Rays((cx, gy - 230), 560, FIRE, spin=9.0)
    boss = Apparition(_image(c, "summon_fire", FIRE), (cx, gy + 300), H * 0.70, FIRE, "back")
    boss.a, boss.k, boss.bright, boss.bright_color = 0.0, 0.72, 1.0, mix(FIRE, WHITE, 0.55)
    embers = ParticleEmitter((cx, gy), "fire", rate=55, duration=5.4, radius=300, angle=-90, spread=30,
                             speed=0.6, size=0.8, life=1.4)

    def meteor(i, t):
        tc, ft = c.center(t), c.feet(t)
        start = Vector2(tc.x + 420, -140)
        proj = Projectile(start, tc, 0.55, "orb", FIRE, size=34, easing="in_quad")
        tail = ParticleEmitter(start, "fire", rate=240, duration=0.55, radius=18, speed=0.4, size=1.6,
                               follow=lambda p=proj: p.pos, life=0.9)
        extra = []
        if i == n - 1:  # le dernier météore conclut : plus gros, distorsion
            extra = [st.add(ImpactWarp(0.5, 0.06, 10, center=tuple(tc))), st.add(ScreenShake(15, 0.8)),
                     st.add(Flash(WHITE, 0.3, 0.45))]
        return Seq(
            Par(st.add(MagicCircle(ft, 80, FIRE, life=0.9, squash=0.3, points=5)), st.add(proj), st.add(tail),
                c.sfx("summon", 0.4)),
            0.55,
            Par(c.hit(i, shake=8 + 3 * i, color=FIRE, sparks="fire"), c.sfx("explosion"),
                st.add(ParticleEmitter(tc, "fire", count=80, radius=26, spread=360, speed=1.9, size=1.7)),
                st.add(ParticleEmitter(ft, "dust", count=28, radius=40, speed=1.2,
                                       colors=[RED, mix(RED, BLACK, 0.5), FIRE])),
                st.add(Shockwave(ft, FIRE, 12, 260, 0.5, 10, squash=0.32)),
                st.add(Shockwave(tc, GOLD, 10, 140, 0.3, 6)),
                st.add(LightColumn(tc.x, ft.y + 6, 480, 160, FIRE, 0.9)),
                st.add(Flash(FIRE, 0.2, 0.4, additive=True)), _pulse(boss, "bright", 0.5, 0.45), *extra),
        )

    return Seq(
        c.hide_ui(), _cast(c), _duck(c, 0.3, 6.2),
        # acte 1 : la fournaise
        Par(c.sfx("summon"), st.add(tint), st.add(edge), st.add(cracks), st.add(rays), st.add(bars), st.add(embers),
            st.add(ScreenShake(2.5, 1.4, decay=False)), Anim(bars, "k", 1.0, 0.6), Anim(edge, "k", 1.0, 1.3),
            Anim(rays, "k", 0.55, 1.4), Anim(cracks, "p", 1.0, 1.4, "out_quad")),
        # acte 2 : il surgit du sol, silhouette blanche incandescente
        Par(st.add(boss), Anim(boss, "a", 1.0, 0.3), Anim(boss, "pos", Vector2(cx, gy + 30), 0.9, "out_cubic"),
            Anim(boss, "k", 1.0, 0.9, "out_cubic"), Anim(boss, "bright", 0.0, 1.1, "out_quad"),
            st.add(LightColumn(cx, gy + 10, 620, 270, FIRE, 1.2)),
            st.add(ParticleEmitter((cx, gy), "fire", count=150, radius=120, angle=-90, spread=120, speed=2.2,
                                   size=1.6, life=1.3)),
            st.add(Shockwave((cx, gy), FIRE, 20, 520, 0.8, 10, squash=0.3)), st.add(ScreenShake(9, 0.8)),
            st.add(ImpactWarp(0.35, 0.04, 6)), st.add(Flash(FIRE, 0.4, 0.5, additive=True))),
        # acte 3 : le rugissement
        Par(c.sfx("roar"), st.add(ScreenShake(13, 0.9)), st.add(ImpactWarp(0.5, 0.05, 9)),
            st.add(Flash(FIRE, 0.5, 0.5, additive=True)), Anim(rays, "k", 1.0, 0.4), Anim(edge, "k", 1.3, 0.4),
            st.add(Shockwave((cx, gy), GOLD, 20, 760, 0.9, 8, squash=0.3, delay=0.1)),
            st.add(Shockwave((cx, gy - 160), FIRE, 20, 620, 0.8, 8, delay=0.2)),
            st.add(ParticleEmitter(boss.point(0.5, 0.2, (cx, gy + 30)), "fire", count=130, angle=180, spread=55,
                                   speed=2.3, size=1.5, life=1.2)),
            Seq(Anim(boss, "k", 1.12, 0.14, "out_quad"), Anim(boss, "k", 1.0, 0.6, "in_out_quad")),
            Seq(Anim(boss, "jit", 5.0, 0.1), Anim(boss, "jit", 0.0, 0.8))),
        0.1,
        # acte 4 : les météores
        c.each(meteor, stagger=0.3),
        0.2,
        # acte 5 : il se consume
        Par(Anim(boss, "a", 0.0, 0.9, "in_quad"), Anim(boss, "k", 1.1, 0.9, "in_quad"), Anim(boss, "bright", 0.8, 0.5),
            st.add(ParticleEmitter(boss.mouth(0.5), "fire", rate=200, duration=0.8, radius=110, speed=0.7, size=1.3,
                                   angle=-90, spread=60, life=1.4)),
            Anim(cracks, "k", 0.0, 0.9), Anim(edge, "k", 0.0, 0.8), Anim(rays, "k", 0.0, 0.6), Anim(bars, "k", 0.0, 0.7)),
        0.1,
    )


# ----------------------------------------------------------------- Shiva


@scripted("summon.shiva", skippable=True)
def shiva(c):
    """Shiva (~6 s) : le froid tombe (givre, aurore, flocons) / elle descend en silhouette de glace /
    couronne de givre qui aspire des cristaux / piliers sous chaque ennemi / tout éclate en poussière de diamant."""
    W, H = _screen(c)
    cx, gy = W * 0.58, H * 0.84
    st = Stage(c)
    tint = ScreenTint(NAVY, 0.62, 0.8, 4.3, 0.9, layer="back")
    frost, snow, aurora, bars = EdgeGlow(ICE, pulse=0.08), Snow(170), Aurora(), Letterbox()
    rays = Rays((cx, gy - 300), 520, ICE, spin=6.0)
    boss = Apparition(_image(c, "summon_ice", ICE), (cx, gy - 110), H * 0.70, ICE, "back")
    boss.a, boss.k, boss.bright, boss.bright_color = 0.0, 0.95, 1.0, mix(ICE, WHITE, 0.6)

    def crown() -> Vector2:  # couronne de givre au-dessus d'elle
        return boss.point(0.5, 0.07)

    orb = EnergyOrb(crown(), 4, ICE, follow=crown, layer="front")
    inflow = Inflow(crown(), 170, 360, 14, (WHITE, ICE, PALE), layer="front")
    inflow.follow = crown
    pillars: list[IcePillar] = []

    def grow_pillars():
        for i, t in enumerate(c.targets):
            pillars.append(st.spawn(IcePillar(c.feet(t) + Vector2(0, 6), t.rect.w * 0.85, t.rect.h * 1.3, delay=i * 0.22)))

    def break_all():
        for p in pillars:
            p.kill()

    def mist(i, t):
        return st.add(ParticleEmitter(c.feet(t), "ice", rate=50, duration=1.2, radius=t.rect.w * 0.5, angle=-90,
                                      spread=50, speed=0.5, size=0.9, life=1.2, gravity=-30))

    def shatter(i, t):
        ctr = c.center(t)
        return Par(
            c.hit(i, shake=9 + 2 * i, color=ICE, sparks=None),
            st.add(GlassShards(ctr, 44, (PALE, ICE, WHITE), (6, 24), (220, 700), 1.2, 800)),
            st.add(ParticleEmitter(ctr, "sparkle", count=110, radius=t.rect.w * 0.5, speed=0.8, life=2.0,
                                   colors=[WHITE, ICE, PALE], gravity=-8, size=1.0)),
            st.add(Shockwave(ctr, ICE, 10, 200, 0.45, 8)),
        )

    return Seq(
        c.hide_ui(), _cast(c), _duck(c, 0.3, 6.0),
        # acte 1 : le froid tombe
        Par(c.sfx("summon"), st.add(tint), st.add(frost), st.add(snow), st.add(aurora), st.add(bars), st.add(rays),
            st.add(MagicCircle((cx, gy + 5), 260, ICE, life=5.4, squash=0.3, points=6)),
            st.add(ScreenShake(1.5, 1.2, decay=False)), Anim(bars, "k", 1.0, 0.6), Anim(frost, "k", 1.0, 1.2),
            Anim(snow, "k", 1.0, 1.2), Anim(aurora, "k", 1.0, 1.2)),
        # acte 2 : elle descend, silhouette de glace qui se précise
        Par(st.add(boss), Anim(boss, "a", 1.0, 0.9), Anim(boss, "pos", Vector2(cx, gy), 1.3, "out_cubic"),
            Anim(boss, "bright", 0.0, 1.2), Anim(rays, "k", 0.55, 1.2),
            st.add(ParticleEmitter((cx, gy - 200), "sparkle", rate=75, duration=1.3, radius=170, speed=0.3, life=1.5,
                                   colors=[WHITE, ICE, PALE], gravity=-10)),
            st.add(LightColumn(cx, gy, 620, 230, ICE, 1.3)), st.add(Flash(ICE, 0.5, 0.35, additive=True))),
        # acte 3 : elle lève les bras, le givre se rassemble
        Par(c.sfx("charge"), Anim(boss, "k", 1.07, 0.8, "out_back"), st.add(orb), st.add(inflow),
            Anim(orb, "radius", 62.0, 1.0, "in_quad"), Anim(inflow, "k", 1.0, 0.3), Anim(inflow, "pull", 1.0, 1.0, "in_quad"),
            Anim(rays, "k", 0.9, 1.0),
            c.each(lambda i, t: st.add(Shockwave(c.feet(t), ICE, 10, 230, 0.8, 6, squash=0.3, delay=0.2 + i * 0.15)))),
        # acte 4 : les piliers montent sous chaque ennemi
        Par(c.sfx("ice_form"), Call(grow_pillars), st.add(ScreenShake(3.5, 1.3, decay=False)), c.each(mist),
            Anim(orb, "radius", 90.0, 1.0, "in_quad"), Anim(frost, "k", 1.25, 1.0)),
        0.3,
        # acte 5 : tout se brise en même temps
        Call(break_all), Call(orb.kill), Call(inflow.kill),
        Par(c.sfx("ice_shatter"), st.add(Flash(WHITE, 0.45, 0.8, additive=True)), st.add(Flash(ICE, 0.7, 0.45)),
            st.add(ScreenShake(12, 0.6)), st.add(ImpactWarp(0.6, 0.07, 11)),
            st.add(ParticleEmitter((W * 0.3, H * 0.5), "sparkle", count=170, radius=330, speed=0.7, life=2.4,
                                   colors=[WHITE, ICE, PALE], gravity=-6, size=1.1, layer="overlay")),
            c.each(shatter, stagger=0.04), Anim(frost, "k", 0.0, 0.7), Anim(snow, "k", 0.3, 0.7)),
        # acte 6 : la poussière de diamant retombe
        Par(Anim(boss, "a", 0.0, 0.8, "in_quad"), Anim(boss, "bright", 0.6, 0.4), Anim(rays, "k", 0.0, 0.7),
            Anim(aurora, "k", 0.0, 0.8), Anim(snow, "k", 0.0, 0.8), Anim(bars, "k", 0.0, 0.7)),
        0.1,
    )


# ----------------------------------------------------------------- Ramuh


@scripted("summon.ramuh", skippable=True)
def ramuh(c):
    """Ramuh (~6,5 s) : orage (nuages, pluie, éclairs lointains) / un éclair le dépose sur le sol /
    son bâton se charge en aspirant la foudre / jugement : un éclair géant sur chaque ennemi / finale blanche."""
    W, H = _screen(c)
    cx, gy = W * 0.58, H * 0.84
    st = Stage(c)
    tint = ScreenTint(scaled(NAVY, 0.5), 0.76, 0.9, 4.1, 0.9, layer="back")
    clouds, rain, bars = StormClouds(), Rain(), Letterbox()
    rays = Rays((cx, gy - 260), 520, THUNDER, spin=-11.0)
    boss = Apparition(_image(c, "summon_thunder", THUNDER), (cx, gy), H * 0.70, THUNDER, "back")
    boss.a, boss.bright, boss.bright_color = 0.0, 1.0, mix(THUNDER, WHITE, 0.5)
    fx_, fy_ = anchor_top(boss.src, 40)  # le sommet du bâton, où qu'il soit dans l'image
    staff = Crackle(boss.point(fx_, fy_ + 0.025, (cx, gy)))
    staff.r, staff.k = 3.0, 0.0
    inflow = Inflow(staff.pos, 130, 330, 18, (THUNDER, WHITE), layer="front")
    inflow.follow = lambda: staff.pos

    def far_strike(xf: float):
        x = W * xf
        clouds.flash()
        st.spawn(Lightning(Vector2(x, -30), Vector2(x + random.uniform(-60, 60), gy - 20), THUNDER, 7, 0.45,
                           branches=3, jag=0.2, layer="back"))
        st.spawn(Flash(THUNDER, 0.18, 0.22, additive=True))
        c.sound("thunder", 0.4)

    def arrival():
        c.sound("thunder", 0.8)
        clouds.flash()
        st.spawn(Lightning(Vector2(cx, -30), Vector2(cx, gy), THUNDER, 20, 0.7, branches=7, jag=0.16))
        st.spawn(Lightning(Vector2(cx, -30), Vector2(cx, gy), WHITE, 7, 0.55, branches=2, jag=0.1))
        st.spawn(Flash(WHITE, 0.5, 0.85))
        st.spawn(ScreenShake(12, 0.7))
        st.spawn(ImpactWarp(0.4, 0.04, 9))
        st.spawn(LightColumn(cx, gy + 6, 720, 260, THUNDER, 0.9))
        st.spawn(ParticleEmitter((cx, gy), "thunder", count=60, radius=40, speed=1.6))

    def sky_bolt():
        st.spawn(Lightning(Vector2(staff.pos.x + random.uniform(-260, 260), -30), staff.pos, THUNDER, 5, 0.3,
                           branches=1, jag=0.22))
        clouds.flash()

    def judgment(i, t):
        tc, ft = c.center(t), c.feet(t)
        tx = tc.x
        sky = Vector2(tx + random.uniform(-40, 40), -30)
        return Seq(
            Par(st.add(Lightning(staff.pos, tc, THUNDER, 3, 0.4, branches=1, jag=0.22)),  # l'étincelle qui précède
                st.add(MagicCircle(ft, 70, THUNDER, life=0.7, squash=0.3, points=4)),
                st.add(Flash(THUNDER, 0.1, 0.25, additive=True))),
            0.35,
            Par(c.sfx("thunder"), st.add(Lightning(sky, tc, THUNDER, 17, 0.75, branches=6, jag=0.2)),
                st.add(Lightning(Vector2(tx, -30), tc, WHITE, 7, 0.55, branches=2, jag=0.1)),
                st.add(LightColumn(tx, ft.y, 720, 190, THUNDER, 0.75)),
                st.add(Flash(WHITE, 0.3, 0.6)), c.hit(i, shake=11 + 3 * i, color=THUNDER, sparks="thunder"),
                st.add(ParticleEmitter(tc, "thunder", count=48, radius=22, speed=1.5)),
                st.add(Shockwave(ft, THUNDER, 10, 230, 0.45, 8, squash=0.3)),
                st.add(ImpactWarp(0.3, 0.03, 8, center=tuple(tc))), Call(clouds.flash)),
        )

    def finale():
        for _ in range(9):
            st.spawn(Lightning(staff.pos, staff.pos + polar(random.uniform(0, 360), random.uniform(160, 420)),
                               THUNDER, 5, 0.4, branches=1, jag=0.25))

    return Seq(
        c.hide_ui(), _cast(c), _duck(c, 0.3, 6.4),
        # acte 1 : l'orage se lève
        Par(c.sfx("summon"), st.add(tint), st.add(clouds), st.add(rain), st.add(bars),
            st.add(ScreenShake(2, 1.3, decay=False)), Anim(bars, "k", 1.0, 0.6), Anim(clouds, "k", 1.0, 1.1),
            Anim(rain, "k", 1.0, 1.1),
            Seq(0.45, Call(far_strike, 0.14), 0.45, Call(far_strike, 0.86), 0.4)),
        # acte 2 : la foudre le dépose sur le sol
        Par(Call(arrival), st.add(boss), st.add(rays), Anim(boss, "a", 1.0, 0.12), Anim(boss, "bright", 0.0, 1.0),
            Anim(rays, "k", 0.55, 1.0), 1.1),
        # acte 3 : le bâton se charge
        Par(c.sfx("charge"), st.add(staff), st.add(inflow), Anim(staff, "r", 46.0, 1.3, "in_quad"),
            Anim(staff, "k", 1.0, 0.2), Anim(inflow, "k", 1.0, 0.3), Anim(inflow, "pull", 1.0, 1.2, "in_quad"),
            Anim(rays, "k", 0.9, 1.2),
            st.add(MagicCircle((cx, gy + 5), 280, THUNDER, life=3.6, squash=0.3, points=4)),
            st.add(ScreenShake(3.5, 1.3, decay=False)),
            Seq(0.2, Call(sky_bolt), 0.3, Call(sky_bolt), 0.25, Call(sky_bolt), 0.2, Call(sky_bolt), 0.15)),
        Call(inflow.kill),
        # acte 4 : le jugement
        c.each(judgment, stagger=0.42),
        # acte 5 : éclair final
        Par(c.sfx("thunder_big"), Call(finale), st.add(Flash(WHITE, 0.8, 0.95)), st.add(ScreenShake(16, 0.8)),
            st.add(ImpactWarp(0.6, 0.08, 14)), Anim(staff, "k", 0.0, 0.4), Anim(rays, "k", 1.2, 0.2)),
        0.1,
        # acte 6 : retombée
        Par(Anim(boss, "a", 0.0, 0.8), Anim(clouds, "k", 0.0, 0.8), Anim(rain, "k", 0.0, 0.7), Anim(rays, "k", 0.0, 0.6),
            Anim(bars, "k", 0.0, 0.7),
            st.add(ParticleEmitter((W / 2, -10), "thunder", rate=60, duration=0.6, radius=W / 2, angle=90, spread=30,
                                   speed=0.5, life=1.2, gravity=300))),
        0.1,
    )


# ----------------------------------------------------------------- Bahamut


@scripted("summon.bahamut", skippable=True)
def bahamut(c):
    """Bahamut (~7 s) : nuit étoilée / le roi dragon plonge du ciel en zoom / l'orbe aspire les étoiles /
    Mégaflare / l'écran se noie dans le blanc, long tremblement décroissant / retour progressif."""
    W, H = _screen(c)
    cx, gy = W * 0.60, H * 1.0
    st = Stage(c)
    stars = Starfield(0.0, "drift", 240, 1.0,
                      nebula=[(0.28, 0.32, 380, NAVY, 0.9), (0.72, 0.62, 300, HOLY, 0.3), (0.5, 0.08, 340, BLUE, 0.25)])
    bars = Letterbox()
    boss = Apparition(_image(c, "summon_dragon_king", HOLY), (cx, -40), H * 0.74, HOLY, "overlay")
    boss.a, boss.k, boss.bob, boss.bright, boss.bright_color = 0.0, 0.55, 4.0, 0.8, mix(HOLY, WHITE, 0.5)
    mx, my = anchor_head(boss.src)  # gueule, quel que soit le sens de l'image

    def mouth() -> Vector2:
        return boss.point(mx, my)

    mouth0 = boss.point(mx, my, (cx, gy)) if boss.k == 1.0 else Vector2(
        cx + (mx - 0.5) * boss.h * boss.src.get_width() / boss.src.get_height(), gy - boss.h * (1 - my))
    orb = EnergyOrb(mouth0, 4, ICE, follow=mouth, layer="overlay")
    inflow = Inflow(mouth0, 210, 470, 26, (WHITE, ICE, HOLY, GOLD), layer="overlay")
    inflow.follow = mouth
    halo = Rays(mouth0, 300, ICE, spin=30.0, layer="overlay")
    halo.follow = mouth
    back_rays = Rays((cx, gy - 200), 600, HOLY, spin=8.0, layer="overlay")
    ctr = Vector2()
    for t in c.targets:
        ctr += c.center(t)
    ctr = ctr / max(1, len(c.targets))
    beams: list = []

    def fire_beams():
        m = mouth()
        beams.append(st.spawn(MegaBeam(m, ctr, ICE, 230, 1.3, attack=0.2)))
        for t in c.targets:
            beams.append(st.spawn(MegaBeam(m, c.center(t), HOLY, 70, 1.2, attack=0.2)))

    def blast():
        for e in (stars, boss, orb, inflow, halo, back_rays, *beams):
            e.kill()

    def detonate(i, t):
        tc = c.center(t)
        return Seq(0.05 + i * 0.08,
                   Par(c.hit(i, shake=0, color=WHITE, sparks=None, text=False),
                       st.add(ParticleEmitter(tc, "fire", count=70, radius=26, speed=2.0, size=1.6, layer="overlay")),
                       st.add(Shockwave(tc, WHITE, 10, 260, 0.5, 10, layer="overlay"))),
                   0.95 + i * 0.12, c.damage_text(i))

    ring_seq = Seq(*[Seq(st.add(Shockwave(mouth0, ICE if i % 2 else HOLY, 340, 24, 0.7, 5, easing="in_quad", layer="overlay")), 0.34)
                     for i in range(5)])

    return Seq(
        c.hide_ui(), _cast(c), _duck(c, 0.2, 7.0),
        # acte 1 : la nuit
        Par(c.sfx("summon"), st.add(stars), st.add(bars), Anim(stars, "bg", 1.0, 0.6), Anim(bars, "k", 1.0, 0.6),
            st.add(ScreenShake(1.5, 1.0, decay=False)), 0.7),
        # acte 2 : le roi dragon plonge (zoom + parallaxe des étoiles)
        Par(st.add(back_rays), st.add(boss), Anim(boss, "a", 1.0, 0.6), Anim(boss, "pos", Vector2(cx, gy), 1.4, "out_cubic"),
            Anim(boss, "k", 1.0, 1.4, "out_cubic"), Anim(boss, "bright", 0.0, 1.3), Anim(back_rays, "k", 0.5, 1.3),
            Seq(Anim(stars, "speed", 4.0, 0.9, "in_quad"), Anim(stars, "speed", 0.8, 0.6)),
            st.add(ParticleEmitter((cx, 0), "sparkle", rate=100, duration=1.4, radius=170, speed=0.3, life=1.2,
                                   follow=lambda: Vector2(boss.pos.x, boss.pos.y - boss.h * boss.k * 0.5), layer="overlay",
                                   colors=[WHITE, ICE, HOLY])),
            st.add(ScreenShake(2.5, 1.4)), Seq(1.2, c.sfx("roar"), st.add(ImpactWarp(0.4, 0.035, 6)), 0.2)),
        # acte 3 : la charge, l'orbe aspire tout
        Par(c.sfx("charge_big"), st.add(orb), st.add(inflow), st.add(halo), Anim(orb, "radius", 88.0, 1.6, "in_quad"),
            Anim(inflow, "k", 1.0, 0.3), Anim(inflow, "pull", 1.0, 1.6, "in_quad"), Anim(halo, "k", 0.85, 1.6, "in_quad"),
            Anim(halo, "r", 560.0, 1.6, "in_quad"), Anim(boss, "jit", 4.0, 1.6, "in_quad"), Anim(stars, "a", 0.55, 1.6),
            Anim(back_rays, "k", 0.2, 1.0), ring_seq,
            Seq(st.add(ScreenShake(2, 0.6, decay=False)), 0.6, st.add(ScreenShake(4, 0.6, decay=False)), 0.6,
                st.add(ScreenShake(7, 0.4, decay=False)))),
        0.05,
        # acte 4 : Mégaflare
        Par(c.sfx("mega_flare"), Call(fire_beams), Anim(orb, "radius", 165.0, 0.3, "out_quad"), Anim(boss, "jit", 0.0, 0.2),
            Anim(inflow, "k", 0.0, 0.2), Anim(stars, "bg", 0.3, 0.3), st.add(ScreenShake(12, 0.4)),
            st.add(ImpactWarp(0.6, 0.08, 14)), st.add(Flash(ICE, 0.35, 0.6, attack=0.03, additive=True)),
            st.add(Shockwave(mouth0, WHITE, 30, 700, 0.6, 14, layer="overlay"))),
        0.05,
        # acte 5 : le blanc envahit l'écran, le sol tremble
        Par(st.add(Flash(WHITE, 1.4, 1.0, attack=0.45)), Anim(bars, "k", 0.0, 0.4), c.each(detonate),
            Seq(0.45, Call(blast), c.sfx("explosion"), st.add(ScreenShake(22, 1.5)),
                st.add(Shockwave(ctr, WHITE, 20, 1100, 0.9, 26, layer="overlay")),
                st.add(Shockwave(ctr, ICE, 20, 950, 1.0, 16, delay=0.15, layer="overlay")),
                st.add(Shockwave(ctr, HOLY, 20, 800, 1.1, 12, delay=0.3, layer="overlay")),
                st.add(ParticleEmitter(ctr, "sparkle", count=170, speed=3.2, size=1.3, life=1.8, layer="overlay")),
                0.3, c.sfx("explosion", 0.7),
                st.add(ParticleEmitter((W / 2, -10), "sparkle", rate=80, duration=1.2, radius=W / 2, angle=90, spread=40,
                                       speed=0.4, life=1.6, gravity=120, layer="overlay", colors=[WHITE, ICE, HOLY])),
                0.9),
            2.0),
    )
