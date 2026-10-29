"""Bannière : un bandeau qui glisse, reste, puis s'estompe (avertissements, « VICTOIRE »)."""

import pygame

from final_classe.gfx.ui import theme
from final_classe.gfx.ui.draw import render_text

_BANDS: dict[tuple[int, int], pygame.Surface] = {}


class Banner:
    """Bandeau de texte centré. `update(dt)` renvoie False quand il est terminé."""

    def __init__(
        self,
        text: str,
        color=theme.GOLD,
        seconds: float = 2.0,
        y: int = 120,
        size: int = 44,
        title: bool = True,
    ) -> None:
        self.text = text
        self.color = color
        self.seconds = seconds
        self.y = y
        self.size = size
        self.title = title
        self.t = 0.0
        self._line: pygame.Surface | None = None
        self._txt: pygame.Surface | None = None

    def update(self, dt: float) -> bool:
        """Avance ; False une fois fini."""
        self.t += dt
        return self.t < self.seconds

    def _band(self, w: int, band_h: int) -> pygame.Surface:
        key = (w, band_h)
        band = _BANDS.get(key)
        if band is None:
            band = pygame.Surface((w, band_h), pygame.SRCALPHA)
            for x in range(0, w, 4):  # bords qui s'estompent
                edge = min(x, w - x) / (w * 0.25)
                pygame.draw.rect(band, (6, 10, 30, int(150 * min(1.0, edge))), (x, 0, 4, band_h))
            _BANDS[key] = band
        return band

    def draw(self, surface: pygame.Surface) -> None:
        """Dessine le bandeau (entrée en 0,25 s, sortie en 0,35 s)."""
        w, _h = surface.get_size()
        fade_in = min(1.0, self.t / 0.25)
        fade_out = min(1.0, max(0.0, (self.seconds - self.t) / 0.35))
        alpha = int(255 * fade_in * fade_out)
        band_h = self.size + 36
        band = self._band(w, band_h)
        band.set_alpha(alpha)
        y = self.y + int((1 - fade_in) * -20)
        surface.blit(band, (0, y))
        lw = int(w * 0.6 * fade_in)
        if lw > 0:
            if self._line is None or self._line.get_width() != int(w * 0.6):
                self._line = pygame.Surface((int(w * 0.6), 2), pygame.SRCALPHA)
                self._line.fill((*self.color, 200))
            self._line.set_alpha(alpha)
            for ly in (y + 4, y + band_h - 6):
                surface.blit(self._line, ((w - lw) // 2, ly), (0, 0, lw, 2))
        if self._txt is None:
            self._txt = render_text(self.text, self.size, self.color, bold=True, title=self.title).copy()
        self._txt.set_alpha(alpha)
        surface.blit(self._txt, self._txt.get_rect(center=(w // 2, y + band_h // 2)))
