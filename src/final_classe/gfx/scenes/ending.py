"""Fin du jeu : lever de soleil, équipe au complet, générique défilant."""

import math
from typing import override

import pygame

from final_classe.gfx.engine import Game, Scene, make_demo_party, register_scene
from final_classe.gfx.engine.registry import SCENES
from final_classe.gfx.scenes import flow
from final_classe.gfx.scenes._demo import hero_image
from final_classe.gfx.ui import draw_text, theme
from final_classe.gfx.ui.keys import is_confirm
from final_classe.gfx.ui.draw import render_text

SPEED = 46.0  # pixels par seconde

CREDITS = [
    ("T", "FINAL CLASSE"),
    ("S", "Sephiroth est vaincu. Le monde est sauvé !"),
    ("G", 60),
    ("H", "Les héros"),
    ("PARTY", 0),
    ("G", 40),
    ("H", "Les adversaires vaincus"),
    ("L", "Flan · Loup · Bombo · Ahriman · Cactuar · Malboro"),
    ("L", "Tonberry · Golem · Béhémoth · Chimère · Liche"),
    ("L", "Garland · Dragon rouge · Sephiroth"),
    ("G", 40),
    ("H", "Un jeu en Python"),
    ("L", "Modèle objet et combats : le cours Python"),
    ("L", "Interface, scènes et animations : pygame-ce"),
    ("L", "Musiques et bruitages : synthétisés par le code"),
    ("L", "Décors et sprites : générés puis détourés"),
    ("G", 40),
    ("H", "Merci d'avoir joué"),
    ("G", 120),
    ("T", "FIN"),
]


class EndingScene(Scene):
    """Générique qui défile sur `bg_ending` ; une touche ramène au titre quand il est fini."""

    def __init__(self, game: Game) -> None:
        super().__init__(game)
        if game.party is None:
            game.party = make_demo_party()
        self.time = 0.0
        self.scroll = 0.0
        self.heights = [self._height(kind, v) for kind, v in CREDITS]
        self.total = sum(self.heights)
        self.over = False
        self.boost = False
        self._msg = render_text("Appuyez sur Entrée", 22, theme.WHITE).copy()

    def _height(self, kind: str, value) -> int:
        return {"T": 90, "S": 56, "H": 64, "L": 36, "G": int(value) if kind == "G" else 0,
                "PARTY": 190}[kind]

    @override
    def on_enter(self) -> None:
        self.game.audio.play_music("ending")

    @override
    def on_back(self) -> None:
        self._finish()

    def _finish(self) -> None:
        """Première pression : accélère ; deuxième : saute à la fin ; ensuite : retour au titre."""
        if self.over:
            if "title" in SCENES:
                self.game.replace_all(SCENES["title"](self.game, []))
        elif not self.boost:
            self.boost = True
        else:
            self.scroll = self.total + 420
            self.over = True

    @override
    def handle_event(self, event: pygame.event.Event) -> None:
        if is_confirm(event) or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
            self._finish()
        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_DOWN, pygame.K_s):
            self.scroll += 120  # accélérer le générique

    @override
    def update(self, dt: float) -> None:
        self.time += dt
        if not self.over:
            self.scroll += SPEED * (6 if self.boost else 1) * dt
            if self.scroll > self.total + 720 - 300:
                self.scroll = self.total + 420
                self.over = True

    def _draw_party(self, surface: pygame.Surface, y: int) -> None:
        heroes = self.game.party.heroes
        n = len(heroes)
        for i, hero in enumerate(heroes):
            cx = 640 + (i - (n - 1) / 2) * 280
            bob = abs(math.sin(self.time * 2 + i)) * 6
            flow.draw_portrait(surface, self.game.assets, hero_image(hero),
                               pygame.Rect(int(cx) - 70, int(y - bob), 140, 130), flip=True)
            draw_text(surface, hero.name, (int(cx), y + 142), 24, theme.GOLD, "center", bold=True)
            draw_text(surface, f"{hero.title}  Niv. {hero.level}", (int(cx), y + 170), 16, theme.WHITE, "center")

    @override
    def draw(self, surface: pygame.Surface) -> None:
        assets = self.game.assets
        flow.draw_backdrop(surface, assets, "bg_ending")
        surface.blit(flow.solid((800, 720), (6, 10, 34, 105)), (240, 0))
        y = 720 - self.scroll
        for (kind, value), h in zip(CREDITS, self.heights, strict=True):
            if -h < y < 720:
                if kind == "T":
                    text = render_text(str(value), 64, theme.GOLD, bold=True, title=True)
                    surface.blit(text, text.get_rect(center=(640, y + h // 2)))
                elif kind == "S":
                    draw_text(surface, str(value), (640, y + 20), 28, theme.WHITE, "center", title=True)
                elif kind == "H":
                    draw_text(surface, str(value), (640, y + 24), 30, theme.GOLD, "center", bold=True)
                elif kind == "L":
                    draw_text(surface, str(value), (640, y + 8), 22, theme.WHITE, "center")
                elif kind == "PARTY":
                    self._draw_party(surface, int(y))
            y += h
        if self.over:
            alpha = 150 + 100 * math.sin(self.time * 3)
            msg = self._msg
            msg.set_alpha(int(alpha))
            surface.blit(msg, msg.get_rect(center=(640, 690)))


@register_scene("ending")
def make_ending(game: Game, args: list[str]) -> Scene:
    """Fabrique de la scène de fin."""
    return EndingScene(game)
