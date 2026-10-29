"""Sorts : `spell.fire`, `spell.ice`, `spell.thunder`, `spell.cure`."""
from __future__ import annotations

import math
import random

import pygame
from pygame import Vector2

from . import Anim, Call, Par, Seq, scripted
from .. import (EnergyOrb, Effect, Flash, GlassShards, Lightning, MagicCircle, ParticleEmitter, Projectile,
                ScreenTint, Shockwave, BLACK, FIRE, GOLD, GREEN, ICE, PALE, THUNDER, WHITE,
                blit_glow, clamp01, ease, mix)


# ----------------------------------------------------------------- briques locales


class IceCrystals(Effect):
    """Cristaux qui se forment autour d'un point puis se referment ; `kill()` pour les briser."""

    def __init__(self, center, radius: float = 90.0, count: int = 9, form: float = 0.55, seed: int = 0) -> None:
        rng = random.Random(seed)
        self.c, self.r, self.form, self.t = Vector2(center), radius, form, 0.0
        self.items = [(i / count * 360 + rng.uniform(-14, 14), rng.uniform(0.8, 1.25), rng.uniform(0.0, 0.25))
                      for i in range(count)]
        self.layer = "front"

    def update(self, dt: float) -> bool:
        self.t += dt
        return not self.dead

    def render(self, surface: pygame.Surface) -> None:
        for ang, size, lag in self.items:
            k = ease("out_cubic", clamp01((self.t - lag) / self.form))
            if k <= 0:
                continue
            d = Vector2(math.cos(math.radians(ang)), math.sin(math.radians(ang)) * 0.8)
            base = self.c + d * self.r * (1.7 - 0.7 * k)  # les cristaux se referment
            length, wid = 54 * size * k, 13 * size * k
            n = Vector2(-d.y, d.x) * wid
            pts = [base - d * length * 0.5, base + n, base + d * length * 0.5, base - n]
            blit_glow(surface, base, 34 * size * k, ICE, 0.45)
            pygame.draw.polygon(surface, mix(ICE, WHITE, 0.55), pts)
            pygame.draw.polygon(surface, ICE, pts, 3)
            pygame.draw.line(surface, WHITE, pts[0], base, 2)


class HealSpiral(Effect):
    """Spirales de lueurs vertes qui montent autour d'un acteur, avec halo doux."""

    def __init__(self, actor, life: float = 1.3, motes: int = 16) -> None:
        self.actor, self.life, self.n, self.t = actor, life, motes, 0.0
        self.layer = "front"

    def update(self, dt: float) -> bool:
        self.t += dt
        return self.t < self.life

    def render(self, surface: pygame.Surface) -> None:
        r = self.actor.rect
        p = clamp01(self.t / self.life)
        fade = min(1.0, p * 6) * clamp01((1 - p) * 3.5)
        blit_glow(surface, r.center, max(r.w, r.h) * 0.75, GREEN, 0.55 * fade)
        rad = r.w * 0.55
        for strand in range(2):
            for i in range(self.n):
                u = (i / self.n + self.t * 0.8) % 1.0
                ang = u * 7.5 + strand * math.pi
                pos = Vector2(r.centerx + math.cos(ang) * rad * (1 - 0.25 * u),
                              r.bottom - u * r.h * 1.1 + math.sin(ang) * rad * 0.22)
                blit_glow(surface, pos, 12 + 6 * (1 - u), mix(GREEN, WHITE, 0.4 * u), fade * (1 - 0.5 * u))


# ----------------------------------------------------------------- sorts


@scripted("spell.fire")
def fire(c):
    """Feu : cercle magique, boule spiralée, explosion de braises, lueur orange."""
    me = c.caster
    start = c.center(me) + Vector2(0, -20)

    def one(i, t):
        end = c.center(t)

        def boom():
            c.hit_now(i, color=FIRE, shake=9)
            c.spawn(EnergyOrb(end, 120, FIRE, life=0.5))
            c.spawn(ParticleEmitter(end, "fire", count=36, spread=360, angle=-90, speed=1.5, radius=14))
            c.spawn(ParticleEmitter(end, "sparkle", count=14, spread=360, speed=1.6,
                                    colors=[FIRE, GOLD, WHITE], gravity=300))
            c.spawn(Shockwave(end, FIRE, 20, 150, 0.4, 10, squash=0.7))

        return Seq(Call(c.sound, "fire"),
                   c.add(Projectile(start, end, 0.55, "orb", FIRE, 20, arc=60, wobble=(26, 3), easing="in_quad")),
                   0.55, Call(boom))

    return Seq(
        Call(me.set_pose, "cast"), c.sfx("cast"),
        Par(c.add(MagicCircle(c.feet(me), 100, FIRE, life=0.9, squash=0.3, points=5)),
            Anim(me, "scale", 1.05, 0.25, "out_quad"),
            c.add(ParticleEmitter(c.center(me), "fire", rate=40, duration=0.5, radius=40, speed=0.5))),
        Anim(me, "scale", 1.0, 0.12),
        c.each(one, stagger=0.2),
        Call(me.set_pose, "idle"),
        c.add(Flash(FIRE, 0.35, 0.5, additive=True)),
        0.5,
    )


@scripted("spell.ice")
def ice(c):
    """Glace : cristaux qui se forment et se referment, éclats, brume givrée."""
    me = c.caster
    crystals: dict[int, IceCrystals] = {}

    def form(i, t):
        def start():
            crystals[i] = c.spawn(IceCrystals(c.center(t), max(t.rect.w, t.rect.h) * 0.55, seed=i + 3))
            c.spawn(ParticleEmitter(c.feet(t), "ice", rate=30, duration=0.6, radius=40, spread=40, speed=0.4,
                                    gravity=-40))

        def shatter():
            if i in crystals:
                crystals[i].kill()
            ctr = c.center(t)
            c.hit_now(i, color=ICE, shake=8)
            c.sound("ice_shatter")
            c.spawn(GlassShards(ctr, 34, (ICE, WHITE, PALE), (6, 17), (200, 560), 0.9, 700))
            c.spawn(ParticleEmitter(ctr, "ice", count=24, speed=1.4))
            c.spawn(ParticleEmitter(c.feet(t), "dust", count=26, radius=60, spread=120, colors=[ICE, PALE, WHITE],
                                    gravity=-25, speed=0.5, life=1.8, size=1.6))
            c.spawn(Shockwave(ctr, ICE, 10, 130, 0.35, 6))

        return Seq(Call(c.sound, "ice_form"), Call(start), 0.75, Call(shatter))

    return Seq(
        Call(me.set_pose, "cast"), c.sfx("cast"),
        Par(c.add(MagicCircle(c.feet(me), 95, ICE, life=0.8, squash=0.3, points=6)),
            Anim(me, "offset", Vector2(0, -8), 0.25, "out_quad")),
        Anim(me, "offset", Vector2(), 0.15),
        c.each(form, stagger=0.15),
        Call(me.set_pose, "idle"),
        0.5,
    )


@scripted("spell.thunder")
def thunder(c):
    """Foudre : écran sombre, éclair ramifié unique à chaque lancer, flash jaune."""
    me = c.caster
    rng = random.Random()

    def strike(i, t):
        end = c.center(t)
        top = Vector2(end.x + rng.uniform(-60, 60), -30)

        def bolt():
            c.sound("thunder")
            c.spawn(Lightning(top, end, THUNDER, 9, 0.5, branches=5, jag=0.22), "overlay")
            c.spawn(Lightning(top + Vector2(25, 0), end, WHITE, 3, 0.35, branches=2, jag=0.15), "overlay")
            if i == 0:  # un seul flash d'écran par lancer
                c.spawn(Flash(THUNDER, 0.3, 0.6, additive=True))
            c.hit_now(i, color=THUNDER, shake=11)
            c.spawn(ParticleEmitter(end, "thunder", count=30, speed=1.2))
            c.spawn(Shockwave(c.feet(t), THUNDER, 10, 120, 0.3, 6, squash=0.3))

        return Seq(Call(bolt), Anim(t, "offset", Vector2(rng.choice((-6, 6)), 0), 0.04),
                   Anim(t, "offset", Vector2(), 0.2))

    return Seq(
        Call(me.set_pose, "cast"), c.sfx("cast"),
        Par(c.add(ScreenTint(BLACK, 0.6, 0.3, 0.8, 0.4)),
            c.add(MagicCircle(c.feet(me), 90, THUNDER, life=0.8, squash=0.3, points=4)),
            Anim(me, "offset", Vector2(0, -10), 0.3, "out_quad")),
        Anim(me, "offset", Vector2(), 0.1),
        0.15,
        c.each(strike, stagger=0.18),
        Call(me.set_pose, "idle"),
        0.5,
    )


@scripted("spell.cure")
def cure(c):
    """Soin : spirales vertes, étincelles, halo ; +N vert."""
    me = c.caster

    def heal(i, t):
        def burst():
            c.impact_now(i)
            c.damage_text_now(i, text=f"+{c.value(i)}", kind="heal")
            c.spawn(ParticleEmitter(c.center(t), "heal", count=22, radius=40, speed=1.2))
            c.spawn(ParticleEmitter(c.center(t), "sparkle", count=14, radius=50, colors=[GREEN, WHITE], speed=1.0))
            c.spawn(Shockwave(c.feet(t), GREEN, 20, 120, 0.5, 6, squash=0.3))
            t.flash(GREEN, 0.2)

        return Seq(c.sfx("heal"), c.add(HealSpiral(t)),
                   c.add(MagicCircle(c.feet(t), 80, GREEN, life=1.1, squash=0.3, points=6)),
                   0.7, Call(burst))

    return Seq(
        Call(me.set_pose, "cast"),
        Anim(me, "scale", 1.04, 0.15, "out_quad"),
        Anim(me, "scale", 1.0, 0.15),
        c.each(heal, stagger=0.12),
        Call(me.set_pose, "idle"),
        0.8,
    )
