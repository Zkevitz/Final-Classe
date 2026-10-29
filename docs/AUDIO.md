# Audio — musiques et bruitages

Contrat partagé par `audio-composer` (qui produit le son), `vfx-animator` (qui déclenche les bruitages dans les chorégraphies), `pygame-coder` (qui lance les musiques selon les scènes), `playtester` et `sonnet-reviewer`.

## 1. Principe

- **Les musiques sont celles de la licence Final Fantasy** (compositions de Nobuo Uematsu et des autres compositeurs de la série ; projet pédagogique, non commercial). Chaque id du §3 correspond à un morceau officiel, et on le joue de l'une des deux façons suivantes :
  1. **Fichier officiel fourni par l'utilisateur** (prioritaire) : si `assets/audio/original/<id>.(ogg|mp3|flac|wav)` existe, le jeu le joue tel quel. C'est l'utilisateur qui y dépose ses propres fichiers. **Aucun agent ne télécharge de musique** sur Internet.
  2. **Reprise synthétisée** (par défaut) : `audio-composer` transcrit le morceau officiel (mélodie, harmonie, basse, rythme, structure et tonalité d'origine, au plus près) sous forme de partition en code, puis l'orchestre avec le synthé numpy. On doit le reconnaître dès les premières mesures.
- **Les bruitages** restent synthétisés par le code. Ils s'inspirent des sons typiques de la série : le « bip » du curseur, le scintillement du soin, le fracas des invocations.
- **Rendu préalable** : `uv run python -m final_classe.gfx.audio.render [--only <id>]` écrit `assets/audio/music/<id>.wav` et `assets/audio/sfx/<id>.wav`, puis imprime un rapport par fichier (durée, crête en dBFS, RMS, et pour les boucles l'écart au point de bouclage). Le jeu **charge** ces fichiers, après avoir cherché `assets/audio/original/<id>.*`. S'il ne trouve rien, le jeu reste **muet sans planter** et l'écrit une seule fois dans le journal.
- **Le dossier `assets/audio/original/`** contient un `LISEZMOI.txt` (rédigé par `audio-composer`) qui liste, pour chaque id, le titre officiel attendu et le nom de fichier à utiliser.
- **Formats** : musique en mono 32 kHz 16 bits, bruitages en mono 44,1 kHz 16 bits. Crête ≤ −1 dBFS, sans clipping. Total de `assets/audio/` ≤ 60 Mo.
- **Boucles sans couture** : une musique `loop` se termine exactement là où elle recommence (la queue de réverbération est repliée sur le début), sans clic.

## 2. API (`src/final_classe/gfx/audio/`)

```python
audio.play_sfx(name: str, volume: float = 1.0, pan: float = 0.0) -> None   # pan de -1 (gauche) à 1 (droite)
audio.play_music(track: str, fade_ms: int = 800) -> None   # enchaîne en fondu ; ne fait rien si c'est déjà la piste en cours
audio.stop_music(fade_ms: int = 800) -> None
audio.duck(level: float = 0.35, seconds: float = 1.0) -> None   # baisse la musique un moment (invocations, Supernova)
audio.update(dt: float) -> None   # appelé à CHAQUE image par la boucle du moteur (fondus non bloquants des fichiers original/ en streaming)
audio.music_volume / audio.sfx_volume   # 0..1, réglables depuis le menu Options
audio.MUSIC_IDS / audio.SFX_IDS          # tuples des ids des §3 et §4, dans l'ordre (pour le Test son)
```

Un nom inconnu ou un mixer absent (mode sans fenêtre, pas de carte son) ne lève jamais d'exception.

## 3. Musiques

Les ids ne changent pas (le code les utilise déjà). C'est le morceau officiel qui change.

| Id | Utilisée pour | Morceau officiel repris | Orchestration de la reprise | Durée | Boucle |
|---|---|---|---|---|---|
| `title` | Écran titre, création, recrutement | **Prelude** (« Prélude au cristal », série Final Fantasy) | Arpèges de harpe, nappe de cordes | 60 s | oui |
| `prologue` | Nibelheim | **Those Chosen by the Planet** (FF VII) | Cordes graves, chœur sourd, cloche, percussions | 45 s | oui |
| `world_map` | Carte du monde, préparation | **Main Theme of Final Fantasy VII** | Cors, cordes, flûte, caisse claire | 75 s | oui |
| `battle` | Combats ordinaires | **Let the Battles Begin!** (FF VII) | Basse, cuivres, cordes rapides, batterie | 60 s | oui |
| `boss` | Dernière vague de chaque zone (sauf Sephiroth) | **Fight On!** (FF VII) | Orgue, cuivres, basse, timbales | 60 s | oui |
| `final_boss` | Sephiroth | **One-Winged Angel** (FF VII) | Chœur (formants), cordes staccato, cuivres, grosses percussions | 75 s | oui |
| `victory` | Fin d'un combat gagné (jingle) | **Victory Fanfare** (l'introduction, série Final Fantasy) | Fanfare de cuivres, timbales | 5 s | non |
| `victory_loop` | Écran de butin, après le jingle | **Victory Fanfare** (la partie en boucle) | Cuivres, cordes pizzicato | 20 s | oui |
| `shop` | Boutique de Cid, événements calmes | **Cid's Theme** (FF VII) | Cuivres légers, marimba, contrebasse | 40 s | oui |
| `ending` | Fin du jeu | **Final Fantasy** (le thème principal de la série) | Cordes, cors, harpe, final en crescendo | 90 s | oui |
| `game_over` | Équipe K.O. | **Aerith's Theme** (FF VII), extrait | Piano, nappe de cordes | 20 s | non |

## 4. Bruitages

Ils doivent être percutants, courts (0,05 à 1,5 s, jusqu'à 4 s pour les invocations et `supernova`) et superposables. Tous ceux que cite `docs/ANIMATIONS.md` sont obligatoires :

| Famille | Ids |
|---|---|
| Interface | `cursor`, `confirm`, `cancel`, `error`, `menu_open`, `text_blip`, `save`, `buy`, `transition` (le tourbillon d'entrée en combat) |
| Armes | `slash`, `slash_heavy`, `staff_hit`, `impact`, `punch`, `dagger`, `katana_draw`, `wind_slash`, `arrow`, `arrow_power`, `shuriken`, `claw`, `crit` (couche ajoutée aux critiques et aux faiblesses) |
| Magie | `cast`, `charge`, `charge_big`, `fire`, `fire_pillar`, `ice_form`, `ice_shatter`, `thunder`, `thunder_big`, `heal`, `chakra`, `armor_break`, `coins` |
| Invocations | `summon`, `roar`, `explosion`, `mega_flare` |
| Objets et états | `potion`, `elixir`, `revive`, `defend`, `ko_monster`, `ko_hero`, `level_up` |
| Monstres | `supernova`, `needles`, `poison_gas`, `flame_breath` |

## 5. Vérification

Ni Opus ni les agents n'entendent le son. Le rapport du script de rendu doit donc être lu à chaque rendu (crête, clipping, durée, couture des boucles). Le jeu propose un **« Test son »** dans le menu du titre (scène `jukebox`), qui liste les musiques et les bruitages pour que **l'utilisateur** les écoute et les valide.
