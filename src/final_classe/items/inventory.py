"""Inventory : le sac d'objets de l'équipe."""

from collections.abc import Iterator
from typing import Self

from final_classe.items.consumables import ITEMS, Usable


class Inventory:
    """Des objets, rangés ensemble. Il répond à len(), à for, et à in."""

    def __init__(self, *items: Usable) -> None:
        self._items: list[Usable] = list(items)

    def add(self, *items: Usable) -> None:
        """Range un ou plusieurs objets."""
        self._items.extend(items)

    def take(self, name: str) -> Usable | None:
        """Sort du sac le premier objet de ce nom ; None s'il n'y en a pas."""
        for item in self._items:
            if item.name == name:
                self._items.remove(item)
                return item
        return None

    def counts(self) -> dict[str, int]:
        """Combien d'exemplaires de chaque objet : {"Potion": 3, …}."""
        counts: dict[str, int] = {}
        for item in self._items:
            counts[item.name] = counts.get(item.name, 0) + 1
        return counts

    def to_dict(self) -> dict[str, int]:
        """Le sac en dictionnaire : le nombre d'exemplaires de chaque objet."""
        return self.counts()

    @classmethod
    def from_dict(cls, data: dict[str, int]) -> Self:
        """Recrée chaque objet à partir de son nom, autant de fois qu'il le faut."""
        return cls(*(ITEMS[name]() for name, count in data.items() for _ in range(count)))

    def __len__(self) -> int:
        """len(sac) : le nombre d'objets. Un sac vide est aussi « faux » dans un if."""
        return len(self._items)

    def __iter__(self) -> Iterator[Usable]:
        """Une boucle for sur le sac : il délègue à sa liste."""
        return iter(self._items)

    def __contains__(self, name: str) -> bool:
        """L'opérateur in : vrai s'il reste au moins un objet de ce nom."""
        return any(item.name == name for item in self._items)
