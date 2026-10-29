"""Attaques de base (une par job + monstre) : docs/ANIMATIONS.md §1."""
from __future__ import annotations

import random

from pygame import Vector2

from . import Anim, Call, Par, Seq, Wait, scripted
from .. import (AfterImage, Beam, FloatingText, ICE, GOLD, PALE, ParticleEmitter, Projectile, RED, ScreenShake,
                Shockwave, Slash, STEEL, WHITE)


def _face(me, tg) -> int:
    """+1 si la cible est à droite de l'attaquant, -1 sinon."""
    return 1 if tg.home.x > me.home.x else -1


def _recoil(t, s: int, px: float = 14.0):
    """Recul de la cible (poussée dans le sens de l'attaque) puis retour."""
    return Seq(Anim(t, "offset", Vector2(s * px, 0), 0.06, "out_quad"), Anim(t, "offset", Vector2(), 0.22, "out_quad"))


def _pose(me, name: str, hold: float | None = None):
    """Étape de chorégraphie : change la pose du lanceur (sans effet sans planche)."""
    return Call(lambda: getattr(me, "set_pose", lambda *_: None)(name, hold))


def _target(c):
    return c.targets[0] if c.targets else c.caster


@scripted("attack.soldier")
def soldier(c):
    """Élan, grand arc vertical blanc épais, éclats, retour."""
    me, tg = c.caster, _target(c)
    s = _face(me, tg)
    go = c.approach(me, tg, gap=95)
    mid = c.center(tg)
    arc = Slash.arc(mid + Vector2(-s * 10, 0), 50, -105 if s > 0 else -75, 75 if s > 0 else 105, ry=135,
                    duration=0.15, width=36, life=0.4, color=WHITE, glow_color=ICE)
    dust = ParticleEmitter(me.home, "dust", count=10, spread=150)
    return Seq(
        _pose(me, "windup"),
        Par(Anim(me, "offset", Vector2(-s * 26, -10), 0.22, "in_out_quad"), c.add(dust)),
        c.sfx("slash_heavy"),
        Par(Anim(me, "offset", go, 0.17, "out_back"), Seq(0.11, _pose(me, "strike", 0.3))),
        c.add(arc),
        Par(c.hit(0, shake=12), _recoil(tg, s, 18),
            c.add(ParticleEmitter(mid, "sparkle", count=18, speed=1.4, colors=[WHITE, ICE, GOLD]))),
        0.2,
        Par(Anim(me, "offset", Vector2(), 0.35, "in_out_quad"), _pose(me, "idle")),
    )


@scripted("attack.black_mage")
def black_mage(c):
    """Petit pas, coup de bâton, gerbe d'étincelles rouges."""
    me, tg = c.caster, _target(c)
    s = _face(me, tg)
    step = c.approach(me, tg, gap=140)
    mid = c.center(tg)
    swing = Slash.arc(mid + Vector2(-s * 15, -10), 40, -120 if s > 0 else -60, 20 if s > 0 else 160, ry=60,
                      duration=0.1, width=12, life=0.2, color=RED, core=PALE)
    sparks = ParticleEmitter(mid, "thunder", count=16, speed=0.7, colors=[RED, (255, 150, 100), WHITE])
    return Seq(
        _pose(me, "windup"),
        Anim(me, "offset", Vector2(-s * 10, 0), 0.12, "out_quad"),
        Anim(me, "offset", step * 0.8, 0.2, "out_cubic"),
        c.sfx("staff_hit"),
        _pose(me, "strike", 0.3),
        c.add(swing),
        Par(c.hit(0, shake=5, color=RED, sparks=None), c.add(sparks), _recoil(tg, s, 8)),
        0.2,
        Par(Anim(me, "offset", Vector2(), 0.3, "in_out_quad"), _pose(me, "idle")),
    )


@scripted("attack.knight")
def knight(c):
    """Charge bouclier, estoc lumineux bleu-blanc, anneau d'impact."""
    me, tg = c.caster, _target(c)
    s = _face(me, tg)
    go = c.approach(me, tg, gap=105)
    mid = c.center(tg)

    def thrust():
        start = Vector2(me.rect.centerx + s * 30, me.rect.centery - 8)
        c.spawn(Beam(start, mid, ICE, width=16, life=0.28, attack=0.05))
        c.spawn(Slash.line(start, mid + Vector2(s * 40, 0), duration=0.08, width=14, life=0.25, color=ICE,
                           core=WHITE))
    return Seq(
        _pose(me, "windup"),
        Anim(me, "offset", Vector2(-s * 22, 0), 0.16, "in_out_quad"),
        Par(c.sfx("slash"), Anim(me, "offset", go * 0.75, 0.2, "in_quad"),
            Anim(me, "scale", 1.06, 0.2, "out_quad")),
        Call(thrust), _pose(me, "strike", 0.35),
        Par(Anim(me, "offset", go, 0.07, "out_quad"), Anim(me, "scale", 1.0, 0.1)),
        c.sfx("impact"),
        Par(c.hit(0, shake=9, color=ICE, ring=False), _recoil(tg, s, 16),
            c.add(Shockwave(mid, ICE, 12, 120, 0.4, 8)), c.add(Shockwave(mid, WHITE, 8, 70, 0.3, 5))),
        0.22,
        Par(Anim(me, "offset", Vector2(), 0.35, "in_out_quad"), _pose(me, "idle")),
    )


@scripted("attack.monk")
def monk(c):
    """Élan, 3 coups de poing rapides ; la valeur est répartie sur 3 chiffres (impact au 3e)."""
    me, tg = c.caster, _target(c)
    s = _face(me, tg)
    go = c.approach(me, tg, gap=85)
    total = c.value(0)
    a = int(total * 0.3)
    b = int(total * 0.3)
    parts = [a, b, total - a - b]
    mid = c.center(tg)

    def punch(k: int):
        def fn():
            last = k == 2
            c.sound("punch")
            tg.flash(WHITE, 0.07)
            p = mid + Vector2(random.uniform(-20, 20), random.uniform(-30, 20))
            c.spawn(Shockwave(p, WHITE if not last else GOLD, 6, 55 if not last else 85, 0.22, 5))
            c.spawn(ParticleEmitter(p, "sparkle", count=6 if not last else 12, speed=0.9))
            c.spawn(ScreenShake(4 if not last else 8, 0.12))
            txt = FloatingText(str(parts[k]), c.head(tg) + Vector2(s * 22 * (k - 1), 18 + 6 * k),
                               WHITE, size=26 if not last else 34, crit=last and c.crit(0))
            c.spawn(txt)
            if last:
                c.impact_now(0)
        return Seq(Call(fn),
                   Anim(tg, "offset", Vector2(s * 9, 0), 0.04), Anim(tg, "offset", Vector2(), 0.08))

    def jab(k: int, dy: float):
        return Seq(_pose(me, "strike", 0.12), Anim(me, "offset", go + Vector2(s * 10, dy), 0.05, "out_quad"))

    return Seq(
        _pose(me, "windup"),
        Anim(me, "offset", Vector2(-s * 14, 0), 0.12, "out_quad"),
        Anim(me, "offset", go + Vector2(-s * 20, 0), 0.16, "out_cubic"),
        Par(jab(0, -10), punch(0)), _pose(me, "windup"), 0.05,
        Par(jab(1, 8), punch(1)), _pose(me, "windup"), 0.05,
        Par(jab(2, -2), punch(2)),
        _pose(me, "strike", 0.3),
        0.2,
        Par(Anim(me, "offset", Vector2(), 0.35, "in_out_quad"), _pose(me, "idle")),
    )


@scripted("attack.thief")
def thief(c):
    """Traversée éclair avec image rémanente, entaille en X, retour."""
    me, tg = c.caster, _target(c)
    s = _face(me, tg)
    through = c.approach(me, tg, gap=-120)
    mid = c.center(tg)

    def ghost():
        c.spawn(AfterImage.of(me, color=STEEL, life=0.45, alpha=190))

    def cross():
        c.spawn(Slash.line(mid + Vector2(-55, -60), mid + Vector2(55, 60), duration=0.07, width=14, life=0.2,
                           color=PALE, core=WHITE))
        c.spawn(Slash.line(mid + Vector2(55, -60), mid + Vector2(-55, 60), duration=0.07, width=14, life=0.2,
                           color=PALE, core=WHITE, delay=0.06))
    return Seq(
        _pose(me, "windup"),
        Anim(me, "offset", Vector2(-s * 12, 6), 0.1, "out_quad"),
        Call(ghost), c.sfx("dagger"),
        Par(Anim(me, "offset", through, 0.16, "in_expo"),
            Seq(0.08, _pose(me, "strike", 0.3), Call(ghost), Call(cross), 0.04, c.sfx("dagger"))),
        c.hit(0, shake=7, ring=False),
        _recoil(tg, s, 14),
        0.1,
        Call(ghost),
        Par(Anim(me, "offset", Vector2(), 0.3, "in_out_quad"), _pose(me, "idle")),
    )


@scripted("attack.samurai")
def samurai(c):
    """Disparition, ligne horizontale fine à travers la cible, réapparition, flash en retard."""
    me, tg = c.caster, _target(c)
    s = _face(me, tg)
    mid = c.center(tg)
    line = Slash.line(mid + Vector2(-s * 190, -4), mid + Vector2(s * 190, 4), duration=0.09, width=7, life=0.35,
                      color=WHITE, core=WHITE, glow_color=ICE)

    def vanish():
        me.visible = False
        c.spawn(AfterImage.of(me, color=PALE, life=0.3, alpha=150))

    def appear():
        me.visible = True
        c.spawn(Shockwave(c.feet(me), PALE, 8, 70, 0.3, 4, squash=0.35))
        c.spawn(ParticleEmitter(c.center(me), "sparkle", count=8, colors=[WHITE, ICE]))

    c.on_end(lambda: setattr(me, "visible", True))
    return Seq(
        _pose(me, "windup"),
        c.sfx("katana_draw"),
        0.1,
        Call(vanish),
        0.08,
        c.add(line),
        0.14,
        Call(appear), _pose(me, "strike", 0.35),
        0.28,
        c.hit(0, shake=8, color=WHITE, ring=False),
        Par(_recoil(tg, s, 10), c.add(ParticleEmitter(mid, "thunder", count=10, speed=0.6, colors=[WHITE, ICE]))),
        0.25,
        _pose(me, "idle"),
    )


@scripted("attack.archer")
def archer(c):
    """Reste en place, recul de l'arc, flèche qui suit une courbe, impact à l'arrivée."""
    me, tg = c.caster, _target(c)
    s = _face(me, tg)
    start = Vector2(me.rect.centerx + s * 40, me.rect.centery - 12)
    end = c.center(tg)
    dur = 0.5

    def shoot():
        c.spawn(Projectile(start, end, dur, "arrow", color=ICE, size=10, arc=70, easing="in_quad", trail=True,
                           on_arrive=lambda: c.hit_now(0, shake=7, color=WHITE)))
    return Seq(
        _pose(me, "windup"),
        Anim(me, "offset", Vector2(-s * 10, 0), 0.22, "out_quad"),
        c.sfx("arrow"),
        Par(Anim(me, "offset", Vector2(s * 6, 0), 0.05), Call(shoot), _pose(me, "strike", 0.3)),
        Anim(me, "offset", Vector2(), 0.2, "out_quad"),
        dur - 0.25 + 0.1,
        _recoil(tg, s, 8),
        0.35,
        _pose(me, "idle"),
    )


@scripted("attack.ninja")
def ninja(c):
    """Shuriken qui tourne vers la cible, puis revient dans la main."""
    me, tg = c.caster, _target(c)
    s = _face(me, tg)
    hand = Vector2(me.rect.centerx + s * 30, me.rect.centery - 18)
    end = c.center(tg)

    def back():
        c.spawn(Projectile(end, hand, 0.38, "shuriken", color=STEEL, size=11, easing="out_quad", spin=26,
                           on_arrive=lambda: c.spawn(ParticleEmitter(hand, "sparkle", count=6, speed=0.5))))

    def throw():
        c.spawn(Projectile(hand, end, 0.32, "shuriken", color=STEEL, size=12, easing="in_quad", spin=30,
                           on_arrive=lambda: (c.hit_now(0, shake=6, color=WHITE), back())))
    return Seq(
        _pose(me, "windup"),
        Anim(me, "offset", Vector2(-s * 12, 0), 0.14, "out_quad"),
        c.sfx("shuriken"),
        Par(Anim(me, "offset", Vector2(s * 12, 0), 0.06), Call(throw), _pose(me, "strike", 0.3)),
        Anim(me, "offset", Vector2(), 0.2, "out_quad"),
        0.12, c.sfx("shuriken"),
        0.5,
        _pose(me, "idle"),
    )


@scripted("attack.monster")
def monster(c):
    """Le monstre bondit vers le héros, trois griffures diagonales rouges."""
    me, tg = c.caster, _target(c)
    s = _face(me, tg)
    go = c.approach(me, tg, gap=85)
    mid = c.center(tg)

    def claw(k: int):
        o = Vector2(-s * 0, (k - 1) * 0) + Vector2((k - 1) * 30, 0)
        return Slash.line(mid + o + Vector2(-36, -70), mid + o + Vector2(36, 70), duration=0.07, width=13,
                          life=0.3, color=RED, core=PALE, delay=0.07 * k)
    return Seq(
        _pose(me, "windup"),
        Anim(me, "offset", Vector2(-s * 10, 6), 0.16, "out_quad"),
        Anim(me, "offset", go + Vector2(0, -70), 0.15, "out_quad"),
        Anim(me, "offset", go, 0.08, "in_quad"),
        _pose(me, "strike", 0.3),
        c.sfx("claw"),
        Par(*[c.add(claw(k)) for k in range(3)]),
        0.12,
        Par(c.hit(0, shake=9, color=RED, ring=False), _recoil(tg, s, 14),
            c.add(ParticleEmitter(mid, "thunder", count=14, speed=0.8, colors=[RED, (255, 150, 100), WHITE]))),
        0.2,
        Par(Anim(me, "offset", Vector2(), 0.35, "in_out_quad"), _pose(me, "idle")),
    )
