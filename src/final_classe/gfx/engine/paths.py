"""Chemins du projet, construits depuis ce fichier (jamais depuis le dossier courant)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # racine du projet (contient assets/, sauvegardes/)
ASSETS_DIR = ROOT / "assets"
IMG_DIR = ASSETS_DIR / "img"
MANIFEST = ASSETS_DIR / "manifest.json"
