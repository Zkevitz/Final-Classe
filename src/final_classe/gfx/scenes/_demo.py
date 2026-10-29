"""Aides communes aux scènes d'avant-partie : scénario automatique (`--demo`) et décors sombres."""

from collections.abc import Callable

import pygame

from final_classe.gfx.engine.game import Game
from final_classe.gfx.ui import vertical_gradient

# Les jobs : id d'image par nom de classe (docs/ARCHITECTURE-GFX.md §6) et description courte.
HERO_IMAGE = {
    "Soldier": "hero_soldier", "BlackMage": "hero_black_mage", "Knight": "hero_knight",
    "Monk": "hero_monk", "Thief": "hero_thief", "Samurai": "hero_samurai",
    "Archer": "hero_archer", "Ninja": "hero_ninja",
}
JOB_TEXT = {
    "Soldier": "Un combattant d'élite, épée immense à la main. Omnislash : trois coups d'affilée sur un ennemi.",
    "BlackMage": "Fragile, mais ses sorts font des ravages. Feu : une attaque magique qui brûle sa cible.",
    "Knight": "Une armure épaisse et beaucoup de PV. Brise-armure : frappe, puis divise par deux la DÉF de la cible.",
    "Monk": "Il se bat à mains nues et soigne ses alliés. Chakra : rend MAG × 15 PV à un allié.",
    "Thief": "Rapide, ses doigts vident la bourse des monstres. Vol : prend tous les gils de la cible.",
    "Samurai": "Lent, mais sa lame traverse les armures. Lame bannie : ne compte que la moitié de la DÉF.",
    "Archer": "Un tireur précis. Tir précis : FOR × 12 de dégâts, sans tenir compte de la DÉF.",
    "Ninja": "Le plus rapide de tous. Lancer : ses shurikens touchent tous les ennemis à la fois.",
}


# Recrues qui ont leur propre sprite (par nom de héros).
NAMED_IMAGE = {  # nom -> (classe de job, sprite)
    "Lulu": ("BlackMage", "hero_lulu"), "Basch": ("Knight", "hero_basch"),
    "Amarant": ("Monk", "hero_amarant"),
}


def hero_image(hero_or_class: object) -> str:
    """L'id d'image d'un héros : sprite nommé (Lulu, Basch, Amarant), sinon celui de son job."""
    if not isinstance(hero_or_class, type):
        named = NAMED_IMAGE.get(str(getattr(hero_or_class, "name", "")))
        if named and named[0] == type(hero_or_class).__name__:
            return named[1]
    cls = hero_or_class if isinstance(hero_or_class, type) else type(hero_or_class)
    return HERO_IMAGE.get(cls.__name__, "hero_soldier")


def key_event(key: int, char: str = "") -> pygame.event.Event:
    """Un évènement clavier fabriqué (pour le mode `--demo`)."""
    return pygame.event.Event(pygame.KEYDOWN, key=key, unicode=char, mod=0)


class DemoScript:
    """Liste d'actions datées (secondes cumulées) jouées par `update` tant qu'aucun fondu n'est en cours."""

    def __init__(self, game: Game, steps: list[tuple[float, Callable[[], None]]]) -> None:
        self.game = game
        self.steps = sorted(steps, key=lambda s: s[0])
        self.t = 0.0
        self.i = 0

    def update(self, dt: float) -> None:
        """Avance le scénario et déclenche les actions échues."""
        if self.game.transitioning:
            return
        self.t += dt
        while self.i < len(self.steps) and self.steps[self.i][0] <= self.t:
            action = self.steps[self.i][1]
            self.i += 1
            action()


_backdrops: dict[int, pygame.Surface] = {}


def draw_backdrop(surface: pygame.Surface, game: Game, darkness: int = 120) -> None:
    """`bg_title` assombri (ou dégradé nocturne si l'image manque), mis en cache par niveau."""
    cached = _backdrops.get(darkness)
    if cached is None:
        cached = pygame.Surface((1280, 720))
        if game.assets.exists("bg_title"):
            cached.blit(game.assets.image("bg_title"), (0, 0))
        else:
            cached.blit(vertical_gradient((1280, 720), (10, 16, 60), (40, 30, 90)), (0, 0))
        veil = pygame.Surface((1280, 720), pygame.SRCALPHA)
        veil.fill((4, 8, 28, darkness))
        cached.blit(veil, (0, 0))
        _backdrops[darkness] = cached
    surface.blit(cached, (0, 0))
