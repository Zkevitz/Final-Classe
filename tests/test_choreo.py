"""Chorégraphies : `play` ne lève jamais d'exception, et le catalogue de docs/ANIMATIONS.md est complet."""

import re

import pygame
import pytest
from conftest import ROOT
from pygame import Vector2

from final_classe.gfx.fx.choreo import REGISTRY, ActionContext, play

KEY = re.compile(r"`((?:attack|skill|spell|summon|item|monster|state|action)\.[a-z_]+)`")


def catalog_keys() -> list[str]:
    text = (ROOT / "docs" / "ANIMATIONS.md").read_text(encoding="utf-8")
    return sorted(set(KEY.findall(text)))


class _Actor:
    def __init__(self, x: int) -> None:
        self.home = Vector2(x, 450)
        self.offset = Vector2()
        self.scale, self.rotation, self.alpha, self.visible = 1.0, 0.0, 255, True
        self.tint = None
        self.rect = pygame.Rect(x - 40, 300, 80, 150)

    def flash(self, color=(255, 255, 255), seconds=0.12):
        pass

    def set_pose(self, pose, hold=None):
        pass


def test_le_catalogue_n_est_pas_vide():
    assert len(catalog_keys()) >= 30


@pytest.mark.parametrize("key", catalog_keys())
def test_chaque_cle_du_catalogue_est_dans_le_registre(key):
    assert key in REGISTRY, f"{key} (docs/ANIMATIONS.md) absente de REGISTRY"


def test_play_cle_inconnue_ne_leve_pas(game):
    impacts: list[int] = []
    ctx = ActionContext(caster=_Actor(300), targets=[_Actor(900)], values=[12], critical=[False],
                        on_impact=impacts.append, fx=game.fx, audio=game.audio, assets=game.assets)
    choreo = play("cle.qui.n.existe.pas", ctx)
    for _ in range(600):
        if not choreo.update(1 / 60):
            break
    assert hasattr(choreo, "update") and hasattr(choreo, "draw")


def test_play_sans_services_ne_leve_pas():
    ctx = ActionContext(caster=_Actor(300), targets=[_Actor(900)])
    choreo = play("n_importe_quoi", ctx)
    assert choreo is not None
