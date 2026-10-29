"""Rendu des WAV : python -m final_classe.gfx.audio.render [--only <id>]."""
from __future__ import annotations

import argparse
import sys
import time
import wave
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from . import AUDIO_DIR, MUSIC_IDS, SFX_IDS
from .music import get_score
from .score import render as render_score
from .sfx import render_sfx
from .synth import SR_MUSIC, SR_SFX, to_int16


def write_wav(path, x: np.ndarray, sr: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(to_int16(x).tobytes())


def report(kind: str, name: str, x: np.ndarray, sr: int, loop: bool, secs: float) -> None:
    peak = 20 * np.log10(max(np.max(np.abs(x)), 1e-9))
    rms = 20 * np.log10(max(np.sqrt(np.mean(x ** 2)), 1e-9))
    line = f"{kind:5s} {name:14s} {len(x) / sr:6.2f}s  crête {peak:6.2f} dBFS  RMS {rms:6.2f} dBFS"
    if loop:
        d = np.abs(np.diff(x))
        seam = abs(x[0] - x[-1]) / (d.max() or 1e-9)
        line += f"  couture {seam:4.2f} (saut au bouclage / plus forte attaque ; <1 : pas pire qu'une attaque)"
    if loop and seam > 0.9:
        line += "  !! CLIC DE BOUCLE ?"
    if peak > -1.0:
        line += "  !! ECRETAGE"
    if rms < -40:
        line += "  !! SILENCE"
    print(line + f"  [{secs:4.1f}s de rendu]")


def _job(kind: str, name: str):
    """Rend un fichier (exécuté dans un processus de travail) et l'écrit."""
    t = time.time()
    if kind == "music":
        score = get_score(name)
        x = render_score(score, SR_MUSIC)
        write_wav(AUDIO_DIR / "music" / f"{name}.wav", x, SR_MUSIC)
        return kind, name, x, SR_MUSIC, score.loop, time.time() - t
    x = render_sfx(name)
    write_wav(AUDIO_DIR / "sfx" / f"{name}.wav", x, SR_SFX)
    return kind, name, x, SR_SFX, False, time.time() - t


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="id d'une musique ou d'un bruitage")
    args = ap.parse_args(argv)
    t0 = time.time()
    jobs = []
    for mid in MUSIC_IDS:
        if args.only and args.only != mid:
            continue
        if get_score(mid) is None:
            print(f"musique {mid} : pas encore composée")
            continue
        jobs.append(("music", mid))
    jobs += [("sfx", sid) for sid in SFX_IDS if not args.only or args.only == sid]
    # les plus longues d'abord, en parallèle sur les cœurs disponibles
    jobs.sort(key=lambda j: j[0] != "music")
    done = 0
    with ProcessPoolExecutor() as pool:
        for res in pool.map(_job, *zip(*jobs)) if jobs else []:
            report(*res)
            done += 1
    if args.only and not done:
        print(f"id inconnu : {args.only}")
        return 2
    total = sum(p.stat().st_size for p in AUDIO_DIR.rglob("*.wav"))
    print(f"{done} fichier(s) rendu(s) en {time.time() - t0:.1f}s ; assets/audio = {total / 1e6:.1f} Mo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
