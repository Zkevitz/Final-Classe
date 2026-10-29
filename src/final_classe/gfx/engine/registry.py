"""Registre des scènes : `--scene nom[:arg[:arg]]` et navigation par nom."""

import importlib
import sys
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from final_classe.gfx.engine.game import Game
    from final_classe.gfx.engine.scene import Scene

SceneFactory = Callable[["Game", list[str]], "Scene"]
"""Une fabrique reçoit le jeu et les arguments après le nom (``battle:plains:1`` → ``["plains", "1"]``)."""

SCENES: dict[str, SceneFactory] = {}

# Les scènes prévues (docs/ARCHITECTURE-GFX.md §5) et le module qui les définit.
KNOWN_SCENES = (
    "title", "options", "prologue", "creation", "recruit", "world_map", "event", "prepare",
    "battle", "loot", "shop", "victory", "game_over", "ending", "jukebox",
)


def register_scene(name: str) -> Callable[[SceneFactory], SceneFactory]:
    """Décorateur : ``@register_scene("title")`` sur une fabrique ``(game, args) -> Scene``."""

    def decorator(factory: SceneFactory) -> SceneFactory:
        SCENES[name] = factory
        return factory

    return decorator


def load_scenes() -> None:
    """Importe les modules de `gfx/scenes/` (ceux qui n'existent pas encore sont ignorés)."""
    importlib.import_module("final_classe.gfx.scenes")


def make_scene(game: "Game", spec: str) -> "Scene":
    """Crée la scène décrite par `spec` ; KeyError si le nom est inconnu."""
    name, *args = spec.split(":")
    return SCENES[name](game, args)


def describe_scenes() -> str:
    """La liste des scènes valides, pour le message d'erreur du mode sans fenêtre."""
    lines = [f"  {name}" for name in sorted(SCENES)]
    missing = [n for n in KNOWN_SCENES if n not in SCENES]
    out = "Scènes disponibles :\n" + "\n".join(lines)
    if missing:
        out += "\nPrévues mais pas encore écrites : " + ", ".join(missing)
    return out


def log_error(message: str) -> None:
    """Écrit un avertissement sur stderr."""
    print(message, file=sys.stderr)
