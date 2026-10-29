"""Le stockage : le seul package qui touche au disque."""

from final_classe.storage.errors import SaveError
from final_classe.storage.save import SLOTS, load_game, peek, save_game

__all__ = ["SLOTS", "SaveError", "load_game", "peek", "save_game"]
