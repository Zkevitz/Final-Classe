"""Fin d'une chorégraphie, jouée ou passée (§8) ; repli de la scène de combat ; pose K.O. dessinée."""

import types

import pygame
import pytest
from pygame import Vector2

from final_classe.gfx.fx import FloatingText, FxManager
from final_classe.gfx.fx.choreo import ActionContext, play
from final_classe.gfx.scenes import battle as battle_mod
from final_classe.gfx.scenes.battle_actors import BattleActor
from final_classe.gfx.engine.demo import make_demo_party


class Actor:
    def __init__(self, x, y=450):
        self.home = Vector2(x, y)
        self.offset = Vector2()
        self.scale, self.rotation, self.alpha, self.visible = 1.0, 0.0, 255, True
        self.tint = None
        self.rect = pygame.Rect(x - 50, y - 150, 100, 150)
        self.poses: list[str] = []

    def flash(self, color=(255, 255, 255), seconds=0.12):
        pass

    def set_pose(self, pose, hold=None):
        self.poses.append(pose)


class Audio:
    def __init__(self):
        self.ducks: list[tuple] = []

    def play_sfx(self, *a, **k):
        pass

    def duck(self, *a, **k):
        self.ducks.append(a)


@pytest.fixture(autouse=True)
def tracked_effects(monkeypatch):
    """Note les effets créés par `Stage` (ceux que la chorégraphie doit tuer à sa fin)."""
    from final_classe.gfx.fx.summon_fx import Stage

    seen: list = []
    real = Stage.spawn

    def spy(self, effect, layer=None):
        seen.append(effect)
        return real(self, effect, layer)

    monkeypatch.setattr(Stage, "spawn", spy)
    return seen


def _run(game, key, n_targets, skip_at=None, extra=None):
    caster = Actor(950)
    targets = [Actor(300 + 60 * i, 420 + 50 * i) for i in range(n_targets)]
    impacts: list[int] = []
    fx, audio = FxManager(), Audio()
    values = [100 * (i + 1) for i in range(n_targets)]
    ctx = ActionContext(caster, targets, values, [False] * n_targets, impacts.append, fx, audio, game.assets,
                        dict(extra or {}))
    choreo = play(key, ctx)
    t = 0.0
    while choreo.update(1 / 60) and t < 20:
        t += 1 / 60
        fx.update(1 / 60)
        if skip_at is not None and t >= skip_at:
            choreo.skip()
            break
    fx.update(0.0)
    return caster, targets, impacts, fx, audio


def _check_end(caster, impacts, fx, audio, n, texts=True, tracked=()):
    assert sorted(impacts) == list(range(n)), impacts  # exactement un on_impact par cible
    assert (1.0, 0) in audio.ducks or (1.0, 0.0) in audio.ducks, audio.ducks
    assert caster.poses == [] or caster.poses[-1] == "idle", caster.poses
    alive = [e for e in tracked if not e.dead]  # les effets suivis par Stage sont tués (un skip tardif n'en laisse pas)
    assert alive == [], alive
    if texts:
        assert len([e for e in fx.effects if isinstance(e, FloatingText)]) >= n


@pytest.mark.parametrize("skip_at", [None, 0.5])
def test_defend_lanceur_revient_a_idle(game, skip_at):
    caster, _t, impacts, fx, audio = _run(game, "action.defend", 1, skip_at)
    assert caster.poses and caster.poses[-1] == "idle", caster.poses


@pytest.mark.parametrize("skip_at", [None, 1.0])
def test_supernova_jouee_ou_passee(game, skip_at):
    caster, _t, impacts, fx, audio = _run(game, "monster.supernova", 3, skip_at)
    assert (1.0, 0) in audio.ducks or (1.0, 0.0) in audio.ducks, audio.ducks
    assert sorted(impacts) == [0, 1, 2]
    assert caster.poses == [] or caster.poses[-1] == "idle"


@pytest.mark.parametrize("key", ["summon.ifrit", "summon.shiva", "summon.ramuh", "summon.bahamut"])
def test_invocation_passee_a_mi_parcours(game, key, tracked_effects):
    caster, _t, impacts, fx, audio = _run(game, key, 3, skip_at=1.0)
    _check_end(caster, impacts, fx, audio, 3, tracked=tracked_effects)
    assert not fx.hide_ui if hasattr(fx, "hide_ui") else True


def test_meta_skip_oublie_les_impacts(game, monkeypatch, tracked_effects):
    from final_classe.gfx.fx.choreo import Choreography

    monkeypatch.setattr(Choreography, "skip", lambda self: setattr(self, "done", True))
    with pytest.raises(AssertionError):
        test_invocation_passee_a_mi_parcours(game, "summon.ifrit", tracked_effects)


# --- repli de la scène de combat -------------------------------------------------------------
def test_fallback_choreo_skip_emet_les_impacts_restants():
    got: list[int] = []
    ctx = types.SimpleNamespace(targets=[Actor(1), Actor(2), Actor(3)], on_impact=got.append)
    c = battle_mod._FallbackChoreo(ctx)
    c.update(0.1)
    c.skip()
    assert got == [0, 1, 2] and c.done
    c.skip()
    assert got == [0, 1, 2]  # jamais deux fois
    got2: list[int] = []
    c2 = battle_mod._FallbackChoreo(types.SimpleNamespace(targets=[Actor(1), Actor(2)], on_impact=got2.append))
    c2.update(0.5)  # l'impact naturel a eu lieu
    c2.skip()
    assert got2 == [0, 1]


def test_meta_fallback_skip_sans_impact(monkeypatch):
    monkeypatch.setattr(battle_mod._FallbackChoreo, "skip", lambda self: setattr(self, "done", True))
    with pytest.raises(AssertionError):
        test_fallback_choreo_skip_emet_les_impacts_restants()


# --- _sheet_ko : pose dessinée seulement si la planche a `ko` ---------------------------------
def _ko_actor(game):
    actor = BattleActor(game, make_demo_party().heroes[0], "hero", Vector2(300, 500))
    assert actor.has_sheet
    actor.ko = True
    actor.set_pose("idle")
    return actor


def test_sheet_ko_selon_la_planche(game, monkeypatch):
    actor = _ko_actor(game)
    assert actor.pose == "ko" and actor._sheet_ko is True
    real = game.assets._sheet(actor.sprite)
    monkeypatch.setattr(game.assets, "_sheet", lambda _id: {k: v for k, v in real.items() if k != "ko"})
    assert actor._sheet_ko is False  # sans pose ko : gadgets du code (rotation, grisé…)


def test_meta_sheet_ko_sans_verification(game, monkeypatch):
    monkeypatch.setattr(BattleActor, "_sheet_ko",
                        property(lambda self: self.has_sheet and self.side == "hero" and self.pose == "ko"))
    with pytest.raises(AssertionError):
        test_sheet_ko_selon_la_planche(game, monkeypatch)




@pytest.mark.parametrize("kind", ["heal", "mp", "damage"])
def test_valeur_passee_s_affiche_avec_son_type(game, kind):
    """`ctx.extra["kind"]` (posé par la scène) : un soin passé s'affiche en soin, pas en dégâts."""
    _c, _t, impacts, fx, _a = _run(game, "item.potion", 1, skip_at=0.1, extra={"kind": kind})
    texts = [e for e in fx.effects if isinstance(e, FloatingText)]
    assert sorted(impacts) == [0] and len(texts) == 1
    assert texts[0].kind == kind


def test_meta_kind_ignore(game, monkeypatch):
    from final_classe.gfx.fx.choreo import Choreography

    real = Choreography.damage_text_now
    monkeypatch.setattr(Choreography, "damage_text_now", lambda self, i, text=None, kind="damage", **kw: real(self, i, text, "damage", **kw))
    with pytest.raises(AssertionError):
        test_valeur_passee_s_affiche_avec_son_type(game, "heal")


# --- skip APRÈS l'impact mais AVANT le chiffre -------------------------------------------------
def _texts(fx):
    return [e for e in fx.effects if isinstance(e, FloatingText)]


@pytest.mark.parametrize("kind, prefix, suffix", [("damage", "", ""), ("heal", "+", ""), ("mp", "+", " PM")])
def test_skip_apres_impact_avant_chiffre_affiche_un_chiffre_par_cible(game, monkeypatch, kind, prefix, suffix):
    from final_classe.gfx.fx.choreo import REGISTRY, scripted

    @scripted("test.impact_sans_chiffre")
    def late(c):
        from final_classe.gfx.fx.choreo import Call, Seq

        return Seq(Call(c.impact_now, 0), Call(c.impact_now, 1), 5.0, c.damage_text(0), c.damage_text(1))

    try:
        _c, _t, impacts, fx, _a = _run(game, "test.impact_sans_chiffre", 2, skip_at=1.0, extra={"kind": kind})
    finally:
        REGISTRY.pop("test.impact_sans_chiffre", None)
    assert sorted(impacts) == [0, 1]
    assert sorted(t.text for t in _texts(fx)) == [f"{prefix}100{suffix}", f"{prefix}200{suffix}"]


@pytest.mark.parametrize("key, n", [("summon.bahamut", 3), ("monster.supernova", 3)])
@pytest.mark.parametrize("skip_at", [0.5, 1.5, 2.5, 4.0])
def test_skip_a_toute_etape_un_seul_chiffre_par_cible(game, key, n, skip_at):
    _c, _t, impacts, fx, _a = _run(game, key, n, skip_at=skip_at)
    assert sorted(impacts) == list(range(n))
    shown = sorted(t.text.lstrip("+").removesuffix(" PM") for t in _texts(fx))
    assert shown == sorted(str(100 * (i + 1)) for i in range(n)), shown


def test_meta_skip_tardif_sans_chiffre(game, monkeypatch):
    from final_classe.gfx.fx.choreo import Choreography

    def old_finish(self, natural=False):  # le bug : le chiffre n'est ajouté que si l'impact manquait aussi
        self.done = True
        for i in range(len(self.targets)):
            if i not in self._impacted:
                self.impact_now(i)
                if not natural and self.value(i) != 0 and i not in self._texted:
                    self.damage_text_now(i)

    monkeypatch.setattr(Choreography, "_finish", old_finish)
    with pytest.raises(AssertionError):
        test_skip_apres_impact_avant_chiffre_affiche_un_chiffre_par_cible(game, monkeypatch, "damage", "", "")


# --- un héros K.O. reste dessiné ---------------------------------------------------------------
@pytest.mark.parametrize("index", [0, 1, 2])
def test_heros_ko_reste_dessine(game, index):
    from final_classe.gfx.scenes.battle import BattleScene

    game.party = make_demo_party()
    scene = BattleScene(game, 0, 0)
    actor = scene.heroes[index]  # 0 Soldat, 1 Mage noir (hero_black_mage, avec planche), 2 Voleur
    actor.model.take_damage(10**6)
    game.push(scene, transition=None)
    scene.phase = "idle"  # intro passée
    scene._ko_pass()
    for _ in range(300):  # ~5 s de vraie boucle (le FxManager du jeu fait avancer les chorégraphies)
        game.step(1 / 60)
    assert actor.ko and not actor.alive
    assert actor.visible and actor.alpha > 0
    layer = pygame.Surface(game.size, pygame.SRCALPHA)
    actor.draw(layer)
    rect = actor.rect.clip(layer.get_rect())
    opaque = pygame.mask.from_surface(layer.subsurface(rect), threshold=200).count()
    assert opaque > 200, (actor.sprite, opaque)


def test_meta_heros_ko_invisible(game, monkeypatch):
    monkeypatch.setattr(BattleActor, "draw", lambda self, surface: None)
    with pytest.raises(AssertionError):
        test_heros_ko_reste_dessine(game, 1)
