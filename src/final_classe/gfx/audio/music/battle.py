"""Musique `battle` : reprise de « Let the Battles Begin! » (Final Fantasy VII, Nobuo Uematsu).

144 BPM, ré mineur, 36 mesures (60 s), boucle. Forme : intro (4) | A (8) | B (8) | A' (8) | pont (4) | coda (4).
Fidélité : APPROXIMATIVE. Sûr : caractère (ostinato de doubles croches staccato sur pédale avec bande chromatique,
roulement de caisse claire d'intro, batterie rock rapide, cuivres syncopés sur le riff, cordes qui montent).
Reconstitué de mémoire et non garanti : la hauteur exacte des notes de la mélodie, la tonalité (ré mineur choisi) et l'ordre des sections.
"""
from __future__ import annotations

from ..score import Score, Track
from ._orch_battle import line, ostinato, roll
from .common import bars_of, root, stack, total_bars

A = ["Dm", "Dm", "Bb", "C", "Dm", "Dm", "Gm", "A"]
B = ["Bb", "C", "Dm", "Dm", "Bb", "C", "A", "A"]
FORM = [("intro", ["Dm", "Dm", "Dm", "A"]), ("A", A), ("B", B), ("A2", A), ("bridge", ["Gm", "A", "Gm", "A"]),
        ("coda", ["Dm", "Bb", "C", "Dm"])]
MEL_A = ["D5:1.5 D5:.5 F5:1 A5:1", "G5:1.5 F5:.5 E5:1 D5:1", "D5:1.5 D5:.5 F5:1 Bb5:1", "A5:1.5 G5:.5 E5:2",
         "D5:1.5 D5:.5 F5:1 A5:1", "A5:1.5 G5:.5 F5:1 E5:1", "G5:1 A5:1 Bb5:1 D6:1", "C#6:2 A5:1 E5:1"]
MEL_B = ["F5:1 F5:.5 G5:.5 Bb5:2", "E5:1 E5:.5 G5:.5 C6:2", "F5:1 A5:1 D6:2", "C6:1 A5:1 F5:2",
         "F5:1 F5:.5 G5:.5 Bb5:2", "G5:1 G5:.5 A5:.5 C6:1 E6:1", "E6:1.5 D6:.5 C#6:1 A5:1", "A5:3 r:1"]
BRIDGE = ["D6:4", "C#6:4", "D6:2 F6:2", "E6:3 C#6:1"]
CODA = ["D6:1.5 A5:.5 D6:2", "D6:1.5 Bb5:.5 D6:2", "E6:1.5 C6:.5 E6:2", "D6:1 A5:1 F5:1 D5:1"]
HARM = {"Dm": 0, "Bb": 0, "C": 0, "Gm": 0, "A": 0}


def build() -> Score:
    kit = Track("perc", level=-23, send=0.1)
    tim = Track("timpani", level=-28, send=0.3)
    bass = Track("bass_drive", level=-24, send=0.05)
    stac = Track("strings_stac", level=-27, send=0.25)
    run = Track("strings_stac", level=-27, send=0.25)
    brass = Track("brass", level=-24, send=0.3)
    brass2 = Track("brass", level=-30, send=0.3)
    horn = Track("horn", level=-29, send=0.3)
    pad = Track("strings", level=-30, send=0.4)
    harp = Track("harp", level=-36, send=0.4)
    for name, j, bi, ch, t0, last in bars_of(FORM):
        r = root(ch, 38)
        vel = {"intro": .7, "A": .85, "B": .9, "A2": .95, "bridge": .9, "coda": 1.0}[name]
        # basse : pédale en croches avec bande chromatique (note voisine grave, l'effet du riff)
        for k in range(8):
            bass.add(t0 + k * .5, .4, r + (12 if k in (3, 7) else 0) - (1 if k == 5 and j % 2 else 0), vel * (1 if k % 2 == 0 else .7))
        # ostinato de doubles croches en cordes staccato sur la fondamentale
        if not (name == "intro" and j < 2):
            ostinato(stac, t0, root(ch, 50), [0, 0, 12, 0] if name != "bridge" else [0, 7, 12, 7], .25, vel * .8)
        # batterie
        for b in (0, 2, 2.5):
            kit.add(t0 + b, .2, "kick", vel)
        for b in (1, 3):
            kit.add(t0 + b, .2, "snare", vel)
        for k in range(8):
            kit.add(t0 + k * .5, .1, "hat_open" if k == 7 else "hat", .55 if k % 2 else .8)
        if j == 0 and name != "intro":
            kit.add(t0, 2, "crash", .85)
            tim.add(t0, 1, "timpani", .9)
        if name == "intro" and j == 0:
            roll(kit, t0, 3.5, "snare", .25, .8, .25)
        if last and name in ("intro", "A", "B", "A2", "bridge"):
            roll(kit, t0 + 3, 1, "tom_hi", .5, 1, .125)
            roll(tim, t0 + 3, 1, "timpani", .5, 1, .25)
        # harmonie
        if name in ("A", "A2", "B", "coda"):
            pad.chord(t0, 4, [p + 12 for p in stack(ch, 55)], vel * .6)
        if name in ("A2", "B", "bridge", "coda"):
            horn.chord(t0, 4, stack(ch, 50, 3), vel * .7)
        # mélodies
        if name in ("A", "A2"):
            line(brass, t0, MEL_A[j], vel, accent=.05)
            if name == "A2":
                line(brass2, t0, MEL_A[j], .8, shift=-4)
                line(pad, t0, MEL_A[j], .7, shift=12)
        if name == "B":
            line(brass, t0, MEL_B[j], vel, accent=.05)
            line(pad, t0, MEL_B[j], .7, shift=12)
            for k in range(8):  # arpèges de harpe en soutien
                harp.add(t0 + k * .5, .4, stack(ch, 62)[k % 3] + 12 * (k // 3 % 2), .5)
        if name == "bridge":
            line(brass, t0, BRIDGE[j], vel)
            line(pad, t0, BRIDGE[j], .8, shift=-12)
            for k in range(8):
                run.add(t0 + k * .5, .45, [62, 66, 69, 74][k % 4] + 2 * j, .6 + .04 * k)
        if name == "coda":
            line(brass, t0, CODA[j], vel)
            line(brass2, t0, CODA[j], .9, shift=-7)
            line(pad, t0, CODA[j], .8, shift=12)
    return Score(bpm=144, bars=total_bars(FORM), rt60=1.5, wet=.2, drive=2.4, rms_db=-17,
                 tracks=[kit, tim, bass, stac, run, brass, brass2, horn, pad, harp])
