"""La boutique de Cid : acheter, vendre, et les objets."""

from final_classe.characters import Party
from final_classe.game.creation import ask_int
from final_classe.game.display import console
from final_classe.items import Shop


def buy(shop: Shop, party: Party) -> None:
    """L'étal, trié par prix ; la pièce achetée rejoint le sac."""
    shelf = shop.shelf
    if not shelf:
        console.print("[red]L'étal est vide.[/]")
        return
    for number, item in enumerate(shelf, start=1):
        console.print(f"  {number}. {item}  [yellow]{item.price} gils[/]")
    console.print("  0. Retour")
    choice = ask_int("Acheter : ", 0, len(shelf))
    if choice == 0:
        return
    item = shelf[choice - 1]
    if not party.buy(item):
        console.print("[red]Pas assez de gils ![/]")
        return
    shop.stock.remove(item)  # remove compare avec __eq__ : une pièce égale disparaît de l'étal
    console.print(f"[green]{item.name} rejoint le sac.[/]")


def sell(shop: Shop, party: Party) -> None:
    """Une pièce du sac, revendue à moitié prix ; Cid la remet sur l'étal."""
    if not party.bag:
        console.print("[red]Le sac est vide.[/]")
        return
    for number, item in enumerate(party.bag, start=1):
        console.print(f"  {number}. {item}  [yellow]{item.price // 2} gils[/]")
    console.print("  0. Retour")
    choice = ask_int("Vendre : ", 0, len(party.bag))
    if choice == 0:
        return
    item = party.bag[choice - 1]
    gain = party.sell(item)
    shop.stock.append(item)
    console.print(f"[green]{item.name} vendu : +{gain} gils.[/]")


def buy_goods(shop: Shop, party: Party) -> None:
    """Des objets ; chaque achat crée un objet neuf, à partir de sa classe."""
    for number, kind in enumerate(shop.goods, start=1):
        console.print(f"  {number}. {kind.name}  [yellow]{kind.PRICE} gils[/]")
    console.print("  0. Retour")
    choice = ask_int("Acheter : ", 0, len(shop.goods))
    if choice == 0:
        return
    kind = shop.goods[choice - 1]
    if party.gil < kind.PRICE:
        console.print("[red]Pas assez de gils ![/]")
        return
    party.gil -= kind.PRICE
    party.items.add(kind())
    console.print(f"[green]{kind.name} rejoint le sac ({len(party.items)} objets).[/]")


def visit(shop: Shop, party: Party) -> None:
    """La boutique, jusqu'au départ."""
    console.print(f"\n[bold]{shop.merchant}[/] : « Approchez ! Du solide, et pas cher. »")
    while True:
        console.print(
            f"\nBourse : [yellow]{party.gil} gils[/]   1. Acheter  2. Vendre  3. Objets  0. Partir"
        )
        choice = ask_int("> ", 0, 3)
        if choice == 0:
            return
        if choice == 1:
            buy(shop, party)
        elif choice == 2:
            sell(shop, party)
        else:
            buy_goods(shop, party)
