"""Hero : un héros a toujours un job, qui fixe ses PV, ses PM, sa VIT et sa compétence."""

from abc import abstractmethod
from typing import Any, Self, override

from final_classe.characters.base import Character
from final_classe.items import Equipment, Materia, Slot, Target, Usable
from final_classe.stats import Stats


class Hero(Character):
    """Un héros de Final Classe. Abstraite : on crée toujours un job."""

    BASE_HP = 600
    BASE_MP = 60
    SPEED = 10
    JOB_NAME = "Héros"
    SKILL_NAME = "Compétence"
    SKILL_COST = 0
    SKILL_TARGET = Target.ENEMY
    SKILL_TEXT = "{user} utilise {skill} sur {target} : {value} dégâts."
    LEVEL_UP = Stats(strength=3, magic=3, defense=3, resistance=3)  # à chaque niveau

    def __init__(self, name: str, strength: int, magic: int, defense: int, resistance: int) -> None:
        super().__init__(
            name, self.BASE_HP, self.BASE_MP, strength, magic, defense, resistance, self.SPEED
            # name, self.BASE_HP, self.BASE_MP, 999, 999, defense, resistance, self.SPEED
        )
        self.level = 1
        self.xp = 0
        self.guarding = False  # en garde : les coups reçus sont divisés par deux
        self.gear: dict[Slot, Equipment] = {}  # une pièce par emplacement
        self.loot: list[Usable] = []  # les objets volés, jusqu'au butin

    @property
    def name(self) -> str:
        """Le nom du héros."""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        value = value.strip()
        if not value:
            raise ValueError("Un héros a besoin d'un nom")
        self._name = value

    @property
    def title(self) -> str:
        """Le nom du job."""
        return self.JOB_NAME

    @property
    def equipment(self) -> list[Equipment]:
        """Les pièces portées."""
        return list(self.gear.values())

    def equip(self, item: Equipment) -> Equipment | None:
        """Range la pièce à son emplacement ; renvoie celle qu'elle remplace, ou None."""
        previous = self.gear.get(item.slot)
        self.gear[item.slot] = item
        return previous

    @property
    def spells(self) -> list[Materia]:
        """Les sorts du héros : les materias montées sur son équipement.

        L'appelant demande hero.spells ; il n'a pas à savoir que les sorts viennent
        des materias, montées sur les pièces d'équipement.
        """
        spells: list[Materia] = []
        for item in self.equipment:
            spells.extend(item.materias)
        return spells

    @property
    @override
    def stats(self) -> Stats:
        """La base, plus chaque pièce d'équipement : Stats sait s'additionner."""
        return sum((item.stats for item in self.equipment), super().stats)

    @property
    def can_use_skill(self) -> bool:
        """Vrai s'il reste assez de PM pour la compétence."""
        return self._mp >= self.SKILL_COST

    @property
    def xp_to_next(self) -> int:
        """L'XP qu'il faut pour passer au niveau suivant."""
        return self.level * 100

    def use_skill(self, *targets: Character) -> int:
        """La méthode modèle : paie les PM une fois, puis applique l'effet à chaque cible."""
        if not self.can_use_skill:
            return 0
        self._mp -= self.SKILL_COST
        return sum(self.skill_effect(target) for target in targets)

    @abstractmethod
    def skill_effect(self, target: Character) -> int:
        """L'effet de la compétence sur une cible : chaque job écrit le sien."""

    def can_cast(self, materia: Materia) -> bool:
        """Vrai si la materia est montée sur l'équipement, et s'il reste assez de PM."""
        return materia in self.spells and self._mp >= materia.cost

    def cast(self, materia: Materia, *targets: Character) -> int:
        """Lance le sort d'une materia : les PM une fois, puis la materia fait le travail."""
        if not self.can_cast(materia):
            return 0
        self._mp -= materia.cost
        return sum(materia.cast(self, target) for target in targets)

    def to_dict(self) -> dict[str, Any]:
        """Le héros en dictionnaire : son job, sa progression, sa base et son équipement."""
        return {
            "job": self.JOB_NAME,
            "name": self.name,
            "level": self.level,
            "xp": self.xp,
            "max_hp": self.max_hp,
            "max_mp": self.max_mp,
            "stats": self._base.to_dict(),  # la base seule : l'équipement est sauvé à part
            "gear": [item.to_dict() for item in self.equipment],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Recrée un héros : cls est le job appelé, Knight.from_dict crée un Knight."""
        base = Stats.from_dict(data["stats"])
        hero = cls(data["name"], base.strength, base.magic, base.defense, base.resistance)
        hero._base = base
        hero.level = data["level"]
        hero.xp = data["xp"]
        hero.max_hp = data["max_hp"]
        hero.max_mp = data["max_mp"]
        for item in data["gear"]:
            hero.equip(Equipment.from_dict(item))
        hero.rest()
        return hero

    def start_turn(self) -> None:
        """Le début du tour du héros : il quitte sa garde."""
        self.guarding = False

    def defend(self) -> None:
        """Se met en garde jusqu'à son prochain tour."""
        self.guarding = True

    @override
    def take_damage(self, amount: int) -> int:
        """En garde, le héros n'encaisse que la moitié du coup."""
        if self.guarding:
            amount //= 2
        return super().take_damage(amount)

    def rest(self) -> None:
        """Entre deux combats : tous les PV et les PM, même après un K.O."""
        self._hp = self.max_hp
        self._mp = self.max_mp

    def gain_xp(self, amount: int) -> int:
        """Ajoute de l'XP ; renvoie le nombre de niveaux gagnés."""
        self.xp += amount
        levels = 0
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level += 1
            self.max_hp += 100
            self.max_mp += 10
            self._base += self.LEVEL_UP  # une nouvelle Stats, rangée à la place de l'ancienne
            levels += 1
        if levels:  # un nouveau niveau remet les PV et les PM au maximum
            self.rest()
        return levels
