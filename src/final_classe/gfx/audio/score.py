"""Moteur de partitions : pistes de notes (en temps musical) -> signal mono mixé avec réverbération."""
from __future__ import annotations

import zlib
from dataclasses import dataclass, field

import numpy as np

from .instruments import INSTRUMENTS, drum
from .synth import SR_MUSIC, db, highpass, make_ir, midi_to_hz, normalize, note, reverb, soft_clip

# note = (beat, durée_en_temps, hauteur, vélocité) ; hauteur : nom/MIDI, ou nom de percussion (str)
DRUMS = {"kick", "snare", "hat", "hat_open", "tom_hi", "tom_mid", "tom_lo", "timpani", "taiko", "crash", "rim"}


@dataclass
class Track:
    inst: str
    notes: list = field(default_factory=list)
    gain: float = 1.0      # niveau dans le mixage (dB)
    send: float = 0.25     # part envoyée à la réverbération (0..1)
    level: float | None = None  # si fourni : RMS cible (dBFS) de la piste quand elle joue (remplace gain)

    def add(self, beat, dur, pitch, vel=0.8):
        self.notes.append((beat, dur, pitch, vel))

    def chord(self, beat, dur, pitches, vel=0.8):
        for p in pitches:
            self.notes.append((beat, dur, p, vel))


@dataclass
class Score:
    bpm: float
    bars: int
    tracks: list
    beats_per_bar: int = 4
    loop: bool = True
    rt60: float = 1.6
    wet: float = 0.22
    peak_db: float = -1.5
    drive: float = 1.2
    seed: int = 7
    swing: float = 0.0     # 0..1 : croches de contretemps retardées (1 = triolet)
    tail: float = 2.5      # secondes de queue ajoutées si pas de boucle
    rms_db: float | None = None  # RMS final visé (dBFS), plafonné par peak_db
    fade_out: float = 0.0  # fondu final (s) pour les non-boucles

    @property
    def beats(self) -> float:
        return self.bars * self.beats_per_bar

    @property
    def seconds(self) -> float:
        return self.beats * 60.0 / self.bpm


def _render_note(tr: Track, pitch, dur_s, vel, sr, variant):
    if isinstance(pitch, str) and pitch in DRUMS:
        return drum(pitch, vel, sr, np.random.default_rng(zlib.crc32(pitch.encode()) + variant))
    f = midi_to_hz(note(pitch))
    return INSTRUMENTS[tr.inst](f, dur_s, vel, sr, np.random.default_rng(int(f * 10) % 9973 + variant))


def render(score: Score, sr: int = SR_MUSIC, raw: bool = False) -> np.ndarray:
    """Rend la partition. En boucle, queues et réverbération sont repliées sur le début."""
    spb = 60.0 / score.bpm
    L0 = int(round(score.seconds * sr))
    L = L0 if score.loop else L0 + int(score.tail * sr)
    tail = int(4.5 * sr)
    rng = np.random.default_rng(score.seed)
    dry = np.zeros(L)
    send = np.zeros(L)
    for tr in score.tracks:
        buf = np.zeros(L + tail)
        cache: dict = {}
        count: dict = {}
        for beat, dur, pitch, vel in tr.notes:
            key = (pitch, round(dur, 3), round(vel, 2))
            c = count.get(key, 0)
            count[key] = c + 1
            variant = c % 3 if isinstance(pitch, str) and pitch in DRUMS else 0
            ck = key + (variant,)
            if ck not in cache:
                cache[ck] = _render_note(tr, pitch, dur * spb, vel, sr, variant)
            sig = cache[ck]
            if score.swing and abs(beat % 1 - 0.5) < 1e-6:
                beat += score.swing / 6.0
            s0 = int(round(beat * spb * sr))
            if s0 >= L0:
                continue
            seg = sig[: L + tail - s0]
            buf[s0:s0 + len(seg)] += seg
        if score.loop:
            out = buf[:L].copy()
            ex = buf[L:]
            out[: len(ex)] += ex
        else:
            out = buf[:L]
        g = db(tr.gain)
        if tr.level is not None:
            hop = int(0.05 * sr)
            ms = (out[: len(out) // hop * hop].reshape(-1, hop) ** 2).mean(1)
            act = ms > ms.max() * 1e-3 if ms.max() > 0 else ms > 0
            g = db(tr.level) / (np.sqrt(ms[act].mean()) if act.any() else 1.0)
        dry += out * g
        send += out * g * tr.send
    ir = make_ir(sr, score.rt60, rng)
    wet = reverb(send, ir, circular=True) if score.loop else reverb(send, ir)[:L]
    mix = dry + wet * score.wet * 4.0
    mix = highpass(mix, sr, 32, 2)
    if not score.loop and score.fade_out > 0:
        k = int(score.fade_out * sr)
        mix[-k:] *= np.linspace(1, 0, k) ** 2
    if not score.loop:
        mix[:int(0.002 * sr)] *= np.linspace(0, 1, int(0.002 * sr))
    if raw:  # niveaux bruts, pour équilibrer les pistes
        return mix
    mix = soft_clip(mix / (np.max(np.abs(mix)) or 1.0), score.drive)
    if score.rms_db is None:
        return normalize(mix, score.peak_db)
    mix *= db(score.rms_db) / (np.sqrt(np.mean(mix ** 2)) or 1.0)
    p = np.max(np.abs(mix))
    return mix * min(1.0, db(score.peak_db) / p)
