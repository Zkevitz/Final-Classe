"""Chorégraphies de combat : contrat, petit DSL de séquences, REGISTRY, `play`.

GUIDE DES ANIMATEURS (un module par fichier : attacks, skills, spells, summons,
items, monsters). Chaque module s'enregistre lui-même ; ce fichier les importe
en tolérant ceux qui n'existent pas encore.

Le DSL (toutes les étapes sont des `Step` ; `update(dt)` renvoie True tant qu'elle court) :
    Seq(a, b, c)              étapes l'une après l'autre
    Par(a, b, c)              étapes en même temps (fini quand toutes le sont)
    Wait(0.2)  ou  0.2        attendre (un nombre seul dans Seq/Par = Wait)
    Call(fn, *args)  ou  fn   appeler une fonction (un callable seul = Call)
    Anim(obj, "offset", Vector2(80, 0), 0.25, "out_back")   interpoler un attribut
                              (nombre, Vector2, tuple ; départ = valeur actuelle)
    [a, b]                    une liste dans Seq/Par = Par
Helpers de `c` (la Choreography passée à la fonction) :
    c.impact(i)  c.hit(i, ...)  c.sfx("slash")  c.add(effet)  c.approach(...)
    c.each(fn, stagger=0.1)   un pas de chorégraphie par cible
    c.center(a) c.head(a) c.feet(a)   points d'un acteur ; c.value(i), c.crit(i)
    c.hide_ui()               cache l'interface (invocations) ; c.on_end(fn) nettoyage
    c.skippable = True        pour les invocations (Entrée la passe)

Exemple complet (attaque à l'épée, ~25 lignes) :

    from . import scripted, Seq, Par, Anim, Call
    from .. import Slash, Shockwave, WHITE, ICE
    from pygame import Vector2

    @scripted("attack.demo")
    def demo(c):
        me, tg = c.caster, c.targets[0]
        go = c.approach(me, tg, gap=80)                  # offset pour arriver devant la cible
        arc = Slash.arc(c.center(tg), 90, -120, 40, ry=110, duration=0.14, width=24, color=ICE)
        return Seq(
            Anim(me, "offset", Vector2(-18, 0), 0.12, "out_quad"),       # armer le coup
            c.sfx("slash_heavy"),
            Anim(me, "offset", go, 0.18, "out_back"),                    # élan
            c.add(arc),                                                  # traînée
            c.hit(0, shake=10),                                          # impact UNIQUE : PV, flash, chiffre
            0.1,
            Anim(me, "offset", Vector2(), 0.3, "in_out_quad"),           # retour
        )

`c.hit(i)` appelle `ctx.on_impact(i)` UNE fois, fait flasher la cible, affiche le chiffre
(dégâts, soin, critique en or) et secoue l'écran. Pour des cas à part (soin, PM, 3 coups
répartis), utilise `c.impact(i)` + `c.damage_text(i, text=..., kind="heal"|"mp"|"free")`.
Les effets (`c.add`) vivent dans le FxManager : la chorégraphie se termine à la fin de la
séquence, les particules en cours finissent seules. À la fin (ou `skip()`), les impacts
oubliés sont émis et les `offset`/`scale`/`rotation` des acteurs sont remis à zéro.
Un module expose en plus des fonctions libres si besoin ; seules les clés du catalogue
(`docs/ANIMATIONS.md`) sont enregistrées.
"""
from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

import pygame
from pygame import Vector2

from .. import (Effect, FloatingText, FxManager, Shockwave, ScreenShake, ParticleEmitter,  # noqa: F401
                clamp01, ease, lerp, GOLD, GREEN, BLUE, WHITE)

# ----------------------------------------------------------------- contrat


class Actor(Protocol):
    """Combattant fourni par la scène de combat (voir docs/ARCHITECTURE-GFX.md §3)."""

    home: Vector2
    offset: Vector2
    scale: float
    rotation: float
    alpha: int
    visible: bool
    tint: tuple[int, int, int] | None
    rect: pygame.Rect

    def flash(self, color=(255, 255, 255), seconds: float = 0.12) -> None: ...

    def set_pose(self, pose: str, hold: float | None = None) -> None: ...


def _noop(i: int) -> None:
    return None


@dataclass
class ActionContext:
    caster: Any
    targets: list
    values: list = field(default_factory=list)
    critical: list = field(default_factory=list)
    on_impact: Callable[[int], None] = _noop
    fx: FxManager | None = None
    audio: Any = None
    assets: Any = None
    extra: dict = field(default_factory=dict)


# ----------------------------------------------------------------- DSL


class Step:
    """Étape de séquence. `update(dt)` -> True tant qu'elle court ; `left` = temps non consommé."""

    left = 0.0

    def update(self, dt: float) -> bool:
        return False


class Wait(Step):
    def __init__(self, seconds: float) -> None:
        self.d, self.t = seconds, 0.0

    def update(self, dt: float) -> bool:
        self.t += dt
        if self.t >= self.d:
            self.left = self.t - self.d
            return False
        return True


class Call(Step):
    """Appelle `fn(*args)` une fois, immédiatement."""

    def __init__(self, fn: Callable, *args) -> None:
        self.fn, self.args = fn, args

    def update(self, dt: float) -> bool:
        self.fn(*self.args)
        self.left = dt
        return False


class Anim(Step):
    """Interpole `obj.attr` vers `to` en `duration` s (départ : valeur actuelle, ou `frm`)."""

    def __init__(self, obj: Any, attr: str, to, duration: float, easing="out_quad", frm=None) -> None:
        self.obj, self.attr, self.to, self.d, self.easing, self.frm = obj, attr, to, max(1e-6, duration), easing, frm
        self.t = 0.0
        self.start = None

    def update(self, dt: float) -> bool:
        if self.start is None:
            cur = getattr(self.obj, self.attr) if self.frm is None else self.frm
            self.start = Vector2(cur) if isinstance(cur, Vector2) else cur
        self.t += dt
        k = ease(self.easing, self.t / self.d)
        a, b = self.start, self.to
        setattr(self.obj, self.attr, lerp(a, Vector2(b) if isinstance(a, Vector2) else b, k))
        if self.t >= self.d:
            self.left = self.t - self.d
            return False
        return True


def as_step(x: Any) -> Step:
    if isinstance(x, Step):
        return x
    if x is None:
        return Wait(0.0)
    if isinstance(x, (int, float)):
        return Wait(float(x))
    if isinstance(x, (list, tuple)):
        return Par(*x)
    if callable(x):
        return Call(x)
    raise TypeError(f"étape inconnue : {x!r}")


class Seq(Step):
    """Étapes l'une après l'autre (le reste de `dt` est reporté à l'étape suivante)."""

    def __init__(self, *steps: Any) -> None:
        self.steps = [as_step(s) for s in steps]
        self.i = 0

    def update(self, dt: float) -> bool:
        while self.i < len(self.steps):
            cur = self.steps[self.i]
            if cur.update(dt):
                return True
            dt = cur.left
            self.i += 1
        self.left = dt
        return False


class Par(Step):
    """Étapes en parallèle ; terminé quand toutes le sont."""

    def __init__(self, *steps: Any) -> None:
        self.steps = [as_step(s) for s in steps]

    def update(self, dt: float) -> bool:
        running, left = [], dt
        for s in self.steps:
            if s.update(dt):
                running.append(s)
            else:
                left = min(left, s.left)
        self.steps = running
        self.left = left if not running else 0.0
        return bool(running)


# ----------------------------------------------------------------- Choreography


class Choreography(Effect):
    """Chorégraphie : un effet avec `skippable` et `skip()`. Sous-classer et définir `script()`."""

    skippable = False
    reset_on_end = True
    max_seconds = 14.0
    layer = "none"

    def __init__(self, ctx: ActionContext) -> None:
        self.ctx = ctx
        self.caster = ctx.caster
        self.targets = list(ctx.targets)
        self.fx = ctx.fx if ctx.fx is not None else FxManager()
        self.audio = ctx.audio
        self.done = False
        self.time = 0.0
        self._impacted: set[int] = set()
        self._texted: set[int] = set()
        self._finalizers: list[Callable[[], None]] = []
        self._ui_hidden = False
        self.root: Step = as_step(self.script())

    def script(self) -> Any:
        """À surcharger : renvoie la séquence (Seq/Par/...)."""
        return Seq()

    # --- cycle de vie
    def update(self, dt: float) -> bool:
        if self.done:
            return False
        self.time += dt
        running = self.root.update(dt)
        if not running or self.time > self.max_seconds:
            self._finish(natural=not running)
        return not self.done

    def skip(self) -> None:
        if not self.done:
            self._finish()

    def _finish(self, natural: bool = False) -> None:
        self.done = True
        for i in range(len(self.targets)):
            self.impact_now(i)
            if not natural and self.value(i) != 0 and i not in self._texted:  # skip : le chiffre s'affiche quand même
                kind = str(self.ctx.extra.get("kind", "damage"))
                txt = {"heal": f"+{self.value(i)}", "mp": f"+{self.value(i)} PM"}.get(kind)
                try:
                    self.damage_text_now(i, text=txt, kind=kind)
                except Exception as exc:  # noqa: BLE001
                    print(f"[choreo] texte : {exc}", file=sys.stderr)
        for fn in self._finalizers:
            try:
                fn()
            except Exception as exc:  # noqa: BLE001 - un nettoyage raté ne bloque jamais le jeu
                print(f"[choreo] nettoyage : {exc}", file=sys.stderr)
        if self._ui_hidden:
            self.fx.hide_ui = False
        if self.reset_on_end:
            for a in [self.caster, *self.targets]:
                for attr, val in (("offset", Vector2()), ("scale", 1.0), ("rotation", 0.0)):
                    try:
                        setattr(a, attr, val)
                    except AttributeError:
                        pass

    def on_end(self, fn: Callable[[], None]) -> None:
        """Enregistre un nettoyage appelé à la fin ou au `skip()` (ex. `actor.visible = True`)."""
        self._finalizers.append(fn)

    # --- données
    def value(self, i: int) -> int:
        return self.ctx.values[i] if 0 <= i < len(self.ctx.values) else 0

    def crit(self, i: int) -> bool:
        return bool(self.ctx.critical[i]) if 0 <= i < len(self.ctx.critical) else False

    @staticmethod
    def center(a) -> Vector2:
        return Vector2(a.rect.center)

    @staticmethod
    def head(a) -> Vector2:
        return Vector2(a.rect.centerx, a.rect.top)

    @staticmethod
    def feet(a) -> Vector2:
        return Vector2(a.rect.centerx, a.rect.bottom)

    @staticmethod
    def approach(actor, target, gap: float = 90.0) -> Vector2:
        """Offset qui amène `actor` à `gap` px (aux pieds) devant `target`."""
        goal = Vector2(target.home) + Vector2(target.offset)
        d = goal - Vector2(actor.home)
        n = d.normalize() if d.length() > 1 else Vector2(1, 0)
        return d - n * gap

    # --- immédiat (usage dans les fonctions appelées par Call)
    def sound(self, name: str, volume: float = 1.0) -> None:
        if self.audio is not None:
            try:
                self.audio.play_sfx(name, volume)
            except Exception:  # noqa: BLE001
                pass

    def impact_now(self, i: int) -> None:
        if i not in self._impacted and 0 <= i < len(self.targets):
            self._impacted.add(i)
            self.ctx.on_impact(i)

    def spawn(self, effect: Effect, layer: str | None = None, tag: str | None = None) -> Effect:
        return self.fx.add(effect, layer, tag)

    def damage_text_now(self, i: int, text: str | None = None, kind: str = "damage", delay: float = 0.0,
                        color=None) -> None:
        t = self.targets[i]
        self._texted.add(i)
        v = self.value(i)
        crit = self.crit(i) and kind == "damage"
        col = color or {"damage": WHITE, "heal": GREEN, "mp": BLUE, "free": WHITE}.get(kind, WHITE)
        self.fx.add(FloatingText(text if text is not None else str(v), self.head(t) + Vector2(0, 18), col,
                                 crit=crit, kind=kind, delay=delay))

    def hit_now(self, i: int, shake: float | None = None, flash: bool = True, text: bool = True,
                ring: bool = True, kind: str = "damage", color=WHITE, sparks: str | None = "sparkle") -> None:
        t = self.targets[i]
        crit = self.crit(i)
        self.impact_now(i)
        if crit:
            self.sound("crit")
        if flash and kind == "damage":
            t.flash(color, 0.12)
        if text:
            self.damage_text_now(i, kind=kind)
        c = self.center(t)
        if shake is None:
            shake = min(14.0, 3 + self.value(i) / 10)
        if kind == "damage" and shake > 0:
            self.fx.add(ScreenShake(shake * (1.5 if crit else 1.0), 0.18 + shake * 0.012))
        if ring:
            self.fx.add(Shockwave(c, GOLD if crit else color, 10, 70 + (30 if crit else 0), 0.3, 6))
        if sparks:
            self.fx.add(ParticleEmitter(c, sparks, count=10 + (10 if crit else 0), speed=1.0))

    # --- étapes (à placer dans Seq/Par)
    def sfx(self, name: str, volume: float = 1.0) -> Step:
        return Call(self.sound, name, volume)

    def impact(self, i: int) -> Step:
        return Call(self.impact_now, i)

    def hit(self, i: int, **kw) -> Step:
        return Call(lambda: self.hit_now(i, **kw))

    def damage_text(self, i: int, **kw) -> Step:
        return Call(lambda: self.damage_text_now(i, **kw))

    def add(self, effect: Effect, layer: str | None = None, tag: str | None = None) -> Step:
        return Call(self.spawn, effect, layer, tag)

    def each(self, fn: Callable[[int, Any], Any], stagger: float = 0.0) -> Par:
        """Une étape par cible : `fn(i, target)` renvoie une étape, décalée de `stagger` s."""
        return Par(*[Seq(i * stagger, fn(i, t)) for i, t in enumerate(self.targets)])

    def hide_ui(self, hidden: bool = True) -> Step:
        def f() -> None:
            self.fx.hide_ui = hidden
            self._ui_hidden = hidden
        return Call(f)


# ----------------------------------------------------------------- registre

REGISTRY: dict[str, Callable[[ActionContext], Choreography]] = {}


def register(key: str):
    """Décorateur : enregistre une classe `Choreography` ou une fabrique `f(ctx)` sous `key`."""
    def deco(obj):
        REGISTRY[key] = obj
        return obj
    return deco


def scripted(key: str, skippable: bool = False, reset: bool = True):
    """Décorateur : `def f(c) -> Step` devient une chorégraphie enregistrée sous `key`."""
    def deco(fn):
        cls = type(fn.__name__, (Choreography,), {
            "skippable": skippable, "reset_on_end": reset, "__doc__": fn.__doc__,
            "script": lambda self: fn(self)})
        REGISTRY[key] = cls
        return fn
    return deco


def play(key: str, ctx: ActionContext) -> Choreography:
    """Chorégraphie de `key` ; clé inconnue ou erreur -> chorégraphie générique, jamais d'exception."""
    factory = REGISTRY.get(key) or REGISTRY.get("generic")
    try:
        return factory(ctx)
    except Exception as exc:  # noqa: BLE001
        print(f"[choreo] {key} : {exc!r} -> générique", file=sys.stderr)
        return REGISTRY["generic"](ctx)


MODULES = ("_example", "attacks", "skills", "spells", "summons", "items", "monsters")


def _load() -> None:
    for name in MODULES:
        full = f"{__name__}.{name}"
        try:
            importlib.import_module(full)
        except ModuleNotFoundError as exc:
            if exc.name != full:
                print(f"[choreo] {name} : {exc!r}", file=sys.stderr)
        except Exception as exc:  # noqa: BLE001 - un module cassé ne doit pas tuer le jeu
            print(f"[choreo] {name} : {exc!r}", file=sys.stderr)


_load()
