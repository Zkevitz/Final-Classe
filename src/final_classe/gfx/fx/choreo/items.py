"""Objets, défense et états : `item.*`, `action.defend`, `state.ko_hero`, `state.ko_monster`, `state.level_up`."""
from __future__ import annotations

import math
import random

import pygame
from pygame import Vector2

from . import Anim, Call, FloatingText, Par, Seq, scripted
from .. import (BLUE, Effect, FIRE, GOLD, GREEN, HOLY, HexShield, ICE, LightColumn, MagicCircle, ParticleEmitter,
                PALE, Shockwave, THUNDER, WHITE, blit_glow, clamp01, ease, mix, RED)

RAINBOW = [FIRE, THUNDER, GREEN, ICE, HOLY, BLUE, WHITE]


# ----------------------------------------------------------------- briques locales

_BOTTLES: dict[tuple, pygame.Surface] = {}


def bottle(color) -> pygame.Surface:
    """Icône de fiole (verre, liquide coloré, bouchon), mise en cache par couleur."""
    key = tuple(color)
    s = _BOTTLES.get(key)
    if s is None:
        s = pygame.Surface((34, 46), pygame.SRCALPHA)
        glass = (232, 236, 248, 90)
        pygame.draw.circle(s, glass, (17, 29), 14)
        pygame.draw.rect(s, glass, (12, 6, 10, 14))
        pygame.draw.circle(s, color + (255,), (17, 31), 11)
        pygame.draw.rect(s, color + (255,), (13, 16, 8, 6))
        pygame.draw.circle(s, mix(color, WHITE, 0.55) + (255,), (13, 27), 3)
        pygame.draw.circle(s, WHITE + (255,), (17, 29), 14, 2)
        pygame.draw.rect(s, WHITE + (255,), (12, 6, 10, 14), 2)
        pygame.draw.rect(s, (160, 110, 70, 255), (11, 1, 12, 6), border_radius=2)
        _BOTTLES[key] = s
    return s


class Vial(Effect):
    """Fiole lancée en l'air : arc de `start` à `end`, qui tournoie, avec une lueur."""

    def __init__(self, start, end, color, duration: float = 0.6, height: float = 120.0, spins: float = 2.0) -> None:
        self.p0, self.p1, self.color = Vector2(start), Vector2(end), color
        self.d, self.h, self.spins, self.t = max(1e-3, duration), height, spins, 0.0
        self.layer = "front"

    def update(self, dt: float) -> bool:
        self.t += dt
        return self.t < self.d

    def render(self, surface: pygame.Surface) -> None:
        k = clamp01(self.t / self.d)
        pos = self.p0.lerp(self.p1, ease("in_out_quad", k))
        pos.y -= math.sin(k * math.pi) * self.h
        blit_glow(surface, pos, 30, self.color, 0.5)
        img = pygame.transform.rotozoom(bottle(self.color), k * 360 * self.spins, 1.0)
        surface.blit(img, img.get_rect(center=pos))


class Feather(Effect):
    """Plume dorée qui descend en virevoltant de `start` à `end`."""

    def __init__(self, start, end, duration: float = 1.0) -> None:
        self.p0, self.p1, self.d, self.t = Vector2(start), Vector2(end), max(1e-3, duration), 0.0
        self.layer = "front"
        s = pygame.Surface((22, 70), pygame.SRCALPHA)
        pygame.draw.ellipse(s, WHITE + (255,), (2, 0, 18, 60))
        pygame.draw.ellipse(s, GOLD + (255,), (2, 0, 18, 60), 3)
        pygame.draw.line(s, FIRE + (255,), (11, 4), (11, 69), 3)
        for y in range(10, 50, 9):
            pygame.draw.line(s, GOLD + (255,), (11, y + 6), (4, y), 2)
            pygame.draw.line(s, GOLD + (255,), (11, y + 6), (18, y), 2)
        self.img = s

    def update(self, dt: float) -> bool:
        self.t += dt
        return self.t < self.d

    def render(self, surface: pygame.Surface) -> None:
        k = clamp01(self.t / self.d)
        e = ease("out_quad", k)
        sway = math.sin(k * math.pi * 4.5) * 46 * (1 - e)
        pos = self.p0.lerp(self.p1, e) + Vector2(sway, 0)
        blit_glow(surface, pos, 36, GOLD, 0.55 * (1 - 0.4 * k))
        img = pygame.transform.rotozoom(self.img, math.cos(k * math.pi * 4.5) * 35 * (1 - e), 1.0)
        surface.blit(img, img.get_rect(center=pos))


def _origin(c, t) -> Vector2:
    """Point de départ d'un lancer : la tête du lanceur (au-dessus de lui s'il se soigne lui-même)."""
    return c.head(c.caster) + Vector2(0, -10 if c.caster is not t else -40)


def _vial_step(c, i, t, color, burst, flight: float = 0.6):
    """Lance une fiole sur `t` puis appelle `burst()` à l'arrivée."""
    end = c.head(t) + Vector2(0, -6)
    return Seq(c.add(Vial(_origin(c, t), end, color, flight, 130)), flight, Call(burst))


# ----------------------------------------------------------------- objets


@scripted("item.potion")
def potion(c):
    """Potion : fiole verte lancée en l'air, éclat, bulles vertes qui montent."""
    def one(i, t):
        def burst():
            c.impact_now(i)
            c.damage_text_now(i, text=f"+{c.value(i)}", kind="heal")
            ctr = c.center(t)
            c.spawn(ParticleEmitter(c.head(t), "sparkle", count=14, radius=14, colors=[WHITE, GREEN, PALE], speed=1.3))
            c.spawn(ParticleEmitter(ctr, "heal", rate=26, duration=0.7, radius=max(20, t.rect.w * 0.3), speed=0.9))
            c.spawn(Shockwave(c.head(t), GREEN, 8, 70, 0.3, 5))
            t.flash(GREEN, 0.2)

        return Seq(Call(c.sound, "potion"), _vial_step(c, i, t, GREEN, burst))

    return Seq(Call(c.caster.set_pose, "cast"), c.each(one, stagger=0.1), Call(c.caster.set_pose, "idle"), 0.9)


@scripted("item.ether")
def ether(c):
    """Éther : fiole bleue, particules violettes et bleues, « +N PM » bleu."""
    def one(i, t):
        def burst():
            c.impact_now(i)
            c.damage_text_now(i, text=f"+{c.value(i)} PM", kind="mp")
            ctr = c.center(t)
            c.spawn(ParticleEmitter(c.head(t), "sparkle", count=16, radius=14, colors=[BLUE, HOLY, WHITE], speed=1.3))
            c.spawn(ParticleEmitter(ctr, "holy", rate=26, duration=0.7, radius=max(20, t.rect.w * 0.3),
                                    colors=[BLUE, HOLY, (190, 215, 255)], speed=1.1))
            c.spawn(Shockwave(c.head(t), BLUE, 8, 80, 0.35, 5))
            t.flash(BLUE, 0.2)

        return Seq(Call(c.sound, "potion"), _vial_step(c, i, t, BLUE, burst))

    return Seq(Call(c.caster.set_pose, "cast"), c.each(one, stagger=0.1), Call(c.caster.set_pose, "idle"), 0.9)


@scripted("item.phoenix_down")
def phoenix_down(c):
    """Plume de phénix : descend en virevoltant, anneau de flammes douces, le héros se relève."""
    def one(i, t):
        top = c.head(t) + Vector2(0, -170)
        land = c.center(t)

        def revive():
            c.impact_now(i)
            c.sound("revive")
            c.damage_text_now(i, text=f"+{c.value(i)}", kind="heal")
            c.spawn(Shockwave(c.feet(t), FIRE, 20, 150, 0.6, 9, squash=0.3))
            c.spawn(Shockwave(c.feet(t), GOLD, 10, 110, 0.5, 6, squash=0.3, delay=0.08))
            c.spawn(ParticleEmitter(c.feet(t), "fire", count=34, radius=60, spread=50, speed=0.7,
                                    colors=[GOLD, (255, 170, 60), WHITE]))
            c.spawn(ParticleEmitter(land, "sparkle", count=18, radius=40, colors=[GOLD, WHITE], speed=1.0))
            t.tint = None
            t.flash(GOLD, 0.25)

        return Seq(
            c.add(Feather(top, land, 1.0)),
            1.0,
            Call(revive),
            Call(t.set_pose, "hurt"),
            Par(Anim(t, "rotation", 0.0, 0.35, "out_back"), Anim(t, "offset", Vector2(), 0.35, "out_back"),
                Anim(t, "scale", 1.0, 0.35, "out_back")),
            Call(t.set_pose, "idle"),
        )

    return Seq(Call(c.caster.set_pose, "cast"), c.each(one, stagger=0.1), Call(c.caster.set_pose, "idle"), 0.6)


@scripted("item.elixir")
def elixir(c):
    """Élixir : fiole dorée, explosion d'étincelles arc-en-ciel, PV et PM au maximum."""
    def one(i, t):
        def burst():
            c.impact_now(i)
            c.sound("elixir")
            ctr = c.center(t)
            c.spawn(ParticleEmitter(ctr, "sparkle", count=60, radius=20, colors=RAINBOW, speed=2.2, size=1.3))
            c.spawn(ParticleEmitter(ctr, "sparkle", rate=40, duration=0.8, radius=50, colors=RAINBOW, speed=0.8,
                                    angle=-90, spread=90))
            c.spawn(Shockwave(ctr, GOLD, 10, 160, 0.5, 10))
            c.spawn(Shockwave(ctr, WHITE, 5, 110, 0.35, 5))
            c.spawn(FloatingText("PV / PM MAX", c.head(t) + Vector2(0, -14), GOLD, 30, kind="free"))
            c.damage_text_now(i, text=f"+{c.value(i)}", kind="heal", delay=0.15)
            t.flash(GOLD, 0.25)

        return Seq(Call(c.sound, "potion"), _vial_step(c, i, t, GOLD, burst, 0.65))

    return Seq(Call(c.caster.set_pose, "cast"), c.each(one, stagger=0.1), Call(c.caster.set_pose, "idle"), 1.0)


# ----------------------------------------------------------------- défense


@scripted("action.defend")
def defend(c):
    """Défense : cercle bleuté au sol, bulle hexagonale qui reste (tag `shield:<id>`)."""
    me = c.caster
    feet = c.feet(me)
    tag = f"shield:{id(me)}"

    def raise_shield():
        c.fx.kill(tag)
        c.spawn(HexShield(me, ICE, tag=tag), "front", tag)

    c.on_end(lambda: me.set_pose("idle"))  # fin ou skip : retour à la pose de base (la bulle reste)
    return Seq(
        Call(me.set_pose, "ready"),
        c.sfx("defend"),
        Par(c.add(MagicCircle(feet, 90, ICE, life=0.9, squash=0.3, points=6)),
            Anim(me, "scale", 0.94, 0.15, "out_quad")),
        Call(raise_shield),
        Par(c.add(Shockwave(feet, ICE, 20, 140, 0.45, 6, squash=0.3)),
            Anim(me, "scale", 1.0, 0.25, "out_back"),
            c.add(ParticleEmitter(c.center(me), "sparkle", count=14, radius=50, colors=[WHITE, ICE]))),
        0.35,
    )


# ----------------------------------------------------------------- états


@scripted("state.ko_monster")
def ko_monster(c):
    """K.O. monstre : flash blanc, puis fondu et dissolution en particules qui montent."""
    def one(i, t):
        rng = random.Random(i)
        r = t.rect

        def puff():
            p = Vector2(rng.uniform(r.left, r.right), rng.uniform(r.top, r.bottom))
            c.spawn(ParticleEmitter(p, "dust", count=7, radius=14, angle=-90, spread=50, speed=0.7,
                                    colors=[PALE, WHITE, ICE], gravity=-140, life=1.4))
            c.spawn(ParticleEmitter(p, "sparkle", count=2, radius=10, angle=-90, spread=60, speed=0.5,
                                    colors=[WHITE], gravity=-120))

        steps = [Call(c.sound, "ko_monster"), Call(t.flash, WHITE, 0.3), Anim(t, "scale", 1.04, 0.12)]
        dissolve = Par(Anim(t, "alpha", 0, 0.85, "in_quad"),
                       Seq(*[Seq(Call(puff), 0.06) for _ in range(14)]),
                       Anim(t, "offset", Vector2(0, -16), 0.85, "out_quad"))
        return Seq(*steps, 0.1, dissolve)

    return Seq(c.each(one, stagger=0.1), 0.25)


@scripted("state.ko_hero", reset=False)
def ko_hero(c):
    """K.O. héros : il s'agenouille (rotation, affaissement) et grisonne ; la pose reste."""
    def one(i, t):
        gray = (115, 118, 135)
        return Seq(
            Call(c.sound, "ko_hero"),
            Call(t.flash, RED, 0.15),
            Par(Anim(t, "rotation", 16.0, 0.45, "out_back"),
                Anim(t, "offset", Vector2(5, 14), 0.45, "out_quad"),
                Anim(t, "scale", 0.93, 0.45, "out_quad"),
                Seq(0.1, Call(setattr, t, "tint", gray)),
                c.add(ParticleEmitter(c.feet(t), "dust", count=12, radius=30, spread=160, speed=0.7))),
        )

    return Seq(c.each(one, stagger=0.1), 0.3)


@scripted("state.level_up")
def level_up(c):
    """Niveau supérieur : colonne de lumière dorée, étincelles, « NIVEAU ! »."""
    def one(i, t):
        def go():
            c.spawn(LightColumn(t.rect.centerx, t.rect.bottom, 560, 130, GOLD, 1.3))
            c.spawn(Shockwave(c.feet(t), GOLD, 20, 170, 0.6, 9, squash=0.3))
            c.spawn(ParticleEmitter(c.feet(t), "sparkle", rate=50, duration=0.9, radius=t.rect.w * 0.4,
                                    angle=-90, spread=30, speed=2.4, colors=[GOLD, WHITE, (255, 244, 200)],
                                    gravity=-60))
            c.spawn(FloatingText("NIVEAU !", c.head(t) + Vector2(0, -22), GOLD, 46, kind="free", life=1.6,
                                 delay=0.25))

        return Seq(Call(c.sound, "level_up"), Call(go),
                   Anim(t, "scale", 1.08, 0.2, "out_back"), Anim(t, "scale", 1.0, 0.3, "in_out_quad"))

    return Seq(c.each(one, stagger=0.1), 1.0)
