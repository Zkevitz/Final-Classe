"""Petites primitives de dessin : dégradés, texte ombré, découpe de texte."""

import pygame

from final_classe.gfx.ui import theme
from final_classe.gfx.ui.fonts import get_font

_text_cache: dict[tuple, pygame.Surface] = {}
_grad_cache: dict[tuple, pygame.Surface] = {}


def vertical_gradient(size: tuple[int, int], top, bottom) -> pygame.Surface:
    """Une surface en dégradé vertical (mise en cache)."""
    key = (size, tuple(top), tuple(bottom))
    surf = _grad_cache.get(key)
    if surf is None:
        w, h = size
        surf = pygame.Surface(size)
        for y in range(h):
            t = y / max(1, h - 1)
            color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
            pygame.draw.line(surf, color, (0, y), (w, y))
        if len(_grad_cache) > 200:
            _grad_cache.clear()
        _grad_cache[key] = surf
    return surf


def render_text(
    text: str,
    size: int = 24,
    color=theme.TEXT,
    bold: bool = False,
    title: bool = False,
    shadow: bool = True,
) -> pygame.Surface:
    """Texte rendu avec ombre portée 2 px (noir 60 %), mis en cache."""
    key = (text, size, tuple(color), bold, title, shadow)
    surf = _text_cache.get(key)
    if surf is None:
        font = get_font(size, bold, title)
        base = font.render(text, True, color)
        if shadow:
            surf = pygame.Surface((base.get_width() + 2, base.get_height() + 2), pygame.SRCALPHA)
            sh = font.render(text, True, theme.BLACK)
            sh.set_alpha(153)
            surf.blit(sh, (2, 2))
            surf.blit(base, (0, 0))
        else:
            surf = base
        if len(_text_cache) > 600:
            _text_cache.clear()
        _text_cache[key] = surf
    return surf


def draw_text(
    surface: pygame.Surface,
    text: str,
    pos: tuple[int, int],
    size: int = 24,
    color=theme.TEXT,
    anchor: str = "topleft",
    **kwargs,
) -> pygame.Rect:
    """Dessine un texte ; `anchor` est un attribut de Rect (topleft, center, midtop…)."""
    surf = render_text(text, size, color, **kwargs)
    rect = surf.get_rect(**{anchor: pos})
    surface.blit(surf, rect)
    return rect


def wrap_text(text: str, size: int, max_width: int, bold: bool = False) -> list[str]:
    """Coupe le texte en lignes qui tiennent dans `max_width` (les retours à la ligne sont respectés)."""
    font = get_font(size, bold)
    lines: list[str] = []
    for paragraph in text.split("\n"):
        line = ""
        for word in paragraph.split(" "):
            test = f"{line} {word}".strip()
            if font.size(test)[0] <= max_width or not line:
                line = test
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines
