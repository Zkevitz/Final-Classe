"""Défaite : « GAME OVER », Réessayer (recharge la sauvegarde) ou Titre."""

from typing import override

import pygame

from final_classe.gfx.engine.game import Game
from final_classe.gfx.engine.registry import SCENES, register_scene
from final_classe.gfx.engine.scene import Scene
from final_classe.gfx.ui import Menu, draw_text, is_confirm, theme, vertical_gradient


class GameOverScene(Scene):
    """L'équipe est K.O."""

    def __init__(self, game: Game, zone: int = 0, wave: int = 0) -> None:
        super().__init__(game)
        self.zone, self.wave = zone, wave
        self.t = 0.0
        self.menu = Menu(["Réessayer", "Titre"], (490, 450), 300, row_h=46, font_size=28, align="center")

    @override
    def on_enter(self) -> None:
        self.game.audio.play_music("game_over")

    def _choose(self, idx: int) -> None:
        g = self.game
        if idx == 0:
            from final_classe.gfx.scenes.battle import BattleScene

            if g.load(g.slot):
                try:
                    from final_classe.gfx.scenes.flow import start_zone
                except ImportError:
                    g.replace_all(BattleScene(g, g.zone, g.wave))
                else:
                    start_zone(g, g.zone)
                return
            if g.party is not None:  # pas de sauvegarde : ce combat, équipe reposée
                g.party.rest()
            g.replace_all(BattleScene(g, self.zone, self.wave))
        elif "title" in SCENES:
            g.replace_all(SCENES["title"](g, []))
        else:
            g.quit()

    @override
    def on_back(self) -> None:
        """Échap ne quitte pas l'écran."""

    @override
    def handle_event(self, event: pygame.event.Event) -> None:
        if self.t < 1.2:
            return
        idx = self.menu.handle_event(event)
        if idx is not None:
            self._choose(idx)

    @override
    def update(self, dt: float) -> None:
        self.t += dt
        self.menu.update(dt)

    @override
    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(vertical_gradient(surface.get_size(), (10, 6, 16), (2, 2, 6)), (0, 0))
        k = min(1.0, self.t / 1.5)
        title = self.game.assets.text("GAME OVER", 96, theme.HP_LOW, bold=True, title=True).copy()
        title.set_alpha(int(255 * k))
        surface.blit(title, title.get_rect(center=(640, 260)))
        draw_text(surface, "L'équipe est K.O…", (640, 340), 26, theme.TEXT_DIM, "midtop")
        if self.t >= 1.2:
            self.menu.draw(surface, self.game.assets)


@register_scene("game_over")
def make_game_over(game: Game, args: list[str]) -> Scene:
    """Écran de défaite de démonstration."""
    return GameOverScene(game)
