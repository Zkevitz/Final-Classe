# Final Classe

Un mini-RPG inspiré de Final Fantasy, construit pas à pas pour apprendre la POO.

Le jeu existe en deux versions qui partagent le même modèle (`characters/`, `items/`, `storage/`) :
la **version terminal** du cours et une **version graphique pygame** (sprites HD, combats ATB, chorégraphies d'attaques, musiques originales).

## Installation

Prérequis : Python 3.14 et [uv](https://docs.astral.sh/uv/). Dépendances : pygame-ce, numpy, Pillow, rich.

```bash
uv sync
```

## Lancer le jeu

Version terminal :

```bash
uv run final-classe
```

Version graphique :

```bash
uv run final-classe-gfx
```

ou, dans tous les cas :

```bash
uv run python -m final_classe.gfx
```

## Commandes (version graphique)

| Touche | Action |
|---|---|
| Flèches | Déplacer le curseur |
| Entrée / Espace | Valider |
| Échap | Retour / menu |
| F11 | Plein écran |
| Souris | Acceptée dans les menus |
| Entrée pendant une invocation | La passer |

## Nouveautés de l'itération 2

Les héros, Sephiroth et Garland disposent maintenant de 8 poses (idle, ready, windup, strike, cast, hurt, ko, victory) enchaînées en combat avec un fondu de 70 ms. Les invocations Ifrit, Shiva, Ramuh, et Bahamut ont des chorégraphies de 6,8 à 7 s en plusieurs actes (Entrée pour les passer). La musique est composée à partir de reprises synthétisées des morceaux de Final Fantasy (Prélude, Victory Fanfare, One-Winged Angel…), à écouter dans Options > Test son.

Les joueurs peuvent déposer leurs propres fichiers audio dans `assets/audio/original/<id>.ogg` (ou `.mp3`, `.flac`, `.wav`) : ils sont joués en priorité, et le jeu ne télécharge rien. Les ids et les titres attendus sont listés dans `assets/audio/original/LISEZMOI.txt`.

### Commandes vérifiées

- Lancer le jeu en mode graphique :
  ```bash
  uv run python -m final_classe.gfx
  ```

- Lancer un démonstrateur de scène :
  ```bash
  uv run python -m final_classe.gfx --headless --scene battle:crater:3 --demo --seconds 10 --shots shots/demo
  ```

- Lancer le démonstrateur d'invocation :
  ```bash
  uv run python -m final_classe.gfx.fx.demo --headless --only summon
  ```

- Rendre les fichiers audio :
  ```bash
  uv run python -m final_classe.gfx.audio.render
  ```

- Exécuter les tests de non-régression :
  ```bash
  uv run pytest -q
  ```

En mode `--demo`, une scène figée pendant 5 s écrit `BLOQUÉ` et sort avec le code 3. Une fin de partie écrit `FIN DE DÉMO` et sort avec le code 0.

Le dossier `tests/` contient 152 tests de non-régression (environ 15 s).

## Contenu du jeu

- Écran titre : 3 emplacements de sauvegarde, Options (volumes, plein écran, Test son).
- Prologue de Nibelheim, création du héros (nom, job, répartition de points), recrutement de 2 compagnons.
- Carte du monde et 5 zones : les Plaines de Dalmasca, la Forêt de Macalania, la Grotte des cristaux, le Sanctuaire du Chaos, le Cratère Nord.
- Événements d'avant-zone : marchand, coffre, Cid, Garland, Sephiroth.
- Boutique, préparation (équipement, materias), combats ATB façon Final Fantasy, butin, game over, fin.

## Sauvegardes

Dossier `sauvegardes/`, compatible avec la version terminal.

## Architecture

```
src/final_classe/
├── characters/      modèle POO du cours (intouché)
├── items/  storage/  stats.py   logique réutilisée par les deux versions
├── game/            version terminal (intouchée)
└── gfx/             version graphique
    ├── engine/      boucle, pile de scènes, assets (placeholders si une image manque), mode sans fenêtre
    ├── ui/          fenêtres façon FF, jauges, menus, dialogues, saisie
    ├── scenes/      une scène par fichier ; flow.py orchestre l'aventure
    ├── fx/          briques d'effets (particules, flashs, transitions…)
    │   └── choreo/  une chorégraphie unique par attaque, compétence, sort, invocation, objet, attaque de monstre
    └── audio/       synthétiseur numpy, partitions, rendu WAV, lecture
assets/
├── manifest.json    liste des images
├── img/             images HD lues par le jeu (générées par Codex, puis détourées)
└── audio/           musiques et bruitages rendus
```

Documentation détaillée : [ARCHITECTURE-GFX.md](docs/ARCHITECTURE-GFX.md), [DIRECTION-ARTISTIQUE.md](docs/DIRECTION-ARTISTIQUE.md), [ANIMATIONS.md](docs/ANIMATIONS.md), [AUDIO.md](docs/AUDIO.md).

## Outils de test

Lancer une scène sans fenêtre et enregistrer des captures (les sauvegardes de test vont dans `shots/headless/`) :

```bash
uv run python -m final_classe.gfx --headless --scene battle:plains:1 --demo --seconds 20 --shots shots/battle
```

Démo des effets :

```bash
uv run python -m final_classe.gfx.fx.demo --headless --only summon.
```

Rendu de l'audio (musiques et bruitages synthétisés par le code) :

```bash
uv run python -m final_classe.gfx.audio.render
```

## Mentions

Projet pédagogique non commercial. Final Fantasy est une marque de Square Enix.
