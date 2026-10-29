"""Point d'entrée en ligne de commande : jeu normal ou mode sans fenêtre (docs/ARCHITECTURE-GFX.md §5)."""

import argparse
import os
import random
import sys
import time
import traceback
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    """Les options du §5."""
    p = argparse.ArgumentParser(prog="final_classe.gfx", description="Final Classe, version pygame")
    p.add_argument("--headless", action="store_true", help="sans fenêtre, dt fixe de 1/60 s")
    p.add_argument("--scene", help="scène à ouvrir (title, battle:plains:1, event:forest…)")
    p.add_argument("--demo", action="store_true", help="la scène joue toute seule (IA)")
    p.add_argument("--action", help="force la chorégraphie jouée à chaque tour (summon.bahamut)")
    p.add_argument("--seconds", type=float, default=6.0, help="durée en mode sans fenêtre")
    p.add_argument("--shot-every", type=float, default=1.0, help="période des captures (s)")
    p.add_argument("--shots", help="dossier des captures PNG")
    p.add_argument("--shot-scale", type=float, default=0.5, help="échelle des captures")
    p.add_argument("--debug-freeze", type=float, default=None, metavar="S",
                   help="test du garde-fou : fige la scène après S secondes (avec --demo)")
    p.add_argument("--seed", type=int, default=None, help="graine aléatoire")
    return p


def run_cli(argv: list[str] | None = None) -> int:
    """Lance le jeu ; renvoie le code de sortie (0 ok, 1 exception, 2 scène inconnue)."""
    args = build_parser().parse_args(argv)
    if args.headless:  # avant pygame.init()
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
    if args.shots:  # chemin relatif au dossier de lancement, avant le chdir de Game
        args.shots = str(Path(args.shots).resolve())
    seed = args.seed if args.seed is not None else (1 if args.headless else None)
    if seed is not None:
        random.seed(seed)

    from final_classe.gfx.engine.demo import make_demo_party
    from final_classe.gfx.engine.game import Game
    from final_classe.gfx.engine.registry import SCENES, describe_scenes, load_scenes, make_scene

    load_scenes()
    spec = args.scene or "title"
    name = spec.split(":")[0]
    if name not in SCENES:
        print(f"Scène inconnue : « {name} »\n{describe_scenes()}", file=sys.stderr)
        return 2

    frames = 0
    started = time.perf_counter()
    code = 0
    game = None
    try:
        game = Game(headless=args.headless, seed=seed)
        game.demo = args.demo
        game.force_action = args.action
        if args.scene:  # ouverture directe : partie de démonstration prête
            game.party = make_demo_party()
        game.push(make_scene(game, spec))
        if not args.headless:
            game.run()
        else:
            frames = _run_headless(game, args)
    except Exception:
        traceback.print_exc()
        code = 1
    finally:
        elapsed = max(1e-9, time.perf_counter() - started)
        if args.headless:
            print(f"FPS moyen: {frames / elapsed:.1f}")
            if code == 0 and getattr(args, "blocked", False):
                code = 3
        if game is not None:
            import pygame

            pygame.quit()
    return code


BLOCK_SECONDS = 5.0  # durée d'immobilité (scène et image) avant `BLOQUÉ`
BLOCK_TOLERANCE = 1.5  # écart moyen max (0-255) entre deux empreintes pour les dire identiques
BLOCK_SAMPLE = 0.25  # période de l'empreinte (s)


def terminal_scene(scene) -> str | None:
    """Le nom d'une scène terminale d'une démo (`game_over`, `ending` fini), sinon None."""
    name = type(scene).__name__
    if name == "GameOverScene":
        return "game_over"
    if name == "EndingScene" and getattr(scene, "over", False):
        return "ending"
    return None


class StuckWatch:
    """Détecte une démo figée : même scène et même image (à une tolérance près) pendant 5 s."""

    def __init__(self) -> None:
        self.scene: object | None = None
        self.ref = None
        self.since = 0.0
        self.name = ""

    @staticmethod
    def fingerprint(surface):
        """Empreinte : l'image réduite à 64×36 (tolère la respiration des sprites)."""
        import numpy as np
        import pygame

        small = pygame.transform.smoothscale(surface, (64, 36))
        return pygame.surfarray.array3d(small).astype(np.int16)

    def update(self, game, now: float) -> bool:
        """Appeler à intervalle régulier avec le temps simulé ; vrai si la démo est bloquée."""
        import numpy as np

        scene = game.scene
        fp = self.fingerprint(game.screen)
        same = (scene is self.scene and self.ref is not None
                and float(np.abs(fp - self.ref).mean()) <= BLOCK_TOLERANCE)
        if not same:
            self.scene, self.ref, self.since = scene, fp, now
            self.name = type(scene).__name__ if scene is not None else "?"
            return False
        return now - self.since >= BLOCK_SECONDS


def _run_headless(game, args) -> int:
    """Boucle à dt fixe (1/60 s) avec captures périodiques ; renvoie le nombre d'images."""
    dt = 1 / 60
    watch = StuckWatch() if args.demo else None
    sample = max(1, round(BLOCK_SAMPLE / dt))
    total = max(1, round(args.seconds / dt))
    every = max(1, round(args.shot_every / dt)) if args.shots else 0
    shot_no = 0
    end_frame: int | None = None
    for frame in range(1, total + 1):
        if getattr(args, "debug_freeze", None) is None or frame * dt <= args.debug_freeze:
            game.step(dt)
        if not game.running:
            break
        if args.demo and type(game.scene).__name__ == "EndingScene":
            game.scene.boost = True  # démo : le générique défile vite jusqu'à `over`
        end = terminal_scene(game.scene) if args.demo else None
        if end is not None:
            if end_frame is None:
                end_frame = frame
            if frame - end_frame >= 60:  # la scène terminale tourne 1 s (captures comprises)
                print(f"FIN DE DÉMO: {end}")
                if args.shots:
                    shot_no += 1
                    game.screenshot(Path(args.shots) / f"shot_{shot_no:03d}.png", args.shot_scale)
                break
        if watch is not None and end is None and type(game.scene).__name__ != "EndingScene" and frame % sample == 0 and watch.update(game, frame * dt):
            print(f"BLOQUÉ: {watch.name} depuis {frame * dt - watch.since:.0f} s")
            args.blocked = True
            if args.shots:
                game.screenshot(Path(args.shots) / f"shot_{shot_no + 1:03d}.png", args.shot_scale)
            break
        if every and (frame % every == 0 or frame == total):
            shot_no += 1
            game.screenshot(Path(args.shots) / f"shot_{shot_no:03d}.png", args.shot_scale)
    if args.shots:
        print(f"{shot_no} capture(s) dans {args.shots}")
    return frame
