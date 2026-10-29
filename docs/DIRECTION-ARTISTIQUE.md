# Direction artistique — Final Classe (version pygame)

Document de référence partagé par **tous** les membres de l'équipe : Codex (images), `pygame-coder` (interface), `vfx-animator` (effets), `sonnet-reviewer` et `playtester` (contrôle).
Rien ne s'invente en dehors de ce document : un besoin nouveau → on l'ajoute ici d'abord.

## 1. Le style

**HD propre, inspiré des Final Fantasy modernes en 2D** : illustration numérique nette, cel-shading doux (aplats + dégradés subtils), contours fins et propres, couleurs saturées mais harmonieuses, lumière venant **d'en haut à gauche**. Fantasy héroïque, ton épique et lumineux.

**Interdit :** pixel art, rendu 3D/photoréaliste, croquis, aquarelle baveuse, flou, grain, texte ou lettres dans l'image, filigrane, cadre, signature.

**Préfixe de prompt commun** (ajouté automatiquement par le skill `gen-sprite`) :

> High-quality 2D JRPG game art in the style of modern Final Fantasy key art, clean crisp digital illustration, soft cel shading with subtle gradients, clean thin line art, vibrant harmonious colors, lighting from the upper left, sharp details, no text, no letters, no watermark, no frame, no signature.

**Personnages, monstres, invocations et lieux : fidèles aux originaux de Final Fantasy.** C'est un projet pédagogique non commercial (démonstration à des stagiaires). Le champ `ref` du manifeste nomme l'original (« Cloud Strife from Final Fantasy VII… »), et le champ `prompt` décrit précisément son apparence canonique, pour que la description suffise si Codex refuse le nom (relance avec `--no-ref`).

| Job du jeu | Personnage original |
|---|---|
| Soldat | Cloud Strife (FF VII) |
| Mage noir | Vivi Ornitier (FF IX) |
| Chevalier | Cecil Harvey en Paladin (FF IV) |
| Moine | Tifa Lockhart (FF VII) |
| Voleur | Zidane Tribal (FF IX) |
| Samouraï | Auron (FF X) |
| Archer | Fran (FF XII), en armure complète |

**Tenues des personnages féminins** (Fran, Tifa, Lulu, Shiva…) : elles restent fidèles mais **couvrantes** (manches, robe longue, armure complète), sans quoi le filtre de Codex refuse l'image. C'est arrivé avec Shiva.
| Ninja | Yuffie Kisaragi (FF VII) |

## 2. Les sprites (héros, monstres, invocations, icônes)

- **Un seul sujet, entier, centré**, rien de coupé (pieds, armes, ailes, queue compris), aucune ombre portée au sol, aucun décor.
- **Fond uni de la couleur clé** du manifeste (`#FF00FF` magenta par défaut, `#00FF00` vert **uniquement** pour les sujets violets ou roses : sur des cheveux fins ou clairs, le vert déteint et ne se rattrape pas, comme on l'a constaté avec Sephiroth), parfaitement plat, sans dégradé ni ombre : le script de post-traitement le rend transparent.
- **Orientation (vue de profil trois-quarts, style combat FF) :**
  - Les **héros** sont à **droite** de l'écran et **regardent vers la GAUCHE**.
  - Les **monstres** sont à **gauche** et **regardent vers la DROITE**.
  - Les **invocations** combattent pour les héros : elles **regardent vers la GAUCHE**, comme eux, vers les monstres.
  - Le code ne retourne jamais un sprite (les armes changeraient de main).
- **Pose** : posture de combat au repos, prête à l'action (le code anime : respiration, élan, recul).
- **Proportions des héros** : héroïques et stylisées, environ 6 têtes, même échelle pour les huit jobs.

## 2 bis. Les planches de poses (héros, Sephiroth, Garland)

Les assets qui ont un champ `sheet` dans le manifeste ont, en plus de leur sprite, une **planche de 8 poses** dessinée par Codex en une seule image (1536×1024, grille de 4 colonnes × 2 lignes, cases de 384×512) :

| Case | Pose | Description demandée |
|---|---|---|
| 1 | `idle` | Posture de combat au repos (la même que le sprite de référence) |
| 2 | `ready` | En garde, prêt à bondir, poids sur la jambe avant |
| 3 | `windup` | Arme ramenée en arrière, élan juste avant de frapper |
| 4 | `strike` | Coup porté à pleine extension, vers l'avant (gauche pour les héros, droite pour les boss ; pour les archers : la flèche vient de partir) |
| 5 | `cast` | Lance une magie ou une technique : main levée, concentration |
| 6 | `hurt` | Encaisse un coup : recule, buste penché en arrière, grimace |
| 7 | `ko` | À genou, épuisé, tête basse, arme au sol (boss : chancelle, vaincu) |
| 8 | `victory` | Pose de victoire emblématique (boss : pose arrogante et menaçante) |

Règles de la planche :
- **Exactement le même personnage** que l'image de référence fournie (tenue, couleurs, arme, proportions, style). Seule la pose change.
- **Même échelle dans les 8 cases** ; dans chaque ligne, les pieds sont sur la même ligne de sol.
- **Chaque pose tient entièrement dans sa case**, armes comprises, avec une marge. Aucune case ne déborde sur sa voisine.
- Même orientation que le sprite (héros vers la GAUCHE, boss vers la DROITE), même éclairage, fond uni de la couleur clé, **sans lignes de grille, sans numéros, sans texte**.

## 3. Les décors

- Paysage peint, **sans personnage ni créature**, format paysage, recadré en **1280×720**.
- **Le tiers inférieur est un sol dégagé et lisible** (c'est là que se tiennent les combattants) ; le détail et la profondeur vont dans les deux tiers supérieurs.
- Contraste modéré : les sprites doivent ressortir devant.

## 4. L'interface (dessinée par le code, pas par Codex)

Fenêtres façon FF classique, nettes à toute résolution :

| Élément | Valeur |
|---|---|
| Fond de fenêtre | dégradé vertical `#24358C` → `#0B1440`, opacité 92 % |
| Bordure | 2 px `#E8ECF8`, coins arrondis 10 px, liseré intérieur 1 px `#6F80C8` |
| Texte | `#FFFFFF`, ombre 2 px `#000000` à 60 % |
| Texte secondaire | `#A9B4D8` |
| Accent / sélection / or | `#F2C14E` |
| PV | `#4ADE80` (passe à `#F2C14E` sous 50 %, `#EF4444` sous 25 %) |
| PM | `#60A5FA` |
| Jauge ATB | `#E8ECF8`, pleine : `#F2C14E` qui pulse |
| Dégâts | blanc ; critique / faiblesse : `#F2C14E` plus grand |
| Soin | `#4ADE80` |
| Feu / Glace / Foudre / Sacré | `#FF6B2D` / `#7FD8FF` / `#FFE94A` / `#C8A2FF` |

- **Résolution logique** 1280×720, mise à l'échelle avec bandes noires si la fenêtre a un autre ratio.
- **Polices** : `pygame.font.SysFont` avec repli dans l'ordre `["Segoe UI Semibold", "Segoe UI", "Trebuchet MS", "Arial"]` ; titres en `Georgia`/`Cambria`. Toujours tester les accents (é, è, à, ï, ★).
- Le titre « FINAL CLASSE » est **rendu par le code** (texte + dégradé + éclat), jamais dans une image.
- Le curseur est la main gantée `ui_cursor` qui oscille horizontalement.

## 5. Les animations (signature visuelle)

Toutes calculées par le code, indépendantes du nombre d'images par seconde (`dt`) :

- **Repos** : respiration (léger étirement vertical ±2 %), lévitation sinusoïdale pour les monstres volants (`floating` dans le manifeste).
- **Attaque** : élan vers la cible avec une interpolation `easeOutBack`, impact, retour.
- **Impact** : flash blanc du sprite (2 images), recul, tremblement de l'écran proportionnel aux dégâts, chiffres de dégâts qui rebondissent puis s'estompent.
- **Magie** : particules par élément (braises, cristaux de glace, éclairs ramifiés), halo additif.
- **Invocation** : écran assombri, splash art de l'invocation qui entre en fondu-zoom, puis vague d'énergie.
- **K.O.** : le monstre se dissout (fondu + particules) ; le héros s'agenouille (rotation + teinte grise).
- **Transitions** : spirale/éclats de verre façon FF à l'entrée d'un combat, fondu au noir entre les scènes.
- **Victoire** : héros en pose de victoire (petit saut), décompte de l'XP et des gils, bannière dorée.
