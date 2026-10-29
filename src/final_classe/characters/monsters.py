"""Monster : chaque espèce redéfinit ses statistiques en attributs de classe."""

import random
from collections.abc import Sequence
from typing import override

from final_classe.characters.base import Character
from final_classe.characters.hit import Hit
from final_classe.items import Element


class Monster(Character):
    """Un monstre de Final Classe."""

    NAME = "Monstre"
    HP = 100
    MP = 0
    STRENGTH = 10
    MAGIC = 1
    DEFENSE = 1
    RESISTANCE = 1
    SPEED = 10
    XP = 0
    GIL = 0
    WEAKNESS: Element | None = None  # l'élément qu'il craint

    def __init__(self, name: str | None = None, **changes: int) -> None:
        stats = {
            "hp": self.HP,
            "mp": self.MP,
            "strength": self.STRENGTH,
            "magic": self.MAGIC,
            "defense": self.DEFENSE,
            "resistance": self.RESISTANCE,
            "speed": self.SPEED,
        }
        stats.update(changes)  # une variante, Wolf("Loup alpha", hp=600)
        super().__init__(name or self.NAME, **stats)
        self.xp = self.XP
        self.gil = self.GIL

    @property
    @override
    def title(self) -> str:
        """Un monstre n'a pas de job."""
        return "Monstre"

    @override
    def damage_multiplier(self, element: Element | None) -> int:
        """Les dégâts doublent sur la faiblesse du monstre."""
        return 2 if element is not None and element is self.WEAKNESS else 1

    @property
    def warning(self) -> str | None:
        """Ce que le monstre laisse deviner de son prochain tour ; rien, par défaut."""
        return None

    def act(self, heroes: Sequence[Character]) -> list[Hit]:
        """Le tour du monstre : il attaque un héros debout, au hasard.

        Renvoie un Hit par coup porté.
        """
        target = random.choice([hero for hero in heroes if hero.is_alive])
        return [Hit("attaque", target, self.attack(target))]
