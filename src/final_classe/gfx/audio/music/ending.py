"""Musique `ending` : reprise du thème principal « Final Fantasy » (Nobuo Uematsu, série Final Fantasy).

80 BPM, do majeur, 30 mesures (90 s), boucle. Forme : intro de harpe (2) | A cors et cordes (8) | B flûte et cordes (8)
| A' plénier avec timbales et chœur (8) | final en crescendo (4).
Fidélité : RECONSTRUITE. Sûr : le caractère (arpèges de harpe qui portent tout le morceau, thème noble aux cors puis aux cordes,
montée finale en crescendo). Reconstitué de mémoire, non garanti : les hauteurs exactes de la mélodie et la progression
d'accords. L'utilisateur peut déposer le fichier officiel dans assets/audio/original/ending.*.
"""
from __future__ import annotations

from ..score import Score, Track
from ._orch_battle import line, roll
from .common import arp, bars_of, root, stack, total_bars

A = ["C", "Am", "F", "G", "C", "Am", "F", "G"]
B = ["Am", "F", "C", "G", "Am", "F", "G", "G"]
FORM = [("intro", ["C", "G"]), ("A", A), ("B", B), ("A2", A), ("fin", ["F", "G", "C", "C"])]
MEL_A = ["E5:1 G5:1 C6:2", "C6:1.5 B5:.5 A5:2", "A5:1 C6:1 F6:2", "E6:1.5 D6:.5 B5:2",
         "E5:1 G5:1 C6:2", "C6:1.5 B5:.5 A5:2", "A5:1 G5:1 F5:1 A5:1", "D5:1.5 G5:.5 B5:2"]
MEL_B = ["E6:2 C6:1 A5:1", "C6:2 A5:1 F5:1", "G5:1 C6:1 E6:2", "D6:3 B5:1",
         "E6:2 C6:1 A5:1", "F6:2 A5:1 C6:1", "D6:2 B5:1 G5:1", "B5:3 r:1"]
FIN = ["A5:2 C6:2", "B5:2 D6:2", "C6:2 E6:2", "E6:1 G6:1 C7:2"]


def build() -> Score:
    harp = Track("harp", level=-27, send=0.5)
    horn = Track("horn", level=-26, send=0.4)
    lead = Track("strings", level=-26, send=0.45)
    pad = Track("strings", level=-30, send=0.45)
    cello = Track("strings_dark", level=-28, send=0.35)
    flute = Track("flute", level=-29, send=0.4)
    choir = Track("choir", level=-32, send=0.55)
    tim = Track("timpani", level=-29, send=0.4)
    for name, j, bi, ch, t0, last in bars_of(FORM):
        vel = {"intro": .6, "A": .7, "B": .8, "A2": .95, "fin": 1.0}[name] + (.02 * j if name == "fin" else 0)
        pat = arp(ch, 48, 6)
        for k, i in enumerate((0, 1, 2, 3, 4, 3, 2, 1)):  # arpège ample de harpe, 8 croches par mesure
            harp.add(t0 + k * .5, 1.2, pat[i] + 12 * (name in ("B", "A2", "fin")), vel * (.85 if k % 2 else 1.0))
        if name != "intro":
            pad.chord(t0, 4, stack(ch, 55), vel * .55)
            cello.add(t0, 3.9, root(ch, 36), vel * .8)
        if name == "A":
            line(horn, t0, MEL_A[j], vel, legato=1.0, shift=-12)
            line(lead, t0, MEL_A[j], vel * .7, legato=1.0)
        if name == "B":
            line(lead, t0, MEL_B[j], vel, legato=1.0)
            line(flute, t0, MEL_B[j], .8, legato=1.0, shift=12)
        if name == "A2":
            line(lead, t0, MEL_A[j], vel, legato=1.0)
            line(horn, t0, MEL_A[j], vel * .9, legato=1.0, shift=-12)
            line(choir, t0, MEL_A[j], vel * .8, legato=1.0, shift=-12)
            line(flute, t0, MEL_A[j], .7, shift=12)
            tim.add(t0, 3, "timpani", vel * .8)
        if name == "fin":
            line(lead, t0, FIN[j], vel, legato=1.0)
            line(horn, t0, FIN[j], vel, legato=1.0, shift=-12)
            line(choir, t0, FIN[j], vel * .9, legato=1.0, shift=-12)
            tim.add(t0, 3, "timpani", vel)
            if j == 3:
                roll(tim, t0 + 1, 3, "timpani", .4, 1.0, .25)
    return Score(bpm=80, bars=total_bars(FORM), rt60=3.0, wet=.3, drive=1.6, rms_db=-20,
                 tracks=[harp, horn, lead, pad, cello, flute, choir, tim])
