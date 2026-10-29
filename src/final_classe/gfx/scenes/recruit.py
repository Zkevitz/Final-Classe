"""Recrutement : le héros du joueur choisit deux compagnons parmi les héros disponibles."""

from typing import override

import pygame

from final_classe.characters import Hero, Party
from final_classe.game.recruit import TEAM_SIZE, recruits  # fonctions pures de la version terminal
from final_classe.gfx.engine.game import Game
from final_classe.gfx.engine.registry import SCENES, register_scene
from final_classe.gfx.engine.scene import Scene
from final_classe.gfx.scenes._demo import DemoScript, draw_backdrop, hero_image, key_event
from final_classe.gfx.ui import Banner, Menu, draw_text, draw_window, theme

PAUSE = 2.4  # durée de l'écran « l'équipe est formée » en mode démo


class RecruitScene(Scene):
    """Liste des candidats à gauche, fiche à droite, équipe en bas."""

    def __init__(self, game: Game) -> None:
        super().__init__(game)
        leader = game.party.heroes[0] if game.party else recruits()[0]
        self.team: list[Hero] = [leader]
        self.available = [h for h in recruits()]
        self.menu = Menu([], (50, 110), width=360, row_h=46, font_size=24)
        self._refresh()
        self.time = 0.0
        self.done = False
        self.done_t = 0.0
        self.banner: Banner | None = None
        self.script = DemoScript(game, [
            (1.0, lambda: self.handle_event(key_event(pygame.K_DOWN))),
            (1.8, lambda: self.handle_event(key_event(pygame.K_RETURN))),
            (3.2, lambda: self.handle_event(key_event(pygame.K_DOWN))),
            (3.6, lambda: self.handle_event(key_event(pygame.K_DOWN))),
            (4.4, lambda: self.handle_event(key_event(pygame.K_RETURN))),
        ]) if game.demo else None

    def _refresh(self) -> None:
        self.menu.set_items([f"{h.name}  ·  {h.title}" for h in self.available])
        self.menu.cursor = min(self.menu.cursor, max(0, len(self.available) - 1))

    @override
    def on_enter(self) -> None:
        self.game.audio.play_music("title")

    @override
    def on_back(self) -> None:
        """Échap : reprend le dernier compagnon, ou revient à la création."""
        self.game.audio.play_sfx("cancel")
        if self.done:
            return
        if len(self.team) > 1:
            self.available.insert(0, self.team.pop())
            self._refresh()
        elif "creation" in SCENES:
            self.game.replace(SCENES["creation"](self.game, []))

    def _validate(self) -> None:
        """L'équipe est complète : elle devient la `Party` du jeu."""
        self.done = True
        self.done_t = 0.0
        self.game.party = Party(self.team)
        self.game.zone = self.game.wave = 0
        self.game.save()  # zone 0, vague 0 : « Continuer » repart d'ici
        self.game.audio.play_sfx("level_up")

    def _leave(self) -> None:
        for name in ("world_map",):
            if name in SCENES:
                self.game.replace(SCENES[name](self.game, []))
                return
        if self.banner is None:
            self.banner = Banner("La carte du monde arrive bientôt", seconds=2.0, y=300, size=32)

    @override
    def handle_event(self, event: pygame.event.Event) -> None:
        if self.game.transitioning:
            return
        if self.done:
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN) and self.done_t > 0.4:
                self._leave()
            return
        before = self.menu.cursor
        chosen = self.menu.handle_event(event)
        if self.menu.cursor != before:
            self.game.audio.play_sfx("cursor")
        if chosen is not None:
            self.game.audio.play_sfx("confirm")
            self.team.append(self.available.pop(chosen))
            self._refresh()
            if len(self.team) >= TEAM_SIZE:
                self._validate()

    @override
    def update(self, dt: float) -> None:
        self.time += dt
        if self.script:
            self.script.update(dt)
        self.menu.update(dt)
        if self.done:
            self.done_t += dt
            if self.game.demo and self.done_t > PAUSE:
                self._leave()
        if self.banner and not self.banner.update(dt):
            self.banner = None

    # --- dessin ---------------------------------------------------------------------------
    def _draw_sheet(self, surface: pygame.Surface, hero: Hero) -> None:
        panel = pygame.Rect(430, 110, 800, 380)
        draw_window(surface, panel)
        self.game.assets.draw_sprite(surface, hero_image(hero), (panel.x + 190, panel.bottom - 30), 1.15)
        x = panel.x + 370
        draw_text(surface, hero.name, (x, panel.y + 22), 38, theme.GOLD, bold=True, title=True)
        draw_text(surface, hero.title, (x, panel.y + 70), 24, theme.TEXT_DIM)
        lines = (
            f"PV {hero.max_hp}      PM {hero.max_mp}      VIT {hero.speed}",
            f"FOR {hero.strength}   MAG {hero.magic}   DÉF {hero.defense}   RÉS {hero.resistance}",
        )
        for i, text in enumerate(lines):
            draw_text(surface, text, (x, panel.y + 125 + i * 40), 24)
        draw_text(surface, f"Compétence : {hero.SKILL_NAME}", (x, panel.y + 235), 26, theme.GOLD)
        draw_text(surface, f"Coût : {hero.SKILL_COST} PM", (x, panel.y + 272), 22, theme.TEXT_DIM)

    def _draw_team(self, surface: pygame.Surface) -> None:
        draw_window(surface, (50, 520, 1180, 150))
        draw_text(surface, f"Équipe ({len(self.team)}/{TEAM_SIZE})", (80, 532), 22, theme.GOLD)
        for i in range(TEAM_SIZE):
            cx = 330 + i * 330
            if i < len(self.team):
                hero = self.team[i]
                self.game.assets.draw_sprite(surface, hero_image(hero), (cx - 90, 655), 0.5)
                draw_text(surface, hero.name, (cx - 40, 570), 26, theme.TEXT)
                draw_text(surface, hero.title, (cx - 40, 604), 20, theme.TEXT_DIM)
            else:
                draw_text(surface, "— libre —", (cx - 40, 585), 24, theme.TEXT_DIM)

    @override
    def draw(self, surface: pygame.Surface) -> None:
        draw_backdrop(surface, self.game, 150)
        if self.done:
            draw_text(surface, "L'équipe est formée !", (640, 70), 44, theme.GOLD, "center", bold=True,
                      title=True)
            draw_window(surface, (180, 150, 920, 330))
            for i, hero in enumerate(self.team):
                cx = 340 + i * 300
                self.game.assets.draw_sprite(surface, hero_image(hero), (cx, 420), 0.9)
                draw_text(surface, hero.name, (cx, 440), 26, theme.TEXT, "midtop")
                draw_text(surface, hero.title, (cx, 472 - 0), 20, theme.TEXT_DIM, "midtop")
            draw_text(surface, "Appuyez sur une touche pour partir à l'aventure", (640, 560), 22,
                      theme.TEXT_DIM, "center")
        else:
            n = len(self.team)
            draw_text(surface, f"Recrutez un compagnon ({n}/{TEAM_SIZE})", (640, 56), 38, theme.GOLD,
                      "center", bold=True, title=True)
            self.menu.draw(surface, self.game.assets)
            if self.available:
                self._draw_sheet(surface, self.available[self.menu.cursor])
            self._draw_team(surface)
            draw_text(surface, "Haut / bas : choisir   Entrée : recruter   Échap : retour", (640, 696), 16,
                      theme.TEXT_DIM, "center")
        if self.banner:
            self.banner.draw(surface)


@register_scene("recruit")
def make_recruit(game: Game, args: list[str]) -> Scene:
    """Fabrique de la scène de recrutement."""
    return RecruitScene(game)
