"""Les scènes du jeu : un fichier par scène, chacune s'enregistre dans `engine.registry.SCENES`."""

import importlib
import traceback

from final_classe.gfx.engine.registry import log_error

MODULES = (
    "title", "options", "prologue", "creation", "recruit", "world_map", "event", "prepare",
    "battle", "loot", "shop", "victory", "game_over", "ending", "jukebox",
)


def _load() -> None:
    for name in MODULES:
        full = f"{__name__}.{name}"
        try:
            importlib.import_module(full)
        except ModuleNotFoundError as error:
            if error.name != full:  # un import cassé dans la scène : on le dit
                log_error(f"[scenes] {name} : {error!r}")
        except Exception:
            log_error(f"[scenes] {name} ne s'importe pas :\n{traceback.format_exc()}")


_load()
