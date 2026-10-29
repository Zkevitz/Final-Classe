"""Poses (§3, §8 « Poses : qui les pose ») et garde-fou « BLOQUÉ » (§5)."""

import json

import pygame
import pytest
from conftest import ROOT
from pygame import Vector2

from final_classe.gfx.engine.demo import make_demo_party
from final_classe.gfx.scenes.battle import BattleScene
from final_classe.gfx.scenes.battle_actions import Resolved
from final_classe.gfx.scenes.battle_actors import BattleActor

SHEET = ROOT / "assets" / "img" / "hero_soldier"


# --- assets.frame / frame_anchor -------------------------------------------------------------
def test_frame_et_ancre_avec_planche(game):
    data = json.loads((SHEET / "frames.json").read_text(encoding="utf-8"))["frames"]
    for pose in ("idle", "strike", "ko"):
        img = game.assets.frame("hero_soldier", pose)
        assert img.get_size() == tuple(data[pose]["size"])
        assert game.assets.frame_anchor("hero_soldier", pose) == Vector2(data[pose]["anchor"])
    assert game.assets.has_sheet("hero_soldier")


def test_pose_inconnue_replie_sur_idle(game):
    assert game.assets.frame("hero_soldier", "pose_inconnue") is game.assets.frame("hero_soldier", "idle")


def test_repli_sans_planche_sprite_simple_et_feet_rect(game):
    a = game.assets
    assert not a.has_sheet("hero_sans_planche")
    assert a.frame("hero_sans_planche", "strike") is a.image("hero_sans_planche")
    box = a.feet_rect("hero_sans_planche")
    assert a.frame_anchor("hero_sans_planche", "strike") == Vector2(box.centerx, box.bottom)


# --- BattleActor.set_pose --------------------------------------------------------------------
def _soldier_actor(game):
    hero = make_demo_party().heroes[0]  # Soldat : planche disponible
    actor = BattleActor(game, hero, "hero", Vector2(300, 500))
    assert actor.has_sheet
    return actor


def test_base_ko_si_ko(game):
    actor = _soldier_actor(game)
    actor.model.take_damage(10**6)
    actor.ko = True
    actor.set_pose("idle")
    assert actor.pose == "ko" and actor.base_pose() == "ko"
    actor.update(0.2)
    assert actor.pose == "ko"


def test_retour_a_la_pose_de_base_apres_hold(game):
    actor = _soldier_actor(game)
    actor.set_pose("hurt", hold=0.3)
    for _ in range(12):  # 0,2 s
        actor.update(1 / 60)
    assert actor.pose == "hurt"
    for _ in range(12):  # 0,4 s au total
        actor.update(1 / 60)
    assert actor.pose == "idle"


def test_changement_de_pose_en_plein_fondu_sans_saut_d_opacite(game):
    from final_classe.gfx.scenes import battle_actors

    actor = _soldier_actor(game)
    seq = {0: "windup", 2: "strike", 3: "hurt", 4: "cast", 5: "ready", 6: "windup", 7: "strike", 8: "hurt",
           9: "cast", 10: "ready", 11: "idle"}
    for step in range(60):
        changed = step in seq
        if changed:
            actor.set_pose(seq[step])
        before = [(p, a) for p, a in actor._layers]
        actor.update(0.01)
        assert len(actor._layers) <= 6
        assert all(0.0 <= a <= 1.0 for _p, a in actor._layers)
        if not changed:  # hors changement de pose, aucune opacité ne régresse
            for (p0, a0), (p1, a1) in zip(before, actor._layers[-len(before):], strict=False):
                if p0 == p1:
                    assert a1 >= a0 - 1e-9, (step, before, actor._layers)
    # la couche du dessus finit pleine, et seule
    assert actor._layers[-1][1] == 1.0 and len(actor._layers) == 1
    assert actor.pose == actor._layers[-1][0]
    assert battle_actors.POSE_FADE <= 0.2  # le fondu reste bref (~70 ms)


def test_meta_fondu_qui_n_aboutit_jamais(game, monkeypatch):
    from final_classe.gfx.scenes import battle_actors

    monkeypatch.setattr(battle_actors, "POSE_FADE", 1e9)
    with pytest.raises(AssertionError):
        test_changement_de_pose_en_plein_fondu_sans_saut_d_opacite(game)


# --- hurt posé par on_impact de la scène -----------------------------------------------------
def test_hurt_pose_sur_la_cible_touchee_par_on_impact(game):
    game.party = make_demo_party()
    scene = BattleScene(game, 0, 0)
    foe, victim = scene.foes[0], scene.heroes[0]
    calls: list[tuple] = []
    real = victim.set_pose

    def spy(pose, hold=None, instant=False):
        calls.append((pose, hold))
        return real(pose, hold, instant)

    victim.set_pose = spy
    victim.model.take_damage(5)
    scene._start(Resolved("attack.monster", foe, [victim], [5], [False]))
    for _ in range(900):
        scene.update(1 / 60)
        if calls:
            break
    assert ("hurt", 0.3) in calls
