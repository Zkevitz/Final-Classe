"""Chorégraphies d'exemple : `generic` (repli de `play`) et `action.defend`."""
from __future__ import annotations

import math

from pygame import Vector2

from . import Anim, Call, Par, Seq, scripted
from .. import (HexShield, ICE, MagicCircle, ParticleEmitter, PALE, Shockwave, Slash, WHITE)


@scripted("generic")
def generic(c):
    """Attaque générique : armer, élan, entaille, impact, retour."""
    me = c.caster
    tg = c.targets[0] if c.targets else me
    away = Vector2(-1 if tg.home.x > me.home.x else 1, 0)
    go = c.approach(me, tg, gap=90)
    mid = c.center(tg)
    slash = Slash.arc(mid, 85, -110, 50, ry=105, duration=0.14, width=22, color=PALE, glow_color=ICE)
    dust = ParticleEmitter(me.home, "dust", count=8, spread=140)

    def strike(i, t):
        return Seq(c.hit(i), Anim(t, "offset", -away * 14, 0.06),
                   Anim(t, "offset", Vector2(), 0.2, "out_quad"))

    return Seq(
        Par(Anim(me, "offset", away * 22, 0.14, "out_quad"), c.add(dust)),
        c.sfx("slash"),
        Anim(me, "offset", go, 0.16, "out_back"),
        c.add(slash),
        c.each(strike, stagger=0.08),
        0.12,
        Anim(me, "offset", Vector2(), 0.32, "in_out_quad"),
    )


@scripted("action.defend")
def defend(c):
    """Défense : cercle bleuté au sol, bulle hexagonale qui reste (tag `shield:<id>`)."""
    me = c.caster
    feet = c.feet(me)
    tag = f"shield:{id(me)}"

    def raise_shield():
        c.fx.kill(tag)
        c.spawn(HexShield(me, ICE, tag=tag), "front", tag)

    return Seq(
        Call(c.sound, "defend"),
        Par(c.add(MagicCircle(feet, 90, ICE, life=0.9, squash=0.3, points=6)),
            Anim(me, "scale", 0.94, 0.15, "out_quad")),
        Call(raise_shield),
        Par(c.add(Shockwave(feet, ICE, 20, 140, 0.45, 6, squash=0.3)),
            Anim(me, "scale", 1.0, 0.25, "out_back"),
            c.add(ParticleEmitter(c.center(me), "sparkle", count=14, radius=50, colors=[WHITE, ICE]))),
        0.35,
    )
