"""Musique `final_boss` : reprise de « One-Winged Angel » (Final Fantasy VII, Nobuo Uematsu).

140 BPM, mi phrygien / mi mineur, 44 mesures (75 s), boucle.
Forme : intro, coups d'orchestre et cuivres (4) | chant « Sephiroth! » sur l'ostinato de cordes (8) | A chœur (8) | B cuivres (8)
| C envol du chœur (8) | final plénier (8).
Fidélité : APPROXIMATIVE. Sûr : le dispositif (ostinato de doubles croches staccato à la seconde mineure mi-fa, chant scandé
« Se-phi-roth » du chœur de formants sur note répétée, grands coups de timbales et de taiko, cuivres graves en montées chromatiques,
chœur qui s'envole en fin de morceau). Reconstitué de mémoire, non garanti : les hauteurs précises des phrases chantées
du chœur (le texte latin du morceau n'est pas chanté : voyelles seules), la tonalité exacte et l'ordre des sections.
"""
from __future__ import annotations

from ..score import Score, Track
from ._orch_battle import line, ostinato, roll
from .common import bars_of, root, stack, total_bars

CH_A = ["Em", "F", "Em", "F", "Em", "C", "F", "B"]
CH_B = ["Am", "C", "G", "D", "Am", "F", "B", "B"]
CH_C = ["C", "G", "Am", "Em", "F", "C", "F", "B"]
FORM = [("intro", ["Em", "F", "Em", "B"]), ("chant", ["Em", "F"] * 4), ("A", CH_A), ("B", CH_B), ("C", CH_C),
        ("fin", CH_A)]
OST = [0, 1, 0, 0, 12, 0, 1, 0]
# Chant scandé « Se-phi-ROTH ! » (une mesure sur deux), note répétée avec le demi-ton phrygien
CHANT = ["E4:.5 E4:.5 F4:1 E4:2", "E4:.5 E4:.5 G4:1 F4:2"]
INTRO_BRASS = ["E3:1 F3:1 E3:2", "F3:1 G3:1 F3:2", "E3:1 B3:1 E4:2", "F4:1 E4:1 B3:1 B3:1"]
A = ["B4:2 C5:1 B4:1", "C5:2 A4:1 C5:1", "B4:1 E5:1 G5:2", "A5:2 G5:1 C5:1",
     "B4:2 C5:1 B4:1", "E5:2 D5:1 B4:1", "C5:1 A4:1 C5:1 G5:1", "B4:1 D#5:1 F#5:2"]
B = ["E5:2 C5:1 A4:1", "G5:2 E5:2", "D5:1.5 B4:.5 G4:2", "D5:1 F#5:1 A5:2",
     "A5:2 G5:1 E5:1", "F5:2 A5:1 C6:1", "D#6:4", "B5:2 F#5:2"]
C = ["E5:2 G5:2", "G5:2 B5:2", "A5:1 B5:1 C6:2", "B5:2 G5:2",
     "A5:2 F5:1 A5:1", "G5:2 C6:2", "A5:2 C6:2", "B5:1 D#6:1 F#6:2"]


def build() -> Score:
    choir = Track("choir", level=-24, send=0.55)
    oh = Track("choir_oh", level=-28, send=0.55)
    brass = Track("brass", level=-23, send=0.3)
    horn = Track("horn", level=-27, send=0.3)
    stac = Track("strings_stac", level=-26, send=0.25)
    pad = Track("strings", level=-30, send=0.4)
    bass = Track("bass_drive", level=-24, send=0.08)
    perc = Track("perc", level=-22, send=0.2)
    tim = Track("timpani", level=-25, send=0.3)
    bell = Track("bell", level=-36, send=0.5)
    for name, j, bi, ch, t0, last in bars_of(FORM):
        vel = {"intro": .7, "chant": .8, "A": .85, "B": .9, "C": .95, "fin": 1.0}[name]
        r = root(ch, 40)
        if name != "intro":
            ostinato(stac, t0, root(ch, 52), OST if ch != "B" else [0, 1, 0, 0, 12, 0, 1, 0], .25, vel * .85)
        for b in (0, 1.5, 3):
            bass.add(t0 + b, 1.0, r - 12 if r > 45 else r, vel)
        if name != "intro":
            oh.chord(t0, 4, stack(ch, 52, 3), vel * .8)
            pad.chord(t0, 4, [p + 12 for p in stack(ch, 52)], vel * .7)
        perc.add(t0, .3, "taiko", vel)
        perc.add(t0 + 2, .3, "taiko", vel * .85)
        if name not in ("intro", "chant"):
            perc.add(t0 + 3.5, .3, "taiko", vel * .8)
            perc.add(t0 + 1, .1, "snare", vel * .8)
            perc.add(t0 + 3, .1, "snare", vel * .8)
        if j == 0:
            perc.add(t0, 2.2, "crash", .85 if name != "intro" else .5)
            bell.add(t0, 3, root(ch, 76), .7)
        if last and name != "intro":
            roll(tim, t0 + 2, 2, "timpani", .5, 1.0, .25)
        if name == "intro":
            line(brass, t0, INTRO_BRASS[j], vel, accent=.1)
            line(horn, t0, INTRO_BRASS[j], vel, shift=-12)
            tim.add(t0, 1, "timpani", .9)
            tim.add(t0 + 2, 1, "timpani", .8)
            if j == 3:
                roll(tim, t0 + 2, 2, "timpani", .4, 1.0, .25)
        if name == "chant":
            line(choir, t0, CHANT[j % 2], .95, accent=.05)
            line(oh, t0, CHANT[j % 2], .8, shift=-12)
        if name == "A":
            line(choir, t0, A[j], .9)
            line(horn, t0, A[j], .6, shift=-12)
        if name == "B":
            line(brass, t0, B[j], .9)
            choir.chord(t0, 4, stack(ch, 55, 3), .6)
        if name == "C":
            line(choir, t0, C[j], .95)
            line(choir, t0, C[j], .7, shift=-5)
            line(brass, t0, C[j], .6, shift=-12)
        if name == "fin":
            line(brass, t0, A[j] if j < 4 else B[j], 1.0)
            line(choir, t0, A[j] if j < 4 else B[j], .9, shift=12)
            line(horn, t0, A[j] if j < 4 else B[j], .8, shift=-12)
    return Score(bpm=140, bars=total_bars(FORM), rt60=2.4, wet=.26, drive=2.2, rms_db=-17,
                 tracks=[choir, oh, brass, horn, stac, pad, bass, perc, tim, bell])
