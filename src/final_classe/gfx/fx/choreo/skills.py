"""Compétences de job (`skill.<job>`) : docs/ANIMATIONS.md §2.

Briques locales : Crescent, SplitHalves, BreakText, Reticle, CoinFlight, PotionPop, Glint, RisingRing.
"""
from __future__ import annotations

import math
import random

import pygame
from pygame import Vector2

from . import Anim, Call, Par, Seq, Wait, scripted
from .. import (AfterImage, Beam, Effect, EnergyOrb, Flash, FloatingText, GlassShards, GOLD, GREEN, ICE, LightColumn,
                MagicCircle, NAVY, PALE, ParticleEmitter, Projectile, RED, ScreenShake, ScreenTint, Shockwave,
                Slash, STEEL, BLUE, FIRE, WHITE, HOLY, blit_glow, scratch, clamp01, ease, lerp, polar, scaled,
                text_surface)


def _face(me, tg) -> int:
    return 1 if tg.home.x > me.home.x else -1


def _pose(me, name: str, hold: float | None = None):
    """Étape de chorégraphie : change la pose du lanceur (sans effet sans planche)."""
    return Call(lambda: getattr(me, "set_pose", lambda *_: None)(name, hold))


def _target(c):
    return c.targets[0] if c.targets else c.caster


def _recoil(t, s: int, px: float = 14.0):
    return Seq(Anim(t, "offset", Vector2(s * px, 0), 0.06, "out_quad"), Anim(t, "offset", Vector2(), 0.22, "out_quad"))


# ----------------------------------------------------------------- briques locales


class Crescent(Effect):
    """Croissant géant qui balaie l'écran horizontalement (`direction` = +1 vers la droite)."""

    def __init__(self, y: float, x0: float, direction: int, duration: float = 0.5, size: float = 250.0,
                 color=RED) -> None:
        self.y, self.x0, self.dir, self.duration, self.color = y, x0, direction, duration, color
        self.t = 0.0
        tip = size * 0.5
        outer = [(math.cos(math.radians(a)) * size, math.sin(math.radians(a)) * size * 1.05) for a in range(-60, 61, 6)]
        inner = [(tip + (x - tip) * 0.42, yy) for x, yy in reversed(outer)]
        self.shape = outer + inner
        self.outer = outer
        self.size = size

    def update(self, dt: float) -> bool:
        self.t += dt
        return self.t < self.duration + 0.25

    def render(self, surface: pygame.Surface) -> None:
        w = surface.get_width()
        x1 = w + self.size * 1.5 if self.dir > 0 else -self.size * 1.5
        p = ease("in_quad", clamp01(self.t / self.duration))
        x = lerp(self.x0, x1, p)
        fade = clamp01(1 - (self.t - self.duration) / 0.25)
        if fade <= 0.02:
            return
        layer = scratch(surface.get_size(), "crescent")
        layer.fill((0, 0, 0, 0))
        for j in range(6, -1, -1):
            k = (1 - j / 7) * fade
            cx = x - self.dir * j * 34
            pts = [(cx + self.dir * px, self.y + py) for px, py in self.shape]
            pygame.draw.polygon(layer, self.color + (int(255 * k * (1 if j == 0 else 0.6)),), pts)
            if j == 0:
                arc = [(cx + self.dir * px, self.y + py) for px, py in self.outer]
                pygame.draw.lines(layer, WHITE + (int(255 * fade),), False, arc, 5)
        surface.blit(layer, (0, 0))
        blit_glow(surface, (x + self.dir * self.size * 0.6, self.y), self.size * 0.9, self.color, 0.6 * fade)


class SplitHalves(Effect):
    """Cible tranchée en diagonale : deux moitiés qui se décalent un instant puis se rejoignent."""

    def __init__(self, actor, life: float = 0.75) -> None:
        self.actor, self.life, self.t = actor, life, 0.0
        r = actor.rect
        img = getattr(actor, "image", None)
        if img is None:
            img = pygame.Surface(r.size, pygame.SRCALPHA)
            w, h = r.size
            pygame.draw.ellipse(img, STEEL + (255,), (w * 0.2, 0, w * 0.6, h * 0.45))
            pygame.draw.rect(img, STEEL + (255,), (w * 0.15, h * 0.3, w * 0.7, h * 0.7), border_radius=int(w * 0.2))
        w, h = img.get_size()
        a, b = (-10, h * 0.7), (w + 10, h * 0.3)
        self.top, self.bot = img.copy(), img.copy()
        pygame.draw.polygon(self.top, (0, 0, 0, 0), [a, b, (w + 10, h + 10), (-10, h + 10)])
        pygame.draw.polygon(self.bot, (0, 0, 0, 0), [a, b, (w + 10, -10), (-10, -10)])
        d = (Vector2(b) - Vector2(a)).normalize()
        self.n = Vector2(d.y, -d.x)
        self.a, self.b = Vector2(a), Vector2(b)
        self.size = (w, h)
        self.anchor = r.midbottom
        actor.visible = False

    def _done(self) -> None:
        self.actor.visible = True

    def update(self, dt: float) -> bool:
        self.t += dt
        if self.t >= self.life:
            self._done()
            return False
        return True

    def kill(self) -> None:
        self._done()
        self.dead = True

    def render(self, surface: pygame.Surface) -> None:
        t = self.t
        if t < 0.1:
            amp = ease("out_back", t / 0.1) * 22
        elif t < self.life - 0.25:
            amp = 22
        else:
            amp = 22 * (1 - ease("in_out_quad", (t - (self.life - 0.25)) / 0.25))
        w, h = self.size
        o = Vector2(self.anchor[0] - w / 2, self.anchor[1] - h)
        surface.blit(self.top, o + self.n * amp)
        surface.blit(self.bot, o - self.n * amp)
        if amp > 1:
            k = clamp01(amp / 22)
            pygame.draw.line(surface, scaled(WHITE, k), o + self.a, o + self.b, 4)
            blit_glow(surface, o + (self.a + self.b) / 2, 90 * k, RED, 0.8 * k)


class BreakText(Effect):
    """Texte qui flotte puis se brise en deux et tombe."""

    def __init__(self, text: str, pos, color=BLUE, size: int = 44, hold: float = 0.55) -> None:
        s = text_surface(text, size, color, 3)
        w, h = s.get_size()
        self.l = s.subsurface((0, 0, w // 2, h)).copy()
        self.r = s.subsurface((w // 2, 0, w - w // 2, h)).copy()
        self.pos, self.hold, self.t, self.w = Vector2(pos), hold, 0.0, w

    def update(self, dt: float) -> bool:
        self.t += dt
        return self.t < self.hold + 0.6

    def render(self, surface: pygame.Surface) -> None:
        t = self.t
        up = Vector2(0, -30 * ease("out_cubic", t / 0.5))
        if t < self.hold:
            sc = 1 + 0.25 * max(0.0, 1 - t / 0.15)
            for part, dx in ((self.l, -self.w / 4), (self.r, self.w / 4)):
                img = pygame.transform.rotozoom(part, 0, sc) if sc > 1.01 else part
                surface.blit(img, img.get_rect(center=self.pos + up + (dx * (sc if sc > 1 else 1), 0)))
            return
        k = (t - self.hold) / 0.6
        a = int(255 * clamp01(1 - k))
        for part, dx, rot in ((self.l, -self.w / 4, 1), (self.r, self.w / 4, -1)):
            img = pygame.transform.rotate(part, rot * 70 * k * k)
            img.set_alpha(a)
            p = self.pos + up + Vector2(dx + rot * -90 * k, 260 * k * k)
            surface.blit(img, img.get_rect(center=p))


class Reticle(Effect):
    """Réticule qui se resserre (et tourne) sur `pos`."""

    def __init__(self, pos, duration: float = 0.7, r0: float = 150.0, r1: float = 30.0, color=GOLD) -> None:
        self.pos, self.duration, self.r0, self.r1, self.color, self.t = Vector2(pos), duration, r0, r1, color, 0.0

    def update(self, dt: float) -> bool:
        self.t += dt
        return self.t < self.duration + 0.2

    def render(self, surface: pygame.Surface) -> None:
        p = clamp01(self.t / self.duration)
        r = lerp(self.r0, self.r1, ease("out_cubic", p))
        fade = clamp01(1 - (self.t - self.duration) / 0.2)
        col = scaled(self.color if p < 1 else WHITE, fade)
        c = (int(self.pos.x), int(self.pos.y))
        pygame.draw.circle(surface, col, c, int(r), 3)
        pygame.draw.circle(surface, scaled(col, 0.5), c, int(r * 1.35), 1)
        rot = (1 - p) * 90
        for i in range(4):
            d = polar(rot + i * 90)
            pygame.draw.line(surface, col, self.pos + d * (r * 0.6), self.pos + d * (r * 1.6), 3)
        pygame.draw.circle(surface, scaled(RED, fade), c, 4)
        blit_glow(surface, c, r * 1.2, self.color, 0.3 * p * fade)


class CoinFlight(Effect):
    """Pièces d'or qui volent de `src` vers `dst` sur des courbes décalées."""

    def __init__(self, src, dst_fn, count: int = 12) -> None:
        self.dst_fn = dst_fn
        self.t = 0.0
        s = Vector2(src)
        self.coins = [(s + Vector2(random.uniform(-25, 25), random.uniform(-40, 20)),
                       random.uniform(0.0, 0.35), random.uniform(0.45, 0.65), random.uniform(-110, -40))
                      for _ in range(count)]

    def update(self, dt: float) -> bool:
        self.t += dt
        return any(self.t < d + du for _, d, du, _ in self.coins)

    def render(self, surface: pygame.Surface) -> None:
        dst = self.dst_fn()
        for p0, delay, dur, lift in self.coins:
            k = (self.t - delay) / dur
            if not 0 <= k < 1:
                continue
            e = ease("in_out_quad", k)
            pos = p0.lerp(dst, e) + Vector2(0, lift * math.sin(math.pi * e))
            w = max(2, int(10 * abs(math.cos(self.t * 14 + delay * 20))))
            pygame.draw.ellipse(surface, GOLD, (pos.x - w / 2, pos.y - 5, w, 10))
            pygame.draw.ellipse(surface, (255, 235, 160), (pos.x - w / 4, pos.y - 3, max(1, w // 2), 5))
            blit_glow(surface, pos, 14, GOLD, 0.6)


class PotionPop(Effect):
    """Petite icône de potion (dessinée) et son nom, qui montent et s'estompent."""

    def __init__(self, name: str, pos, life: float = 1.4) -> None:
        label = text_surface(name, 22, PALE, 2)
        s = pygame.Surface((46 + label.get_width(), 50), pygame.SRCALPHA)
        pygame.draw.rect(s, PALE, (14, 2, 10, 12))
        pygame.draw.circle(s, BLUE, (19, 32), 15)
        pygame.draw.circle(s, WHITE, (19, 32), 15, 2)
        pygame.draw.circle(s, WHITE, (14, 27), 3)
        pygame.draw.rect(s, (200, 130, 60), (12, 0, 14, 5))
        s.blit(label, (42, 14))
        self.surf, self.pos, self.life, self.t = s, Vector2(pos), life, 0.0

    def update(self, dt: float) -> bool:
        self.t += dt
        return self.t < self.life

    def render(self, surface: pygame.Surface) -> None:
        k = self.t / self.life
        self.surf.set_alpha(int(255 * clamp01(min(1, (1 - k) * 3))))
        r = self.surf.get_rect(midtop=self.pos + Vector2(0, -40 * ease("out_cubic", k)))
        surface.blit(self.surf, r)


class Glint(Effect):
    """Éclat en étoile à quatre branches (reflet sur une lame)."""

    def __init__(self, pos, size: float = 90.0, life: float = 0.4, color=WHITE) -> None:
        self.pos, self.size, self.life, self.color, self.t = Vector2(pos), size, life, color, 0.0

    def update(self, dt: float) -> bool:
        self.t += dt
        return self.t < self.life

    def render(self, surface: pygame.Surface) -> None:
        p = self.t / self.life
        k = math.sin(math.pi * clamp01(p))
        L = self.size * k
        for ang, ln in ((0, 1.0), (90, 0.7), (45, 0.4), (135, 0.4)):
            d = polar(ang)
            pygame.draw.line(surface, scaled(self.color, k), self.pos - d * L * ln, self.pos + d * L * ln, 3 if ln > 0.5 else 2)
        blit_glow(surface, self.pos, self.size * 0.9 * k, self.color, 0.9 * k)


class RisingRing(Effect):
    """Anneau (ellipse) qui monte des pieds à la tête."""

    def __init__(self, feet, height: float, color=GOLD, radius: float = 70.0, life: float = 0.8) -> None:
        self.feet, self.h, self.color, self.r, self.life, self.t = Vector2(feet), height, color, radius, life, 0.0

    def update(self, dt: float) -> bool:
        self.t += dt
        return self.t < self.life

    def render(self, surface: pygame.Surface) -> None:
        p = clamp01(self.t / self.life)
        y = self.feet.y - self.h * ease("out_quad", p)
        a = math.sin(math.pi * p)
        r = self.r * (1 - 0.3 * p)
        rect = pygame.Rect(self.feet.x - r, y - r * 0.25, 2 * r, r * 0.5)
        pygame.draw.ellipse(surface, scaled(self.color, a * 0.5), rect.inflate(8, 4), 6)
        pygame.draw.ellipse(surface, scaled(WHITE, a), rect, 3)


# ----------------------------------------------------------------- compétences


@scripted("skill.soldier")
def soldier(c):
    """Omnislash : saut, 5 frappes-éclair depuis des angles différents, plongeon final, flash blanc."""
    me, tg = c.caster, _target(c)
    s = _face(me, tg)
    mid = c.center(tg)
    feet = c.feet(tg)
    angles = [200, 335, 150, 25, 250]
    state = {"prev": None}

    def ghost():
        c.spawn(AfterImage.of(me, color=ICE, life=0.45, alpha=170))

    def jump_out():
        ghost()

    def strike(k: int):
        def fn():
            ghost()
            a = angles[k]
            spot = feet + Vector2(math.cos(math.radians(a)) * 175, math.sin(math.radians(a)) * 55)
            me.offset = spot - Vector2(me.home)
            p0 = mid + (spot - feet) * 0.9 + Vector2(0, -30)
            p1 = 2 * mid - p0
            c.spawn(Slash.line(p0, p1, bulge=18 * (1 if k % 2 else -1), duration=0.07, width=24, life=0.28,
                               color=ICE, core=WHITE, glow_color=ICE))
            c.spawn(Slash.line(p0 * 1.0, p1, duration=0.06, width=8, life=0.2, color=WHITE, core=WHITE, delay=0.02))
            c.sound("slash")
            tg.flash(ICE, 0.06)
            c.spawn(ParticleEmitter(mid, "sparkle", count=7, speed=1.0, colors=[WHITE, ICE]))
            c.spawn(Shockwave(mid, ICE, 6, 60 + 8 * k, 0.2, 4))
            c.spawn(ScreenShake(3 + k, 0.1))
            tg.offset = Vector2(s * (7 if k % 2 else -5), -3 * k)
        return Seq(_pose(me, "windup"), 0.03, _pose(me, "strike", 0.14), Call(fn), 0.09)

    def dive_start():
        ghost()
        goal = c.approach(me, tg, gap=40)
        me.offset = goal + Vector2(-s * 30, -260)
        c.sound("charge")

    def finale(i, t):
        def fn():
            c.sound("slash_heavy")
            c.impact_now(i)
            tc = c.center(t)
            t.flash(WHITE, 0.2)
            c.spawn(FloatingText(str(c.value(i)), c.head(t) + Vector2(0, 18), GOLD, crit=True))
            c.spawn(Shockwave(tc, WHITE, 10, 260, 0.5, 14))
            c.spawn(Shockwave(tc, GOLD, 10, 190, 0.4, 8, delay=0.06))
            c.spawn(Shockwave(c.feet(t), ICE, 20, 300, 0.55, 6, squash=0.3))
            c.spawn(ParticleEmitter(tc, "sparkle", count=46, speed=2.2, colors=[WHITE, ICE, GOLD], size=1.3))
            c.spawn(ParticleEmitter(tc, "thunder", count=24, speed=1.0, colors=[WHITE, ICE]))
        return Seq(Call(fn), Anim(t, "offset", Vector2(s * 24, 0), 0.07, "out_quad"),
                   Anim(t, "offset", Vector2(), 0.3, "out_quad"))

    return Seq(
        c.add(ScreenTint(NAVY, 0.45, 0.2, 1.3, 0.4, layer="back")),
        _pose(me, "windup"),
        Par(c.sfx("charge"), Anim(me, "offset", Vector2(-s * 20, -300), 0.26, "in_out_quad"),
            Call(jump_out)),
        0.06,
        *[strike(k) for k in range(5)],
        0.04,
        _pose(me, "windup"),
        Call(dive_start),
        Par(Anim(me, "offset", c.approach(me, tg, gap=40), 0.13, "in_expo"),
            Seq(0.09, _pose(me, "strike", 0.35)),
            c.add(Beam(mid + Vector2(-s * 30, -300), mid, WHITE, width=26, life=0.3, attack=0.06))),
        Par(c.add(Flash(WHITE, 0.45, 1.0, layer="overlay")),
            c.add(ScreenShake(22, 0.5)),
            c.each(finale, stagger=0.05)),
        0.12,
        Par(Anim(me, "offset", Vector2(), 0.3, "in_out_quad"), _pose(me, "idle")),
    )


@scripted("skill.black_mage")
def black_mage_fire(c):
    """Feu : cercle magique rouge sous le mage, colonne de flammes SOUS la cible."""
    me, tg = c.caster, _target(c)

    def pillar(i, t):
        f = c.feet(t)

        def fn():
            c.spawn(Shockwave(f, FIRE, 10, 150, 0.5, 8, squash=0.3))
            c.spawn(MagicCircle(f, 80, RED, life=0.7, squash=0.3, points=5))
            c.spawn(LightColumn(f.x, f.y, 440, 130, FIRE, life=0.9))
            c.spawn(ParticleEmitter(f, "fire", rate=140, duration=0.55, radius=45, speed=1.5, size=1.4))
            c.spawn(ParticleEmitter(f - Vector2(0, 90), "fire", count=26, speed=1.8, radius=30, spread=120))
        return Seq(Call(fn), 0.12, c.hit(i, shake=12, color=FIRE, ring=False),
                   Anim(t, "offset", Vector2(0, -6), 0.08), Anim(t, "offset", Vector2(), 0.25))

    return Seq(
        _pose(me, "cast"),
        c.sfx("cast"),
        Par(c.add(MagicCircle(c.feet(me), 105, RED, life=1.0, squash=0.3, points=6)),
            c.add(ParticleEmitter(c.feet(me), "fire", rate=60, duration=0.8, radius=70, speed=0.5, size=0.7)),
            Anim(me, "offset", Vector2(0, -8), 0.5, "in_out_sine")),
        0.2,
        c.sfx("fire_pillar"),
        c.each(pillar, stagger=0.1),
        0.45,
        Par(Anim(me, "offset", Vector2(), 0.2, "out_quad"), _pose(me, "idle")),
    )


@scripted("skill.knight")
def knight_armor_break(c):
    """Brise-armure : l'épée se charge, frappe lourde, éclats de métal, « DÉF ↓ » qui se brise."""
    me, tg = c.caster, _target(c)
    s = _face(me, tg)
    go = c.approach(me, tg, gap=100)
    mid = c.center(tg)
    sword = Vector2(me.rect.centerx + s * 38, me.rect.centery - 30)
    orb = EnergyOrb(sword, 6, ICE, life=0.75, grow=55)

    def smash():
        c.sound("armor_break")
        c.spawn(GlassShards(mid, 26, colors=(STEEL, PALE, WHITE, ICE), size=(7, 20), speed=(220, 620), life=1.0,
                            angle=-90 - s * 25, spread=220))
        c.spawn(Slash.arc(mid + Vector2(-s * 12, 0), 55, -110 if s > 0 else -70, 60 if s > 0 else 120, ry=125,
                          duration=0.12, width=30, life=0.35, color=ICE, core=WHITE))
        c.spawn(BreakText("DÉF ↓", c.head(tg) + Vector2(0, -25), BLUE))

    return Seq(
        _pose(me, "windup"),
        c.sfx("charge"),
        Par(c.add(orb), Anim(me, "offset", Vector2(-s * 16, -4), 0.7, "in_out_quad"),
            c.add(ParticleEmitter(sword, "ice", rate=40, duration=0.6, radius=40, speed=0.35, attract=sword))),
        Anim(me, "offset", go, 0.14, "in_expo"),
        Call(smash), _pose(me, "strike", 0.35),
        Par(c.hit(0, shake=16, color=ICE, ring=False), _recoil(tg, s, 22),
            c.add(Shockwave(mid, ICE, 10, 150, 0.4, 10)), c.add(Shockwave(mid, WHITE, 6, 90, 0.3, 5))),
        0.55,
        Par(Anim(me, "offset", Vector2(), 0.35, "in_out_quad"), _pose(me, "idle")),
    )


@scripted("skill.monk")
def monk_chakra(c):
    """Chakra : méditation, anneau doré qui monte, pétales vers l'allié, soin vert."""
    me, tg = c.caster, _target(c)
    mc = c.center(me)
    tc = c.center(tg)
    petals = ParticleEmitter(mc, "holy", rate=45, duration=0.7, radius=30, speed=1.3, size=1.1,
                             colors=[GOLD, PALE, HOLY, (255, 190, 210)], attract=tc, attract_force=900, gravity=0)

    def heal():
        c.sound("heal")
        c.impact_now(0)
        c.damage_text_now(0, kind="heal")
        f = c.feet(tg)
        c.spawn(LightColumn(f.x, f.y, 330, 110, GREEN, life=0.9))
        c.spawn(ParticleEmitter(tc, "heal", count=26, radius=45, speed=1.1))
        c.spawn(Shockwave(f, GREEN, 15, 130, 0.6, 6, squash=0.3))

    return Seq(
        _pose(me, "cast"),
        c.sfx("chakra"),
        Par(Anim(me, "offset", Vector2(0, -22), 0.5, "in_out_sine"),
            c.add(MagicCircle(c.feet(me), 85, GOLD, life=1.3, squash=0.3, points=8)),
            c.add(RisingRing(c.feet(me), me.rect.height, GOLD, 75, 0.8)),
            Seq(0.35, c.add(RisingRing(c.feet(me), me.rect.height, WHITE, 60, 0.7)))),
        0.15,
        Par(c.add(petals), c.add(Glint(mc, 70, 0.4, GOLD)), Wait(0.7)),
        Call(heal),
        Par(Anim(me, "offset", Vector2(), 0.4, "in_out_sine"), _pose(me, "idle"), Wait(0.5)),
    )


@scripted("skill.thief")
def thief_steal(c):
    """Vol : ruée, main tendue, pièces vers le voleur, « +N gils » doré et potion éventuelle."""
    me, tg = c.caster, _target(c)
    s = _face(me, tg)
    go = c.approach(me, tg, gap=75)
    mid = c.center(tg)
    gil = c.ctx.extra.get("gil")
    if gil is None:
        gil = c.value(0)
    stolen = c.ctx.extra.get("stolen")

    def grab():
        hand = c.center(me) + Vector2(s * 55, -10)
        c.spawn(Slash.line(hand, mid, duration=0.07, width=9, life=0.2, color=PALE, core=WHITE))
        c.spawn(Glint(mid + Vector2(-s * 20, -10), 60, 0.3, GOLD))

    def loot():
        c.sound("coins")
        c.spawn(ParticleEmitter(mid, "coins", count=16, speed=0.8))
        c.spawn(CoinFlight(mid, lambda: c.center(me) + Vector2(0, -20), 14))
        head = c.head(me) + Vector2(0, -6)
        if gil:
            c.spawn(FloatingText(f"+{gil} gils", head, GOLD, size=32, kind="free", delay=0.4))
        else:
            c.spawn(FloatingText("Rien à voler", head, PALE, size=26, kind="free", delay=0.5))
        if stolen:
            c.spawn(PotionPop(str(stolen), head + Vector2(0, 36)))

    return Seq(
        _pose(me, "windup"),
        Anim(me, "offset", Vector2(-s * 14, 4), 0.12, "out_quad"),
        c.sfx("dagger"),
        Anim(me, "offset", go, 0.17, "out_expo"),
        Call(grab), _pose(me, "strike", 0.3),
        Par(c.hit(0, shake=3, text=False, color=GOLD, ring=False), _recoil(tg, s, 10)),
        0.1,
        Call(loot),
        0.2,
        Par(Anim(me, "offset", Vector2(), 0.3, "in_out_quad"), _pose(me, "idle")),
        0.4 if stolen else 0.2,
    )


@scripted("skill.samurai")
def samurai_blade(c):
    """Lame bannie : écran sombre, éclat sur la garde, croissant rouge géant, cible fendue en retard."""
    me, tg = c.caster, _target(c)
    s = _face(me, tg)
    guard = Vector2(me.rect.centerx + s * 36, me.rect.centery - 6)
    mid = c.center(tg)

    def cut(i, t):
        tc = c.center(t)

        def fn():
            c.sound("katana_draw")
            c.spawn(Slash.line(tc + Vector2(-s * 140, 70), tc + Vector2(s * 140, -70), duration=0.08, width=9,
                               life=0.4, color=WHITE, core=WHITE, glow_color=RED))
            c.spawn(SplitHalves(t, 0.55))
            c.on_end(lambda: setattr(t, "visible", True))
            c.hit_now(i, shake=18, flash=False, ring=False, color=RED, sparks=None)
            c.spawn(Shockwave(tc, RED, 10, 170, 0.45, 8))
            c.spawn(ParticleEmitter(tc, "thunder", count=20, speed=1.0, colors=[RED, WHITE, (255, 150, 100)]))
        return Seq(Call(fn))

    return Seq(
        c.add(ScreenTint(BLACK_, 0.7, 0.25, 1.6, 0.5, layer="back")),
        0.2,
        _pose(me, "windup"),
        Par(c.sfx("katana_draw"), c.add(Glint(guard, 110, 0.45, WHITE)),
            Anim(me, "offset", Vector2(-s * 8, 0), 0.4, "in_out_quad")),
        0.12,
        Par(c.sfx("wind_slash"), Anim(me, "offset", Vector2(s * 10, 0), 0.08), _pose(me, "strike", 0.5),
            c.add(Crescent(mid.y - 10, guard.x, s, 0.5, 250, RED))),
        0.3,
        c.each(cut, stagger=0.06),
        0.5,
        Par(Anim(me, "offset", Vector2(), 0.25, "out_quad"), _pose(me, "idle")),
    )


BLACK_ = (0, 0, 0)


@scripted("skill.archer")
def archer_precise(c):
    """Tir précis : réticule qui se resserre, flèche chargée de lumière qui perce en rayon, critique."""
    me, tg = c.caster, _target(c)
    s = _face(me, tg)
    mid = c.center(tg)
    bow = Vector2(me.rect.centerx + s * 40, me.rect.centery - 12)
    far = mid + (mid - bow).normalize() * 420

    def release():
        c.sound("arrow_power")
        c.spawn(Beam(bow, far, GOLD, width=34, life=0.4, attack=0.05))
        c.spawn(Beam(bow, far, WHITE, width=12, life=0.3, attack=0.04))
        c.spawn(Projectile(bow, mid, 0.14, "arrow", color=GOLD, size=14, easing="linear"))

    def pierce():
        c.hit_now(0, shake=15, color=GOLD, text=False, ring=False, sparks=None)
        c.spawn(FloatingText(str(c.value(0)), c.head(tg) + Vector2(0, 18), GOLD, crit=True))
        c.spawn(Shockwave(mid, GOLD, 8, 140, 0.4, 8))
        c.spawn(Shockwave(mid, WHITE, 8, 80, 0.3, 5))
        c.spawn(ParticleEmitter(mid, "sparkle", count=30, speed=1.6, colors=[WHITE, GOLD]))
        c.spawn(Flash(GOLD, 0.2, 0.5, layer="overlay", additive=True))

    return Seq(
        c.add(ScreenTint(BLACK_, 0.35, 0.3, 0.9, 0.3, layer="back")),
        _pose(me, "windup"),
        Par(c.sfx("charge"), c.add(Reticle(mid, 0.75, 150, 28, GOLD)),
            c.add(EnergyOrb(bow, 5, GOLD, life=0.85, grow=40)),
            Anim(me, "offset", Vector2(-s * 8, 0), 0.8, "out_quad")),
        0.12,
        Par(Call(release), _pose(me, "strike", 0.35), Anim(me, "offset", Vector2(s * 6, 0), 0.05)),
        0.13,
        Call(pierce),
        Par(_recoil(tg, s, 20), Anim(me, "offset", Vector2(), 0.3, "out_quad")),
        0.45,
        _pose(me, "idle"),
    )


@scripted("skill.ninja")
def ninja_throw(c):
    """Lancer (tous) : saut hors champ, pluie de shurikens sur tous les ennemis, impacts en cascade."""
    me = c.caster
    sky_x = me.home.x + 60
    n = 3

    def rain(i, t):
        tc = c.center(t)

        def throw(k: int):
            last = k == n - 1

            def fn():
                c.sound("shuriken")
                start = Vector2(sky_x + random.uniform(-40, 40), -30)
                end = tc + Vector2(random.uniform(-25, 25), random.uniform(-40, 30))

                def land():
                    if last:
                        c.hit_now(i, shake=6, color=WHITE)
                    else:
                        t.flash(WHITE, 0.05)
                        c.spawn(ParticleEmitter(end, "sparkle", count=5, speed=0.8))
                        c.spawn(Shockwave(end, STEEL, 4, 35, 0.18, 3))
                c.spawn(Projectile(start, end, 0.3, "shuriken", color=STEEL, size=11, easing="in_quad",
                                   spin=28, wobble=(18, 1.5), on_arrive=land))
            return Seq(Call(fn), 0.1)

        return Seq(*[throw(k) for k in range(n)], 0.3)

    def volley(i, t):
        return Seq(_pose(me, "strike", 0.2), rain(i, t), _pose(me, "windup"))

    def vanish():
        c.spawn(AfterImage.of(me, color=STEEL, life=0.4, alpha=170))
        c.spawn(ParticleEmitter(me.home, "dust", count=10, spread=140))

    def land_back():
        c.spawn(ParticleEmitter(me.home, "dust", count=14, spread=170, speed=1.3))
        c.spawn(Shockwave(c.feet(me), PALE, 10, 90, 0.3, 4, squash=0.3))

    return Seq(
        _pose(me, "windup"),
        Par(Call(vanish), c.sfx("shuriken"), Anim(me, "offset", Vector2(40, -620), 0.3, "in_cubic")),
        0.1,
        c.each(volley, stagger=0.18),
        0.15,
        Par(Anim(me, "offset", Vector2(), 0.35, "out_bounce"), _pose(me, "idle")),
        Call(land_back),
        0.25,
    )
