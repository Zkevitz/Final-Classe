"""Musique `victory` : reprise de la Victory Fanfare (série Final Fantasy, version FF VII, Nobuo Uematsu).

Do majeur, 4/4, 150 BPM, jingle de 5,0 s sans boucle.
SÛR (docs/AUDIO-REFERENCES.md) : do x3 en triolet, do tenu, la♭-si♭-do en noires, broderie sur le do, accord final plein.
RECONSTITUÉ : l'harmonisation et le détail de la broderie.
"""
from __future__ import annotations

from ..score import Score, Track
from .common import seq

T = 1 / 3  # triolet de croches (1 temps = 3 notes)


def build() -> Score:
    brass = Track("brass", level=-19, send=0.3)
    horn = Track("horn", level=-22, send=0.3)
    low = Track("brass", level=-24, send=0.3)
    tim = Track("timpani", level=-22, send=0.3)
    perc = Track("perc", level=-27, send=0.3)
    strings = Track("strings", level=-28, send=0.4)
    # ta-ta-ta TAAA (do x3 en triolet, do tenu) | ta-TAA, ta-TAA : la♭, si♭, do en noires, broderie sur le do | accord plein
    mel = [(T, "C5"), (T, "C5"), (T, "C5"), (2, "C5"), (1, "Ab4"), (1, "Bb4"), (T, "C5"), (T, "D5"), (T, "C5")]
    seq(brass, 0, mel, .95, legato=.92)
    seq(horn, 0, [(T, "E4"), (T, "E4"), (T, "E4"), (2, "E4"), (1, "F4"), (1, "G4"), (1, "G4")], .75, legato=.92)
    seq(low, 0, [(3, "C3"), (1, "Ab2"), (1, "Bb2"), (1, "C3")], .85)
    tf = 7
    brass.chord(tf, 5, ["C5", "E5", "G5", "C6"], 1.0)
    horn.chord(tf, 5, ["C4", "G4", "E5"], .9)
    low.chord(tf, 5, ["C2", "C3", "G3"], .95)
    strings.chord(0, 12, ["C4", "E4", "G4"], .6)
    tim.add(tf, 5, "timpani", 1.0)
    perc.add(tf, 5, "crash", 1.0)
    for b in (0, 3, 4, 5, 6):
        tim.add(b, .4, "timpani", .8 if b % 2 == 0 else .55)
    for k in range(9):
        perc.add(k * T, .1, "snare", .3 + .02 * k)
    return Score(bpm=150, bars=3, loop=False, tail=.2, fade_out=.8, rt60=1.2, wet=.2, drive=2.0, rms_db=-17,
                 tracks=[brass, horn, low, strings, tim, perc])
