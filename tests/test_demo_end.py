"""Fin de démo (`FIN DE DÉMO`, code 0) et garde-fou `BLOQUÉ` (§5), pilotés en process."""

import types

import pygame
import pytest

from final_classe.gfx.engine import runner
from final_classe.gfx.engine.demo import make_demo_party
from final_classe.gfx.engine.scene import Scene
from final_classe.gfx.scenes.game_over import GameOverScene


def _args(seconds):
    return types.SimpleNamespace(demo=True, seconds=seconds, shot_every=1.0, shots=None, shot_scale=0.5,
                                 debug_freeze=None, blocked=False)


class Static(Scene):
    """Une scène qui ne change jamais."""

    def draw(self, surface):
        surface.fill((10, 20, 30))


class Moving(Scene):
    """Une scène qui bouge à chaque image."""

    t = 0.0

    def update(self, dt):
        self.t += dt

    def draw(self, surface):
        surface.fill((10, 20, 30))
        pygame.draw.rect(surface, (255, 255, 255), (int(self.t * 200) % 1000, 100, 200, 200))


def test_terminal_scene_reconnait_game_over(game):
    game.party = make_demo_party()
    assert runner.terminal_scene(GameOverScene(game, 0, 0)) == "game_over"
    assert runner.terminal_scene(Static(game)) is None


def test_demo_qui_atteint_game_over_fin_de_demo_sans_blocage(game, capsys):
    game.party = make_demo_party()
    game.demo = True
    game.push(GameOverScene(game, 0, 0), transition=None)
    args = _args(30)
    runner._run_headless(game, args)
    out = capsys.readouterr().out
    assert "FIN DE DÉMO: game_over" in out and "BLOQUÉ" not in out
    assert args.blocked is False


def test_meta_game_over_pris_pour_un_blocage(game, capsys, monkeypatch):
    monkeypatch.setattr(runner, "terminal_scene", lambda scene: None)
    with pytest.raises(AssertionError):
        test_demo_qui_atteint_game_over_fin_de_demo_sans_blocage(game, capsys)


def test_scene_figee_5_s_donne_bloque_et_code_3(game, capsys):
    game.demo = True
    game.push(Static(game), transition=None)
    args = _args(9)
    runner._run_headless(game, args)
    out = capsys.readouterr().out
    assert "BLOQUÉ: Static" in out and args.blocked is True


class FakeGame:
    """Juste ce que lit `StuckWatch` : `scene` et `screen`. Aucune horloge, aucun rendu réel."""

    def __init__(self, scene):
        self.scene = scene
        self.screen = pygame.Surface((1280, 720))
        self.screen.fill((10, 20, 30))

    def shift(self, k):
        """Une image différente (un carré blanc qui avance)."""
        self.screen.fill((10, 20, 30))
        pygame.draw.rect(self.screen, (255, 255, 255), ((k * 97) % 1000, 100, 200, 200))


def test_stuckwatch_n_alerte_pas_avant_5_s_puis_alerte():
    game, watch = FakeGame(object()), runner.StuckWatch()
    for k in range(0, 20):  # échantillons tous les 0,25 s : t = 0 ... 4,75 s
        assert watch.update(game, k * 0.25) is False
    assert watch.update(game, 4.99) is False
    assert watch.update(game, 5.0) is True


def test_stuckwatch_n_alerte_jamais_sur_image_mobile():
    game, watch = FakeGame(object()), runner.StuckWatch()
    for k in range(0, 80):  # 20 s simulées, l'image change à chaque échantillon
        game.shift(k)
        assert watch.update(game, k * 0.25) is False


def test_stuckwatch_se_reinitialise_au_changement_de_scene():
    game, watch = FakeGame(object()), runner.StuckWatch()
    for k in range(0, 17):  # 4 s d'immobilité
        watch.update(game, k * 0.25)
    game.scene = object()  # nouvelle scène, image identique : le compteur repart de 4,5
    assert watch.update(game, 4.5) is False
    assert watch.update(game, 9.0) is False
    assert watch.update(game, 9.5) is True


def test_meta_garde_fou_desactive(game, capsys, monkeypatch):
    monkeypatch.setattr(runner.StuckWatch, "update", lambda self, g, now: False)
    with pytest.raises(AssertionError):
        test_scene_figee_5_s_donne_bloque_et_code_3(game, capsys)


def test_fin_de_demo_produit_au_moins_une_capture(game, capsys, tmp_path):
    game.party = make_demo_party()
    game.demo = True
    game.push(GameOverScene(game, 0, 0), transition=None)
    args = _args(30)
    args.shots = str(tmp_path / "shots")
    runner._run_headless(game, args)
    out = capsys.readouterr().out
    assert "FIN DE DÉMO: game_over" in out
    assert len(list((tmp_path / "shots").glob("shot_*.png"))) >= 1


def test_meta_fin_de_demo_sans_capture(game, capsys, tmp_path, monkeypatch):
    monkeypatch.setattr(type(game), "screenshot", lambda self, *a, **k: None)
    with pytest.raises(AssertionError):
        test_fin_de_demo_produit_au_moins_une_capture(game, capsys, tmp_path)


def test_ending_en_demo_se_termine_par_fin_de_demo(game, capsys):
    from final_classe.gfx.scenes.ending import EndingScene

    game.party = make_demo_party()
    game.demo = True
    game.push(EndingScene(game), transition=None)
    args = _args(150)
    runner._run_headless(game, args)
    out = capsys.readouterr().out
    assert "FIN DE DÉMO: ending" in out and "BLOQUÉ" not in out
    assert args.blocked is False
