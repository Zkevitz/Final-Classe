"""Jauges PV / PM / ATB."""

import math

import pygame

from final_classe.gfx.ui import theme
from final_classe.gfx.ui.draw import draw_text

_HL: dict[tuple[int, int], pygame.Surface] = {}
_GLOW: dict[tuple[int, int], pygame.Surface] = {}


def _highlight(size: tuple[int, int]) -> pygame.Surface:
    """Reflet clair d'une jauge (mis en cache par taille)."""
    surf = _HL.get(size)
    if surf is None:
        surf = pygame.Surface(size, pygame.SRCALPHA)
        surf.fill((255, 255, 255, 55))
        _HL[size] = surf
    return surf


def _glow(size: tuple[int, int]) -> pygame.Surface:
    """Halo doré d'une jauge ATB pleine (alpha réglé à l'usage)."""
    surf = _GLOW.get(size)
    if surf is None:
        surf = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.rect(surf, (*theme.GOLD, 255), surf.get_rect(), border_radius=6)
        _GLOW[size] = surf
    return surf


def hp_color(ratio: float) -> tuple[int, int, int]:
    """Vert, puis or sous 50 %, rouge sous 25 %."""
    if ratio < 0.25:
        return theme.HP_LOW
    if ratio < 0.5:
        return theme.HP_MID
    return theme.HP


def draw_bar(
    surface: pygame.Surface,
    rect: pygame.Rect | tuple,
    ratio: float,
    color,
    back=(10, 14, 36),
    border=theme.INNER_LINE,
) -> None:
    """Une barre horizontale remplie à `ratio` (0..1)."""
    rect = pygame.Rect(rect)
    ratio = max(0.0, min(1.0, ratio))
    r = rect.height // 2
    pygame.draw.rect(surface, back, rect, border_radius=r)
    if ratio > 0:
        fill = pygame.Rect(rect.x, rect.y, min(rect.width, max(rect.height, int(rect.width * ratio))), rect.height)
        pygame.draw.rect(surface, color, fill, border_radius=r)
        shine = pygame.Rect(fill.x + 3, fill.y + 1, max(0, fill.width - 6), max(1, rect.height // 3))
        surface.blit(_highlight(shine.size), shine)
    pygame.draw.rect(surface, border, rect, 1, border_radius=r)


def draw_hp(surface, rect, current: float, maximum: float, label: bool = True) -> None:
    """Jauge de PV, avec la valeur « 123/456 » au-dessus à droite."""
    rect = pygame.Rect(rect)
    ratio = current / maximum if maximum else 0.0
    draw_bar(surface, rect, ratio, hp_color(ratio))
    if label:
        draw_text(
            surface, f"{int(round(current))}/{int(maximum)}", (rect.right, rect.y - 4), 16,
            anchor="bottomright",
        )


def draw_mp(surface, rect, current: float, maximum: float, label: bool = True) -> None:
    """Jauge de PM."""
    rect = pygame.Rect(rect)
    draw_bar(surface, rect, current / maximum if maximum else 0.0, theme.MP)
    if label:
        draw_text(
            surface, f"{int(round(current))}/{int(maximum)}", (rect.right, rect.y - 4), 16,
            anchor="bottomright", color=theme.MP,
        )


def draw_atb(surface, rect, ratio: float, time: float = 0.0) -> None:
    """Jauge ATB : claire, et dorée qui pulse une fois pleine."""
    rect = pygame.Rect(rect)
    if ratio >= 1.0:
        pulse = 0.5 + 0.5 * math.sin(time * 8)
        color = tuple(int(theme.ATB_FULL[i] + (255 - theme.ATB_FULL[i]) * 0.35 * pulse) for i in range(3))
        glow = _glow((rect.width + 8, rect.height + 8))
        glow.set_alpha(int(255 * (0.25 + 0.25 * pulse)))
        surface.blit(glow, (rect.x - 4, rect.y - 4))
    else:
        color = theme.ATB
    draw_bar(surface, rect, ratio, color)
