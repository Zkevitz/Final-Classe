"""Aides de composition : accords, gammes en degrés, mélodies, batterie."""
from __future__ import annotations

from ..score import Track

_ROOT = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_QUAL = {"": (0, 4, 7), "m": (0, 3, 7), "7": (0, 4, 7, 10), "m7": (0, 3, 7, 10), "maj7": (0, 4, 7, 11),
         "sus2": (0, 2, 7), "sus4": (0, 5, 7), "dim": (0, 3, 6), "add9": (0, 4, 7, 14), "madd9": (0, 3, 7, 14),
         "6": (0, 4, 7, 9), "5": (0, 7, 12)}
MODES = {"major": (0, 2, 4, 5, 7, 9, 11), "minor": (0, 2, 3, 5, 7, 8, 10), "lydian": (0, 2, 4, 6, 7, 9, 11),
         "phrygian": (0, 1, 3, 5, 7, 8, 10), "dorian": (0, 2, 3, 5, 7, 9, 10)}


def parse(name: str):
    """'F#m7' -> (classe de hauteur, intervalles)."""
    pc = _ROOT[name[0]]
    i = 1
    while i < len(name) and name[i] in "#b":
        pc += 1 if name[i] == "#" else -1
        i += 1
    return pc % 12, _QUAL[name[i:]]


def root(name: str, near: int) -> int:
    """Fondamentale de l'accord, la plus proche au-dessus de `near`."""
    pc, _ = parse(name)
    return near + (pc - near) % 12


def stack(name: str, low: int = 55, n: int | None = None) -> list[int]:
    """Notes de l'accord en position serrée, la plus grave >= low."""
    pc, iv = parse(name)
    base = low + (pc - low) % 12
    out = [base + x for x in iv]
    return out if n is None else out[:n]


def arp(name: str, low: int, n: int) -> list[int]:
    """n notes montant à travers les notes de l'accord (sur plusieurs octaves)."""
    t = stack(name, low)
    return [t[k % len(t)] + 12 * (k // len(t)) for k in range(n)]


def scale(tonic: int, mode: str):
    """Fonction degré -> MIDI ; degré 7 = octave ; altération en demi-tons via (degré, alt)."""
    iv = MODES[mode]

    def f(d, alt=0):
        return tonic + iv[d % 7] + 12 * (d // 7) + alt
    return f


def mel(tr: Track, t0: float, items, sc, vel: float = 0.8, legato: float = 0.95, shift: int = 0) -> float:
    """Écrit une mélodie : items = [(durée, degré | (degré, alt) | None)] ; renvoie le temps de fin."""
    t = t0
    for dur, d in items:
        if d is not None:
            m = sc(*d) if isinstance(d, tuple) else sc(d)
            tr.add(t, dur * legato, m + shift, vel)
        t += dur
    return t


def bars_of(form):
    """Itère (section, j, n°_mesure, accord, début_en_temps, dernière_mesure) sur toute la forme."""
    i = 0
    for name, chords in form:
        for j, ch in enumerate(chords):
            yield name, j, i, ch, i * 4.0, j == len(chords) - 1
            i += 1


def total_bars(form) -> int:
    return sum(len(c) for _, c in form)


def hits(tr: Track, t0: float, pattern: dict, vel: float = 1.0) -> None:
    """pattern = {'kick': [0, 2], 'snare': [1, 3], ...} (temps dans la mesure)."""
    for name, bs in pattern.items():
        for b in bs:
            tr.add(t0 + b, 0.2, name, vel * (0.75 if b % 1 else 1.0))


def seq(tr: Track, t0: float, items, vel: float = 0.8, legato: float = 0.95) -> float:
    """Écrit une séquence en notes absolues : items = [(durée, 'E5' | MIDI | [accord] | None)] ; renvoie la fin.

    Une durée peut être fractionnaire (1/3 pour les triolets).
    """
    t = t0
    for dur, p in items:
        if p is not None:
            for q in (p if isinstance(p, (list, tuple)) else (p,)):
                tr.add(t, dur * legato, q, vel)
        t += dur
    return t
