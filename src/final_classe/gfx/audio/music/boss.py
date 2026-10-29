"""Musique `boss` : reprise de « Fight On! » (Final Fantasy VII, Nobuo Uematsu).

168 BPM, la mineur, 42 mesures (60 s), boucle. Forme : intro (2) | A riff (8) | B (8) | A' (8) | C séquence descendante (8) | A'' (8).
Fidélité : APPROXIMATIVE / RECONSTRUITE. Sûr : l'esprit (tempo très rapide, orgue et cuivres martelant un riff de notes
répétées en croches, basse galopante, timbales et chœur). Reconstitué de mémoire, non garanti : les hauteurs exactes de la
mélodie, la tonalité et la progression d'accords.
"""
from __future__ import annotations

from ..score import Score, Track
from ._orch_battle import line, roll
from .common import bars_of, root, stack, total_bars

A = ["Am", "Am", "F", "G", "Am", "Am", "Dm", "E"]
B = ["F", "G", "Am", "Am", "F", "G", "E", "E"]
C = ["Am", "G", "F", "E", "Am", "G", "F", "E"]
FORM = [("intro", ["E", "E"]), ("A", A), ("B", B), ("A2", A), ("C", C), ("A3", A)]
RIFF_A = ["A4:.5 A4:.5 C5:.5 A4:.5 E5:1 D5:.5 C5:.5", "B4:.5 B4:.5 D5:.5 B4:.5 A5:1 G5:.5 E5:.5",
          "A4:.5 A4:.5 C5:.5 A4:.5 F5:1 E5:.5 C5:.5", "B4:.5 B4:.5 D5:.5 B4:.5 G5:1 F5:.5 D5:.5",
          "A4:.5 A4:.5 C5:.5 A4:.5 E5:1 D5:.5 C5:.5", "E5:.5 E5:.5 A5:.5 E5:.5 C6:1 B5:.5 A5:.5",
          "D5:.5 D5:.5 F5:.5 D5:.5 A5:1 G5:.5 F5:.5", "E5:1 G#5:1 B5:1 E6:1"]
MEL_B = ["C6:1.5 A5:.5 F5:2", "D6:1.5 B5:.5 G5:2", "E6:2 C6:1 A5:1", "A5:2 C6:1 E6:1",
         "C6:1.5 A5:.5 F5:2", "D6:1.5 B5:.5 G5:2", "E6:1 D6:1 B5:1 G#5:1", "B5:3 r:1"]
MEL_C = ["A5:1 C6:1 E6:2", "G5:1 B5:1 D6:2", "F5:1 A5:1 C6:2", "G#5:1 B5:1 E6:2"] * 2
INTRO = ["E5:.5 F5:.5 E5:.5 D#5:.5 E5:2", "E5:.5 F5:.5 E5:.5 D#5:.5 B5:2"]


def build() -> Score:
    bass = Track("bass_drive", level=-22, send=0.06)
    organ = Track("organ", level=-27, send=0.3)
    brass = Track("brass", level=-24, send=0.3)
    brass2 = Track("brass", level=-30, send=0.3)
    horn = Track("horn", level=-29, send=0.3)
    stac = Track("strings_stac", level=-29, send=0.25)
    choir = Track("choir", level=-31, send=0.5)
    kit = Track("perc", level=-23, send=0.12)
    tim = Track("timpani", level=-27, send=0.3)
    for name, j, bi, ch, t0, last in bars_of(FORM):
        vel = {"intro": .8, "A": .85, "B": .9, "A2": .95, "C": .9, "A3": 1.0}[name]
        r = root(ch, 33)
        # basse galopante : croches pointées
        for k, off in enumerate([0, 0, 12, 0, 0, 0, 12, 7]):
            bass.add(t0 + k * .5, .4, r + off, vel * (1 if k % 2 == 0 else .7))
        organ.chord(t0, 4, [p for p in stack(ch, 48)], vel * .7)
        # batterie
        for b in (0, 1.5, 2, 3.5) if name != "intro" else (0, 2):
            kit.add(t0 + b, .2, "kick", vel)
        for b in (1, 3):
            kit.add(t0 + b, .2, "snare", vel)
        for k in range(8):
            kit.add(t0 + k * .5, .1, "hat", .5 if k % 2 else .75)
        if j == 0:
            kit.add(t0, 2, "crash", .8)
            tim.add(t0, 1, "timpani", .9)
        if last:
            roll(kit, t0 + 3, 1, "snare", .5, 1, .125)
            roll(tim, t0 + 2.5, 1.5, "timpani", .5, 1, .25)
        if name in ("A", "A2", "A3"):
            line(brass, t0, RIFF_A[j], vel, accent=.05)
            line(organ, t0, RIFF_A[j], .75)
            if name != "A":
                line(brass2, t0, RIFF_A[j], .8, shift=-5)
                line(horn, t0, RIFF_A[j], .8, shift=-12)
            for k in range(8):
                stac.add(t0 + k * .5, .4, r + 24, .5)
        if name == "B":
            line(brass, t0, MEL_B[j], vel)
            line(choir, t0, MEL_B[j], .8)
            stac.chord(t0, 4, [p + 12 for p in stack(ch, 55)], .5)
        if name == "C":
            line(brass, t0, MEL_C[j], vel)
            line(choir, t0, MEL_C[j], .85, shift=-12)
            line(horn, t0, MEL_C[j], .7, shift=-12)
        if name == "intro":
            line(brass, t0, INTRO[j], vel)
            line(organ, t0, INTRO[j], .9, shift=-12)
    return Score(bpm=168, bars=total_bars(FORM), rt60=1.8, wet=.22, drive=2.4, rms_db=-17,
                 tracks=[bass, organ, brass, brass2, horn, stac, choir, kit, tim])
