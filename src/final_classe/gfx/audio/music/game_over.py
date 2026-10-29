"""Musique `game_over` : extrait d'Aerith's Theme (FF VII, Nobuo Uematsu).

Ré majeur / si mineur, 66 BPM, 4 mesures + queue (~20 s), sans boucle.
RECONSTRUITE : de mémoire, on garde le caractère (piano, arpèges ascendants de la main gauche, mélodie douce qui
retombe sur la tonique, nappe de cordes) ; les hauteurs exactes de la mélodie sont approximatives.
Fichier officiel à déposer pour la version exacte.
"""
from __future__ import annotations

from ..score import Score, Track
from .common import arp, root, scale, seq, stack

CH = ["Bm", "G", "Em", "Bm"]
MEL = [[(1.5, "F#5"), (.5, "G5"), (1, "F#5"), (1, "D5")], [(1.5, "B4"), (.5, "D5"), (2, "G5")],
       [(1.5, "G5"), (.5, "F#5"), (1, "E5"), (1, "B4")], [(4, "B4")]]


def build() -> Score:
    piano = Track("piano", level=-22, send=0.5)
    lh = Track("piano", level=-27, send=0.5)
    pad = Track("strings_dark", level=-34, send=0.7)
    harp = Track("harp", level=-33, send=0.55)
    for j, ch in enumerate(CH):
        t0 = j * 4.0
        seq(piano, t0, MEL[j], .75 - .08 * j, legato=1.0)
        lh.add(t0, 4, root(ch, 36), .6)
        for k, p in enumerate(arp(ch, 47, 8)):  # arpège ascendant de la main gauche, en croches
            lh.add(t0 + k * .5, .8, p, .4 + .02 * k)
        pad.chord(t0, 4, stack(ch, 71, 3), .5)
        harp.add(t0 + 2, 2, root(ch, 83), .4)
    piano.add(12, 5, 59, .5)  # si grave, dernière résonance
    return Score(bpm=66, bars=4, loop=False, tail=4.5, fade_out=3.5, rt60=3.4, wet=.32, drive=1.4, rms_db=-23,
                 tracks=[piano, lh, pad, harp])
