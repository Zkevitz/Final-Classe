"""Fenêtre bleue façon Final Fantasy : dégradé, bordure 2 px, liseré intérieur."""

import pygame

from final_classe.gfx.ui import theme
from final_classe.gfx.ui.draw import vertical_gradient

_cache: dict[tuple[int, int, int], pygame.Surface] = {}


def window_surface(size: tuple[int, int], radius: int = theme.RADIUS) -> pygame.Surface:
    """Le fond de fenêtre prêt à blitter (mis en cache par taille)."""
    key = (size[0], size[1], radius)
    surf = _cache.get(key)
    if surf is not None:
        return surf
    w, h = size
    surf = pygame.Surface(size, pygame.SRCALPHA)
    surf.blit(vertical_gradient(size, theme.WIN_TOP, theme.WIN_BOTTOM), (0, 0))
    mask = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, theme.WIN_ALPHA), (0, 0, w, h), border_radius=radius)
    surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    pygame.draw.rect(
        surf, theme.INNER_LINE, (4, 4, w - 8, h - 8), 1, border_radius=max(2, radius - 3)
    )
    pygame.draw.rect(surf, theme.BORDER, (0, 0, w, h), 2, border_radius=radius)
    if len(_cache) > 100:
        _cache.clear()
    _cache[key] = surf
    return surf


def draw_window(surface: pygame.Surface, rect: pygame.Rect | tuple) -> pygame.Rect:
    """Dessine une fenêtre bleue à `rect` ; renvoie le rect."""
    rect = pygame.Rect(rect)
    surface.blit(window_surface(rect.size), rect.topleft)
    return rect
