"""Aides d'orchestration pour battle, boss, final_boss, ending : mélodies écrites en notation texte."""
from __future__ import annotations

import re

from ..score import Track

_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_RE = re.compile(r"^([A-G])([#b]?)(-?\d)$")


def midi(name: str) -> int:
    """'F#4' -> 66."""
    m = _RE.match(name)
    p = _PC[m.group(1)] + {"#": 1, "b": -1, "": 0}[m.group(2)]
    return 12 * (int(m.group(3)) + 1) + p


def parse_line(text: str):
    """'D5:1.5 r:.5 F5:1' -> [(durée, midi | None)] ; 'r' = silence."""
    out = []
    for tok in text.split():
        n, d = tok.split(":")
        out.append((float(d), None if n == "r" else midi(n)))
    return out


def line(tr: Track, t0: float, text: str, vel: float = .85, legato: float = .95, shift: int = 0, accent: float = 0.0) -> float:
    """Écrit une ligne sur la piste ; renvoie le temps de fin. `accent` renforce les notes sur le temps."""
    t = t0
    for d, p in parse_line(text):
        if p is not None:
            v = vel + (accent if t % 1 == 0 else 0)
            tr.add(t, d * legato, p + shift, min(1.0, v))
        t += d
    return t


def roll(tr: Track, t0: float, dur: float, name: str, v0: float = .4, v1: float = 1.0, step: float = .125) -> None:
    """Roulement crescendo de percussion."""
    n = max(1, int(dur / step))
    for k in range(n):
        tr.add(t0 + k * step, .15, name, v0 + (v1 - v0) * k / n)


def ostinato(tr: Track, t0: float, pitch: int, pattern, step: float = .25, vel: float = .8, bars: float = 1.0) -> None:
    """Répète un motif d'intervalles (demi-tons) par pas de `step` pendant `bars` mesures."""
    n = int(bars * 4 / step)
    for k in range(n):
        off = pattern[k % len(pattern)]
        tr.add(t0 + k * step, step * .8, pitch + off, vel * (1.0 if k % 4 == 0 else .68))
