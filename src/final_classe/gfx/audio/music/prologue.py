"""Musique `prologue` : reprise de Those Chosen by the Planet (FF VII, Nobuo Uematsu).

Ré mineur, 85,5 BPM, 16 mesures (45 s), boucle. RECONSTRUITE : de mémoire, on garde l'ambiance (trémolo grave de
cordes, battement lourd, chœur sourd, cloche, plainte descendante au cor sur le mode mineur avec sensible do#).
Les hauteurs exactes de la mélodie et la forme officielle ne sont pas garanties. Fichier officiel à déposer pour la version exacte.
"""
from __future__ import annotations

from ..score import Score, Track
from .common import bars_of, mel, root, scale, stack, total_bars

FORM = [("A", ["Dm", "Dm", "Bb", "A"]), ("B", ["Dm", "Gm", "Bb", "A"]),
        ("C", ["Dm", "F", "Gm", "Dm"]), ("D", ["Bb", "Bb", "A", "A"])]
sc = scale(62, "minor")  # ré4 : 0 ré,1 mi,2 fa,3 sol,4 la,5 si♭,6 do
CS = (6, 1)  # do# (sensible)
MEL = {
    "A": [[(2, 4), (1, 5), (1, 4)], [(3, 2), (1, 1)], [(2, 2), (1, 3), (1, 2)], [(1, 1), (1, CS), (2, 1)]],
    "B": [[(1.5, 7), (.5, 6), (1, 5), (1, 4)], [(2, 5), (1, 4), (1, 3)], [(1, 7), (1, 5), (2, 2)], [(2, 4), (2, CS)]],
    "C": [[(2, 9), (1, 8), (1, 7)], [(1, 9), (1, 7), (2, 5)], [(2, 8), (1, 7), (1, 5)], [(4, 7)]],
    "D": [[(4, 5)], [(2, 5), (2, 6)], [(4, CS)], [(2, CS), (2, 4)]],
}


def build() -> Score:
    trem = Track("strings_stac", level=-27, send=0.3)
    cello = Track("strings_dark", level=-27, send=0.3)
    taiko = Track("perc", level=-21, send=0.3)
    horn = Track("horn", level=-24, send=0.4)
    lead = Track("strings_dark", level=-26, send=0.4)
    choir = Track("choir_oh", level=-31, send=0.5)
    tim = Track("timpani", level=-27, send=0.4)
    bell = Track("bell", level=-31, send=0.6)
    for name, j, bi, ch, t0, last in bars_of(FORM):
        vel = {"A": .5, "B": .65, "C": .8, "D": .9}[name]
        r, f = root(ch, 38), root(ch, 38) + 7
        for k in range(16):  # trémolo en doubles croches sur fondamentale et quinte
            trem.add(t0 + k * .25, .22, r if k % 4 < 2 else f, vel * (.45 + .25 * (k % 4 == 0)))
        cello.add(t0, 3.95, r - 12 + 12, vel * .9)
        taiko.add(t0, .3, "taiko", vel)
        if j == 0:
            bell.add(t0, 3, root(ch, 74), .6)
        taiko.add(t0 + 2.5, .3, "taiko", vel * .7)
        if name in ("C", "D"):
            taiko.add(t0 + 1.5, .3, "taiko", vel * .6)
            taiko.add(t0 + 3.5, .3, "taiko", vel * .6)
        if name == "A" and j > 0 or name != "A":
            mel(horn, t0, MEL[name][j], sc, .75 + .15 * (name in "CD"))
        else:
            mel(horn, t0, MEL[name][j], sc, .7)
        if name in ("B", "C"):
            mel(lead, t0, MEL[name][j], sc, .8, shift=12)
        if name in ("C", "D"):
            choir.chord(t0, 4, stack(ch, 57, 3), .8)
        if name == "D" and j >= 2:
            for k in range(8):
                tim.add(t0 + k * .5, .4, "timpani", .5 + .07 * k + .2 * (j - 2))
    return Score(bpm=85.5, bars=total_bars(FORM), rt60=2.2, wet=.28, drive=1.8, rms_db=-19,
                 tracks=[trem, cello, taiko, horn, lead, choir, tim, bell])
