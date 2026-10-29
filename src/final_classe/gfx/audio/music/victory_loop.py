"""Musique `victory_loop` : suite en boucle de la Victory Fanfare (Final Fantasy, Nobuo Uematsu).

Do majeur, 96 BPM, 8 mesures (20 s). RECONSTRUITE : la fanfare officielle n'a pas de partie bouclée ;
on la prolonge avec son motif (do-do-do en triolet, la♭-si♭-do) en questions-réponses, sur la cadence
do / la♭ / si♭ / do typique des fanfares de victoire de la série, en cordes pizzicato, cuivres légers et flûte.
"""
from __future__ import annotations

from ..score import Score, Track
from .common import arp, bars_of, root, seq, total_bars

T = 1 / 3
FORM = [("A", ["C", "C", "Ab", "Bb", "C", "F", "Bb", "G"])]
MOTIF_Q = [(T, "C5"), (T, "C5"), (T, "C5"), (3 * T, "C5"), (T, "Ab4"), (T, "Bb4"), (4 * T, "C5")]      # question
MOTIF_R = [(T, "G4"), (T, "G4"), (T, "G4"), (3 * T, "G4"), (T, "Bb4"), (T, "Ab4"), (4 * T, "G4")]
MEL = {0: MOTIF_Q, 1: [(2, "E5"), (1, "D5"), (1, "C5")],
       2: [(T, "Ab4"), (T, "Ab4"), (T, "Ab4"), (3 * T, "Ab4"), (T, "Bb4"), (T, "C5"), (4 * T, "Eb5")],
       3: [(2, "D5"), (1, "C5"), (1, "Bb4")],
       4: [(T, "C5"), (T, "C5"), (T, "C5"), (3 * T, "E5"), (T, "D5"), (T, "C5"), (4 * T, "G5")],
       5: [(1, "A5"), (1, "G5"), (1, "F5"), (1, "A4")],
       6: [(T, "Bb4"), (T, "C5"), (T, "D5"), (3 * T, "F5"), (T, "Eb5"), (T, "D5"), (4 * T, "Bb4")],
       7: [(2, "G5"), (1, "F5"), (1, "D5")]}


def build() -> Score:
    pizz = Track("pizz", level=-26, send=0.3)
    bass = Track("upright", level=-25, send=0.15)
    flute = Track("flute", level=-26, send=0.4)
    brass = Track("brass", level=-27, send=0.3)
    harp = Track("harp", level=-31, send=0.4)
    perc = Track("perc", level=-33, send=0.2)
    for name, j, bi, ch, t0, last in bars_of(FORM):
        for k, p in enumerate(arp(ch, 57, 8)):
            pizz.add(t0 + k * .5, .4, p, .7 if k % 2 == 0 else .5)
        bass.add(t0, .9, root(ch, 36), .9)
        bass.add(t0 + 2, .9, root(ch, 36) + 7, .75)
        harp.add(t0, 1, root(ch, 72), .5)
        perc.add(t0 + 1, .1, "rim", .5)
        perc.add(t0 + 3, .1, "rim", .5)
        seq(flute, t0, MEL[j], .8, legato=.9)
        if j in (0, 2, 4, 6):
            seq(brass, t0, MEL[j], .6, legato=.9)
    return Score(bpm=96, bars=total_bars(FORM), rt60=1.4, wet=.2, drive=1.5, rms_db=-21,
                 tracks=[pizz, bass, flute, brass, harp, perc])
