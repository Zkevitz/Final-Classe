"""Menu vertical (ou en colonnes) avec curseur main gantée qui oscille."""

import math

import pygame

from final_classe.gfx.ui import theme
from final_classe.gfx.ui.draw import draw_text
from final_classe.gfx.ui.keys import is_confirm, nav
from final_classe.gfx.ui.window import draw_window


def draw_cursor(surface: pygame.Surface, assets, pos: tuple[int, int], time: float = 0.0) -> None:
    """Le curseur : `ui_cursor` s'il existe, sinon une flèche dorée ; oscille horizontalement.

    `pos` est le point de pointe (bord gauche du libellé, milieu de ligne).
    """
    x = pos[0] + math.sin(time * 6) * 4
    y = pos[1]
    if assets is not None and assets.exists("ui_cursor"):
        img = assets.image("ui_cursor")
        h = 36
        w = max(1, int(img.get_width() * h / img.get_height()))
        img = assets.scaled("ui_cursor", (w, h))
        surface.blit(img, (x - w, y - h // 2))
        return
    pts = [(x, y), (x - 18, y - 11), (x - 18, y + 11)]
    pygame.draw.polygon(surface, theme.BLACK, [(px + 2, py + 2) for px, py in pts])
    pygame.draw.polygon(surface, theme.GOLD, pts)
    pygame.draw.polygon(surface, theme.WHITE, pts, 1)


class Menu:
    """Liste d'entrées navigable au clavier et à la souris.

    `handle_event` renvoie l'index confirmé, sinon None. Les entrées désactivées
    (`enabled[i] = False`) sont grisées et ne se confirment pas.
    """

    def __init__(
        self,
        items: list[str],
        topleft: tuple[int, int],
        width: int = 300,
        row_h: int = 42,
        font_size: int = 26,
        columns: int = 1,
        window: bool = True,
        align: str = "left",
    ) -> None:
        self.items = list(items)
        self.enabled = [True] * len(items)
        self.cursor = 0
        self.topleft = topleft
        self.width = width
        self.row_h = row_h
        self.font_size = font_size
        self.columns = columns
        self.window = window
        self.align = align
        self.time = 0.0

    @property
    def rows(self) -> int:
        """Nombre de lignes."""
        return math.ceil(len(self.items) / self.columns)

    @property
    def rect(self) -> pygame.Rect:
        """Le rectangle de la fenêtre du menu."""
        return pygame.Rect(self.topleft[0], self.topleft[1], self.width, self.rows * self.row_h + 28)

    def _item_rect(self, i: int) -> pygame.Rect:
        col_w = (self.width - 40) // self.columns
        row, col = i // self.columns, i % self.columns
        return pygame.Rect(
            self.topleft[0] + 20 + col * col_w, self.topleft[1] + 14 + row * self.row_h,
            col_w, self.row_h,
        )

    def set_items(self, items: list[str]) -> None:
        """Remplace les entrées (le curseur reste dans les bornes)."""
        self.items = list(items)
        self.enabled = [True] * len(items)
        self.cursor = min(self.cursor, max(0, len(items) - 1))

    def move(self, dx: int, dy: int) -> None:
        """Déplace le curseur, en bouclant."""
        n = len(self.items)
        if not n:
            return
        if self.columns == 1:
            self.cursor = (self.cursor + dy + dx * 0) % n
            return
        row, col = divmod(self.cursor, self.columns)
        col = (col + dx) % self.columns
        row = (row + dy) % self.rows
        self.cursor = min(n - 1, row * self.columns + col)

    def handle_event(self, event: pygame.event.Event) -> int | None:
        """Gère une entrée ; renvoie l'index confirmé ou None."""
        dx, dy = nav(event)
        if dx or dy:
            self.move(dx, dy)
            return None
        if is_confirm(event):
            return self.cursor if self.enabled[self.cursor] else None
        if event.type == pygame.MOUSEMOTION:
            for i in range(len(self.items)):
                if self._item_rect(i).collidepoint(event.pos):
                    self.cursor = i
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i in range(len(self.items)):
                if self._item_rect(i).collidepoint(event.pos):
                    self.cursor = i
                    return i if self.enabled[i] else None
        return None

    def update(self, dt: float) -> None:
        """Fait avancer l'oscillation du curseur."""
        self.time += dt

    def draw(self, surface: pygame.Surface, assets=None, show_cursor: bool = True) -> None:
        """Dessine la fenêtre, les entrées et le curseur."""
        if self.window:
            draw_window(surface, self.rect)
        for i, label in enumerate(self.items):
            r = self._item_rect(i)
            selected = i == self.cursor and show_cursor
            color = theme.GOLD if selected else (theme.TEXT if self.enabled[i] else theme.TEXT_DIM)
            if not self.enabled[i]:
                color = (110, 118, 150)
            if self.align == "center":
                draw_text(surface, label, (r.centerx, r.centery), self.font_size, color, "center")
            else:
                draw_text(surface, label, (r.x + 28, r.centery), self.font_size, color, "midleft")
            if selected:
                draw_cursor(surface, assets, (r.x + 22, r.centery), self.time)
