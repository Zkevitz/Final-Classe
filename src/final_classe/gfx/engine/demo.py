"""Partie de démonstration pour `--scene` : 3 héros de jobs différents et un inventaire de départ."""

from final_classe.characters import Party, Soldier, Thief
from final_classe.characters.jobs import BlackMage
from final_classe.items import Elixir, Ether, catalog


def make_demo_party() -> Party:
    """Soldat, Mage noir et Voleur équipés, avec materias, objets et quelques gils."""
    soldier = Soldier("Aldric", strength=18, magic=14, defense=15, resistance=13)
    mage = BlackMage("Mira", strength=12, magic=20, defense=13, resistance=15)
    thief = Thief("Kael", strength=16, magic=12, defense=14, resistance=18)
    soldier.equip(catalog.bronze_sword())
    soldier.equip(catalog.leather_armor())
    staff = catalog.rod()
    staff.attach(catalog.fire())
    mage.equip(staff)
    mage.equip(catalog.leather_armor())
    thief.equip(catalog.bronze_sword())
    party = Party([soldier, mage, thief])
    party.gil = 1250
    party.items.add(Ether(), Ether(), Elixir())
    party.bag.append(catalog.chain_mail())
    party.materias.extend([catalog.cure(), catalog.ice()])
    return party
