# Catalogue des animations de combat

Chaque action du combat a **sa propre chorégraphie**, identifiée par une **clé stable**. Ce document est la liste fermée de ces clés : `vfx-animator` les implémente, `pygame-coder` les déclenche, `audio-composer` fournit les sons cités (colonne Sons, noms de `docs/AUDIO.md`). Le contrat technique (`Choreography`, `ActionContext`, `Actor`, calques) se trouve dans `docs/ARCHITECTURE-GFX.md` §3.

Conventions : durée totale entre 0,8 et 2,5 s (les invocations : 4 à 7 s, et elles peuvent être passées avec Entrée), impact signalé par `ctx.on_impact(i)` **une fois par cible**, au moment exact du coup. Les couleurs viennent de `docs/DIRECTION-ARTISTIQUE.md`.

## 0. Les poses (planches de personnages)

Les héros, Sephiroth et Garland ont 8 poses (`docs/DIRECTION-ARTISTIQUE.md` §2 bis). Chaque chorégraphie les enchaîne avec `actor.set_pose(...)`, et les mouvements codés (élan, recul, saut) se superposent aux changements de pose. Sans planche, `set_pose` ne fait rien et l'animation reste celle du code.

| Moment | Pose |
|---|---|
| Repos, attente de l'ATB | `idle` (avec la respiration du code) |
| Jauge ATB pleine, menu ouvert sur ce héros, `action.defend` | `ready` |
| Élan d'une attaque ou d'une compétence physique | `windup` |
| Impact (au moment de `ctx.on_impact`) | `strike`, tenue 0,2 à 0,35 s |
| Sort, invocation, objet, compétence magique (Feu, Chakra) | `cast`, tenue pendant toute l'incantation |
| Le combattant encaisse un coup | `hurt`, tenue 0,3 s, puis retour à la pose de base |
| K.O. | `ko`, gardée jusqu'à la résurrection (`item.phoenix_down` → `hurt` puis `idle`) |
| Fin de combat gagné | `victory` (avec le saut du code) |

Les attaques à plusieurs coups (Omnislash, l'enchaînement du Moine, Lancer) alternent `windup` et `strike` à chaque coup.

## 1. Attaques de base (une par job)

| Clé | Chorégraphie | Sons |
|---|---|---|
| `attack.soldier` | Élan (`easeOutBack`), grand arc de taille vertical avec traînée blanche épaisse, impact + éclats, retour | `slash_heavy` |
| `attack.black_mage` | Petit pas, coup de bâton, petite gerbe d'étincelles rouges | `staff_hit` |
| `attack.knight` | Charge bouclier en avant, estoc avec trait lumineux bleu-blanc, anneau d'impact | `slash`, `impact` |
| `attack.monk` | Élan, enchaînement de 3 coups de poing rapides (3 impacts : anneaux + petit tremblement à chaque fois) ; la valeur est répartie sur les 3 chiffres | `punch` ×3 |
| `attack.thief` | Traversée éclair de la cible avec une image rémanente, entaille en X | `dagger` ×2 |
| `attack.samurai` | Disparition, une ligne horizontale fine traverse la cible, réapparition à sa place, puis la cible flashe **après** une courte pause | `katana_draw` |
| `attack.archer` | Reste en place, recul de l'arc, flèche projectile avec traînée qui suit une courbe | `arrow` |
| `attack.ninja` | Shuriken projectile qui tourne, avec traînée, puis revient dans la main | `shuriken` |
| `attack.monster` | Le monstre bondit vers le héros, trois griffures diagonales rouges | `claw` |

## 2. Compétences de job (`SKILL_NAME`)

| Clé | Compétence | Chorégraphie | Sons |
|---|---|---|---|
| `skill.soldier` | Omnislash | Saut, puis 5 frappes-éclair autour de la cible depuis des angles différents (images rémanentes cyan, une traînée par coup), coup final plongeant, gros tremblement + flash blanc de l'écran. Chiffre final en or | `slash` ×5, `slash_heavy` |
| `skill.black_mage` | Feu | Cercle magique rouge au sol sous le mage, puis colonne de flammes qui jaillit **sous** la cible (différente du sort Feu) | `cast`, `fire_pillar` |
| `skill.knight` | Brise-armure | L'épée se charge (lueur bleue qui grossit), frappe lourde, éclats de métal qui volent, texte « DÉF ↓ » bleu qui se brise | `charge`, `armor_break` |
| `skill.monk` | Chakra | Méditation (le moine flotte légèrement), anneau doré qui monte, particules de lotus qui volent vers l'allié, soin vert | `chakra`, `heal` |
| `skill.thief` | Vol | Ruée vers la cible, main tendue, pièces d'or qui jaillissent et volent vers le voleur, « +N gils » doré (et une icône de potion si l'objet est volé) | `dagger`, `coins` |
| `skill.samurai` | Lame bannie | L'écran s'assombrit, éclat sur la garde du katana, croissant rouge géant qui balaie l'écran, puis la ligne de coupe apparaît en retard et la cible se « fend » (deux moitiés décalées un instant) | `katana_draw`, `wind_slash` |
| `skill.archer` | Tir précis | Zoom léger + réticule qui se resserre sur la cible, ralenti, flèche chargée de lumière qui perce en rayon, chiffre critique | `charge`, `arrow_power` |
| `skill.ninja` | Lancer (tous) | Saut hors champ, pluie de shurikens tournoyants sur **tous** les ennemis, impacts en cascade | `shuriken` ×n |

## 3. Sorts (materias)

| Clé | Sort | Chorégraphie | Sons |
|---|---|---|---|
| `spell.fire` | Feu | Cercle magique, boule de feu tourbillonnante lancée en spirale, explosion de braises et lueur orange additive | `cast`, `fire` |
| `spell.ice` | Glace | Cristaux de glace qui se forment autour de la cible et se referment, puis volent en éclats, brume givrée | `cast`, `ice_form`, `ice_shatter` |
| `spell.thunder` | Foudre | L'écran s'assombrit, éclair ramifié (généré procéduralement, différent à chaque fois) qui tombe du haut, flash jaune, étincelles | `cast`, `thunder` |
| `spell.cure` | Soin | Spirales vertes qui montent autour de l'allié, étincelles, halo doux | `heal` |

## 4. Invocations (le grand spectacle, 4 à 7 s)

| Clé | Invocation | Chorégraphie | Sons |
|---|---|---|---|
| `summon.ifrit` | Ifrit (`summon_fire`) | L'interface se cache, l'écran vire au rouge sombre, le sol se fissure (lignes de lave), la créature surgit du bas dans un fondu-zoom, rugit (tremblement), et des météores de feu s'abattent sur chaque ennemi | `summon`, `roar`, `explosion` ×n |
| `summon.shiva` | Shiva (`summon_ice`) | Givre qui envahit les bords de l'écran, flocons, la déesse apparaît en fondu, lève les bras : des piliers de glace surgissent sous chaque ennemi, puis tout se brise en même temps (« poussière de diamant ») | `summon`, `ice_form`, `ice_shatter` |
| `summon.ramuh` | Ramuh (`summon_thunder`) | Nuages d'orage qui assombrissent le ciel, le sage apparaît, lève son bâton qui crépite, et un éclair du jugement géant frappe chaque ennemi, flash blanc | `summon`, `thunder` ×n, `thunder_big` |
| `summon.bahamut` | Bahamut (`summon_dragon_king`) | Écran noir, champ d'étoiles, le roi dragon descend du ciel, charge un orbe de lumière dans sa gueule (il grossit et aspire des particules), rayon « Méga Flare », énorme explosion blanche, long tremblement | `summon`, `charge_big`, `mega_flare` |

## 5. Objets, défense et états

| Clé | Chorégraphie | Sons |
|---|---|---|
| `item.potion` | Fiole lancée en l'air (icône), éclat, bulles vertes qui montent | `potion` |
| `item.ether` | Fiole, particules violettes et bleues, « +N PM » bleu | `potion` |
| `item.phoenix_down` | Plume qui descend en virevoltant, anneau de flammes douces, le héros se relève (fin de la pose K.O.) | `revive` |
| `item.elixir` | Fiole dorée, explosion d'étincelles arc-en-ciel, PV et PM au maximum | `elixir` |
| `action.defend` | Bulle hexagonale bleutée qui apparaît autour du héros et reste en léger scintillement jusqu'à son prochain tour | `defend` |
| `state.ko_monster` | Le monstre flashe en blanc puis se dissout en particules qui montent (fondu + dispersion) | `ko_monster` |
| `state.ko_hero` | Le héros s'agenouille (rotation + affaissement), teinte grise | `ko_hero` |
| `state.level_up` | Colonne de lumière dorée + « NIVEAU ! » | `level_up` |

## 6. Attaques spéciales des monstres (`Hit.action`)

L'interface associe le nom d'action (en français, dans `characters/bestiary.py`) à une clé. Une action inconnue → `attack.monster`.

| `Hit.action` | Clé | Chorégraphie | Sons |
|---|---|---|---|
| `attaque` | `attack.monster` | Voir §1 | `claw` |
| `Supernova` (Sephiroth) | `monster.supernova` | **Le clou du spectacle** : écran noir, champ d'étoiles qui défile, une étoile se contracte puis explose en onde blanche sur toute l'équipe, retour à l'image avec chiffres en cascade | `charge_big`, `supernova` |
| `Explosion` (Bombo) | `monster.explosion` | Le Bombo enfle et clignote de plus en plus vite, explosion orange, il disparaît | `charge`, `explosion` |
| `1000 épines` (Pampa) | `monster.needles` | Pluie d'aiguilles fines très rapides vers la cible, « 1000 » énorme | `needles` |
| `Mauvaise haleine` (Morbol) | `monster.bad_breath` | Nuage toxique vert-violet qui envahit l'écran depuis le monstre, bulles, teinte verdâtre sur l'équipe | `poison_gas` |
| `Souffle de feu` (Dragon rouge) | `monster.fire_breath` | Cône de flammes balayant toute l'équipe, distorsion de chaleur, braises | `flame_breath` |
