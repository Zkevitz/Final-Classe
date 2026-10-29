"""Ondes de choc (additives) et formation des héros (§8)."""

import numpy as np
import pygame
import pytest
from pygame import Vector2

from final_classe.characters import Samurai
from final_classe.gfx.engine.demo import make_demo_party
from final_classe.gfx.fx import Shockwave
from final_classe.gfx.scenes import battle_actors
from final_classe.gfx.scenes.victory import VictoryScene
from final_classe.game.zones import ZONES


# --- ondes de choc : jamais de pixel assombri sur fond clair ----------------------------------
@pytest.mark.parametrize("color", [(255, 255, 255), (60, 60, 200), (200, 40, 20), (90, 90, 90)])
def test_shockwave_n_assombrit_aucun_pixel(color):
    for t in (0.05, 0.15, 0.3):
        wave = Shockwave((200, 150), color, 10, 120, 0.4, 10, squash=0.6)
        wave.update(t)
        white = pygame.Surface((400, 300))
        white.fill((255, 255, 255))
        wave.render(white)
        assert pygame.surfarray.array3d(white).min() == 255, (color, t)
        # ... mais elle dessine bien quelque chose (sinon un rendu vide passerait)
        black = pygame.Surface((400, 300))
        wave.render(black)
        assert pygame.surfarray.array3d(black).max() > 0, (color, t)


def test_meta_shockwave_vide(monkeypatch):
    monkeypatch.setattr(Shockwave, "render", lambda self, surface: None)
    with pytest.raises(AssertionError):
        test_shockwave_n_assombrit_aucun_pixel((255, 255, 255))


def test_hero_positions_zero_heros():
    assert battle_actors.hero_positions(0) == []
    assert battle_actors.hero_positions(0, []) == []
    assert len(battle_actors.hero_positions(1)) == 1


def test_meta_hero_positions_zero(monkeypatch):
    monkeypatch.setattr(battle_actors, "hero_positions", lambda n, widths=None: [Vector2()] * max(n, 1))
    with pytest.raises(AssertionError):
        test_hero_positions_zero_heros()


# --- formation -------------------------------------------------------------------------------
TEAMS = {
    "soldat_mage_voleur": ["Soldier", "BlackMage", "Thief"],
    "soldat_mage_voleur_moine": ["Soldier", "BlackMage", "Thief", "Monk"],
    "chevalier_lulu_samourai_archer": ["Knight", "Lulu", "Samurai", "Archer"],
}


def _team(names):
    from final_classe.characters import Archer, Knight, Monk, Soldier, Thief
    from final_classe.characters.jobs import BlackMage

    jobs = {"Soldier": (Soldier, "Aldric"), "BlackMage": (BlackMage, "Mira"), "Thief": (Thief, "Kael"),
            "Monk": (Monk, "Yan"), "Knight": (Knight, "Basch"), "Lulu": (BlackMage, "Lulu"),
            "Samurai": (Samurai, "Auron"), "Archer": (Archer, "Fran")}
    return [jobs[n][0](jobs[n][1], 15, 15, 15, 15) for n in names]


def _boxes(game, heroes, formation):
    """Boîtes absolues par pose (idle puis ko), de chaque héros, et les positions des pieds."""
    from final_classe.gfx.scenes._demo import hero_image

    sprites = [hero_image(h) for h in heroes]
    poses = [[game.assets.frame_box(s, "idle"), game.assets.frame_box(s, "ko")] for s in sprites]
    pos = formation(poses)
    return poses, pos


@pytest.mark.parametrize("team", list(TEAMS))
def test_formation_aucun_heros_cache_a_plus_d_un_tiers(game, team):
    heroes = _team(TEAMS[team])
    poses, pos = _boxes(game, heroes, battle_actors.hero_formation)
    assert len(pos) == len(heroes)
    order = sorted(range(len(heroes)), key=lambda i: pos[i].y)  # du fond vers l'avant
    assert len({p.y for p in pos}) == len(heroes)
    for k in (0, 1):  # idle, ko
        boxes = [poses[i][k].move(round(pos[i].x), round(pos[i].y)) for i in order]
        for i, rate in zip(order, battle_actors.occlusion_rates(boxes), strict=True):
            assert rate <= 1 / 3 + 0.01, (team, i, k, rate)
    # bornes d'écran (§8 Formation)
    for i in range(len(heroes)):
        for box in poses[i]:
            r = box.move(round(pos[i].x), round(pos[i].y))
            assert r.left >= battle_actors.FORMATION_LEFT and r.right <= battle_actors.FORMATION_RIGHT, (team, i, r)
        assert pos[i].y <= battle_actors.FORMATION_FEET_MAX


def test_occlusion_rates_fonction_pure():
    big = pygame.Rect(0, -200, 200, 200)
    small = pygame.Rect(50, -100, 50, 100)
    back_big = battle_actors.occlusion_rates([big, small])  # le petit est devant le grand
    assert back_big[1] == 0.0 and back_big[0] == pytest.approx(0.125)
    assert battle_actors.occlusion_rates([small, big])[0] == pytest.approx(1.0)  # petit derrière : caché à 100 %


def _tassee(poses):
    return [Vector2(1000 + 10 * i, 400 + 50 * i) for i in range(len(poses))]


def test_meta_formation_tassee(game, monkeypatch):
    monkeypatch.setattr(battle_actors, "hero_formation", _tassee)
    with pytest.raises(AssertionError):
        test_formation_aucun_heros_cache_a_plus_d_un_tiers(game, "soldat_mage_voleur")


def test_victoire_et_combat_ont_les_memes_positions(game):
    from final_classe.gfx.scenes.battle import BattleScene

    game.party = make_demo_party()
    battle = BattleScene(game, 0, 0)
    victory = VictoryScene(game, ZONES[0].waves()[0], 0, 0, 3)
    assert [a.home for a in battle.heroes] == [a.home for a in victory.heroes]


def test_meta_victoire_positions_differentes(game, monkeypatch):
    from final_classe.gfx.scenes import victory

    monkeypatch.setattr(victory, "place_heroes", lambda assets, heroes: [setattr(a, "home", Vector2(100 * i, 500)) for i, a in enumerate(heroes)])
    with pytest.raises(AssertionError):
        test_victoire_et_combat_ont_les_memes_positions(game)


def test_meta_shockwave_assombrissante(monkeypatch):
    def dark(self, surface):  # le bug : anneau sombre en mélange normal
        pygame.draw.ellipse(surface, (20, 20, 20), pygame.Rect(100, 100, 200, 100), 6)

    monkeypatch.setattr(Shockwave, "render", dark)
    with pytest.raises(AssertionError):
        test_shockwave_n_assombrit_aucun_pixel((255, 255, 255))
