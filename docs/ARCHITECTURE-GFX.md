# Architecture de la version pygame

Contrat technique partagé par `pygame-coder`, `vfx-animator`, `playtester` et `sonnet-reviewer`. Le style visuel est dans `docs/DIRECTION-ARTISTIQUE.md`, la liste des images dans `assets/manifest.json`.

## 1. Principes

- **Bibliothèque : `pygame-ce`** (déjà installée, avec Pillow et numpy). On écrit `import pygame`. Python 3.14.
- **La logique existe déjà, on ne la réécrit pas.** `characters/`, `items/`, `storage/` et `stats.py` sont réutilisés tels quels.
- **`src/final_classe/characters/` est intouchable** : un hook demande la confirmation de l'utilisateur à toute modification. On associe une classe à son sprite **côté interface** (dictionnaire classe → id du manifeste), jamais en ajoutant un attribut au modèle.
- **`src/final_classe/game/` reste la version terminal** et ne se modifie pas. On peut **importer** ses fonctions **pures** (les vagues `plains()`, `forest()`…, `first_shop()`, `second_shop()`, `ZONES[i].name`), mais **jamais** appeler une fonction qui affiche ou lit au clavier (`before_*`, `open_chest`, `equip_starters`, `give_signatures`, `fight`, `prepare`, `visit`, `recruit`, `create_hero`, `ask_*`) : `input()` bloquerait la fenêtre. Leur contenu narratif est refait en scènes.
- **La logique s'applique tout de suite, l'affichage rattrape.** `hero.attack(target)` ou `monster.act(heroes)` modifient les PV immédiatement : la scène lance l'animation **après**, avec des PV affichés qui glissent vers la vraie valeur, et ne joue le K.O. qu'à la fin de l'animation d'impact.
- **Sauvegardes** : `storage.save_game` / `load_game`, compatibles avec la version terminal. Le dossier `sauvegardes/` est relatif au dossier courant : le point d'entrée fait `os.chdir` vers la racine du projet.

## 2. Arborescence et propriétaires

```
src/final_classe/gfx/
├── __init__.py          main() : point d'entrée « final-classe-gfx »      pygame-coder
├── __main__.py          python -m final_classe.gfx                         pygame-coder
├── engine/              boucle, scènes, entrées, assets, texte             pygame-coder
│                        (instancie `Audio` et `FxManager`, ne les code pas)
├── ui/                  fenêtres FF, jauges, menus, curseur, polices       pygame-coder
├── scenes/              un fichier par scène                               pygame-coder
├── fx/                  briques d'effets, transitions                      vfx-animator
│   ├── choreo/          chorégraphies : attacks, skills, spells,           vfx-animator
│   │                    summons, items, monsters (un fichier chacun)       (un animateur par fichier)
│   └── demo.py          démo sans fenêtre de toutes les chorégraphies      vfx-animator
└── audio/               synthé, partitions, rendu, lecture                 audio-composer
assets/raw/              images brutes de Codex                             Codex
assets/img/              images post-traitées (lues par le jeu)             script gen-sprite
assets/audio/            musiques et bruitages rendus (WAV)                 audio-composer
shots/                   captures du playtester (ignoré par git)            playtester
```

Le point d'entrée `final-classe-gfx` est déjà déclaré dans `pyproject.toml` (lancer `uv sync` si la commande est introuvable) ; `uv run python -m final_classe.gfx` marche dans tous les cas.

Les fichiers `fx/__init__.py` (`FxManager`, briques) et `fx/choreo/__init__.py` (`REGISTRY`, `register`, `play`) appartiennent au **premier** `vfx-animator` (lot des briques). Les animateurs suivants n'y touchent pas : chaque module de `choreo/` s'enregistre lui-même avec le décorateur `@register("attack.soldier")`, et `choreo/__init__.py` importe ses modules en tolérant ceux qui n'existent pas encore.

Deux agents ne travaillent **jamais** en même temps sur le même fichier. Plusieurs `pygame-coder` peuvent travailler en parallèle **sur des scènes différentes** une fois `engine/` et `ui/` en place.

## 3. Contrats entre modules

**Scène** (`engine/scene.py`) :
```python
class Scene:
    def __init__(self, game: "Game") -> None: ...
    def handle_event(self, event: pygame.event.Event) -> None: ...
    def update(self, dt: float) -> None: ...      # dt en secondes
    def draw(self, surface: pygame.Surface) -> None: ...   # surface logique 1280×720
```
`Game` tient la pile de scènes (`push`, `pop`, `replace(scene, transition=...)`), la `Party` courante, l'emplacement de sauvegarde, et les services `assets`, `audio`, `fx`.

**Assets** (`engine/assets.py`) : `assets.image("hero_soldier")` lit le manifeste, charge `assets/img/<id>.png` une seule fois avec `convert_alpha()`, et **renvoie un placeholder** (silhouette colorée + id écrit dessus, aux bonnes dimensions) si le fichier manque. Le jeu ne doit **jamais** planter à cause d'une image absente. Les chemins se construisent depuis `Path(__file__)`, pas depuis le dossier courant (le dossier du projet contient des espaces).

**Assets, ancrage** : un sprite post-traité garde une petite marge transparente ; on l'ancre sur les **pieds réels**, c'est-à-dire le bas de `surface.get_bounding_rect()` (calculé une fois au chargement), centré horizontalement.

**Poses** (planches, voir `docs/DIRECTION-ARTISTIQUE.md` §2 bis) : `assets.frame(asset_id, pose) -> pygame.Surface` renvoie la pose demandée (`assets/img/<id>/<pose>.png`), et `assets.frame_anchor(asset_id, pose) -> Vector2` renvoie le point des pieds (lu dans `assets/img/<id>/frames.json`). Les poses sont toutes à la même échelle : on les dessine en alignant leur ancre sur `home + offset`. **Repli** : si la planche n'existe pas encore, `frame()` renvoie le sprite simple et l'ancre est celle de `feet_rect`. Le jeu marche donc avec ou sans planches.

**Effets** (`fx/`) : chaque effet expose `update(dt) -> bool` (False quand il est terminé) et `draw(surface, layer)`. Le `FxManager` du jeu les met à jour et les dessine par **calques** :
`back` (cercles magiques au sol, derrière les sprites) → sprites des combattants → `front` (projectiles, particules, chiffres) → interface → `overlay` (assombrissement de l'écran, flashs plein écran, splash d'invocation, au-dessus de tout).
Briques minimales : `Tween` (+ fonctions d'easing), `ParticleEmitter` (préréglages `fire`, `ice`, `thunder`, `holy`, `heal`, `dust`, `sparkle`, `coins`, `poison`), `FloatingText` (dégâts, soins, PM, texte libre), `ScreenShake`, `Flash` (sprite ou écran), `ScreenTint` (assombrir ou teinter), `Trail` (traînées d'armes, images rémanentes), `Lightning` (éclair procédural), `BattleTransition` (spirale ou éclats), `Fade`.

**Chorégraphies** (`fx/choreo/`, catalogue dans `docs/ANIMATIONS.md`) :
```python
class Actor(Protocol):          # fourni par la scène de combat, un par combattant
    home: pygame.Vector2       # position au repos (pieds), en lecture seule
    offset: pygame.Vector2     # déplacement temporaire (élan, saut) ; la chorégraphie le remet à 0
    scale: float; rotation: float; alpha: int; visible: bool
    tint: tuple[int, int, int] | None    # teinte (grisé du K.O., rouge du flash…)
    rect: pygame.Rect          # boîte actuelle du sprite à l'écran (pour viser le centre, la tête…)
    def flash(self, color=(255, 255, 255), seconds: float = 0.12) -> None: ...
    def set_pose(self, pose: str, hold: float | None = None) -> None: ...
        # change de pose avec un fondu enchaîné court (~70 ms) ; hold = durée avant le retour
        # automatique à la pose de base (idle, ou ko si le combattant est K.O.) ; None = garde la pose

@dataclass
class ActionContext:
    caster: Actor
    targets: list[Actor]
    values: list[int]          # dégâts ou soins par cible (déjà appliqués au modèle)
    critical: list[bool]       # faiblesse élémentaire ou coup critique, par cible
    on_impact: Callable[[int], None]   # à appeler UNE fois par cible, au moment du coup
    fx: FxManager; audio: Audio; assets: Assets
    extra: dict[str, object]   # ex. {"gil": 120, "stolen": "Potion"} pour Vol ; toujours "kind": "damage" | "heal" | "mp" (type des values)

REGISTRY: dict[str, Callable[[ActionContext], Choreography]]   # clé du catalogue → fabrique
def play(key: str, ctx: ActionContext) -> Choreography   # clé inconnue → chorégraphie générique, jamais d'exception
```
Une `Choreography` est un effet comme les autres (`update`, `draw(surface, layer)`) avec en plus `skippable: bool` (vrai pour les invocations) et `skip()`. La scène de combat attend la fin de la chorégraphie avant de passer au tour suivant, et cache l'interface pendant les invocations et `monster.supernova`.

**Audio** (`audio/`) : contrat complet dans `docs/AUDIO.md` (`play_sfx`, `play_music`, `stop_music`, `duck`). Les fichiers sont rendus à l'avance ; s'il en manque un, ou si le mixer est indisponible, le jeu reste muet sans planter.

## 4. Les scènes (jeu complet)

Titre (nouvelle partie / continuer, 3 emplacements avec résumé, Options : volumes, Test son = scène `jukebox`) → prologue (Nibelheim, duel scripté perdu) → création du héros (saisie du nom au clavier, choix du job) → recrutement → carte du monde (5 zones) → pour chaque zone : événement d'avant-zone (marchand, coffre, Cid, Garland, Sephiroth) → préparation (équipement, materias) → vagues de combats → butin → sauvegarde → … → fin.

**Combat** : ATB façon FF en mode « attente » (les jauges se remplissent selon la VIT, le temps se fige quand un menu est ouvert). Menu Attaquer / compétence du job / Magie / Objet / Se défendre, avec choix de la cible au curseur. Le `warning` des monstres s'affiche dans une bannière.

## 5. Mode sans fenêtre (pour le playtester)

Le point d'entrée accepte :

```
python -m final_classe.gfx --headless --scene <nom> [--demo] [--action <clé>] [--seconds 6] [--shot-every 1.0] [--shots shots/<nom>] [--shot-scale 0.5] [--seed 1]
python -m final_classe.gfx.fx.demo --headless [--only <clé ou préfixe>] [--shots shots/fx] [--shot-every 0.25] [--shot-scale 0.5]
python -m final_classe.gfx.audio.render [--only <id>]
```

- `--headless` met `SDL_VIDEODRIVER=dummy` et `SDL_AUDIODRIVER=dummy` **avant** `pygame.init()`, et utilise un **`dt` fixe de 1/60 s** (captures reproductibles, même si le rendu logiciel est lent). Hors mode sans fenêtre, `dt` est plafonné à 1/30 s.
- `--scene` ouvre directement une scène avec une partie de démonstration (`title`, `prologue`, `creation`, `recruit`, `world_map`, `event:<zone>` (l'événement d'avant-zone), `prepare`, `battle:<zone>:<vague>` (zone = clé `plains`…`crater` ou index 0 à 4 ; vague comptée à partir de 1, par ex. `battle:crater:3` = Sephiroth), `loot`, `shop`, `victory`, `game_over`, `ending`, `jukebox`).
- `fx.demo` joue les chorégraphies sur des **acteurs factices** avec un `Assets` et un `Audio` factices (placeholders, silence) : il ne dépend pas de `engine/`, et peut donc être construit en parallèle.
- `--demo` fait jouer automatiquement la scène (l'IA choisit les actions), pour tester un combat sans clavier. `--action <clé>` force la chorégraphie jouée à chaque tour (par exemple `summon.bahamut`), pour en vérifier une précise dans un vrai combat.
- `--shots` enregistre une capture PNG toutes les `--shot-every` secondes, puis quitte au bout de `--seconds`. `--shot-scale 0.5` (valeur par défaut) enregistre les captures en 640×360 : c'est suffisant pour juger, et **ça divise par quatre le coût en tokens** de leur lecture.
- La sortie se termine par une ligne `FPS moyen: <n>` et le code de retour est différent de 0 en cas d'exception.
- **Détection de blocage** : avec `--demo`, si la scène courante ne change pas ET que l'image reste identique (même empreinte de la surface, avec une tolérance) pendant 5 s, le programme écrit `BLOQUÉ: <scène> depuis <n> s` et sort avec le code 3. Ce garde-fou remplace l'œil du playtester pour les démos figées. **Fin de démo** : en `--demo`, atteindre une scène terminale (`game_over`, ou `ending` une fois son défilement fini) n'est pas un blocage : le programme écrit `FIN DE DÉMO: <scène>` et sort avec le code 0. La détection `BLOQUÉ` ne s'applique qu'aux autres scènes.
- Les sauvegardes du mode sans fenêtre vont dans `shots/headless/` (le jeu fait `os.chdir` vers ce dossier) : un test ou une démo ne touche **jamais** `sauvegardes/`.
- Une scène inconnue affiche la liste des scènes valides et sort avec le code 2.
- Sans `--headless`, le jeu s'ouvre normalement (fenêtre 1280×720 redimensionnable, F11 = plein écran, Échap = retour/menu).

## 6. Correspondances modèle → assets (dans `gfx/`, jamais dans le modèle)

| Modèle | Id d'image | Remarque |
|---|---|---|
| Job du héros (`Soldier`, `BlackMage`, `Knight`, `Monk`, `Thief`, `Samurai`, `Archer`, `Ninja`) | `hero_soldier`, `hero_black_mage`, `hero_knight`, `hero_monk`, `hero_thief`, `hero_samurai`, `hero_archer`, `hero_ninja` | Par classe (`type(hero)`), pas par nom : le joueur choisit le nom |
| Recrues nommées de `game/recruit.py` dont le personnage diffère du sprite du job : `Lulu` (Mage noir), `Basch` (Chevalier), `Amarant` (Moine) | `hero_lulu`, `hero_basch`, `hero_amarant` | Prioritaires sur le sprite du job, par `hero.name` ; une seule fonction `hero_image(hero)` dans `scenes/_demo.py`, utilisée par toutes les scènes |
| Monstre (`Flan`, `Wolf`, `Bomb`, `Ahriman`, `Cactuar`, `Malboro`, `Tonberry`, `Golem`, `Behemoth`, `Chimera`, `Lich`, `Garland`, `RedDragon`, `Sephiroth`) | `mon_flan`, `mon_wolf`, `mon_bomb`, `mon_ahriman`, `mon_cactuar`, `mon_malboro`, `mon_tonberry`, `mon_golem`, `mon_behemoth`, `mon_chimera`, `mon_lich`, `mon_garland`, `mon_red_dragon`, `mon_sephiroth` | Les variantes (« Loup alpha ») gardent le sprite de leur classe. `floating: true` dans le manifeste → lévitation |
| `ZONES[0..4]` | `bg_plains`, `bg_forest`, `bg_cave`, `bg_chaos`, `bg_crater` | Prologue : `bg_prologue` ; titre, création et recrutement : `bg_title` |
| Scènes | carte → `bg_world_map`, boutique → `bg_shop`, fin → `bg_ending`, titre → `ui_emblem` (au-dessus du titre rendu par le code) | |
| Invocations (`Ifrit`, `Shiva`, `Ramuh`, `Bahamut`) | `summon_fire`, `summon_ice`, `summon_thunder`, `summon_dragon_king` | Par nom de materia |
| Objets (`Potion`, `Éther`, `Queue de phénix`, `Élixir`) | `icon_potion`, `icon_ether`, `icon_phoenix_down`, `icon_elixir` | Menus Objet, boutique, butin |
| Materias attaque/soin / invocation | `icon_materia_green` / `icon_materia_red` | |
| Équipement (`Slot.WEAPON` épée ou bâton, `ARMOR`, `ACCESSORY`) | `icon_sword` / `icon_rod`, `icon_armor`, `icon_accessory` | Bâton = arme dont le nom contient « bâton » ou une MAG bonus > FOR bonus |
| Gils, curseur | `icon_gil`, `ui_cursor` | |

## 7. Pièges connus (à éviter dès le départ)

- Windows met à l'échelle les fenêtres en flou : appeler `ctypes.windll.shcore.SetProcessDpiAwareness(1)` (dans un `try`) avant de créer la fenêtre.
- `convert_alpha()` exige une fenêtre créée : on crée l'affichage **avant** de charger les assets.
- Les gros PNG se chargent lentement : on les charge une seule fois et on les met en cache, et on met en cache aussi les versions redimensionnées et les textes rendus.
- Les animations dépendent de `dt`, jamais du nombre d'images : `clock.tick(60)`.
- Les surfaces en mode additif (`special_flags=pygame.BLEND_ADD`) servent aux lueurs ; on ne crée pas de surface par particule et par image.
- Les accents passent par `SysFont` : on ne s'appuie pas sur la police par défaut `freesansbold`.

## 8. Invariants du jeu (source unique)

Toute règle découverte en cours de route s'écrit **ici d'abord**, puis les briefs citent ce paragraphe. L'orchestrateur ne la transmet jamais agent par agent sans l'avoir écrite.

- Le contrat détaillé du déroulement de l'aventure est la docstring de `src/final_classe/gfx/scenes/flow.py` (à lire avant de toucher une scène).
- **Vagues** : `game.wave` compte à partir de 0 ; les arguments de `--scene battle:<zone>:<n>` et de la scène `battle` comptent à partir de 1.
- **Butin** : `party.reward` est appelé **une seule fois** par combat gagné, par la scène `loot`. `flow.after_battle` ne le refait pas.
- **Ordre des événements** identique à la version terminal (`game/adventure.py`, `game/zones.py`) : événement d'avant-zone → préparation → dialogue de boss → vagues → repos → sauvegarde.
- **Nouvelle partie / Réessayer** : on repart d'un état neuf (équipe, boutique, inventaire) ; rien ne survit d'une partie à l'autre. « Réessayer » recharge la **dernière** sauvegarde de l'emplacement en cours (`game.slot`), jamais celle d'une autre partie ni un état antérieur.
- **K.O.** : l'état affiché suit toujours `model.is_alive`. Un héros relevé puis retombé à 0 PV redevient K.O.
- **Recrues** : le sprite d'un héros dépend de son nom ET de son job (`hero_image`) ; toute recrue ou tout personnage nommé du jeu a son id dans le manifeste.
- **Poses : qui les pose** (itération 2). La **scène de combat** gère les poses d'état : `ready` (jauge ATB pleine ou menu ouvert sur ce héros), `hurt` 0,3 s sur **chaque cible touchée**, posée par le callback `on_impact` de la scène (les chorégraphies ne posent jamais `hurt` sur les cibles), `ko` (base quand `not model.is_alive`, après l'animation d'impact), `victory` à la fin d'un combat gagné. Les **chorégraphies** ne posent que les poses du **lanceur** (`windup`, `strike`, `cast`, et `ready` pour `action.defend`), sauf `item.phoenix_down` qui pose `hurt` sur la cible relevée. Une chorégraphie finit toujours avec le lanceur revenu à sa pose de base (`hold`, ou `set_pose("idle")` à la fin). Le changement de pose est un fondu enchaîné d'environ 70 ms : jamais de saut d'une image à l'autre.
- **Fin d'une chorégraphie, jouée jusqu'au bout OU passée (`skip()`, fin forcée)** : le lanceur revient à sa pose de base, la musique est dé-duckée (`audio.duck(1.0, 0)`), chaque cible a reçu exactement un `on_impact` ET son chiffre de dégâts ou de soin, et aucun effet ne reste dans le `FxManager`. Filet de sécurité : la scène de combat remet le lanceur vivant à sa pose de base à la fin de chaque action. C'est la chorégraphie qui gère le `duck`, pas la scène.
- **Formation** : les combattants d'un camp sont étagés en diagonale (façon FF), avec un ordre de dessin du fond vers l'avant. Aucun combattant, debout ou K.O., n'est caché à plus d'un tiers par un autre, et un héros K.O. reste toujours dessiné et lisible. Le combat et l'écran de victoire utilisent les mêmes positions.
- **Ondes de choc, lueurs, rayons** : toujours en `BLEND_ADD` (jamais une couleur assombrie en mélange normal, qui donne des anneaux gris sur fond clair).
- **Blocage** : en `--demo`, une scène figée 5 s se termine par `BLOQUÉ` et le code 3 (§5).

## 9. Tests de non-régression (`tests/`, propriétaire : `sonnet-coder`)

- pytest (déjà installé en dépendance de développement) : `uv run pytest -q`.
- Les tests travaillent dans un dossier temporaire (`tmp_path` + `monkeypatch.chdir`) : ils n'écrivent jamais dans `sauvegardes/`.
- Ils pilotent la logique et les scènes sans fenêtre (`SDL_VIDEODRIVER=dummy`), sans captures.
- **Règle** : chaque bug confirmé par le reviewer ou le playtester reçoit un test qui échoue avant la correction et passe après.
- Un test par invariant du §8.
- `uv run pytest -q` doit passer avant de déclarer une étape finie.
