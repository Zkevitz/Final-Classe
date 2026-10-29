"""Réglages communs : pygame sans fenêtre ni son, et un `Game` jetable dans un dossier temporaire.

Les variables SDL sont posées AVANT tout import de pygame (docs/ARCHITECTURE-GFX.md §9).
"""

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import random  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def settle(game, limit: int = 200) -> None:
    """Fait avancer le jeu jusqu'à la fin des fondus (les changements de scène sont alors appliqués)."""
    for _ in range(limit):
        if not game.transitioning:
            return
        game.update(1 / 30)
    raise AssertionError("fondu qui ne finit pas")


@pytest.fixture
def game_here():
    """Un `Game` sans fenêtre, SANS changer de dossier après sa création (il fait chdir(shots/headless))."""
    from final_classe.gfx.engine.game import Game
    from final_classe.gfx.engine.registry import load_scenes

    start = os.getcwd()
    random.seed(1)
    g = Game(headless=True, seed=1)
    load_scenes()
    yield g
    # pas de pygame.quit() : le cache de polices du jeu survivrait à l'arrêt du module font
    os.chdir(start)


@pytest.fixture
def game(game_here, tmp_path, monkeypatch):
    """Un `Game` sans fenêtre qui travaille dans `tmp_path` (les sauvegardes y vont)."""
    monkeypatch.chdir(tmp_path)
    return game_here


@pytest.fixture
def stub_scenes(monkeypatch):
    """Remplace les scènes du déroulement par des bouchons qui notent (nom, args) dans `calls`."""
    from final_classe.gfx.engine.registry import SCENES
    from final_classe.gfx.engine.scene import Scene

    calls: list[tuple[str, list[str]]] = []

    def make(name):
        def factory(game, args):
            calls.append((name, list(args)))
            return Scene(game)

        return factory

    for name in ("event", "prepare", "battle", "world_map", "ending", "title"):
        monkeypatch.setitem(SCENES, name, make(name))
    return calls
