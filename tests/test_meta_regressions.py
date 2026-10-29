"""Tests méta : on réintroduit chaque bug par monkeypatch, le test d'invariant correspondant DOIT échouer."""

import pytest
import test_assets_cli as assets_tests
import test_flow_invariants as flow_tests

from final_classe.gfx.engine.game import Game
from final_classe.gfx.engine.registry import SCENES
from final_classe.gfx.scenes import _demo, flow
from final_classe.gfx.scenes.battle_actors import BattleActor


def test_meta_butin_deux_fois(game, stub_scenes, monkeypatch):
    original = flow.after_battle

    def double(g):
        g.party.reward([])  # le bug : after_battle refait le butin
        original(g)

    monkeypatch.setattr(flow, "after_battle", double)
    import final_classe.gfx.scenes.loot as loot

    monkeypatch.setattr(loot, "go_next", lambda g: double(g))
    with pytest.raises(AssertionError):
        flow_tests.test_reward_une_seule_fois_de_la_victoire_a_la_vague_suivante(game, stub_scenes, monkeypatch)


def test_meta_reessayer_charge_un_autre_slot(game, stub_scenes, monkeypatch):
    real = Game.load
    monkeypatch.setattr(Game, "load", lambda self, slot: real(self, 1))
    with pytest.raises(AssertionError):
        flow_tests.test_reessayer_recharge_la_derniere_sauvegarde_du_slot_courant(game, stub_scenes)


def test_meta_reessayer_garde_l_ancien_etat(game, stub_scenes, monkeypatch):
    monkeypatch.setattr(Game, "load", lambda self, slot: False)  # la sauvegarde n'est pas rechargée
    with pytest.raises(AssertionError):
        flow_tests.test_reessayer_recharge_la_derniere_sauvegarde_du_slot_courant(game, stub_scenes)


def test_meta_ko_non_releve(game, monkeypatch):
    monkeypatch.setattr(BattleActor, "sync", lambda self, hp=True, mp=True: None)
    with pytest.raises(AssertionError):
        flow_tests.test_ko_suit_is_alive_y_compris_releve_puis_retombe(game)
    with pytest.raises(AssertionError):
        flow_tests.test_scene_combat_rejoue_le_ko_d_un_heros_releve_puis_retombe(game)


def test_meta_ko_ne_suit_pas_is_alive(game, monkeypatch):
    monkeypatch.setattr(BattleActor, "alive", property(lambda self: self.model.hp > 10**9))
    with pytest.raises(AssertionError):
        flow_tests.test_ko_suit_is_alive_y_compris_releve_puis_retombe(game)


def test_meta_hero_image_par_nom_seulement(monkeypatch):
    def by_name(hero):
        named = _demo.NAMED_IMAGE.get(hero.name)
        return named[1] if named else _demo.hero_image(hero)

    monkeypatch.setattr(assets_tests, "hero_image", by_name)
    with pytest.raises(AssertionError):
        assets_tests.test_hero_image_depend_du_nom_et_du_job()


def test_meta_hero_image_par_job_seulement(monkeypatch):
    monkeypatch.setattr(assets_tests, "hero_image", lambda h: _demo.HERO_IMAGE[type(h).__name__])
    with pytest.raises(AssertionError):
        assets_tests.test_hero_image_depend_du_nom_et_du_job()


def test_meta_vagues_comptees_a_partir_de_0(game, stub_scenes, monkeypatch):
    def buggy(g, index, wave):
        g.zone, g.wave = index, wave
        g.replace(SCENES["battle"](g, [flow.ZONE_KEYS[index], str(wave)]), transition="fade")

    monkeypatch.setattr(flow, "start_battle", buggy)
    with pytest.raises(AssertionError):
        flow_tests.test_start_battle_envoie_vague_comptee_a_partir_de_1(game, stub_scenes)


def test_meta_nouvelle_partie_garde_l_ancienne_equipe(game, stub_scenes, monkeypatch):
    from final_classe.gfx.scenes import title

    real = title.TitleScene.handle_event

    def keep(self, event):
        keep_party = self.game.party
        real(self, event)
        self.game.party = keep_party

    monkeypatch.setattr(title.TitleScene, "handle_event", keep)
    with pytest.raises(AssertionError):
        flow_tests.test_nouvelle_partie_repart_d_un_etat_neuf(game, stub_scenes)


def test_meta_recrue_absente_du_manifeste(monkeypatch):
    monkeypatch.setattr(assets_tests, "_manifest_ids", lambda: {"hero_soldier"})
    with pytest.raises(AssertionError):
        assets_tests.test_chaque_recrue_nommee_a_son_id_dans_le_manifeste()


