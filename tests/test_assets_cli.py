"""Recrues et manifeste, placeholder d'image, ligne de commande, sauvegardes du mode sans fenêtre."""

import json
import subprocess
import sys

import pygame
from conftest import ROOT

from final_classe.characters import Knight, Monk, Soldier
from final_classe.characters.jobs import BlackMage
from final_classe.game.recruit import recruits
from final_classe.gfx.engine.demo import make_demo_party
from final_classe.gfx.scenes._demo import HERO_IMAGE, NAMED_IMAGE, hero_image

MANIFEST = ROOT / "assets" / "manifest.json"


def _manifest_ids() -> set[str]:
    return {a["id"] for a in json.loads(MANIFEST.read_text(encoding="utf-8"))["assets"]}


# --- hero_image : nom ET job -----------------------------------------------------------------
def test_hero_image_depend_du_nom_et_du_job():
    assert hero_image(BlackMage("Lulu", 10, 22, 12, 16)) == "hero_lulu"
    assert hero_image(Knight("Basch", 17, 10, 20, 13)) == "hero_basch"
    assert hero_image(Monk("Amarant", 18, 16, 14, 12)) == "hero_amarant"
    # même nom, autre job : le sprite du job
    assert hero_image(Soldier("Lulu", 10, 10, 10, 10)) == "hero_soldier"
    assert hero_image(Soldier("Basch", 10, 10, 10, 10)) == "hero_soldier"
    # même job, autre nom : le sprite du job
    assert hero_image(BlackMage("Mira", 10, 22, 12, 16)) == "hero_black_mage"
    assert hero_image(Knight("Zed", 17, 10, 20, 13)) == "hero_knight"
    assert hero_image(Monk("Yan", 18, 16, 14, 12)) == "hero_monk"
    assert hero_image(Monk) == "hero_monk"  # une classe : toujours le job


def test_chaque_recrue_nommee_a_son_id_dans_le_manifeste():
    ids = _manifest_ids()
    for hero in recruits():
        assert hero_image(hero) in ids, hero.name
    for _job, sprite in NAMED_IMAGE.values():
        assert sprite in ids
    for sprite in HERO_IMAGE.values():
        assert sprite in ids
    for hero in make_demo_party().heroes:
        assert hero_image(hero) in ids


# --- assets ----------------------------------------------------------------------------------
def test_image_inconnue_donne_un_placeholder_sans_exception(game):
    img = game.assets.image("id_qui_n_existe_pas")
    assert isinstance(img, pygame.Surface) and img.get_width() > 0 and img.get_height() > 0
    assert not game.assets.exists("id_qui_n_existe_pas")
    assert game.assets.image("id_qui_n_existe_pas") is img  # mis en cache


# --- ligne de commande -----------------------------------------------------------------------
def test_scene_inconnue_sort_avec_le_code_2(tmp_path):
    res = subprocess.run(
        [sys.executable, "-m", "final_classe.gfx", "--headless", "--scene", "nexiste_pas"],
        cwd=tmp_path, capture_output=True, text=True, timeout=60)
    assert res.returncode == 2
    assert "nexiste_pas" in res.stderr


def test_scene_inconnue_run_cli_renvoie_2(tmp_path, monkeypatch):
    from final_classe.gfx.engine.runner import run_cli

    monkeypatch.chdir(tmp_path)
    assert run_cli(["--headless", "--scene", "nexiste_pas"]) == 2


# --- mode sans fenêtre : jamais dans sauvegardes/ --------------------------------------------
def _snapshot(folder):
    if not folder.exists():
        return {}
    return {p.name: (p.stat().st_mtime_ns, p.stat().st_size) for p in folder.iterdir()}


def test_sauvegarde_en_mode_sans_fenetre_ne_touche_pas_sauvegardes(game_here):
    import os
    from pathlib import Path

    real = ROOT / "sauvegardes"
    before = _snapshot(real)
    work = Path(os.getcwd()).resolve()
    assert work == (ROOT / "shots" / "headless").resolve()  # le chdir du mode sans fenêtre
    game_here.party = make_demo_party()
    game_here.slot = 3
    target = work / "sauvegardes" / "partie-3.json"
    existed = target.exists()
    try:
        assert game_here.save()
        assert target.is_file()
        assert _snapshot(real) == before
    finally:
        if not existed and target.exists():
            target.unlink()
