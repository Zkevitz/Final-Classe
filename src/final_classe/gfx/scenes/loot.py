"""Écran de butin : gils, objets volés, puis suite du déroulement (`flow.after_battle`)."""

from typing import override

import pygame

from final_classe.gfx.engine.game import Game
from final_classe.gfx.engine.registry import SCENES, register_scene
from final_classe.gfx.engine.scene import Scene
from final_classe.gfx.scenes.battle_actors import draw_background
from final_classe.gfx.scenes.victory import BattleResult
from final_classe.gfx.ui import Banner, draw_text, draw_window, is_confirm, theme

ITEM_ICONS = {
    "Potion": "icon_potion", "Éther": "icon_ether",
    "Queue de phénix": "icon_phoenix_down", "Élixir": "icon_elixir",
}


def go_next(game: Game) -> None:
    """Suite du déroulement : `flow.after_battle`, sinon la carte du monde, sinon le titre."""
    try:
        from final_classe.gfx.scenes.flow import after_battle
    except ImportError:
        for name in ("world_map", "title"):
            if name in SCENES:
                game.replace_all(SCENES[name](game, []))
                return
        game.pop("fade")
        return
    after_battle(game)


class LootScene(Scene):
    """Le butin du combat ; Entrée pour continuer."""

    def __init__(self, game: Game, result: BattleResult | None = None) -> None:
        super().__init__(game)
        if game.party is None:
            from final_classe.gfx.engine.demo import make_demo_party

            game.party = make_demo_party()
        self.result = result or BattleResult(0, 0, 3, 200, 120, ["Potion"], [])
        self.t = 0.0
        self._left = False
        self._bg: pygame.Surface | None = None
        self.banner = Banner("BUTIN", theme.GOLD, 99.0, y=70, size=52)

    @override
    def on_enter(self) -> None:
        self.game.audio.play_music("victory_loop")
        self.game.audio.play_sfx("coins")

    def _finish(self) -> None:
        if self._left:
            return
        self._left = True
        g, res = self.game, self.result
        g.zone = res.zone  # le combat qui vient de finir (0-based) : after_battle avance
        g.wave = res.wave
        go_next(g)

    @override
    def handle_event(self, event: pygame.event.Event) -> None:
        if self.t > 0.5 and (is_confirm(event) or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1)):
            self._finish()

    @override
    def update(self, dt: float) -> None:
        self.t += dt
        self.banner.t = min(self.banner.t + dt, 1.0)  # reste affichée
        if self.game.demo and self.t > 2.5:
            self._finish()

    @override
    def draw(self, surface: pygame.Surface) -> None:
        g = self.game
        if self._bg is None:
            self._bg = pygame.Surface(g.size).convert()
            draw_background(g, self._bg, self.result.zone)
            veil = pygame.Surface(g.size, pygame.SRCALPHA)
            veil.fill((4, 8, 28, 150))
            self._bg.blit(veil, (0, 0))
        surface.blit(self._bg, (0, 0))
        self.banner.draw(surface)
        res = self.result
        rows = max(1, len(res.items))
        r = draw_window(surface, (340, 190, 600, 190 + 50 * rows))
        icon = g.assets.scaled("icon_gil", (44, 44))
        surface.blit(icon, (r.x + 30, r.y + 24))
        draw_text(surface, f"+{res.gil} gils", (r.x + 90, r.y + 46), 32, theme.GOLD, "midleft")
        draw_text(surface, f"Bourse : {g.party.gil}", (r.right - 30, r.y + 46), 22, theme.TEXT_DIM, "midright")
        draw_text(surface, "Objets trouvés", (r.x + 30, r.y + 90), 22, theme.TEXT_DIM)
        if not res.items:
            draw_text(surface, "Aucun", (r.x + 60, r.y + 136), 24)
        for i, name in enumerate(res.items):
            icon_id = ITEM_ICONS.get(name)
            if icon_id:
                surface.blit(g.assets.scaled(icon_id, (36, 36)), (r.x + 50, r.y + 120 + 50 * i))
            draw_text(surface, name, (r.x + 100, r.y + 138 + 50 * i), 26, anchor="midleft")
        if int(self.t * 2) % 2 == 0 and self.t > 0.5:
            draw_text(surface, "Entrée : continuer", (640, 676), 22, theme.TEXT_DIM, "midtop")


@register_scene("loot")
def make_loot(game: Game, args: list[str]) -> Scene:
    """Butin de démonstration."""
    return LootScene(game)
