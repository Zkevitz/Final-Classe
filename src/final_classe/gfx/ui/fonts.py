"""Polices : SysFont avec repli, mises en cache (les accents passent par SysFont)."""

import pygame

BODY_FONTS = "segoeuisemibold,segoeui,trebuchetms,arial"
TITLE_FONTS = "georgia,cambria,timesnewroman,serif"

_cache: dict[tuple[int, bool, bool], pygame.font.Font] = {}


def get_font(size: int, bold: bool = False, title: bool = False) -> pygame.font.Font:
    """Une police de la taille demandée (`title` : empattements, façon Georgia)."""
    key = (size, bold, title)
    font = _cache.get(key)
    if font is None:
        if not pygame.font.get_init():
            pygame.font.init()
        font = pygame.font.SysFont(TITLE_FONTS if title else BODY_FONTS, size, bold=bold)
        _cache[key] = font
    return font
