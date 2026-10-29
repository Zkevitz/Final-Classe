"""Options : volumes de la musique et des bruitages, plein écran, accès au Test son."""

from typing import override

import pygame

from final_classe.gfx.engine.game import Game
from final_classe.gfx.engine.registry import SCENES, register_scene
from final_classe.gfx.engine.scene import Scene
from final_classe.gfx.scenes.flow import solid
from final_classe.gfx.ui import (
    Menu, draw_bar, draw_text, draw_window, is_confirm, nav, theme,
)


class OptionsScene(Scene):
    """Gauches/droites règlent les volumes ; Échap revient."""

    transparent = True  # la scène du dessous (le titre) reste visible derrière le voile

    def __init__(self, game: Game) -> None:
        super().__init__(game)
        self.menu = Menu(["Musique", "Bruitages", "Plein écran", "Test son", "Retour"],
                         (330, 190), width=620, row_h=60, font_size=28, window=True)

    def _vol(self, i: int) -> float:
        return self.game.audio.music_volume if i == 0 else self.game.audio.sfx_volume

    def _set_vol(self, i: int, value: float) -> None:
        value = round(max(0.0, min(1.0, value)), 2)
        if i == 0:
            self.game.audio.music_volume = value
        else:
            self.game.audio.sfx_volume = value
            self.game.audio.play_sfx("cursor")

    @override
    def handle_event(self, event: pygame.event.Event) -> None:
        dx, dy = nav(event)
        i = self.menu.cursor
        if dx and i in (0, 1):
            self._set_vol(i, self._vol(i) + 0.1 * dx)
            return
        chosen = self.menu.handle_event(event)
        if chosen == 2:
            self.game.toggle_fullscreen()
        elif chosen == 3 and "jukebox" in SCENES:
            self.game.audio.play_sfx("confirm")
            self.game.push(SCENES["jukebox"](self.game, []), transition="fade")
        elif chosen == 4 or (chosen is None and is_confirm(event) and i == 4):
            self.game.pop(transition="fade")

    @override
    def update(self, dt: float) -> None:
        self.menu.update(dt)

    @override
    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(solid((1280, 720), (0, 0, 0, 150)), (0, 0))
        draw_text(surface, "Options", (640, 130), 44, theme.GOLD, "center", bold=True, title=True)
        self.menu.draw(surface, self.game.assets)
        for i in (0, 1):
            draw_bar(surface, (640, 190 + 14 + i * 60 + 18, 260, 14), self._vol(i), theme.GOLD)
            draw_text(surface, f"{int(self._vol(i) * 100)} %", (920, 190 + 14 + i * 60 + 25), 20,
                      theme.TEXT_DIM, "midright")
        mode = "Oui" if self.game.fullscreen else "Non"
        draw_text(surface, mode, (920, 190 + 14 + 2 * 60 + 25), 22, theme.TEXT_DIM, "midright")
        if "jukebox" not in SCENES:
            draw_text(surface, "bientôt", (920, 190 + 14 + 3 * 60 + 25), 20, theme.TEXT_DIM, "midright")
        draw_text(surface, "Gauche / droite : régler   Échap : retour", (640, 560), 18,
                  theme.TEXT_DIM, "center")


@register_scene("options")
def make_options(game: Game, args: list[str]) -> Scene:
    """Fabrique de la scène Options."""
    return OptionsScene(game)
