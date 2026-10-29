"""Invariants du §8 liés au déroulement : vagues, butin, ordre des événements, Réessayer, K.O."""

import pygame
import pytest
from conftest import settle
from pygame import Vector2

from final_classe.characters import Party, Soldier
from final_classe.characters.jobs import BlackMage
from final_classe.game.zones import ZONES
from final_classe.gfx.engine.demo import make_demo_party
from final_classe.gfx.engine.registry import make_scene
from final_classe.gfx.scenes import flow
from final_classe.gfx.scenes._demo import key_event
from final_classe.storage import SaveError, load_game, save_game


# --- vagues : game.wave part de 0, les arguments de scène de 1 -------------------------------
def test_start_battle_envoie_vague_comptee_a_partir_de_1(game, stub_scenes):
    flow.start_battle(game, 1, 0)
    settle(game)
    assert game.wave == 0
    assert stub_scenes[-1] == ("battle", ["forest", "1"])
    flow.start_battle(game, 1, 2)
    settle(game)
    assert game.wave == 2
    assert stub_scenes[-1] == ("battle", ["forest", "3"])


def test_scene_battle_args_comptes_a_partir_de_1(game):
    game.party = make_demo_party()
    assert make_scene(game, "battle:plains:1").wave == 0
    last = make_scene(game, "battle:crater:3")
    assert last.wave == 2 and last.final  # Sephiroth
    assert make_scene(game, "battle:4:2").zone == 4


def test_after_battle_passe_a_la_vague_suivante_et_sauvegarde(game, stub_scenes):
    game.party = make_demo_party()
    game.zone, game.wave = 0, 0
    flow.after_battle(game)
    settle(game)
    assert game.wave == 1
    assert stub_scenes[-1] == ("battle", ["plains", "2"])
    assert load_game(game.slot)[1:] == (0, 1)  # comme le terminal : zone, vague suivante


def test_after_battle_derniere_vague_ouvre_la_carte_et_sauvegarde(game, stub_scenes):
    game.party = make_demo_party()
    game.zone, game.wave = 0, len(ZONES[0].waves()) - 1
    flow.after_battle(game)
    settle(game)
    assert (game.zone, game.wave) == (1, 0)
    assert stub_scenes[-1][0] == "world_map"
    assert load_game(game.slot)[1:] == (1, 0)


def test_after_battle_apres_le_cratere_va_a_la_fin_sans_sauvegarde(game, stub_scenes):
    game.party = make_demo_party()
    game.zone, game.wave = 4, len(ZONES[4].waves()) - 1
    flow.after_battle(game)
    settle(game)
    assert stub_scenes[-1][0] == "ending"
    with pytest.raises(SaveError):
        load_game(game.slot)


# --- butin : party.reward une seule fois par combat gagné -------------------------------------
def test_reward_une_seule_fois_de_la_victoire_a_la_vague_suivante(game, stub_scenes, monkeypatch):
    from final_classe.gfx.scenes.battle import BattleScene
    from final_classe.gfx.scenes.loot import LootScene
    from final_classe.gfx.scenes.victory import VictoryScene

    game.party = make_demo_party()
    calls: list[int] = []
    real = Party.reward

    def counting(self, monsters):
        calls.append(1)
        return real(self, monsters)

    monkeypatch.setattr(Party, "reward", counting)
    gil0 = game.party.gil
    battle = BattleScene(game, 0, 0)
    gils = sum(m.gil for m in battle.monsters)
    for m in battle.monsters:  # victoire : tous les monstres K.O.
        m.take_damage(10**6)
    game.push(battle, transition=None)
    battle._ko_pass()  # comme après une action : les K.O. sont constatés, le combat se termine
    for _ in range(1500):
        game.step(1 / 60, render=False)
        settle(game)
        if isinstance(game.scene, VictoryScene):
            break
    assert isinstance(game.scene, VictoryScene)
    game.scene._next()
    settle(game)
    assert isinstance(game.scene, LootScene)
    game.scene._finish()  # -> flow.after_battle
    settle(game)
    assert len(calls) == 1
    assert game.party.gil == gil0 + gils  # crédités une seule fois
    assert stub_scenes[-1] == ("battle", ["plains", "2"])


# --- ordre des événements : identique à game/zones.py ----------------------------------------
@pytest.mark.parametrize("index, expected", [
    (0, ["event", "battle"]),
    (1, ["event", "battle"]),
    (2, ["event", "prepare", "battle"]),                       # coffre -> préparation
    (3, ["event", "prepare", "event_after", "battle"]),        # Cid -> préparation -> Garland
    (4, ["event", "prepare", "event_after", "battle"]),        # Bahamut, Cid -> préparation -> Sephiroth
])
def test_ordre_des_evenements_comme_le_terminal(game, stub_scenes, index, expected):
    game.party = make_demo_party()
    game.wave = 0
    flow.start_zone(game, index)
    settle(game)
    names: list[str] = []
    for _ in range(10):
        name, args = stub_scenes[-1]
        names.append("event_after" if name == "event" and "after" in args else name)
        if name == "battle":
            assert args == [flow.ZONE_KEYS[index], "1"]
            break
        if name == "event":
            flow.event_done(game, index, after="after" in args)
        else:
            flow.prepare_done(game)
        settle(game)
    assert names == expected
    # le terminal : zone.before appelle prepare() pour la Grotte, le Sanctuaire et le Cratère
    assert [i for i in range(5) if ZONES[i].before is not None and i >= 2] == list(flow.PREPARE_ZONES)


def test_reprise_au_milieu_d_une_zone_saute_evenement_et_preparation(game, stub_scenes):
    game.party = make_demo_party()
    game.wave = 1
    flow.start_zone(game, 3)
    settle(game)
    assert stub_scenes == [("battle", ["chaos", "2"])]


# --- Nouvelle partie / Réessayer --------------------------------------------------------------
def _save(names, zone, wave, slot, gil=100):
    party = Party([Soldier(names[0], strength=15, magic=10, defense=10, resistance=10),
                   BlackMage(names[1], strength=10, magic=15, defense=10, resistance=10)])
    party.gil = gil
    save_game(party, zone, wave, slot)


def test_nouvelle_partie_repart_d_un_etat_neuf(game, stub_scenes):
    from final_classe.gfx.scenes.title import TitleScene

    game.party = make_demo_party()
    game.zone, game.wave, game.slot = 3, 2, 1
    title = TitleScene(game)
    title._open_slots("new")
    title.handle_event(key_event(pygame.K_DOWN))  # emplacement 2
    title.handle_event(key_event(pygame.K_RETURN))
    assert game.party is None
    assert (game.zone, game.wave, game.slot) == (0, 0, 2)


def test_creation_et_boutique_repartent_de_zero(game):
    first = flow.get_shop(game, "first")
    stock = len(first.stock)
    first.stock.clear()
    again = flow.get_shop(game, "first")
    assert again is not first and len(again.stock) == stock  # stock neuf à chaque visite


def test_reessayer_recharge_la_derniere_sauvegarde_du_slot_courant(game, stub_scenes):
    from final_classe.gfx.scenes.game_over import GameOverScene

    _save(("Autre", "Autre2"), 0, 0, 1)            # un autre emplacement : ne doit jamais être lu
    _save(("Vieux", "Vieux2"), 0, 0, 2)            # sauvegarde ancienne du slot 2
    _save(("Recent", "Recent2"), 1, 1, 2, 777)     # la DERNIÈRE du slot 2
    game.slot = 2
    game.party = make_demo_party()                 # l'état de la partie perdue
    lost = game.party
    scene = GameOverScene(game, 0, 0)
    scene.t = 2.0
    scene.handle_event(key_event(pygame.K_RETURN))  # « Réessayer »
    settle(game)
    assert game.slot == 2
    assert game.party is not lost
    assert [h.name for h in game.party.heroes] == ["Recent", "Recent2"]
    assert game.party.gil == 777
    assert (game.zone, game.wave) == (1, 1)
    assert stub_scenes[-1] == ("battle", ["forest", "2"])  # vague 2 (1-based)


def test_reessayer_sans_sauvegarde_ne_plante_pas(game, stub_scenes):
    from final_classe.gfx.scenes.game_over import GameOverScene

    game.party = make_demo_party()
    game.slot = 3
    scene = GameOverScene(game, 0, 0)
    scene.t = 2.0
    scene.handle_event(key_event(pygame.K_RETURN))
    settle(game)
    assert game.party is not None


# --- K.O. : suit model.is_alive, relevé puis retombé -----------------------------------------
def test_ko_suit_is_alive_y_compris_releve_puis_retombe(game):
    from final_classe.gfx.scenes.battle_actors import BattleActor

    hero = make_demo_party().heroes[0]
    actor = BattleActor(game, hero, "hero", Vector2(300, 500))
    assert actor.alive and not actor.ko
    hero.take_damage(10**6)
    assert not actor.alive
    actor.ko = True
    hero.revive()
    assert actor.alive
    actor.sync()  # impact du Phénix : l'affichage se relève
    assert not actor.ko
    hero.take_damage(10**6)
    assert not actor.alive  # retombé : de nouveau K.O.


def test_scene_combat_rejoue_le_ko_d_un_heros_releve_puis_retombe(game):
    from final_classe.gfx.scenes.battle import BattleScene

    game.party = make_demo_party()
    scene = BattleScene(game, 0, 0)
    actor = scene.heroes[0]

    def ko_cycle():
        scene._ko_pass()
        assert len(scene.ko_choreos) == 1  # l'animation K.O. est (re)jouée
        for c in scene.ko_choreos:
            c.skip()
        scene._finish_ko()

    actor.model.take_damage(10**6)
    ko_cycle()
    assert actor.ko and not actor.alive
    actor.model.revive()
    actor.sync()
    scene._ko_pass()
    assert not actor.ko and scene.ko_choreos == []
    actor.model.take_damage(10**6)
    ko_cycle()
    assert actor.ko and not actor.alive


def test_victoire_affiche_ko_selon_le_modele(game):
    from final_classe.gfx.scenes.victory import VictoryScene

    game.party = make_demo_party()
    game.party.heroes[1].take_damage(10**6)
    scene = VictoryScene(game, ZONES[0].waves()[0], 0, 0, 3)
    assert [a.ko for a in scene.heroes] == [False, True, False]
