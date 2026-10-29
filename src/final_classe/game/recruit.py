"""Le recrutement : les héros de FF rejoignent l'équipe."""

from final_classe.characters import (
    Archer,
    BlackMage,
    Hero,
    Knight,
    Monk,
    Ninja,
    Samurai,
    Soldier,
    Thief,
)
from final_classe.game.creation import ask_int
from final_classe.game.display import console

TEAM_SIZE = 3  # le héros du joueur, et deux compagnons


def recruits() -> list[Hero]:
    """Les héros disponibles : des objets de classes différentes, dans une même liste."""
    return [
        Soldier("Cloud", strength=22, magic=12, defense=16, resistance=10),
        BlackMage("Lulu", strength=10, magic=22, defense=12, resistance=16),
        Knight("Basch", strength=17, magic=10, defense=20, resistance=13),
        Monk("Amarant", strength=18, magic=16, defense=14, resistance=12),
        Thief("Djidane", strength=19, magic=12, defense=13, resistance=16),
        Samurai("Auron", strength=21, magic=10, defense=17, resistance=12),
        Archer("Fran", strength=18, magic=14, defense=12, resistance=16),
        Ninja("Youfie", strength=19, magic=12, defense=12, resistance=17),
    ]


def recruit(hero: Hero) -> list[Hero]:
    """Le joueur choisit ses compagnons ; renvoie l'équipe, son héros en premier."""
    team = [hero]
    available = recruits()
    while len(team) < TEAM_SIZE:
        console.print(f"\nRecrutez un compagnon ({len(team)}/{TEAM_SIZE}) :")
        for number, candidate in enumerate(available, start=1):
            console.print(
                f"  {number}. {candidate.name:<8} {candidate.title:<10} "
                f"PV {candidate.max_hp}  VIT {candidate.speed}  compétence : {candidate.SKILL_NAME}"
            )
        chosen = available.pop(ask_int("Votre choix : ", 1, len(available)) - 1)
        console.print(f"[green]{chosen.name} rejoint l'équipe ![/]")
        team.append(chosen)
    return team
