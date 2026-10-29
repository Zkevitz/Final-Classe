"""Les jobs : chaque classe redéfinit des attributs de classe, et écrit sa compétence."""

from typing import override

from final_classe.characters.base import Character
from final_classe.characters.heroes import Hero
from final_classe.items import Potion, Target


class Soldier(Hero):
    """Le Soldat : une épée immense, et Omnislash."""

    BASE_HP = 700
    BASE_MP = 50
    SPEED = 12
    JOB_NAME = "Soldat"
    SKILL_NAME = "Omnislash"
    SKILL_COST = 12

    @override
    def skill_effect(self, target: Character) -> int:
        """Trois coups d'épée d'affilée."""
        return sum(self.attack(target) for _ in range(3))


class BlackMage(Hero):
    """Le Mage noir : fragile, mais Feu fait mal."""

    BASE_HP = 520
    BASE_MP = 90
    SPEED = 10
    JOB_NAME = "Mage noir"
    SKILL_NAME = "Feu"
    SKILL_COST = 8
    SKILL_TEXT = "{user} lance Feu sur {target} : {value} dégâts."

    @override
    def skill_effect(self, target: Character) -> int:
        """Une attaque magique."""
        return self.magic_attack(target, 12)


class Knight(Hero):
    """Le Chevalier : une armure épaisse, et Brise-armure pour ouvrir la voie à l'équipe."""

    BASE_HP = 820
    BASE_MP = 30
    SPEED = 8
    JOB_NAME = "Chevalier"
    SKILL_NAME = "Brise-armure"
    SKILL_COST = 6
    SKILL_TEXT = (
        "{user} brise l'armure de {target} : {value} dégâts, et sa DÉF est divisée par deux."
    )

    @override
    def skill_effect(self, target: Character) -> int:
        """Une attaque, puis la DÉF de la cible est divisée par deux."""
        damage = self.attack(target)
        target.lower_defense()
        return damage


class Monk(Hero):
    """Le Moine : il se bat à mains nues, et soigne avec le Chakra."""

    BASE_HP = 680
    BASE_MP = 60
    SPEED = 11
    JOB_NAME = "Moine"
    SKILL_NAME = "Chakra"
    SKILL_COST = 10
    SKILL_TARGET = Target.ALLY
    SKILL_TEXT = "{user} utilise Chakra sur {target} : +{value} PV."

    @override
    def skill_effect(self, target: Character) -> int:
        """Soigne l'allié : MAG × 15 PV."""
        return target.heal(self.magic * 15)


class Thief(Hero):
    """Le Voleur : rapide, et ses doigts vident la bourse des monstres."""

    BASE_HP = 600
    BASE_MP = 50
    SPEED = 16
    JOB_NAME = "Voleur"
    SKILL_NAME = "Vol"
    SKILL_COST = 4
    SKILL_TEXT = "{user} vole {value} gils à {target}, et une potion s'il en a trouvé."

    @override
    def skill_effect(self, target: Character) -> int:
        """Prend tous les gils de la cible."""
        stolen = target.gil
        target.gil = 0
        self.gil += stolen
        if stolen > 0:  # une bourse pleine cache souvent une potion
            self.loot.append(Potion())
        return stolen


class Samurai(Hero):
    """Le Samouraï : lent, mais sa Lame bannie traverse les armures."""

    BASE_HP = 760
    BASE_MP = 40
    SPEED = 9
    JOB_NAME = "Samouraï"
    SKILL_NAME = "Lame bannie"
    SKILL_COST = 15

    @override
    def skill_effect(self, target: Character) -> int:
        """Une attaque physique qui ne compte que la moitié de la DÉF."""
        return self.strike(target, self.strength * 12 - target.defense * 5 // 2)


class Archer(Hero):
    """L'Archer : son Tir précis ignore la DÉF."""

    BASE_HP = 580
    BASE_MP = 50
    SPEED = 14
    JOB_NAME = "Archer"
    SKILL_NAME = "Tir précis"
    SKILL_COST = 6

    @override
    def skill_effect(self, target: Character) -> int:
        """FOR × 12, sans tenir compte de la DÉF."""
        return self.strike(target, self.strength * 12)


class Ninja(Hero):
    """Le Ninja : le plus rapide, et ses shurikens touchent tous les ennemis."""

    BASE_HP = 560
    BASE_MP = 50
    SPEED = 18
    JOB_NAME = "Ninja"
    SKILL_NAME = "Lancer"
    SKILL_COST = 8
    SKILL_TARGET = Target.ENEMIES
    SKILL_TEXT = "{user} lance ses shurikens sur {target} : {value} dégâts au total."

    @override
    def skill_effect(self, target: Character) -> int:
        """FOR × 8 − DÉF × 3, sur chaque ennemi."""
        return self.strike(target, self.strength * 8 - target.defense * 3)


# Des classes, rangées dans une liste : la création les propose, la sauvegarde les retrouve.
JOBS: list[type[Hero]] = [Soldier, BlackMage, Knight, Monk, Thief, Samurai, Archer, Ninja]
JOBS_BY_NAME: dict[str, type[Hero]] = {job.JOB_NAME: job for job in JOBS}
