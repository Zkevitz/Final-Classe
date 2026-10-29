"""Character : tout ce que les héros et les monstres partagent."""

from abc import ABC, abstractmethod
from dataclasses import replace

from final_classe.items import Element
from final_classe.stats import Stats


class Character(ABC):
    """Un combattant de Final Classe : un héros ou un monstre."""

    DAMAGE_CAP = 9999

    def __init__(
        self,
        name: str,
        hp: int,
        mp: int,
        strength: int,
        magic: int,
        defense: int,
        resistance: int,
        speed: int,
    ) -> None:
        if min(hp, strength, magic, defense, resistance, speed) < 1:
            raise ValueError("Chaque statistique vaut au moins 1")
        self.name = name
        self._base = Stats(strength, magic, defense, resistance, speed)  # les stats de base
        self.max_hp = hp
        self.max_mp = mp
        self._hp = hp
        self._mp = mp
        self.gil = 0

    @property
    @abstractmethod
    def title(self) -> str:
        """Ce qui s'affiche après le nom : le job du héros, ou « Monstre »."""

    def __str__(self) -> str:
        """Le personnage, pour le joueur : « Vaan (Soldat) »."""
        return f"{self.name} ({self.title})"

    @property
    def stats(self) -> Stats:
        """Les cinq statistiques ; un héros y ajoute son équipement."""
        return self._base

    # Les raccourcis : le reste du jeu continue d'écrire hero.strength.

    @property
    def strength(self) -> int:
        """La Force (FOR)."""
        return self.stats.strength

    @property
    def magic(self) -> int:
        """La Magie (MAG)."""
        return self.stats.magic

    @property
    def defense(self) -> int:
        """La Défense (DÉF)."""
        return self.stats.defense

    @property
    def resistance(self) -> int:
        """La Résistance (RÉS)."""
        return self.stats.resistance

    @property
    def speed(self) -> int:
        """La Vitesse (VIT)."""
        return self.stats.speed

    @property
    def hp(self) -> int:
        """Les PV actuels : en lecture seule."""
        return self._hp

    @property
    def mp(self) -> int:
        """Les PM actuels : en lecture seule."""
        return self._mp

    @property
    def is_alive(self) -> bool:
        """Vrai tant qu'il reste des PV."""
        return self._hp > 0

    @property
    def hp_ratio(self) -> float:
        """La part de PV restante, entre 0 et 1."""
        return self._hp / self.max_hp

    def strike(self, target: Character, damage: int) -> int:
        """Inflige des dégâts bornés entre 1 et 9999 ; renvoie les PV perdus par la cible."""
        damage = max(1, min(Character.DAMAGE_CAP, damage))
        return target.take_damage(damage)

    def attack(self, target: Character) -> int:
        """L'attaque physique : la FOR contre la DÉF de la cible."""
        return self.strike(target, self.strength * 10 - target.defense * 5)

    def magic_attack(self, target: Character, power: int, element: Element | None = None) -> int:
        """L'attaque magique : la MAG contre la RÉS de la cible, doublée sur sa faiblesse."""
        damage = self.magic * power - target.resistance * 5
        return self.strike(target, damage * target.damage_multiplier(element))

    def damage_multiplier(self, element: Element | None) -> int:
        """Le multiplicateur des dégâts d'un élément ; aucune faiblesse par défaut."""
        return 1

    def lower_defense(self) -> None:
        """Divise la DÉF par deux, sans descendre sous 1 : c'est Brise-armure."""
        # Une Stats est gelée : replace en crée une copie, avec une DÉF différente.
        self._base = replace(self._base, defense=max(1, self._base.defense // 2))

    def take_damage(self, amount: int) -> int:
        """Retire des PV, sans descendre sous 0 ; renvoie les PV réellement perdus."""
        lost = min(amount, self._hp)
        self._hp -= lost
        return lost

    def heal(self, amount: int) -> int:
        """Rend des PV à un personnage debout, sans dépasser le maximum ; renvoie les PV rendus."""
        if not self.is_alive:
            return 0
        gained = min(amount, self.max_hp - self._hp)
        self._hp += gained
        return gained

    def restore_mp(self, amount: int) -> int:
        """Rend des PM à un personnage debout, sans dépasser le maximum ; renvoie les PM rendus."""
        if not self.is_alive:
            return 0
        gained = min(amount, self.max_mp - self._mp)
        self._mp += gained
        return gained

    def revive(self) -> int:
        """Relève un personnage K.O. avec la moitié de ses PV ; renvoie les PV rendus."""
        if self.is_alive:
            return 0
        self._hp = self.max_hp // 2
        return self._hp
