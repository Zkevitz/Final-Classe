"""Instruments synthétisés : chaque fonction rend une note (durée du corps + queue de relâchement)."""
from __future__ import annotations

import numpy as np

from .synth import (adsr, additive, bandpass, exp_env, highpass, lowpass, phase_of, saw_weights,
                    soft_clip, sweep, vibrato)


def _cents(c: float) -> float:
    return 2.0 ** (c / 1200.0)


def strings(f, dur, vel, sr, rng, bright=1.0, staccato=False):
    """Section de cordes : 3 voix désaccordées, vibrato tardif, attaque douce."""
    n_sus = int(dur * sr)
    a = min(0.14, dur * 0.35) if not staccato else 0.02
    env = adsr(n_sus, sr, a, 0.08, 0.85, 0.22 if not staccato else 0.08)
    n = len(env)
    w = saw_weights(24, 1.0) * np.exp(-np.arange(24) / (9.0 * bright))
    out = np.zeros(n)
    for c in (-8, 0, 8):
        vib = vibrato(n, sr, rng.uniform(4.8, 5.6), 0.0035, 0.12, 0.3, rng)
        out += additive(phase_of(f * _cents(c) * vib, n, sr), f, sr, w)
    return out * env * (0.12 * vel)


def brass(f, dur, vel, sr, rng, bright=0.9):
    """Cuivres : harmoniques qui s'éclairent après l'attaque, léger glissando d'attaque."""
    n_sus = int(dur * sr)
    env = adsr(n_sus, sr, min(0.045, dur * 0.3), 0.1, 0.8, 0.12)
    n = len(env)
    t = np.arange(n) / sr
    tv = np.clip(0.50 + (bright - 0.5) * (1 - np.exp(-t / 0.07)), 0.1, 0.97) * (0.85 + 0.15 * vel)
    fr = f * (1 - 0.025 * np.exp(-t / 0.04)) * vibrato(n, sr, 5.0, 0.002, 0.25, 0.3, rng)
    out = np.zeros(n)
    for c in (-5, 5):
        out += additive(phase_of(fr * _cents(c), n, sr), f, sr, saw_weights(22, 0.7), tv)
    breath = highpass(rng.standard_normal(n), sr, 2500) * exp_env(n, sr, 0.05) * 0.03
    return (out * 0.1 + breath) * env * vel


def horn(f, dur, vel, sr, rng):
    """Cor : cuivre plus sombre."""
    return brass(f, dur, vel, sr, rng, bright=0.62) * 1.2


def bass(f, dur, vel, sr, rng, drive=0.0):
    """Basse électrique-synthé : scie filtrée + sous-octave sinus."""
    n_sus = int(dur * sr)
    env = adsr(n_sus, sr, 0.004, 0.12, 0.65, 0.07)
    n = len(env)
    ph = phase_of(f, n, sr)
    t = np.arange(n) / sr
    tv = 0.35 + 0.5 * np.exp(-t / 0.12)
    out = additive(ph, f, sr, saw_weights(16, 1.0), tv) * 0.45 + np.sin(ph) * 0.7
    if drive > 0:
        out = soft_clip(out, 1 + drive * 4) * 0.7
    return out * env * vel * 0.55


def _partials(f, n, sr, ratios, amps, taus, rng, inharm=0.0):
    t = np.arange(n) / sr
    out = np.zeros(n)
    for r, a, tau in zip(ratios, amps, taus):
        fr = f * r * np.sqrt(1 + inharm * r * r)
        if fr > 0.45 * sr:
            break
        out += a * np.sin(2 * np.pi * fr * t + rng.uniform(0, 6.28)) * np.exp(-t / tau)
    return out


def harp(f, dur, vel, sr, rng):
    """Harpe : partiels à décroissance rapide, pincement net."""
    n = int((2.2 + 1.2 * (110 / max(f, 110))) * sr)
    K = 14
    k = np.arange(1, K + 1)
    out = _partials(f, n, sr, k, (1 / k ** 1.3) * (0.6 + 0.4 * vel), 1.6 / (1 + 0.55 * k), rng, 0.00008)
    click = highpass(rng.standard_normal(n), sr, 3000) * exp_env(n, sr, 0.004) * 0.02 * vel
    return (out * 0.35 + click) * vel


def piano(f, dur, vel, sr, rng):
    """Piano : deux cordes légèrement désaccordées, marteau, relâchement à la fin de la note."""
    n_sus = int(dur * sr)
    ring = 0.35
    n = n_sus + int(ring * sr)
    K = 18
    k = np.arange(1, K + 1)
    amps = (1 / k ** 1.15) * np.exp(-k / (3 + 9 * vel))
    base_tau = 2.8 / (1 + 0.8 * (f / 261.0))
    out = np.zeros(n)
    for c in (-2.5, 2.5):
        out += _partials(f * _cents(c), n, sr, k, amps, base_tau / (1 + 0.5 * k), rng, 0.00025)
    thump = lowpass(rng.standard_normal(n), sr, 1200) * exp_env(n, sr, 0.012) * 0.04
    rel = np.ones(n)
    rel[n_sus:] = np.linspace(1, 0, n - n_sus) ** 2
    return (out * 0.28 + thump * vel) * rel * vel


def bell(f, dur, vel, sr, rng):
    """Cloche cristalline : partiels inharmoniques."""
    n = int((1.6 + dur) * sr)
    r = np.array([1.0, 2.0, 2.76, 4.07, 5.40, 6.8, 8.93])
    a = np.array([1.0, 0.5, 0.6, 0.3, 0.25, 0.12, 0.08])
    tau = np.array([1.5, 1.0, 0.9, 0.5, 0.4, 0.25, 0.15])
    return _partials(f, n, sr, r, a, tau, rng) * 0.22 * vel


def marimba(f, dur, vel, sr, rng):
    """Marimba : fondamentale + partiel à 4 fois, déclin court."""
    n = int(0.9 * sr)
    out = _partials(f, n, sr, [1, 3.9, 9.2], [1.0, 0.35, 0.08], [0.35, 0.09, 0.03], rng)
    return out * 0.4 * vel


def pizz(f, dur, vel, sr, rng):
    """Cordes pincées : scie filtrée à décroissance rapide."""
    n = int(0.45 * sr)
    ph = phase_of(f, n, sr)
    t = np.arange(n) / sr
    out = additive(ph, f, sr, saw_weights(16, 1.0), np.exp(-t / 0.09) * 0.6 + 0.2)
    return out * exp_env(n, sr, 0.11) * 0.22 * vel


def choir(f, dur, vel, sr, rng, vowel="ah"):
    """Chœur : harmoniques pondérées par des formants, 3 voix, souffle."""
    n_sus = int(dur * sr)
    env = adsr(n_sus, sr, min(0.25, dur * 0.4), 0.15, 0.85, 0.35)
    n = len(env)
    formants = {"ah": ((800, 1.0, 130), (1150, 0.55, 150), (2900, 0.25, 300), (3500, 0.12, 300)),
                "oh": ((450, 1.0, 100), (800, 0.45, 120), (2830, 0.12, 300), (3500, 0.06, 300))}[vowel]
    K = max(1, min(40, int(0.45 * sr / f)))
    k = np.arange(1, K + 1)
    spec = sum(a * np.exp(-((k * f - fc) / bw) ** 2) for fc, a, bw in formants) + 0.03
    w = spec / k ** 0.6
    out = np.zeros(n)
    for c in (-9, 0, 9):
        vib = vibrato(n, sr, rng.uniform(4.6, 5.8), 0.006, 0.2, 0.4, rng)
        out += additive(phase_of(f * _cents(c) * vib, n, sr), f, sr, w)
    breath = bandpass(rng.standard_normal(n), sr, 800, 3500) * 0.01
    return (out * 0.06 + breath) * env * vel


def flute(f, dur, vel, sr, rng):
    """Flûte : presque sinusoïdale, souffle, vibrato."""
    n_sus = int(dur * sr)
    env = adsr(n_sus, sr, min(0.07, dur * 0.3), 0.05, 0.9, 0.12)
    n = len(env)
    vib = vibrato(n, sr, 5.3, 0.004, 0.2, 0.3, rng)
    out = additive(phase_of(f * vib, n, sr), f, sr, np.array([1, 0.3, 0.1, 0.04]))
    breath = bandpass(rng.standard_normal(n), sr, 2500, 6500) * 0.05 * (0.5 + 0.5 * exp_env(n, sr, 0.08))
    return (out * 0.3 + breath) * env * vel


def organ(f, dur, vel, sr, rng):
    """Orgue à tirettes avec léger Leslie."""
    n_sus = int(dur * sr)
    env = adsr(n_sus, sr, 0.015, 0.02, 0.95, 0.08)
    n = len(env)
    vib = vibrato(n, sr, 6.2, 0.0025, 0.0, 0.01, rng)
    ph = phase_of(f * vib, n, sr)
    out = np.zeros(n)
    for r, a in ((1, 1.0), (2, 0.8), (3, 0.55), (4, 0.5), (6, 0.3), (8, 0.22)):
        if f * r < 0.45 * sr:
            out += a * np.sin(r * ph)
    return out * env * vel * 0.12


def guitar(f, dur, vel, sr, rng):
    """Guitare pincée : peu de partiels, déclin moyen, attaque de médiator."""
    n = int(1.1 * sr)
    k = np.arange(1, 11)
    out = _partials(f, n, sr, k, (1 / k ** 1.1) * (0.5 + 0.5 * vel), 0.55 / (1 + 0.45 * k), rng, 0.00005)
    pick = bandpass(rng.standard_normal(n), sr, 1500, 5000) * exp_env(n, sr, 0.006) * 0.03
    return (out * 0.35 + pick) * vel


def upright(f, dur, vel, sr, rng):
    """Contrebasse pizzicato : fondamentale ronde, harmoniques brèves."""
    n = int(0.9 * sr)
    out = _partials(f, n, sr, [1, 2, 3, 4], [1.0, 0.5, 0.25, 0.12], [0.45, 0.2, 0.1, 0.06], rng)
    thud = lowpass(rng.standard_normal(n), sr, 600) * exp_env(n, sr, 0.01) * 0.08
    return (out * 0.55 + thud) * vel


# ------------------------------------------------------------------ batterie
def _noise(rng, n):
    return rng.standard_normal(n)


def drum(name: str, vel: float, sr: int, rng) -> np.ndarray:
    """Percussions : kick, snare, hat, hat_open, tom_*, timpani, taiko, crash, rim."""
    if name == "kick":
        n = int(0.4 * sr)
        body = np.sin(sweep(130, 45, n, sr, 3.0)) * exp_env(n, sr, 0.11)
        click = lowpass(_noise(rng, n), sr, 4000) * exp_env(n, sr, 0.004) * 0.35
        return (body * 0.9 + click) * vel
    if name == "snare":
        n = int(0.35 * sr)
        nz = bandpass(_noise(rng, n), sr, 1200, 9000) * exp_env(n, sr, 0.085)
        tone = np.sin(2 * np.pi * 195 * np.arange(n) / sr) * exp_env(n, sr, 0.05) * 0.45
        return (nz * 0.55 + tone) * vel
    if name in ("hat", "hat_open"):
        n = int((0.07 if name == "hat" else 0.3) * sr)
        tau = 0.018 if name == "hat" else 0.09
        return highpass(_noise(rng, n), sr, 7000) * exp_env(n, sr, tau) * 0.22 * vel
    if name.startswith("tom"):
        f0 = {"tom_hi": 190, "tom_mid": 140, "tom_lo": 100}.get(name, 140)
        n = int(0.5 * sr)
        body = np.sin(sweep(f0 * 1.5, f0, n, sr, 4.0)) * exp_env(n, sr, 0.15)
        return (body + lowpass(_noise(rng, n), sr, 2500) * exp_env(n, sr, 0.01) * 0.2) * 0.8 * vel
    if name == "timpani":
        n = int(1.2 * sr)
        t = np.arange(n) / sr
        body = np.sin(sweep(105, 80, n, sr, 6.0)) * exp_env(n, sr, 0.5)
        body += 0.35 * np.sin(2 * np.pi * 120 * t) * exp_env(n, sr, 0.3)
        return (body + lowpass(_noise(rng, n), sr, 900) * exp_env(n, sr, 0.015) * 0.5) * 0.8 * vel
    if name == "taiko":
        n = int(1.0 * sr)
        body = np.sin(sweep(95, 52, n, sr, 5.0)) * exp_env(n, sr, 0.28)
        slap = bandpass(_noise(rng, n), sr, 300, 2500) * exp_env(n, sr, 0.03) * 0.5
        return (body + slap) * 0.95 * vel
    if name == "crash":
        n = int(2.2 * sr)
        nz = highpass(_noise(rng, n), sr, 3500)
        env = exp_env(n, sr, 0.55) * 0.8 + exp_env(n, sr, 0.08) * 0.5
        return nz * env * 0.3 * vel
    if name == "rim":
        n = int(0.08 * sr)
        return bandpass(_noise(rng, n), sr, 1500, 5000) * exp_env(n, sr, 0.012) * 0.5 * vel
    return np.zeros(int(0.05 * sr))


INSTRUMENTS = {
    "strings": strings, "brass": brass, "horn": horn, "bass": bass, "harp": harp,
    "piano": piano, "bell": bell, "marimba": marimba, "pizz": pizz, "choir": choir,
    "flute": flute, "organ": organ, "guitar": guitar, "upright": upright,
    "strings_stac": lambda f, d, v, sr, rng: strings(f, d, v, sr, rng, staccato=True),
    "strings_dark": lambda f, d, v, sr, rng: strings(f, d, v, sr, rng, bright=0.6),
    "choir_oh": lambda f, d, v, sr, rng: choir(f, d, v, sr, rng, vowel="oh"),
    "bass_drive": lambda f, d, v, sr, rng: bass(f, d, v, sr, rng, drive=1.0),
}
