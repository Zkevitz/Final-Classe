"""Briques de synthèse numpy : oscillateurs, enveloppes, filtres spectraux, réverbération."""
from __future__ import annotations

import numpy as np

SR_MUSIC = 32000
SR_SFX = 44100


def db(x: float) -> float:
    """Décibels vers gain linéaire."""
    return 10.0 ** (x / 20.0)


def midi_to_hz(m: float) -> float:
    return 440.0 * 2.0 ** ((m - 69.0) / 12.0)


_NOTES = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}


def note(name: str | int | float) -> float:
    """'A4', 'F#3', 'Bb2' ou numéro MIDI -> numéro MIDI."""
    if not isinstance(name, str):
        return float(name)
    s = name.strip().lower()
    n = _NOTES[s[0]]
    i = 1
    while i < len(s) and s[i] in "#b":
        n += 1 if s[i] == "#" else -1
        i += 1
    return float(n + 12 * (int(s[i:]) + 1))


# ----------------------------------------------------------------- enveloppes
def adsr(n_sus: int, sr: int, a: float, d: float, s: float, r: float) -> np.ndarray:
    """Enveloppe ADSR : n_sus échantillons avant le relâchement, puis r secondes de release."""
    n_rel = max(1, int(r * sr))
    a_n, d_n = max(1, int(a * sr)), max(1, int(d * sr))
    xs = [0, a_n, a_n + d_n, max(a_n + d_n, n_sus), max(a_n + d_n, n_sus) + n_rel]
    n = xs[-1] + 1
    env = np.interp(np.arange(n), xs, [0.0, 1.0, s, s, 0.0])
    if n_sus < a_n + d_n:  # note très courte : on coupe le haut de l'enveloppe
        pass
    return env


def exp_env(n: int, sr: int, tau: float) -> np.ndarray:
    """Décroissance exponentielle (tau en secondes)."""
    return np.exp(-np.arange(n) / (tau * sr))


def fade(x: np.ndarray, sr: int, ms_in: float = 3.0, ms_out: float = 8.0) -> np.ndarray:
    """Fondus courts aux extrémités (anti-clics)."""
    x = x.copy()
    a, b = min(len(x), int(sr * ms_in / 1000)), min(len(x), int(sr * ms_out / 1000))
    if a > 1:
        x[:a] *= np.linspace(0, 1, a)
    if b > 1:
        x[-b:] *= np.linspace(1, 0, b)
    return x


# ------------------------------------------------------------------- filtres
def spectral_filter(x: np.ndarray, sr: int, gain_fn) -> np.ndarray:
    """Filtre à phase nulle appliqué dans le domaine fréquentiel."""
    n = len(x)
    f = np.fft.rfftfreq(n, 1.0 / sr)
    return np.fft.irfft(np.fft.rfft(x) * gain_fn(f), n)


def lowpass(x, sr, fc, order=2):
    return spectral_filter(x, sr, lambda f: 1.0 / np.sqrt(1.0 + (f / fc) ** (2 * order)))


def highpass(x, sr, fc, order=2):
    def g(f):
        r = (f / fc) ** (2 * order)
        return np.sqrt(r / (1.0 + r))
    return spectral_filter(x, sr, g)


def bandpass(x, sr, lo, hi, order=2):
    return highpass(lowpass(x, sr, hi, order), sr, lo, order)


def swept_noise(rng, n: int, sr: int, fc_curve: np.ndarray, q_bands: int = 8) -> np.ndarray:
    """Bruit dont la coupure (passe-bas) suit fc_curve (Hz, n valeurs) : fondu entre bandes."""
    noise = rng.standard_normal(n)
    lo, hi = max(40.0, float(fc_curve.min())), min(sr * 0.45, float(fc_curve.max()) * 1.01 + 1)
    if hi <= lo * 1.05:
        return lowpass(noise, sr, lo, 2)
    cuts = np.geomspace(lo, hi, q_bands)
    pos = np.interp(np.log(np.clip(fc_curve, lo, hi)), np.log(cuts), np.arange(q_bands))
    out = np.zeros(n)
    for i, fc in enumerate(cuts):
        w = np.clip(1.0 - np.abs(pos - i), 0.0, 1.0)
        if w.any():
            out += w * lowpass(noise, sr, fc, 2)
    return out


# ------------------------------------------------------------- oscillateurs
def phase_of(freq, n: int, sr: int) -> np.ndarray:
    """Phase (radians) pour une fréquence constante ou un tableau de fréquences."""
    f = np.broadcast_to(np.asarray(freq, dtype=float), (n,))
    return 2.0 * np.pi * np.cumsum(f) / sr


def additive(phase: np.ndarray, f0: float, sr: int, weights: np.ndarray, tvar: np.ndarray | None = None) -> np.ndarray:
    """Somme d'harmoniques k=1..K de poids `weights` ; tvar (0..1) assombrit/éclaire avec le temps (poids^…)."""
    k_max = min(len(weights), max(1, int(0.45 * sr / max(f0, 1.0))))
    ks = np.arange(1, k_max + 1)
    out = np.zeros(len(phase))
    for k, w in zip(ks, weights[:k_max]):
        amp = w if tvar is None else w * tvar ** (k - 1)
        out += amp * np.sin(k * phase)
    return out


def saw_weights(K: int, tilt: float = 1.0) -> np.ndarray:
    k = np.arange(1, K + 1)
    return 1.0 / k ** tilt


def vibrato(n: int, sr: int, rate: float, depth: float, delay: float = 0.15, ramp: float = 0.3, rng=None) -> np.ndarray:
    """Facteur de fréquence (1 + vibrato) avec départ progressif."""
    t = np.arange(n) / sr
    amp = np.clip((t - delay) / max(ramp, 1e-3), 0, 1)
    ph0 = 0.0 if rng is None else rng.uniform(0, 2 * np.pi)
    return 1.0 + depth * amp * np.sin(2 * np.pi * rate * t + ph0)


def sweep(f0: float, f1: float, n: int, sr: int, curve: float = 1.0) -> np.ndarray:
    """Fréquences allant de f0 à f1 (curve>1 : plus rapide au début) -> phase."""
    u = np.linspace(0, 1, n) ** (1.0 / curve)
    f = f0 * (f1 / f0) ** u
    return phase_of(f, n, sr)


# -------------------------------------------------------------- réverbération
def make_ir(sr: int, rt60: float, rng, lp_hz: float = 5500.0, predelay: float = 0.012) -> np.ndarray:
    """Réponse impulsionnelle synthétique : bruit dense, graves persistants, aigus plus courts, premières réflexions."""
    n = int(rt60 * 1.1 * sr)
    t = np.arange(n) / sr
    noise = rng.standard_normal(n)
    low = lowpass(noise, sr, 1800.0, 2) * np.exp(-6.9 * t / rt60)
    high = bandpass(rng.standard_normal(n), sr, 1800.0, lp_hz, 2) * np.exp(-6.9 * t / (rt60 * 0.45))
    ir = low * 1.0 + high * 0.55
    pre = int(predelay * sr)
    ir = np.concatenate([np.zeros(pre), ir])
    for dt_, g in ((0.019, 0.5), (0.031, 0.4), (0.047, 0.3), (0.063, 0.25)):
        i = int(dt_ * sr)
        if i < len(ir):
            ir[i] += g * np.abs(ir).max() * 0.6
    ir /= np.sqrt(np.sum(ir ** 2))
    return ir


def reverb(x: np.ndarray, ir: np.ndarray, circular: bool = False) -> np.ndarray:
    """Convolution FFT. circular=True : la queue se replie sur le début (boucles sans couture)."""
    n = len(x)
    if circular:
        ir = ir[: n - 1]
        return np.fft.irfft(np.fft.rfft(x) * np.fft.rfft(ir, n), n)
    m = n + len(ir)
    return np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[: n + len(ir) - 1]


def soft_clip(x: np.ndarray, drive: float = 1.0) -> np.ndarray:
    return np.tanh(x * drive) / np.tanh(drive) if drive > 0 else x


def normalize(x: np.ndarray, peak_db: float) -> np.ndarray:
    p = float(np.max(np.abs(x))) or 1.0
    return x * (db(peak_db) / p)


def to_int16(x: np.ndarray) -> np.ndarray:
    return np.round(np.clip(x, -1.0, 1.0) * 32767).astype(np.int16)
