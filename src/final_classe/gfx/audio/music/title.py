"""Musique `title` : reprise du Prelude (« Prélude au cristal », série Final Fantasy, Nobuo Uematsu).

Do majeur, 72 BPM, 18 mesures (60 s), boucle.
SÛR (docs/AUDIO-REFERENCES.md) : la figure do-ré-mi-sol / la-si-do-mi en doubles croches, montée sur 4 octaves puis descente, une cellule par accord (do, la m, ... fa, sol), harpe en avant ; et la couleur (nappe de cordes, mélodie par-dessus après l'introduction).
RECONSTITUÉ : la mélodie des cordes et des cors (contour montant en do majeur, notes longues) et les accords de
la seconde moitié ; l'enchaînement exact des mesures est approximatif. Fidélité globale : approximative.
"""
from __future__ import annotations

from ..score import Score, Track
from .common import bars_of, root, seq, stack, total_bars

# Une cellule d'arpèges = 2 mesures (32 doubles croches : montée sur 4 octaves puis descente).
# Cellules : do, la m, do, la m, do, la m, fa, sol, do ; accords repris par mesure pour les nappes.
FORM = [("intro", ["C", "C"]), ("A", ["Am", "Am", "C", "C"]), ("B", ["Am", "Am", "C", "C"]),
        ("A2", ["Am", "Am", "F", "F"]), ("out", ["G", "G", "C", "C"])]
# mélodie A : montée par degrés conjoints, appuyée sur mi/sol/do
MEL_A = [[(2, "E5"), (1, "G5"), (1, "E5")], [(2, "C5"), (1, "E5"), (1, "A5")], [(2, "A5"), (1, "G5"), (1, "F5")],
         [(2, "G5"), (1, "F5"), (1, "D5")]]
MEL_B = [[(1, "E5"), (1, "G5"), (2, "C6")], [(1, "A5"), (1, "G5"), (2, "E5")], [(1, "F5"), (1, "A5"), (2, "D6")],
         [(2, "B5"), (1, "G5"), (1, "D5")]]
MEL_O = [[(2, "A5"), (2, "C6")], [(2, "B5"), (2, "D6")], [(4, "C6")], [(4, None)]]


def arpeggio(ch: str):
    """32 doubles croches : do-ré-mi-sol (Cadd2) / la-si-do-mi (Am add2) montant sur 4 octaves, puis descente."""
    r = root(ch, 36) if ch != "Am" else 33 + 12 * 0 + (9 - 33) % 12  # la1/la2 selon l'accord
    cell = (0, 2, 3, 7) if ch == "Am" else (0, 2, 4, 7)  # Am : la-si-do-mi ; autres : r, 2de, 3ce, 5te
    up = [r + 12 * o + x for o in range(4) for x in cell]
    return up + up[-2::-1] + [up[1]]


def build() -> Score:
    harp = Track("harp", level=-19, send=0.45)
    harp2 = Track("harp", level=-33, send=0.5)   # doublure à l'octave, très légère
    bells = Track("bell", level=-33, send=0.55)
    pad = Track("strings", level=-26, send=0.4)
    lead = Track("strings", level=-23, send=0.4)
    horn = Track("horn", level=-26, send=0.35)
    choir = Track("choir", level=-29, send=0.5)
    flute = Track("flute", level=-29, send=0.4)
    cello = Track("strings_dark", level=-27, send=0.3)
    tim = Track("timpani", level=-28, send=0.4)
    for name, j, bi, ch, t0, last in bars_of(FORM):
        vel = {"intro": .6, "A": .7, "B": .8, "A2": .95, "out": .6}[name]
        if j % 2 == 0:  # début d'une cellule de 2 mesures
            for k, p in enumerate(arpeggio(ch)):
                harp.add(t0 + k * .25, .35, p + 12, vel * (1.0 if k % 4 == 0 else .85))
                if k % 2 == 0:
                    harp2.add(t0 + k * .25, .3, p + 24, vel * .5)
        pad.chord(t0, 4, [p + 12 for p in stack(ch, 55)], vel * .6)
        cello.add(t0, 3.9, root(ch, 36), vel * .9)
        if j == 0:
            bells.add(t0, 3, root(ch, 72), .6)
        if name == "A":
            seq(lead, t0, MEL_A[j], .8)
            seq(flute, t0, MEL_A[j], .5, legato=.9)
        if name == "B":
            seq(horn, t0, [(d, _down(p)) for d, p in MEL_B[j]], .8)
            seq(lead, t0, MEL_B[j], .85)
        if name == "A2":
            seq(horn, t0, [(d, _down(p)) for d, p in MEL_A[j]], .85)
            seq(lead, t0, MEL_A[j], .9)
            seq(lead, t0, [(d, _up(p)) for d, p in MEL_A[j]], .6)
            choir.chord(t0, 4, stack(ch, 57, 3), .8)
            if j == 0:
                tim.add(t0, 2, "timpani", .8)
        if name == "out":
            seq(flute, t0, MEL_O[j], .5, legato=.9)
    return Score(bpm=72, bars=total_bars(FORM), rt60=2.6, wet=.3, drive=1.5, rms_db=-19,
                 tracks=[harp, harp2, bells, pad, lead, horn, choir, flute, cello, tim])


def _shift(p, n):
    from ..synth import note
    return None if p is None else int(note(p)) + n


def _down(p):
    return _shift(p, -12)


def _up(p):
    return _shift(p, 12)
