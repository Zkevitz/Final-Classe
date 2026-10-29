"""Résolution des actions du combat : applique la logique au modèle, prépare le contexte de chorégraphie."""

import unicodedata
from dataclasses import dataclass, field

from final_classe.gfx.scenes.battle_actors import BattleActor, job_key
from final_classe.items import Target
from final_classe.items.materia import HealMateria, SummonMateria

ITEM_KEYS = {
    "Potion": "item.potion", "Éther": "item.ether",
    "Queue de phénix": "item.phoenix_down", "Élixir": "item.elixir",
}
MONSTER_KEYS = {
    "attaque": "attack.monster", "Supernova": "monster.supernova", "Explosion": "monster.explosion",
    "1000 épines": "monster.needles", "Mauvaise haleine": "monster.bad_breath",
    "Souffle de feu": "monster.fire_breath",
}
ELEMENT_SPELLS = {"feu": "fire", "glace": "ice", "foudre": "thunder"}


@dataclass
class Resolved:
    """Une action déjà appliquée au modèle, prête pour `play(key, ctx)`."""

    key: str
    caster: BattleActor
    targets: list[BattleActor]
    values: list[int]
    critical: list[bool]
    extra: dict[str, object] = field(default_factory=dict)
    label: str | None = None  # nom affiché en haut de l'écran
    vanish: bool = False  # l'acteur disparaît de lui-même (Bombo)


def _slug(text: str) -> str:
    plain = unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode()
    return plain.lower().replace(" ", "_")


def spell_key(materia: object) -> str:
    """La clé de chorégraphie d'une materia (`spell.fire`, `summon.ifrit`…)."""
    if isinstance(materia, SummonMateria):
        return "summon." + _slug(materia.name)
    if isinstance(materia, HealMateria):
        return "spell.cure"
    element = getattr(materia, "element", None)
    return "spell." + ELEMENT_SPELLS.get(getattr(element, "value", ""), "fire")


def candidates(kind: Target, heroes: list[BattleActor], monsters: list[BattleActor]) -> tuple[list[BattleActor], bool]:
    """Les cibles possibles d'un genre de cible, et si l'action vise tout le groupe."""
    if kind is Target.ENEMIES:
        return [m for m in monsters if m.alive and m.visible], True
    if kind is Target.ALLY:
        return [h for h in heroes if h.alive], False
    if kind is Target.KNOCKED_OUT:
        return [h for h in heroes if not h.alive], False
    return [m for m in monsters if m.alive and m.visible], False


def _deltas(targets: list[BattleActor], before: list[int]) -> list[int]:
    return [abs(t.model.hp - b) for t, b in zip(targets, before, strict=True)]


def resolve_attack(caster: BattleActor, target: BattleActor) -> Resolved:
    """Attaque de base."""
    damage = caster.model.attack(target.model)
    return Resolved(f"attack.{job_key(caster.model)}", caster, [target], [damage], [False])


def resolve_skill(caster: BattleActor, targets: list[BattleActor]) -> Resolved | None:
    """Compétence du job ; None si les PM manquent."""
    hero = caster.model
    if not hero.can_use_skill:
        return None
    gils = len(hero.loot)
    models = [t.model for t in targets]
    before = [m.hp for m in models]
    ret = hero.use_skill(*models)
    values = [ret] if len(targets) == 1 else _deltas(targets, before)
    extra: dict[str, object] = {"skill": hero.SKILL_NAME}
    if job_key(hero) == "thief":
        extra.update(gil=ret, stolen="Potion" if len(hero.loot) > gils else None)
    caster.sync(hp=False)
    return Resolved(f"skill.{job_key(hero)}", caster, targets, values, [False] * len(targets), extra,
                    label=hero.SKILL_NAME)


def resolve_spell(caster: BattleActor, materia, targets: list[BattleActor]) -> Resolved | None:
    """Sort d'une materia ; None si impossible."""
    hero = caster.model
    if not hero.can_cast(materia):
        return None
    models = [t.model for t in targets]
    before = [m.hp for m in models]
    element = getattr(materia, "element", None)
    crit = [bool(element is not None and m.damage_multiplier(element) > 1) for m in models]
    ret = hero.cast(materia, *models)
    values = [ret] if len(targets) == 1 else _deltas(targets, before)
    caster.sync(hp=False)
    return Resolved(spell_key(materia), caster, targets, values, crit, {"spell": materia.name},
                    label=materia.name)


def resolve_item(caster: BattleActor, party, name: str, target: BattleActor) -> Resolved | None:
    """Utilise un objet du sac ; None si absent ou inutile."""
    item = party.items.take(name)
    if item is None:
        return None
    value = item.use(target.model)
    return Resolved(ITEM_KEYS.get(name, "item.potion"), caster, [target], [value], [False],
                    {"item": name}, label=name)


def resolve_defend(caster: BattleActor) -> Resolved:
    """Se défendre."""
    caster.model.defend()
    return Resolved("action.defend", caster, [caster], [0], [False], label="Garde")


def resolve_monster(caster: BattleActor, heroes: list[BattleActor]) -> list[Resolved]:
    """Le tour d'un monstre : `monster.act`, puis une action par sorte de coup."""
    by_model = {h.model: h for h in heroes}
    hits = caster.model.act([h.model for h in heroes])
    if not hits:
        return []
    out: list[Resolved] = []
    groups: dict[str, list] = {}
    for hit in hits:
        groups.setdefault(hit.action, []).append(hit)
    for action, group in groups.items():
        targets = [by_model[h.target] for h in group]
        label = None if action == "attaque" else action
        out.append(Resolved(
            MONSTER_KEYS.get(action, "attack.monster"), caster, targets, [h.damage for h in group],
            [False] * len(group), {"action": action}, label=label, vanish=action == "Explosion",
        ))
    return out
