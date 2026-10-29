"""Classe de base des scènes."""

from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from final_classe.gfx.engine.game import Game


class Scene:
    """Une scène : un écran du jeu. Les sous-classes surchargent ce dont elles ont besoin.

    `transparent = True` : la scène du dessous est dessinée avant celle-ci (fenêtre modale).
    """

    transparent = False

    def __init__(self, game: "Game") -> None:
        self.game = game

    def on_enter(self) -> None:
        """Appelé quand la scène devient la scène courante pour la première fois."""

    def on_resume(self) -> None:
        """Appelé quand la scène du dessus a été retirée (pop)."""

    def on_exit(self) -> None:
        """Appelé quand la scène est retirée de la pile."""

    def on_back(self) -> None:
        """Échap : par défaut, retire la scène si elle n'est pas la dernière."""
        if len(self.game.stack) > 1:
            self.game.pop(transition="fade")

    def handle_event(self, event: pygame.event.Event) -> None:
        """Un évènement (positions de souris déjà converties en coordonnées logiques)."""

    def update(self, dt: float) -> None:
        """Avance de `dt` secondes."""

    def draw(self, surface: pygame.Surface) -> None:
        """Dessine sur la surface logique 1280×720."""
