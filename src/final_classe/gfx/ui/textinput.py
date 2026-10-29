"""Saisie de texte au clavier (nom du héros)."""

import pygame

from final_classe.gfx.ui import theme
from final_classe.gfx.ui.draw import draw_text
from final_classe.gfx.ui.fonts import get_font
from final_classe.gfx.ui.window import draw_window


class TextInput:
    """Champ de texte : `value`, `submitted` (Entrée, texte non vide), caret clignotant."""

    def __init__(
        self,
        prompt: str,
        rect: tuple[int, int, int, int] = (340, 300, 600, 130),
        max_len: int = 12,
        value: str = "",
    ) -> None:
        self.prompt = prompt
        self.rect = pygame.Rect(rect)
        self.max_len = max_len
        self.value = value
        self.submitted = False
        self.time = 0.0

    def handle_event(self, event: pygame.event.Event) -> None:
        """Caractères imprimables, Retour arrière, Entrée."""
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.value.strip():
                self.submitted = True
        elif event.key == pygame.K_BACKSPACE:
            self.value = self.value[:-1]
        elif event.unicode and event.unicode.isprintable() and len(self.value) < self.max_len:
            self.value += event.unicode

    def update(self, dt: float) -> None:
        """Fait clignoter le caret."""
        self.time += dt

    def draw(self, surface: pygame.Surface) -> None:
        """Dessine la fenêtre, l'invite et le texte saisi."""
        draw_window(surface, self.rect)
        draw_text(surface, self.prompt, (self.rect.x + 30, self.rect.y + 20), 24, theme.TEXT_DIM)
        field = pygame.Rect(self.rect.x + 30, self.rect.y + 66, self.rect.width - 60, 44)
        pygame.draw.rect(surface, (8, 12, 34), field, border_radius=6)
        pygame.draw.rect(surface, theme.INNER_LINE, field, 1, border_radius=6)
        text_rect = draw_text(surface, self.value, (field.x + 12, field.centery), 30, anchor="midleft")
        if int(self.time * 2) % 2 == 0:
            x = text_rect.right + 3 if self.value else field.x + 12
            h = get_font(30).get_height() - 6
            pygame.draw.line(surface, theme.GOLD, (x, field.centery - h // 2), (x, field.centery + h // 2), 2)
