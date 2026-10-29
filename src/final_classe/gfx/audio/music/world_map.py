"""Musique `world_map` : reprise du Main Theme of Final Fantasy VII (Nobuo Uematsu).

Do mineur, 108 BPM, 34 mesures (~76 s), boucle, marche majestueuse aux cors.
RECONSTRUITE : on retient de mémoire la tonalité (do mineur), le caractère de marche, le thème d'ouverture
au cor (quinte, sixte bémol, retour à la tonique) et la reprise lyrique à la flûte. Les hauteurs exactes de la
seconde moitié du thème et la basse sont reconstituées. Fichier officiel à déposer pour la version exacte.
"""
from __future__ import annotations

from ..score import Score, Track
from .common import bars_of, hits, mel, root, scale, stack, total_bars

A = ["Cm", "Eb", "Ab", "Fm", "Cm", "Eb", "Fm", "G"]
B = ["Fm", "Ab", "Eb", "Bb", "Fm", "Ab", "G", "G"]
FORM = [("intro", ["Cm", "G"]), ("A", A), ("B", B), ("A2", A), ("B2", B)]
sc = scale(60, "minor")  # do4 (do mineur)
THEME = [[(1, 4), (.5, 5), (.5, 4), (2, 7)], [(1, 6), (.5, 5), (.5, 4), (2, 2)], [(1, 5), (.5, 6), (.5, 7), (2, 9)],
         [(1.5, 8), (.5, 7), (2, 5)], [(1, 4), (.5, 5), (.5, 4), (2, 7)], [(1, 9), (.5, 8), (.5, 6), (2, 4)],
         [(1, 7), (1, 5), (1, 3), (1, 5)], [(1.5, 6), (.5, 8), (2, 4)]]
LYR = [[(2, 9), (1, 8), (1, 7)], [(2, 8), (1, 7), (1, 5)], [(1, 7), (1, 9), (2, 11)], [(1.5, 10), (.5, 9), (2, 8)],
       [(2, 12), (1, 11), (1, 9)], [(1, 10), (1, 9), (2, 8)], [(1, 8), (1, 9), (1, 10), (1, 11)], [(4, 11)]]


def build() -> Score:
    horn = Track("horn", level=-23, send=0.35)
    brass = Track("brass", level=-27, send=0.35)
    flute = Track("flute", level=-25, send=0.4)
    lead = Track("strings", level=-27, send=0.4)
    stac = Track("strings_stac", level=-27, send=0.3)
    bass = Track("bass", level=-23, send=0.1)
    perc = Track("perc", level=-24, send=0.15)
    harp = Track("harp", level=-30, send=0.4)
    tim = Track("timpani", level=-28, send=0.3)
    for name, j, bi, ch, t0, last in bars_of(FORM):
        vel = {"intro": .6, "A": .75, "B": .7, "A2": .9, "B2": .85}[name]
        r = root(ch, 36)
        bass.add(t0, .8, r, vel); bass.add(t0 + 1, .8, r + 7, vel * .8)
        bass.add(t0 + 2, .8, r + 12, vel * .9); bass.add(t0 + 3, .8, r + 7, vel * .8)
        hits(perc, t0, {"kick": [0, 2], "snare": [1, 3], "hat": [0.5, 1.5, 2.5, 3.5]}, vel * .9)
        if last:
            for q in (3.25, 3.5, 3.75):
                perc.add(t0 + q, .1, "snare", .6)
        if name != "B" and name != "B2":
            for b in (.5, 1.5, 2.5, 3.5):
                stac.chord(t0 + b, .3, stack(ch, 57, 3), vel * .8)
        else:
            lead.chord(t0, 4, stack(ch, 57, 3), vel * .7)
            for k, p in enumerate([stack(ch, 60)[i % 3] + 12 * (i // 3) for i in range(8)]):
                harp.add(t0 + k * .5, .5, p, .6)
        if name in ("A", "A2"):
            mel(horn, t0, THEME[j], sc, vel)
            if name == "A2":
                mel(brass, t0, THEME[j], sc, vel * .8, shift=12)
                mel(lead, t0, THEME[j], sc, .7, shift=-12 + 12)
                if j in (0, 4):
                    tim.add(t0, 2, "timpani", .8)
        if name in ("B", "B2"):
            mel(flute, t0, LYR[j], sc, .8)
            if name == "B2":
                mel(horn, t0, LYR[j], sc, .65, shift=-12)
        if name == "intro":
            mel(flute, t0, [(2, 4), (1, 5), (1, 7)] if j == 0 else [(2, 6), (2, 4)], sc, .6)
    return Score(bpm=108, bars=total_bars(FORM), rt60=1.7, wet=.22, drive=1.7, rms_db=-19,
                 tracks=[horn, brass, flute, lead, stac, bass, perc, harp, tim])
