"""Boîte de dialogue : texte qui défile lettre par lettre, pages, indicateur ▼."""

import math

import pygame

from final_classe.gfx.ui import theme
from final_classe.gfx.ui.draw import draw_text, wrap_text
from final_classe.gfx.ui.keys import is_confirm
from final_classe.gfx.ui.window import draw_window


class DialogBox:
    """Des pages de texte (`speaker` optionnel). `done` devient vrai après la dernière page."""

    def __init__(
        self,
        pages: str | list[str],
        speaker: str | None = None,
        rect: tuple[int, int, int, int] = (60, 530, 1160, 160),
        chars_per_second: float = 55.0,
        font_size: int = 26,
    ) -> None:
        self.pages = [pages] if isinstance(pages, str) else list(pages)
        self.speaker = speaker
        self.rect = pygame.Rect(rect)
        self.cps = chars_per_second
        self.font_size = font_size
        self.page = 0
        self.shown = 0.0
        self.done = False
        self.time = 0.0
        self._lines: list[str] = []
        self._wrap()

    def _wrap(self) -> None:
        text = self.pages[self.page] if self.pages else ""
        self._lines = wrap_text(text, self.font_size, self.rect.width - 60)

    @property
    def _total(self) -> int:
        return sum(len(line) for line in self._lines)

    @property
    def page_complete(self) -> bool:
        """Tout le texte de la page est affiché."""
        return self.shown >= self._total

    def advance(self) -> None:
        """Confirme : affiche tout, ou passe à la page suivante, ou termine."""
        if not self.page_complete:
            self.shown = float(self._total)
        elif self.page + 1 < len(self.pages):
            self.page += 1
            self.shown = 0.0
            self._wrap()
        else:
            self.done = True

    def handle_event(self, event: pygame.event.Event) -> None:
        """Entrée / Espace / Z / clic : avance."""
        if is_confirm(event) or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
            self.advance()

    def update(self, dt: float) -> None:
        """Fait défiler le texte."""
        self.time += dt
        if not self.page_complete:
            self.shown = min(float(self._total), self.shown + self.cps * dt)

    def draw(self, surface: pygame.Surface) -> None:
        """Dessine la fenêtre, le nom de l'orateur et les lignes visibles."""
        draw_window(surface, self.rect)
        y = self.rect.y + 20
        if self.speaker:
            draw_text(surface, self.speaker, (self.rect.x + 30, y), self.font_size - 2, theme.GOLD, bold=True)
            y += self.font_size + 10
        remaining = int(self.shown)
        for line in self._lines:
            if remaining <= 0:
                break
            draw_text(surface, line[:remaining], (self.rect.x + 30, y), self.font_size)
            remaining -= len(line)
            y += self.font_size + 8
        if self.page_complete:
            bob = math.sin(self.time * 6) * 3
            cx, cy = self.rect.right - 36, self.rect.bottom - 24 + bob
            pygame.draw.polygon(surface, theme.GOLD, [(cx - 8, cy - 5), (cx + 8, cy - 5), (cx, cy + 6)])
