"""Écran de victoire : fanfare, héros qui sautent, décompte de l'XP et des gils."""

import math
from dataclasses import dataclass, field
from typing import override

import pygame
from pygame import Vector2

from final_classe.gfx.engine.game import Game
from final_classe.gfx.engine.registry import register_scene
from final_classe.gfx.engine.scene import Scene
from final_classe.gfx.scenes.battle_actors import BattleActor, draw_background, place_heroes
from final_classe.gfx.ui import Banner, draw_text, draw_window, is_confirm, theme

try:
    from final_classe.gfx.fx.choreo import ActionContext, play
except Exception:  # noqa: BLE001
    ActionContext = None  # type: ignore[assignment,misc]
    play = None  # type: ignore[assignment]


@dataclass
class BattleResult:
    """Ce que le combat a rapporté (déjà appliqué à l'équipe)."""

    zone: int
    wave: int
    n_waves: int
    xp: int
    gil: int
    items: list[str] = field(default_factory=list)
    leveled: list[tuple[str, int]] = field(default_factory=list)


def compute_result(game: Game, monsters: list, zone: int, wave: int, n_waves: int) -> BattleResult:
    """Applique `party.reward` et résume le butin."""
    party = game.party
    xp = sum(m.xp for m in monsters)
    gil0 = party.gil
    stolen = [item.name for h in party.heroes for item in h.loot]
    leveled = party.reward(monsters)
    return BattleResult(zone, wave, n_waves, xp, party.gil - gil0, stolen,
                        [(h.name, h.level) for h in leveled])


class VictoryScene(Scene):
    """Victoire : XP et gils décomptés, montées de niveau."""

    def __init__(self, game: Game, monsters: list, zone: int, wave: int, n_waves: int) -> None:
        super().__init__(game)
        if game.party is None:
            from final_classe.gfx.engine.demo import make_demo_party

            game.party = make_demo_party()
        self.zone = zone
        self.result = compute_result(game, monsters, zone, wave, n_waves)
        self.heroes = [BattleActor(game, h, "hero", Vector2(), i) for i, h in enumerate(game.party.heroes)]
        place_heroes(game.assets, self.heroes)
        for a in self.heroes:
            a.ko = not a.alive
            a.set_pose("victory" if a.alive else "idle", instant=True)  # idle = ko pour un K.O.
        self.t = 0.0
        self.banner = Banner("VICTOIRE !", theme.GOLD, 3.2, y=70, size=60)
        self._levels_played = 0
        self._left = False

    @override
    def on_enter(self) -> None:
        self.game.audio.play_music("victory")

    def _full_time(self) -> float:
        return 3.0 + 0.6 * len(self.result.leveled)

    def _next(self) -> None:
        if self._left:
            return
        self._left = True
        from final_classe.gfx.scenes.loot import LootScene

        self.game.replace(LootScene(self.game, self.result))

    @override
    def handle_event(self, event: pygame.event.Event) -> None:
        if is_confirm(event) or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
            if self.t < self._full_time():
                self.t = self._full_time()
            else:
                self._next()

    @override
    def update(self, dt: float) -> None:
        self.t += dt
        for i, a in enumerate(self.heroes):
            a.jump = 26 * abs(math.sin((self.t - 0.3 - i * 0.18) * 4)) if (a.alive and 0.3 < self.t < 2.6) else 0.0
            a.update(dt)
        self.banner.update(dt)
        while self._levels_played < len(self.result.leveled) and self.t > 3.0 + 0.6 * self._levels_played:
            name = self.result.leveled[self._levels_played][0]
            actor = next((a for a in self.heroes if a.model.name == name), None)
            self._levels_played += 1
            if actor is not None and play is not None and ActionContext is not None:
                g = self.game
                ctx = ActionContext(caster=actor, targets=[actor], values=[0], critical=[False],
                                    on_impact=lambda i: None, fx=g.fx, audio=g.audio, assets=g.assets, extra={})
                g.fx.add(play("state.level_up", ctx))
        if self.game.demo and self.t > self._full_time() + 1.5:
            self._next()

    @override
    def draw(self, surface: pygame.Surface) -> None:
        g = self.game
        draw_background(g, surface, self.zone)
        g.fx.draw(surface, "back")
        for a in self.heroes:
            a.draw_shadow(surface)
        for a in sorted(self.heroes, key=lambda a: (a.draw_front, a.home.y)):
            a.draw(surface)
        g.fx.draw(surface, "front")
        self.banner.draw(surface)
        r = draw_window(surface, (80, 220, 600, 150 + 36 * len(self.result.leveled)))
        k_xp = min(1.0, max(0.0, (self.t - 0.8) / 1.0))
        k_gil = min(1.0, max(0.0, (self.t - 1.8) / 1.0))
        draw_text(surface, "Expérience", (r.x + 30, r.y + 28), 28, theme.TEXT_DIM)
        draw_text(surface, f"+{int(self.result.xp * k_xp)}", (r.right - 30, r.y + 28), 30, theme.GOLD, "topright")
        draw_text(surface, "chaque héros debout", (r.x + 30, r.y + 62), 18, theme.TEXT_DIM)
        draw_text(surface, "Gils", (r.x + 30, r.y + 96), 28, theme.TEXT_DIM)
        draw_text(surface, f"+{int(self.result.gil * k_gil)}", (r.right - 30, r.y + 96), 30, theme.GOLD, "topright")
        for i, (name, level) in enumerate(self.result.leveled):
            if self.t > 3.0 + 0.6 * i:
                draw_text(surface, f"{name} passe au niveau {level} !", (r.x + 30, r.y + 146 + 36 * i), 26, theme.HP)
        if self.t >= self._full_time() and int(self.t * 2) % 2 == 0:
            draw_text(surface, "Entrée : continuer", (640, 676), 22, theme.TEXT_DIM, "midtop")


@register_scene("victory")
def make_victory(game: Game, args: list[str]) -> Scene:
    """Victoire de démonstration (Flan + Loup, Plaines)."""
    from final_classe.game.zones import ZONES

    return VictoryScene(game, ZONES[0].waves()[2], 0, 2, 3)
