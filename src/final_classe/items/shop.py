"""Shop : une boutique, et son étal."""

from final_classe.items.consumables import Usable
from final_classe.items.equipment import Equipment


class Shop:
    """Une boutique : un marchand, les pièces qu'il vend, et ses objets."""

    def __init__(
        self, merchant: str, stock: list[Equipment], goods: list[type[Usable]] | None = None
    ) -> None:
        self.merchant = merchant
        self.stock = stock  # chaque pièce n'est vendue qu'une fois
        self.goods = goods or []  # des classes d'objets, sans limite de stock

    @property
    def shelf(self) -> list[Equipment]:
        """L'étal, de la pièce la moins chère à la plus chère : sorted() utilise __lt__."""
        return sorted(self.stock)
