"""Partitions des musiques : id -> fabrique de Score."""
from __future__ import annotations

from importlib import import_module

# Ids de docs/AUDIO.md §3 ; seules celles listées dans IMPLEMENTED ont une partition pour l'instant.
IMPLEMENTED = ("battle", "title", "prologue", "world_map", "boss", "final_boss", "victory", "victory_loop", "shop", "ending", "game_over")


def get_score(music_id: str):
    """Retourne le Score de la musique, ou None si elle n'est pas encore composée."""
    if music_id not in IMPLEMENTED:
        return None
    return import_module(f"{__name__}.{music_id}").build()
