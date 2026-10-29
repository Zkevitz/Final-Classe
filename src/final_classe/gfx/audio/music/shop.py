"""Musique `shop` : reprise de Cid's Theme (FF VII, Nobuo Uematsu).

Sol majeur, 100 BPM avec swing, 16 mesures (38 s), boucle. RECONSTRUITE : on ne se souvient pas de la mélodie avec
certitude ; on garde le caractère (allure sautillante, marimba, contrebasse en marche, cuivres légers en réponse).
Forme : A (4) | A bis (4) | B plus haut avec cuivres (4) | A' avec dominante finale (4). Fichier officiel à déposer
pour la version exacte.
"""
from __future__ import annotations

from ..score import Score, Track
from .common import bars_of, mel, parse, root, scale, stack, total_bars

FORM = [("A", ["G", "Em", "C", "D"]), ("A2", ["G", "Em", "Am", "D"]), ("B", ["C", "D", "Bm", "Em"]), ("A3", ["C", "D", "G", "D"])]
sc = scale(67, "major")  # sol4 : 0 sol,1 la,2 si,3 do,4 ré,5 mi,6 fa#
MEL = [
    [(.5, 2), (.5, 4), (.5, 7), (.5, 4), (1, 2), (1, 0)], [(.5, 2), (.5, 4), (.5, 5), (.5, 4), (1, 2), (1, 5)],
    [(.5, 3), (.5, 5), (.5, 7), (.5, 5), (1, 3), (1, 5)], [(.5, 4), (.5, 6), (.5, 8), (.5, 6), (2, 4)],
    [(1, 7), (.5, 8), (.5, 7), (1, 4), (1, 2)], [(1, 5), (.5, 6), (.5, 5), (1, 2), (1, 5)],
    [(1, 8), (.5, 7), (.5, 5), (1, 3), (1, 1)], [(1, 4), (1, 6), (2, 8)],
    [(2, 7), (1, 5), (1, 3)], [(2, 6), (1, 8), (1, 6)], [(1, 9), (1, 8), (1, 6), (1, 4)], [(2, 5), (1, 7), (1, 5)],
    [(.5, 3), (.5, 5), (.5, 7), (.5, 5), (1, 10), (1, 7)], [(.5, 4), (.5, 6), (.5, 8), (.5, 6), (1, 11), (1, 8)],
    [(1, 7), (1, 9), (1, 11), (1, 9)], [(2, 8), (1, 6), (1, 4)],
]


def build() -> Score:
    mar = Track("marimba", level=-22, send=0.3)
    gtr = Track("guitar", level=-27, send=0.25)
    bass = Track("upright", level=-23, send=0.1)
    perc = Track("perc", level=-34, send=0.2)
    vib = Track("bell", level=-38, send=0.4)
    hrn = Track("horn", level=-30, send=0.3)
    forms = list(bars_of(FORM))
    for name, j, bi, ch, t0, last in forms:
        nxt = forms[(bi + 1) % len(forms)][3]
        r = root(ch, 36)
        pc, iv = parse(ch)
        third, fifth = r + iv[1], r + 7
        # marche : racine, tierce, quinte, note d'approche chromatique vers la racine suivante
        approach = root(nxt, 36) + (-1 if root(nxt, 36) > r else 1)
        for b, p, v in ((0, r, 1.0), (1, third, .7), (2, fifth, .8), (3, approach, .65)):
            bass.add(t0 + b, .8, p, v)
        # guitare : accord sur les contretemps 2 et 4 (swingués par le moteur sur les croches)
        for b in (1.5, 3.5):
            gtr.chord(t0 + b, .4, stack(ch, 55, 3), .6)
        gtr.add(t0, .5, root(ch, 52), .5)
        mel(mar, t0, MEL[bi], sc, .85)
        if name in ("B", "A3"):
            mel(hrn, t0, MEL[bi], sc, .6, shift=-12)
        if name == "B":
            mel(vib, t0, MEL[bi], sc, .6, shift=12)
        for k in range(8):
            if k % 2:
                perc.add(t0 + k * .5, .1, "hat", .5)
        perc.add(t0 + 1, .1, "rim", .6)
        perc.add(t0 + 3, .1, "rim", .6)
    return Score(bpm=100, bars=total_bars(FORM), rt60=1.1, wet=.15, drive=1.4, swing=.85, rms_db=-20,
                 tracks=[mar, gtr, bass, perc, vib, hrn])
