"""Attaques spéciales des monstres : Supernova, Explosion, 1000 épines, Mauvaise haleine, Souffle de feu.

Briques locales : `Nova` (étoile qui se contracte puis explose), `Blink` (clignotement qui
s'accélère), `NeedleRain`, `Bubbles`, `FogBank`, `FlameBreath`, `HeatHaze`.
Les starfields/bords viennent de `summons.py`.
"""
from __future__ import annotations

import math
import random

import pygame
from pygame import Vector2

from . import Anim, Call, Par, Seq, scripted
from .. import (Effect, FloatingText, Flash, GlassShards, ParticleEmitter, ScreenShake, Shockwave,
                blit_glow, clamp01, ease, lerp, mix, scaled,
                GOLD, GREEN, FIRE, HOLY, ICE, PALE, POISON, RED, THUNDER, WHITE, NAVY, BLUE)
from .summons import EdgeGlow, Starfield, _screen, soft

# ----------------------------------------------------------------- briques


class Nova(Effect):
    """Étoile : `r` (rayon du coeur), `rays` (0..1), puis `wave` (rayon de l'onde blanche)."""

    layer = "overlay"

    def __init__(self, pos) -> None:
        self.pos, self.r, self.rays, self.wave, self.t = Vector2(pos), 0.0, 0.0, 0.0, 0.0

    def update(self, dt: float) -> bool:
        self.t += dt
        return not self.dead

    def render(self, surface: pygame.Surface) -> None:
        r = self.r * (1 + 0.05 * math.sin(self.t * 17))
        if r > 0.5:
            soft(surface, self.pos, r * 3.6, HOLY, 0.55)
            soft(surface, self.pos, r * 2.2, ICE, 0.8)
            soft(surface, self.pos, r * 1.2, WHITE, 1.0)
            ln = r * 2.6 + self.rays * 300
            for i in range(8):
                a = i * math.pi / 4 + self.t * 0.7
                d = Vector2(math.cos(a), math.sin(a))
                col = scaled(WHITE if i % 2 == 0 else ICE, 0.35 + 0.65 * self.rays)
                pygame.draw.line(surface, col, self.pos + d * r, self.pos + d * ln * (1 if i % 2 == 0 else 0.6), 2)
        if self.wave > 1:
            p = self.pos
            w = int(self.wave)
            for k, col in ((1.0, scaled(HOLY, 0.7)), (0.93, ICE), (0.84, WHITE)):
                pygame.draw.circle(surface, col, (int(p.x), int(p.y)), max(1, int(w * k)))


class Blink(Effect):
    """Fait clignoter un acteur de plus en plus vite et le fait trembler (Bombo avant d'exploser)."""

    layer = "none"

    def __init__(self, actor, duration: float, f0: float = 3.0, f1: float = 24.0, jitter: float = 6.0) -> None:
        self.a, self.d, self.f0, self.f1, self.j = actor, duration, f0, f1, jitter
        self.t = self.phase = 0.0
        self.n = 0

    def update(self, dt: float) -> bool:
        self.t += dt
        p = clamp01(self.t / self.d)
        self.phase += lerp(self.f0, self.f1, p * p) * dt
        if int(self.phase) > self.n:
            self.n = int(self.phase)
            self.a.flash(WHITE if self.n % 2 else FIRE, 0.07 + 0.05 * (1 - p))
        self.a.offset = Vector2(random.uniform(-1, 1), random.uniform(-0.4, 0.4)) * self.j * p
        if self.t >= self.d:
            self.a.offset = Vector2()
            return False
        return True


class NeedleRain(Effect):
    """Volée d'aiguilles fines et très rapides de `src` vers chaque cible, qui restent plantées un instant."""

    layer = "front"

    def __init__(self, src, aims, per: int = 70, spread: float = 0.75, color=GREEN) -> None:
        self.t, self.color, self.n = 0.0, color, []
        src = Vector2(src)
        for k, (ctr, rad) in enumerate(aims):
            for _ in range(per):
                t0 = k * 0.12 + random.random() ** 1.3 * spread
                p1 = Vector2(ctr) + Vector2(random.uniform(-rad.x, rad.x), random.uniform(-rad.y, rad.y))
                p0 = src + Vector2(random.uniform(-20, 20), random.uniform(-40, 30))
                d = p1 - p0
                self.n.append((t0, random.uniform(0.1, 0.17), p0, p1, d.normalize() if d.length() else Vector2(-1, 0),
                               random.uniform(30, 56)))
        self.end = max(n[0] + n[1] for n in self.n) + 0.4

    def update(self, dt: float) -> bool:
        self.t += dt
        return self.t < self.end

    def render(self, surface: pygame.Surface) -> None:
        for t0, dur, p0, p1, u, ln in self.n:
            lt = self.t - t0
            if lt < 0:
                continue
            if lt < dur:
                head = p0.lerp(p1, lt / dur)
                k = 1.0
            else:
                age = (lt - dur) / 0.35
                if age >= 1:
                    continue
                head, k = p1, 1 - age
            tail = head - u * ln
            pygame.draw.line(surface, scaled(self.color, k), tail, head, 2)
            pygame.draw.line(surface, scaled(PALE, k), head - u * ln * 0.35, head, 1)
            if lt < dur:
                surface.fill(scaled(WHITE, k), (int(head.x) - 1, int(head.y) - 1, 3, 3))


class Bubbles(Effect):
    """Bulles toxiques qui montent autour d'une zone."""

    layer = "front"

    def __init__(self, rect: pygame.Rect, count: int = 36, duration: float = 2.4, delay: float = 0.0,
                 color=GREEN) -> None:
        self.b = [[random.uniform(rect.left, rect.right), random.uniform(rect.centery, rect.bottom),
                   random.uniform(30, 90), random.uniform(3, 11), random.uniform(0.8, 1.8),
                   random.uniform(0, duration * 0.6), random.uniform(0, 6.3)] for _ in range(count)]
        self.t, self.color, self.dur = -delay, color, duration

    def update(self, dt: float) -> bool:
        self.t += dt
        return self.t < self.dur + 1.8

    def render(self, surface: pygame.Surface) -> None:
        for x, y, vy, r, life, t0, ph in self.b:
            lt = self.t - t0
            if lt < 0 or lt > life:
                continue
            k = 1 - lt / life
            px, py = x + math.sin(lt * 4 + ph) * 8, y - vy * lt
            col = scaled(self.color, 0.4 + 0.6 * k)
            pygame.draw.circle(surface, col, (int(px), int(py)), max(2, int(r)), 2)
            surface.fill(scaled(WHITE, k), (int(px - r * 0.4), int(py - r * 0.4), 2, 2))


class FogBank(Effect):
    """Nuage toxique qui envahit l'écran depuis `origin` (progression `p` de 0 à 1, `k` = opacité)."""

    layer = "front"

    def __init__(self, origin, W: int, H: int, goal_x: float) -> None:
        self.o, self.p, self.k, self.t = Vector2(origin), 0.0, 1.0, 0.0
        self.blobs = []
        for i in range(13):
            tgt = Vector2(random.uniform(min(goal_x, self.o.x) - 120, max(goal_x, self.o.x) + 120),
                          random.uniform(H * 0.28, H * 0.95))
            self.blobs.append((tgt, random.uniform(150, 260), random.uniform(0, 0.35),
                               random.choice((scaled(POISON, 0.75), scaled(GREEN, 0.55), scaled(POISON, 0.5)))))

    def update(self, dt: float) -> bool:
        self.t += dt
        return not self.dead

    def render(self, surface: pygame.Surface) -> None:
        if self.p <= 0.01 or self.k <= 0.02:
            return
        for tgt, r, d, col in self.blobs:
            q = clamp01((self.p - d) / (1 - d))
            if q <= 0:
                continue
            pos = self.o.lerp(tgt, ease("out_cubic", q))
            pos += Vector2(math.sin(self.t * 1.4 + r), math.cos(self.t * 1.1 + r)) * 14
            soft(surface, pos, 40 + r * ease("out_quad", q), col, 0.6 * clamp01(self.k))


class FlameBreath(Effect):
    """Cône de flammes qui balaie de l'angle `a0` à `a1` (degrés) en `duration`."""

    layer = "front"

    def __init__(self, origin, a0: float, a1: float, duration: float, rate: float = 520.0) -> None:
        self.o, self.a0, self.a1, self.d, self.rate = Vector2(origin), a0, a1, duration, rate
        self.t, self.acc, self.p = 0.0, 0.0, []

    def update(self, dt: float) -> bool:
        self.t += dt
        if self.t < self.d:
            self.acc += self.rate * dt
            n, self.acc = int(self.acc), self.acc - int(self.acc)
            ang = lerp(self.a0, self.a1, ease("in_out_sine", self.t / self.d))
            for _ in range(n):
                a = math.radians(ang + random.uniform(-6, 6))
                sp = random.uniform(650, 980)
                self.p.append([self.o.x, self.o.y, math.cos(a) * sp, math.sin(a) * sp, 0.0, random.uniform(0.45, 0.8),
                               random.uniform(8, 16)])
        keep = []
        for q in self.p:
            q[4] += dt
            if q[4] >= q[5]:
                continue
            k = max(0.0, 1 - 1.6 * dt)
            q[2] *= k
            q[3] = q[3] * k - 70 * dt
            q[0] += q[2] * dt
            q[1] += q[3] * dt
            keep.append(q)
        self.p = keep
        return bool(keep) or self.t < self.d

    def render(self, surface: pygame.Surface) -> None:
        soft(surface, self.o, 70 * clamp01(1 - self.t / (self.d + 0.3)), THUNDER, 0.9)
        for x, y, _, _, age, life, size in self.p:
            u = age / life
            col = mix(WHITE, THUNDER, clamp01(u * 4)) if u < 0.25 else mix(THUNDER, FIRE, clamp01((u - 0.25) / 0.4))
            if u > 0.65:
                col = mix(FIRE, RED, clamp01((u - 0.65) / 0.35))
            soft(surface, (x, y), size * (1 + 3.0 * u), col, (1 - u) ** 1.2 * 0.9)


class HeatHaze(Effect):
    """Distorsion de chaleur : bandes horizontales de l'image déjà dessinée qui ondulent dans `rect`."""

    layer = "overlay"

    def __init__(self, rect: pygame.Rect, life: float, amp: float = 5.0) -> None:
        self.rect, self.life, self.amp, self.t = pygame.Rect(rect), life, amp, 0.0

    def update(self, dt: float) -> bool:
        self.t += dt
        return self.t < self.life

    def render(self, surface: pygame.Surface) -> None:
        r = self.rect.clip(surface.get_rect())
        if r.w < 8 or r.h < 8:
            return
        k = clamp01(self.t / 0.3) * clamp01((self.life - self.t) / 0.4)
        src = surface.subsurface(r).copy()
        sh = 6
        for y in range(0, r.h, sh):
            dx = int(math.sin(self.t * 13 + y * 0.07) * self.amp * k)
            if dx:
                surface.blit(src, (r.x + dx, r.y + y), (0, y, r.w, sh))


# ----------------------------------------------------------------- aides


def _facing(c) -> float:
    """-1 si les cibles sont à gauche du lanceur, +1 sinon."""
    me = c.caster
    mean = sum(t.home.x for t in c.targets) / max(1, len(c.targets))
    return -1.0 if mean < me.home.x else 1.0


def _clear_tints(c):
    def f():
        for t in [c.caster, *c.targets]:
            try:
                t.tint = None
            except AttributeError:
                pass
    c.on_end(f)


def _base_pose(c):
    """Fin ou skip : le lanceur revient à sa pose de base."""
    me = c.caster
    c.on_end(lambda: me.set_pose("idle"))


def _duck(c, level: float, seconds: float):
    """Baisse la musique ; elle revient tout de suite à la fin ou au skip."""
    def f() -> None:
        try:
            if c.audio is not None:
                c.audio.duck(level, seconds)
        except Exception:  # noqa: BLE001
            pass

    def restore() -> None:
        try:
            if c.audio is not None:
                c.audio.duck(1.0, 0.0)
        except Exception:  # noqa: BLE001
            pass

    c.on_end(restore)
    return Call(f)


def _tint(t, color, up: float, down: float, hold: float = 0.0):
    return Seq(Call(setattr, t, "tint", color), up + hold + down, Call(setattr, t, "tint", None))


# ----------------------------------------------------------------- Supernova


@scripted("monster.supernova", skippable=True)
def supernova(c):
    """Supernova : écran noir, étoiles qui défilent, une étoile gonfle, se contracte, explose sur toute l'équipe."""
    W, H = _screen(c)
    me = c.caster
    _base_pose(c)
    star = Starfield(0.0, "stream", 250, 0.8, nebula=[(0.5, 0.42, 420, NAVY, 0.7), (0.2, 0.7, 300, HOLY, 0.18)])
    nova = Nova((W * 0.5, H * 0.42))
    stage = [star, nova]
    c.on_end(lambda: [e.kill() for e in stage])

    inflow = ParticleEmitter(nova.pos, "sparkle", rate=300, duration=1.2, radius=540, speed=0.1, life=1.0,
                             attract=nova.pos, attract_force=1500, gravity=0, layer="overlay",
                             colors=[WHITE, ICE, HOLY])
    rings = Seq(*[Seq(c.add(Shockwave(nova.pos, ICE if i % 2 else HOLY, 520, 10, 0.6, 4, easing="in_quad", layer="overlay")), 0.22)
                  for i in range(5)])

    def hit(i, t):  # l'impact tombe sous le blanc, les chiffres arrivent en cascade quand il se dissipe
        return Seq(i * 0.14, c.impact(i), Call(t.flash, WHITE, 0.5), 0.85, c.damage_text(i),
                   c.add(Shockwave(c.center(t), WHITE, 10, 120, 0.4, 6)))

    return Seq(
        c.hide_ui(),
        Call(me.set_pose, "cast"), _duck(c, 0.3, 7.0),
        Par(c.sfx("charge_big"), Anim(me, "offset", Vector2(0, -60), 1.2, "in_out_sine"),
            Seq(0.2, c.add(star), Anim(star, "bg", 1.0, 0.6))),
        Par(Anim(star, "speed", 3.4, 1.6, "in_quad"),
            Seq(0.3, c.add(nova), Anim(nova, "r", 46.0, 1.2, "out_back"))),
        Par(Anim(nova, "r", 60.0, 0.9, "in_out_sine"), c.add(ScreenShake(2.5, 0.9, decay=False))),
        Par(c.add(inflow), rings, Anim(nova, "r", 5.0, 1.1, "in_expo"), Anim(nova, "rays", 1.0, 1.1, "in_quad"),
            Anim(star, "speed", 0.15, 1.1, "out_quad"), c.add(ScreenShake(6, 1.1, decay=False))),
        Par(Anim(star, "a", 0.1, 0.3), Anim(nova, "rays", 0.0, 0.3)),
        0.15,
        Call(me.set_pose, "strike", 0.9),
        Par(c.sfx("supernova"), c.add(Flash(WHITE, 1.7, 1.0, attack=0.12)), c.add(ScreenShake(24, 2.8)),
            Anim(nova, "wave", 1500.0, 0.9, "out_cubic"),
            Seq(0.45, Call(star.kill), Call(nova.kill)),
            Seq(0.5, Anim(me, "offset", Vector2(), 0.6, "in_out_quad")),
            c.each(hit)),
        Call(me.set_pose, "idle"),
        0.5,
    )


# ----------------------------------------------------------------- Explosion (Bombo)


@scripted("monster.explosion")
def explosion(c):
    """Explosion : le Bombo enfle, clignote de plus en plus vite, explose en orange et disparaît."""
    me = c.caster
    _base_pose(c)
    c.on_end(lambda: setattr(me, "visible", True))
    _clear_tints(c)
    me_c = c.center(me)

    def boom():
        ctr = c.center(me)
        me.visible = False
        c.spawn(Flash(WHITE, 0.15, 0.9))
        c.spawn(Flash(FIRE, 0.6, 0.7, additive=True))
        c.spawn(ScreenShake(16, 0.7))
        c.spawn(ParticleEmitter(ctr, "fire", count=100, radius=30, spread=360, speed=2.6, size=1.7))
        c.spawn(ParticleEmitter(ctr, "dust", count=30, radius=30, speed=2.2, colors=[FIRE, GOLD, PALE]))
        c.spawn(GlassShards(ctr, 22, (FIRE, GOLD, RED), (5, 12), (250, 700), 0.9, 900))
        c.spawn(Shockwave(ctr, FIRE, 20, 760, 0.7, 26, squash=0.75))
        c.spawn(Shockwave(ctr, GOLD, 10, 560, 0.55, 12, delay=0.08, squash=0.75))
        c.sound("explosion")

    def hit(i, t):
        d = (c.center(t) - me_c).length()
        return Seq(d / 1100, c.hit(i, shake=9, color=FIRE, sparks="fire"), _tint(t, (255, 150, 110), 0.1, 0.5))

    return Seq(
        Call(me.set_pose, "windup"),
        c.sfx("charge"),
        Par(Anim(me, "scale", 1.75, 1.5, "in_quad"), c.add(Blink(me, 1.5)),
            c.add(ParticleEmitter(me_c, "dust", rate=30, duration=1.4, radius=40, colors=[STEEL_SMOKE], speed=0.4))),
        Call(me.set_pose, "strike", 0.3),
        Call(boom),
        c.each(hit),
        0.4,
    )


STEEL_SMOKE = (111, 128, 200)


# ----------------------------------------------------------------- 1000 épines (Pampa)


@scripted("monster.needles")
def needles(c):
    """1000 épines : pluie d'aiguilles fines et rapides, « 1000 » énorme."""
    me = c.caster
    _base_pose(c)
    f = _facing(c)
    src = c.center(me) + Vector2(f * 30, -20)
    aims = [(c.center(t), Vector2(t.rect.w * 0.4, t.rect.h * 0.4)) for t in c.targets]
    rain = NeedleRain(src, aims, per=max(40, 200 // max(1, len(aims))))
    top = min(c.head(t).y for t in c.targets) - 60
    mid = sum(c.center(t).x for t in c.targets) / max(1, len(c.targets))

    def hit(i, t):
        return Seq(0.28 + i * 0.12, c.hit(i, shake=6, color=GREEN, sparks="sparkle"),
                   Call(t.flash, WHITE, 0.05), 0.12, Call(t.flash, GREEN, 0.05), 0.1, Call(t.flash, WHITE, 0.05))

    return Seq(
        Call(me.set_pose, "windup"),
        Par(Anim(me, "offset", Vector2(-f * 18, 0), 0.3, "out_quad"), Anim(me, "scale", 1.1, 0.3, "out_quad"),
            c.sfx("needles")),
        Call(me.set_pose, "strike", 0.3),
        Par(Anim(me, "offset", Vector2(f * 8, 0), 0.08, "out_quad"), c.add(rain),
            c.add(FloatingText("1000", (mid, top), WHITE, size=112, kind="free", delay=0.35, life=1.8)),
            Seq(Anim(me, "scale", 1.0, 0.8, "out_elastic")), c.each(hit)),
        0.7,
        Anim(me, "offset", Vector2(), 0.3, "in_out_quad"),
        Call(me.set_pose, "idle"),
    )


# ----------------------------------------------------------------- Mauvaise haleine (Morbol)


@scripted("monster.bad_breath")
def bad_breath(c):
    """Mauvaise haleine : nuage vert-violet qui envahit l'écran, bulles, équipe teintée de vert."""
    W, H = _screen(c)
    me = c.caster
    _base_pose(c)
    f = _facing(c)
    mouth = Vector2(me.rect.centerx + f * me.rect.w * 0.35, me.rect.top + me.rect.h * 0.35)
    goal = sum(c.center(t).x for t in c.targets) / max(1, len(c.targets))
    fog = FogBank(mouth, W, H, goal)
    edge = EdgeGlow(POISON, pulse=0.12)
    _clear_tints(c)
    c.on_end(lambda: (fog.kill(), edge.kill()))
    spray = [ParticleEmitter(mouth, "poison", rate=170, duration=1.3, radius=14, speed=3.4, size=2.0, life=1.1,
                             angle=math.degrees(math.atan2(c.center(t).y - mouth.y, c.center(t).x - mouth.x)),
                             spread=18, layer="front") for t in c.targets]

    def victim(i, t):
        d = (c.center(t) - mouth).length()
        return Seq(0.25 + d / 900, c.hit(i, shake=5, color=POISON, sparks="poison"),
                   Par(c.add(Bubbles(t.rect.inflate(30, 40), 22, 1.6, color=GREEN)),
                       Call(setattr, t, "tint", (150, 235, 160))))

    def cure():
        for t in c.targets:
            t.tint = None

    return Seq(
        Call(me.set_pose, "windup"),
        Par(c.sfx("poison_gas"), Anim(me, "scale", 1.2, 0.5, "out_quad"), Anim(me, "offset", Vector2(-f * 14, 0), 0.5)),
        Call(me.set_pose, "strike", 0.3),
        Par(Anim(me, "scale", 0.94, 0.1), Anim(me, "offset", Vector2(f * 10, 0), 0.1),
            c.add(fog), Anim(fog, "p", 1.0, 1.6, "out_cubic"), *[c.add(s) for s in spray],
            c.add(edge), Anim(edge, "k", 1.0, 0.9), c.add(ScreenShake(3, 1.0)), c.each(victim, stagger=0.12),
            Seq(Anim(me, "scale", 1.0, 0.5, "out_back"), Anim(me, "offset", Vector2(), 0.3))),
        1.3,
        Par(Anim(fog, "k", 0.0, 0.9), Anim(edge, "k", 0.0, 0.9)),
        Call(cure),
        Call(me.set_pose, "idle"),
    )


# ----------------------------------------------------------------- Souffle de feu (Dragon rouge)


@scripted("monster.fire_breath")
def fire_breath(c):
    """Souffle de feu : cône de flammes qui balaie toute l'équipe, distorsion de chaleur, braises."""
    W, H = _screen(c)
    me = c.caster
    _base_pose(c)
    f = _facing(c)
    mouth = Vector2(me.rect.centerx + f * me.rect.w * 0.45, me.rect.top + me.rect.h * 0.3)
    angs = [math.degrees(math.atan2(c.center(t).y - mouth.y, c.center(t).x - mouth.x)) for t in c.targets]
    lo, hi = min(angs), max(angs)
    if hi - lo < 14:  # une seule cible : petit balayage quand même
        lo, hi = lo - 8, hi + 8
    sweep = 1.1
    flame = FlameBreath(mouth, lo - 4, hi + 4, sweep)
    pts = [mouth] + [c.center(t) for t in c.targets]
    haze_rect = pygame.Rect(min(p.x for p in pts) - 80, min(p.y for p in pts) - 140,
                            max(p.x for p in pts) - min(p.x for p in pts) + 160,
                            max(p.y for p in pts) - min(p.y for p in pts) + 280)
    haze = HeatHaze(haze_rect, sweep + 1.0, 6.0)
    _clear_tints(c)

    def victim(i, t):
        frac = clamp01((angs[i] - lo) / max(1e-3, hi - lo))
        d = (c.center(t) - mouth).length()
        return Seq(0.18 + frac * sweep * 0.8 + d / 1000, c.hit(i, shake=8, color=FIRE, sparks="fire"),
                   c.add(ParticleEmitter(c.center(t), "fire", rate=45, duration=0.9, radius=t.rect.w * 0.4, speed=0.7,
                                         size=0.9, life=1.2)),
                   _tint(t, (255, 150, 110), 0.1, 0.7, 0.3))

    return Seq(
        Call(me.set_pose, "windup"),
        Par(c.sfx("flame_breath"), Anim(me, "offset", Vector2(-f * 22, 0), 0.35, "out_quad"),
            Anim(me, "rotation", -f * 6, 0.35, "out_quad"),
            c.add(ParticleEmitter(mouth, "fire", rate=60, duration=0.35, radius=12, speed=0.4, size=0.7))),
        Call(me.set_pose, "strike", 0.5),
        Par(Anim(me, "offset", Vector2(f * 12, 0), 0.1, "out_quad"), Anim(me, "rotation", f * 4, 0.1),
            c.add(flame), c.add(haze), c.add(ScreenShake(5, sweep, decay=False)),
            c.add(Flash(FIRE, 0.4, 0.25, additive=True)), c.each(victim)),
        0.9,
        Par(Anim(me, "offset", Vector2(), 0.35, "in_out_quad"), Anim(me, "rotation", 0.0, 0.35)),
        Call(me.set_pose, "idle"),
    )
