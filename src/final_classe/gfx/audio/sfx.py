"""Bruitages synthétisés (44,1 kHz mono) : un générateur par id de docs/AUDIO.md §4."""
from __future__ import annotations

import zlib

import numpy as np

from .synth import (SR_SFX as SR, bandpass, fade, highpass, lowpass, normalize, reverb, soft_clip,
                    swept_noise, sweep)


# ------------------------------------------------------------------ outils
def N(d):
    return int(d * SR)


def T(d):
    return np.arange(N(d)) / SR


def dec(d, tau):
    return np.exp(-T(d) / tau)


def swell(d, peak=0.5, a=2.0, r=2.0):
    """Enveloppe qui monte jusqu'à `peak` (fraction de d) puis redescend."""
    u = np.linspace(0, 1, N(d))
    return np.where(u < peak, (u / peak) ** a, ((1 - u) / (1 - peak)) ** r)


def tone(f, d, tau=None, harm=(1.0,)):
    t = T(d)
    out = sum(a * np.sin(2 * np.pi * f * (k + 1) * t) for k, a in enumerate(harm))
    return out * (dec(d, tau) if tau else 1.0)


def chirp(f0, f1, d, curve=1.0):
    return np.sin(sweep(f0, f1, N(d), SR, curve))


def ping(f, d, tau, partials=((1, 1.0), (2.76, 0.4), (5.4, 0.15))):
    """Son de cloche/métal : partiels inharmoniques à décroissances décalées."""
    t = T(d)
    out = np.zeros(N(d))
    for i, (r, a) in enumerate(partials):
        if f * r < SR * 0.45:
            out += a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / (tau / (1 + 0.6 * i)))
    return out


def thump(f0, f1, d, tau, curve=3.0):
    return chirp(f0, f1, d, curve) * dec(d, tau)


def noise(rng, d):
    return rng.standard_normal(N(d))


def whoosh(rng, d, f0, f1, peak=0.5, a=2.0, r=2.0, hp=None):
    """Souffle de bruit dont la brillance glisse de f0 à f1."""
    n = N(d)
    fc = np.geomspace(f0, f1, n)
    s = swept_noise(rng, n, SR, fc)
    s = highpass(s, SR, hp if hp else min(f0, f1) * 0.4, 2)
    return s * swell(d, peak, a, r)


def crackle(rng, d, rate, tau=0.006, lo=1500):
    """Crépitements : impulsions aléatoires filtrées."""
    n = N(d)
    imp = (rng.random(n) < rate / SR) * rng.uniform(0.3, 1.0, n) * rng.choice([-1, 1], n)
    ir = rng.standard_normal(int(tau * 8 * SR)) * np.exp(-np.arange(int(tau * 8 * SR)) / (tau * SR))
    return highpass(reverb(imp, ir)[:n], SR, lo, 2)


def place(total, parts):
    """Superpose (décalage_s, signal, gain) sur une durée totale."""
    out = np.zeros(N(total))
    for off, sig, g in parts:
        i = N(off)
        if i >= len(out):
            continue
        seg = sig[: len(out) - i]
        out[i:i + len(seg)] += seg * g
    return out


def rumble(rng, d, fc, tau, mod=0.0):
    s = lowpass(noise(rng, d), SR, fc, 2) * dec(d, tau)
    if mod:
        s *= 1 + mod * np.sin(2 * np.pi * 9 * T(d))
    return s


def boom(rng, d, tau=0.5):
    """Explosion : bruit passe-bas qui s'assombrit + coup de sous-grave."""
    n = N(d)
    fc = np.geomspace(5000, 140, n)
    body = swept_noise(rng, n, SR, fc) * np.exp(-T(d) / tau)
    return body * 1.0 + thump(90, 28, d, tau * 0.7, 4.0) * 1.4


def arp(freqs, step, tau, partials=((1, 1.0), (2.0, 0.3), (3.0, 0.1)), dlast=None):
    total = step * (len(freqs) - 1) + (dlast or tau * 4)
    return place(total, [(i * step, ping(f, tau * 5, tau, partials), 1.0) for i, f in enumerate(freqs)])


# ---------------------------------------------------------------- interface
def cursor(rng):
    return ping(1500, 0.09, 0.025, ((1, 1.0), (2, 0.25)))


def confirm(rng):
    return place(0.28, [(0, ping(880, 0.25, 0.07, ((1, 1), (2, .3))), 0.8), (0.07, ping(1320, 0.2, 0.08, ((1, 1), (2, .3))), 1.0)])


def cancel(rng):
    return place(0.25, [(0, ping(620, 0.2, 0.05, ((1, 1), (2, .2))), 0.9), (0.06, ping(415, 0.2, 0.07, ((1, 1), (2, .2))), 1.0)])


def error(rng):
    b = lambda: tone(170, 0.1, 0.07, (1, .5, .33, .25, .2)) * np.minimum(1, T(0.1) * 400)
    return place(0.26, [(0, b(), 1.0), (0.12, b(), 1.0)])


def menu_open(rng):
    return place(0.3, [(0, whoosh(rng, 0.22, 600, 3500, 0.7) * 0.5, 1.0), (0.12, ping(1050, 0.18, 0.06), 0.6)])


def text_blip(rng):
    return tone(760, 0.04, 0.02, (1, 0.2)) * np.minimum(1, T(0.04) * 800)


def save(rng):
    return arp([1046.5, 1318.5, 1568, 2093], 0.11, 0.18) * 0.9


def buy(rng):
    return place(0.5, [(0, ping(2093, 0.4, 0.09, ((1, 1), (2.4, .5), (4.1, .2))), 1.0), (0.07, ping(2794, 0.4, 0.12, ((1, 1), (2.4, .5), (4.1, .2))), 1.0)])


def transition(rng):
    d = 1.3
    sw = whoosh(rng, d, 200, 7000, 0.85, 2.5, 1.2) * 0.8
    spiral = chirp(180, 1800, d, 2.0) * swell(d, 0.9, 2, 1.5) * (1 + 0.5 * np.sin(2 * np.pi * 14 * T(d)))
    return place(d + 0.3, [(0, sw, 1.0), (0, spiral, 0.35), (d - 0.05, thump(110, 35, 0.3, 0.12), 1.1)])


# -------------------------------------------------------------------- armes
def slash(rng):
    return place(0.25, [(0, whoosh(rng, 0.18, 9000, 2500, 0.35, 1.5, 2.5, 1500), 1.0), (0.05, ping(3600, 0.2, 0.05, ((1, 1), (1.5, .3))), 0.3)])


def slash_heavy(rng):
    return place(0.5, [(0, whoosh(rng, 0.3, 6000, 900, 0.4, 1.8, 2.0, 400), 1.2), (0.12, thump(150, 45, 0.3, 0.1), 0.9),
                       (0.1, ping(2200, 0.4, 0.1, ((1, 1), (2.3, .4), (4.2, .2))), 0.4)])


def staff_hit(rng):
    wood = tone(190, 0.3, 0.06, (1, .5, .2)) + tone(430, 0.3, 0.04, (1,)) * 0.5
    return place(0.3, [(0, wood, 0.9), (0, lowpass(noise(rng, 0.3), SR, 3500) * dec(0.3, 0.008), 0.8), (0, thump(120, 60, 0.3, 0.08), 0.6)])


def impact(rng):
    return place(0.4, [(0, thump(110, 38, 0.4, 0.13), 1.2), (0, lowpass(noise(rng, 0.4), SR, 3500) * dec(0.4, 0.035), 1.0)])


def punch(rng):
    return place(0.22, [(0, thump(170, 60, 0.22, 0.06), 1.1), (0, bandpass(noise(rng, 0.22), SR, 300, 3000) * dec(0.22, 0.02), 0.9)])


def dagger(rng):
    return place(0.2, [(0, whoosh(rng, 0.1, 10000, 4000, 0.4, 1.5, 2, 2500), 0.8), (0.07, ping(4200, 0.12, 0.03, ((1, 1), (1.6, .4))), 0.5)])


def katana_draw(rng):
    d = 0.7
    n = N(d)
    scrape = highpass(swept_noise(rng, n, SR, np.geomspace(2500, 9500, n)), SR, 2500, 2) * (T(d) / d) ** 1.2
    scrape *= 1 + 0.3 * np.sin(2 * np.pi * 70 * T(d))
    ring = place(1.2, [(d - 0.05, ping(3300, 0.5, 0.35, ((1, 1), (1.5, .6), (2.4, .4), (3.8, .2))), 0.8)])
    return place(1.2, [(0, scrape * np.minimum(1, (1 - T(d) / d) * 12 + 0.0), 0.7), (0, ring, 1.0)])


def wind_slash(rng):
    d = 0.55
    w = whoosh(rng, d, 500, 4000, 0.45, 1.5, 1.8, 250) * (1 + 0.35 * np.sin(2 * np.pi * 18 * T(d)))
    return place(d, [(0, w, 1.0), (0.18, whoosh(rng, 0.2, 9000, 3000, 0.3, 1.5, 2.5, 1500), 0.5)])


def arrow(rng):
    d = 0.4
    whistle = chirp(2800, 1700, 0.25, 1.5) * swell(0.25, 0.3, 1, 2) * 0.35
    return place(d, [(0, whistle, 1.0), (0, whoosh(rng, 0.25, 6000, 3000, 0.4, 1.5, 2), 0.5),
                     (0.25, thump(240, 90, 0.15, 0.04, 2.0), 1.0), (0.25, ping(900, 0.15, 0.05), 0.4)])


def arrow_power(rng):
    d = 0.55
    whistle = chirp(1900, 900, 0.3, 1.5) * swell(0.3, 0.3, 1, 2) * 0.45
    return place(d, [(0, whistle, 1.0), (0, whoosh(rng, 0.3, 5000, 1200, 0.4, 1.5, 2), 0.8),
                     (0.3, thump(200, 50, 0.25, 0.09), 1.3), (0.3, lowpass(noise(rng, 0.25), SR, 3000) * dec(0.25, 0.03), 0.8)])


def shuriken(rng):
    d = 0.45
    nz = bandpass(noise(rng, d), SR, 4000, 9000) * (0.5 + 0.5 * np.sin(2 * np.pi * 45 * T(d))) * swell(d, 0.3, 1, 1.5)
    return place(d, [(0, nz, 1.0), (0.3, ping(4400, 0.15, 0.04, ((1, 1), (1.6, .5))), 0.5)])


def claw(rng):
    return place(0.32, [(i * 0.045, whoosh(rng, 0.13, 8000, 2500, 0.3, 1.2, 2.2, 1800), 1.0 - 0.1 * i) for i in range(3)])


def crit(rng):
    return place(0.55, [(0, ping(2400, 0.5, 0.14, ((1, 1), (1.5, .6), (2.0, .5), (3.0, .3))), 0.8),
                        (0, chirp(900, 3200, 0.12, 1.5) * swell(0.12, 0.8, 1, 1.0), 0.4),
                        (0.03, ping(3600, 0.4, 0.1, ((1, 1), (2.76, .3))), 0.5)])


# -------------------------------------------------------------------- magie
def cast(rng):
    d = 0.85
    return place(d, [(0, chirp(380, 1700, d, 1.6) * swell(d, 0.7, 1.5, 1.5) * 0.4, 1.0),
                     (0, whoosh(rng, d, 800, 6000, 0.7, 2, 1.5), 0.4),
                     (0.5, arp([1568, 2093, 2637], 0.08, 0.15), 0.4)])


def charge(rng):
    d = 1.2
    return place(d, [(0, whoosh(rng, d, 300, 5000, 0.92, 2.2, 3), 0.9),
                     (0, chirp(140, 900, d, 2.0) * swell(d, 0.92, 2, 3) * 0.5, 1.0)])


def charge_big(rng):
    d = 1.5
    return place(d, [(0, whoosh(rng, d, 200, 6500, 0.93, 2.4, 3), 1.0),
                     (0, chirp(70, 700, d, 2.4) * swell(d, 0.93, 2, 3) * 0.7, 1.0),
                     (0, tone(1100, d, None, (1, .4)) * swell(d, 0.93, 3, 3) * (1 + 0.6 * np.sin(2 * np.pi * 11 * T(d))) * 0.12, 1.0)])


def fire(rng):
    d = 0.95
    return place(d, [(0, whoosh(rng, d, 3500, 700, 0.15, 0.8, 1.6, 150), 1.0), (0, crackle(rng, d, 90, 0.005) * dec(d, 0.5), 0.9),
                     (0, rumble(rng, d, 200, 0.4), 0.8)])


def fire_pillar(rng):
    d = 1.5
    return place(d, [(0, whoosh(rng, d, 600, 2800, 0.45, 1.5, 1.6, 100), 1.0), (0, crackle(rng, d, 130, 0.006) * swell(d, 0.4, 1, 1.5), 1.0),
                     (0, rumble(rng, d, 250, 0.7) * 1.5, 1.0), (0, thump(80, 35, d, 0.3), 0.7)])


def ice_form(rng):
    d = 0.9
    parts = [(float(o), ping(f, 0.5, 0.12, ((1, 1), (2.76, .5), (5.4, .2))), 0.35) for o, f in
             zip(np.sort(rng.uniform(0, 0.5, 9)), rng.choice([1760, 2093, 2349, 2794, 3136, 3520, 4186], 9))]
    return place(d, parts + [(0, whoosh(rng, 0.5, 3000, 9000, 0.6, 1.5, 1.5, 2500), 0.35)])


def ice_shatter(rng):
    d = 0.95
    parts = [(float(o), ping(f, 0.4, 0.07, ((1, 1), (2.76, .5))), 0.3) for o, f in
             zip(np.sort(rng.uniform(0.02, 0.5, 12)), rng.uniform(2200, 6500, 12))]
    return place(d, parts + [(0, highpass(noise(rng, 0.4), SR, 3000) * dec(0.4, 0.06), 1.0), (0, thump(160, 60, 0.25, 0.05), 0.7)])


def thunder(rng):
    d = 1.5
    crack = highpass(noise(rng, 0.25), SR, 800) * dec(0.25, 0.025)
    return place(d, [(0, crack, 1.4), (0.02, rumble(rng, 1.4, 350, 0.55, 0.5) * 2.5, 1.0), (0, chirp(3000, 300, 0.12, 3) * dec(0.12, 0.04), 0.4)])


def thunder_big(rng):
    d = 1.5
    crack = highpass(noise(rng, 0.3), SR, 600) * dec(0.3, 0.035)
    return place(d, [(0, crack, 1.5), (0.1, highpass(noise(rng, 0.25), SR, 600) * dec(0.25, 0.03), 1.0),
                     (0.02, rumble(rng, 1.45, 450, 0.7, 0.6) * 3.0, 1.0), (0, thump(100, 30, 0.5, 0.2), 1.0),
                     (0, chirp(4000, 200, 0.2, 3) * dec(0.2, 0.07), 0.4)])


def heal(rng):
    notes = [784, 988, 1175, 1568, 1976]
    return place(1.3, [(i * 0.09, ping(f, 0.8, 0.22, ((1, 1), (2, .3), (3, .1))), 0.8) for i, f in enumerate(notes)] +
                 [(0, whoosh(rng, 1.0, 1500, 7000, 0.5, 1.5, 1.5, 1000), 0.2)])


def chakra(rng):
    d = 1.3
    f = np.linspace(210, 330, N(d))
    ph = 2 * np.pi * np.cumsum(f) / SR
    pad = (np.sin(ph) + 0.4 * np.sin(2 * ph) + 0.2 * np.sin(3 * ph)) * swell(d, 0.45, 1.5, 1.5)
    return place(d, [(0, pad, 0.7), (0.35, ping(990, 0.9, 0.3, ((1, 1), (2, .4), (3, .2))), 0.6), (0.5, ping(1320, 0.8, 0.3, ((1, 1), (2, .4))), 0.5)])


def armor_break(rng):
    d = 0.85
    return place(d, [(0, bandpass(noise(rng, 0.25), SR, 800, 7000) * dec(0.25, 0.05), 1.3), (0, thump(180, 55, 0.3, 0.07), 0.9),
                     (0.02, ping(1400, 0.6, 0.18, ((1, 1), (1.47, .6), (2.09, .4), (2.8, .3))), 0.5),
                     (0.1, ping(2300, 0.5, 0.15, ((1, 1), (1.7, .5), (2.4, .3))), 0.4),
                     (0.2, crackle(rng, 0.5, 70, 0.004, 3000) * dec(0.5, 0.2), 0.8)])


def coins(rng):
    offs = np.sort(rng.uniform(0, 0.7, 9))
    return place(1.2, [(float(o), ping(float(rng.choice([2637, 3136, 3520, 4186])), 0.4, 0.07, ((1, 1), (2.3, .5), (3.9, .25))), 0.4) for o in offs])


# -------------------------------------------------------------- invocations
def summon(rng):
    d = 3.4
    pad = np.zeros(N(d))
    for f, a in ((110, 1.0), (165, 0.8), (220, 0.8), (277, 0.5), (330, 0.5), (440, 0.4)):
        fr = f * (0.8 + 0.2 * np.linspace(0, 1, N(d)) ** 0.5)
        ph = 2 * np.pi * np.cumsum(fr) / SR
        pad += a * (np.sin(ph) + 0.3 * np.sin(2 * ph))
    pad *= swell(d, 0.72, 2, 3) * 0.15
    return place(d, [(0, pad, 1.0), (0, whoosh(rng, d, 300, 6000, 0.72, 2.2, 3), 0.7),
                     (2.35, boom(rng, 1.0, 0.45), 1.2), (2.35, arp([1568, 2093, 2637, 3136], 0.06, 0.4), 0.5)])


def roar(rng):
    d = 1.8
    t = T(d)
    gr = (np.sin(2 * np.pi * np.cumsum(np.linspace(55, 90, N(d)) * (1 + 0.15 * np.sin(2 * np.pi * 27 * t))) / SR))
    gr = np.tanh(gr * 4) * (0.6 + 0.4 * np.sin(2 * np.pi * 31 * t))
    nz = bandpass(noise(rng, d), SR, 300, 2200) * 0.6
    env = swell(d, 0.25, 0.8, 1.6)
    return (gr * 0.9 + nz) * env


def explosion(rng):
    d = 1.8
    return place(d, [(0, boom(rng, d, 0.55), 1.0), (0, crackle(rng, d, 60, 0.008) * dec(d, 0.4), 0.5)])


def mega_flare(rng):
    d = 4.0
    return place(d, [(0, whoosh(rng, 1.7, 200, 7000, 0.95, 2.4, 4), 0.9), (0, chirp(60, 900, 1.7, 2.4) * swell(1.7, 0.95, 2, 4) * 0.6, 0.9),
                     (1.7, boom(rng, 2.3, 0.9), 1.5), (1.7, highpass(noise(rng, 2.3), SR, 3500) * dec(2.3, 0.5), 0.45),
                     (1.8, crackle(rng, 2.0, 80, 0.006) * dec(2.0, 0.8), 0.7)])


# --------------------------------------------------------- objets et états
def potion(rng):
    offs = [0, 0.12, 0.22]
    bub = [(o, chirp(f0, f0 * 2.2, 0.09, 1.0) * swell(0.09, 0.4) * 0.6, 0.8) for o, f0 in zip(offs, (380, 450, 520))]
    return place(0.65, bub + [(0.28, arp([2093, 2637, 3136], 0.06, 0.1), 0.4)])


def elixir(rng):
    return place(1.0, [(0, potion(rng), 0.9), (0.3, arp([1046, 1318, 1568, 2093], 0.08, 0.2), 0.7)])


def revive(rng):
    d = 1.5
    f = np.linspace(260, 520, N(d))
    ph = 2 * np.pi * np.cumsum(f) / SR
    choir = (np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.25 * np.sin(3 * ph)) * swell(d, 0.5, 1.5, 1.5) * 0.4
    return place(d, [(0, choir, 1.0), (0, arp([523, 659, 784, 1047, 1319, 1568, 2093], 0.09, 0.3), 0.9)])


def defend(rng):
    return place(0.45, [(0, ping(700, 0.4, 0.14, ((1, 1), (1.6, .6), (2.5, .5), (3.7, .3))), 0.8), (0, thump(180, 70, 0.2, 0.05), 1.0),
                        (0, bandpass(noise(rng, 0.1), SR, 1000, 6000) * dec(0.1, 0.01), 0.6)])


def ko_monster(rng):
    d = 0.95
    return place(d, [(0, chirp(500, 60, 0.6, 2.0) * dec(0.6, 0.25) * 0.7, 1.0), (0, whoosh(rng, 0.7, 4000, 300, 0.2, 1, 1.5, 100), 0.8),
                     (0.1, crackle(rng, 0.8, 80, 0.004, 4000) * dec(0.8, 0.3), 0.5)])


def ko_hero(rng):
    d = 1.2
    f = np.geomspace(440, 120, N(d))
    ph = 2 * np.pi * np.cumsum(f) / SR
    return place(d, [(0, (np.sin(ph) + 0.4 * np.sin(2 * ph)) * swell(d, 0.1, 1, 1.2) * 0.5, 1.0), (0.55, thump(90, 35, 0.6, 0.2), 0.9)])


def level_up(rng):
    d = 1.5
    notes = [523, 659, 784, 1047]
    seq = [(i * 0.12, ping(f, 0.6, 0.25, ((1, 1), (2, .4), (3, .2), (4, .1))), 0.8) for i, f in enumerate(notes)]
    chord = sum(ping(f, 1.0, 0.5, ((1, 1), (2, .3))) for f in (1047, 1319, 1568, 2093))
    return place(d, seq + [(0.5, chord, 0.35), (0, whoosh(rng, 0.6, 1500, 8000, 0.6, 1.5, 1.5, 1000), 0.15)])


# ----------------------------------------------------------------- monstres
def supernova(rng):
    d = 4.0
    t_pre = 2.4
    return place(d, [(0, whoosh(rng, t_pre, 150, 8000, 0.97, 2.8, 6), 1.0), (0, chirp(40, 1200, t_pre, 2.8) * swell(t_pre, 0.97, 2.4, 6) * 0.7, 0.9),
                     (0, tone(2200, t_pre, None, (1, .4)) * swell(t_pre, 0.97, 4, 6) * (1 + 0.7 * np.sin(2 * np.pi * 9 * T(t_pre))) * 0.1, 1.0),
                     (t_pre, boom(rng, 1.6, 0.9), 1.6), (t_pre, highpass(noise(rng, 1.6), SR, 4000) * dec(1.6, 0.4), 0.45),
                     (t_pre + 0.05, thump(60, 22, 1.4, 0.6), 1.0), (t_pre + 0.1, crackle(rng, 1.5, 90, 0.007) * dec(1.5, 0.7), 0.7)])


def needles(rng):
    offs = np.sort(rng.uniform(0, 0.4, 10))
    return place(0.6, [(float(o), bandpass(noise(rng, 0.04), SR, 3500, 9000) * dec(0.04, 0.008) * 0.8 + ping(float(rng.uniform(3000, 5000)), 0.04, 0.012) * 0.4, 0.9) for o in offs])


def poison_gas(rng):
    d = 1.5
    hiss = highpass(noise(rng, d), SR, 2500) * swell(d, 0.4, 1.2, 1.2) * 0.5
    bub = np.zeros(N(d))
    for o in np.sort(rng.uniform(0.1, 1.2, 9)):
        f0 = float(rng.uniform(150, 350))
        seg = chirp(f0, f0 * 2.2, 0.08, 1.0) * swell(0.08, 0.4) * 0.5
        i = N(float(o))
        bub[i:i + len(seg)] += seg[: len(bub) - i]
    return place(d, [(0, hiss, 1.0), (0, bub, 0.9), (0, rumble(rng, d, 180, 1.0) * swell(d, 0.5), 0.5)])


def flame_breath(rng):
    d = 1.5
    nz = whoosh(rng, d, 700, 2200, 0.45, 1.3, 1.5, 120) * (1 + 0.35 * np.sin(2 * np.pi * 22 * T(d)))
    return place(d, [(0, nz, 1.0), (0, rumble(rng, d, 300, 1.0) * swell(d, 0.4), 1.0), (0, crackle(rng, d, 100, 0.005) * swell(d, 0.45), 0.7)])


GENERATORS = {f.__name__: f for f in (
    cursor, confirm, cancel, error, menu_open, text_blip, save, buy, transition,
    slash, slash_heavy, staff_hit, impact, punch, dagger, katana_draw, wind_slash, arrow, arrow_power, shuriken, claw, crit,
    cast, charge, charge_big, fire, fire_pillar, ice_form, ice_shatter, thunder, thunder_big, heal, chakra, armor_break, coins,
    summon, roar, explosion, mega_flare,
    potion, elixir, revive, defend, ko_monster, ko_hero, level_up,
    supernova, needles, poison_gas, flame_breath)}

# Crête cible en dBFS (par défaut -2) : les sons d'interface restent discrets
PEAKS = {"cursor": -12, "text_blip": -14, "confirm": -8, "cancel": -9, "error": -8, "menu_open": -10, "save": -6, "buy": -6,
         "crit": -4, "coins": -6, "potion": -5, "defend": -4}


def render_sfx(sfx_id: str) -> np.ndarray:
    """Rend un bruitage (float, crête normalisée, fondus anti-clic)."""
    rng = np.random.default_rng(zlib.crc32(sfx_id.encode()))
    x = GENERATORS[sfx_id](rng)
    x = soft_clip(x / (np.max(np.abs(x)) or 1.0), 1.3)
    x = fade(x, SR, 2.0, 12.0)
    return normalize(x, PEAKS.get(sfx_id, -2.0))
