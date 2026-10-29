"""Party : l'équipe a des héros, une bourse, un sac, des objets et des materias."""

from typing import Any, Self

from final_classe.characters.heroes import Hero
from final_classe.characters.jobs import JOBS_BY_NAME
from final_classe.characters.monsters import Monster
from final_classe.items import (
    Equipment,
    Inventory,
    Materia,
    PhoenixDown,
    Potion,
    materia_from_dict,
)


class Party:
    """L'équipe : le héros du joueur en premier, puis ses compagnons."""

    def __init__(self, heroes: list[Hero]) -> None:
        self.heroes = heroes
        self.gil = 0
        self.bag: list[Equipment] = []  # l'équipement qui n'est porté par personne
        self.materias: list[Materia] = []  # les materias qui ne sont montées nulle part
        self.items = Inventory(Potion(), Potion(), Potion(), PhoenixDown())

    @property
    def leader(self) -> Hero:
        """Le héros du joueur."""
        return self.heroes[0]

    @property
    def standing(self) -> list[Hero]:
        """Les héros encore debout."""
        return [hero for hero in self.heroes if hero.is_alive]

    @property
    def knocked_out(self) -> list[Hero]:
        """Les héros K.O."""
        return [hero for hero in self.heroes if not hero.is_alive]

    def reward(self, monsters: list[Monster]) -> list[Hero]:
        """L'XP aux héros debout, les gils (même ceux volés) dans la bourse.

        Renvoie les héros qui ont gagné au moins un niveau.
        """
        xp = sum(monster.xp for monster in monsters)
        self.gil += sum(monster.gil for monster in monsters)
        for hero in self.heroes:  # les gils volés par un héros rejoignent la bourse
            self.gil += hero.gil
            hero.gil = 0
            self.items.add(*hero.loot)  # et les objets volés, le sac
            hero.loot.clear()
        return [hero for hero in self.standing if hero.gain_xp(xp) > 0]

    def buy(self, item: Equipment) -> bool:
        """Achète une pièce : les gils sont payés, et elle rejoint le sac. False s'il en manque."""
        if self.gil < item.price:
            return False
        self.gil -= item.price
        self.bag.append(item)
        return True

    def sell(self, item: Equipment) -> int:
        """Vend une pièce du sac à moitié prix ; renvoie les gils gagnés."""
        self.bag.remove(item)
        self.gil += item.price // 2
        return item.price // 2

    def to_dict(self) -> dict[str, Any]:
        """L'équipe en dictionnaire : chaque objet donne le sien."""
        return {
            "heroes": [hero.to_dict() for hero in self.heroes],
            "gil": self.gil,
            "bag": [item.to_dict() for item in self.bag],
            "materias": [materia.to_dict() for materia in self.materias],
            "items": self.items.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Recrée l'équipe ; JOBS_BY_NAME choisit la classe de chaque héros."""
        party = cls([JOBS_BY_NAME[hero["job"]].from_dict(hero) for hero in data["heroes"]])
        party.gil = data["gil"]
        party.bag = [Equipment.from_dict(item) for item in data["bag"]]
        party.materias = [materia_from_dict(materia) for materia in data["materias"]]
        party.items = Inventory.from_dict(data["items"])
        return party

    def rest(self) -> None:
        """Entre deux combats, chaque héros se repose."""
        for hero in self.heroes:
            hero.rest()
