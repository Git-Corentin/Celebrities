# Rubik'solution

Solveur de Rubik's cube 3×3 avec interface graphique, écrit par Corentin
Nicodème en 2019 et restructuré depuis.

Le programme demande les six faces du cube, calcule une résolution par la
méthode CFOP, raccourcit la suite obtenue, puis la présente mouvement par
mouvement — sous forme de flèches ou en notation.

## Lancement

```
python3 main.py
```

Seul `tkinter` est indispensable. Sous Debian ou Ubuntu :

```
sudo apt install python3-tk
```

Deux modules facultatifs :

| Module | Apport | En son absence |
|---|---|---|
| `Pillow` | mise à l'échelle exacte des images, aperçu de la webcam | facteurs entiers, PNG et GIF seulement ; pas de webcam |
| `opencv-python` | lecture des couleurs à la webcam | le mode webcam est signalé indisponible |
| `RubikTwoPhase` | option « Résolution optimale » | seule la méthode CFOP est proposée |

```
pip install Pillow opencv-python RubikTwoPhase
```

Le dossier `Images Rubik's/` et le dossier `Mémoire Rubik's/` se placent à côté
de `main.py`. Les noms de fichiers sont retrouvés quelle que soit leur
orthographe — apostrophes, espaces ou tirets bas.

## Organisation

```
main.py                     point d'entrée
rubiksolution/
    config.py               réglages, chemins, échelle de l'écran
    ressources.py           chargement des images et des icônes
    preferences.py          lecture et écriture de « Mémoire Rubik's »
    cube/
        permutations.py     les six permutations élémentaires
        etat.py             la classe Cube, les pièces et leurs emplacements
        algorithmes.py      F2L, OLL, PLL, motifs, tables de reconnaissance
        solveur.py          la résolution CFOP
        optimal.py          la résolution courte, par algorithme deux phases
        optimisation.py     raccourcissement de la suite de mouvements
        notation.py         traduction vers les quatre notations
    vision/webcam.py        détection des couleurs
    ui/                     les écrans et les fenêtres
tests/
    test_cube.py            moteur, solveur, optimiseur, notation
    test_vision.py          reconnaissance des couleurs, format international
    test_interface.py       parcours complet de l'interface
```

Le paquet `cube` ne dépend ni de `tkinter` ni d'`opencv` : il s'utilise seul.

```python
from rubiksolution.cube.etat import Cube
from rubiksolution.cube.solveur import resoudre
from rubiksolution.cube.optimisation import optimiser

cube = Cube().jouer_suite("R U R' U' F2 B L D".split())
print(optimiser(resoudre(cube)))
```

## Tests

```
python3 tests/test_cube.py
python3 tests/test_vision.py
python3 tests/test_interface.py                 # avec écran
xvfb-run -a python3 tests/test_interface.py     # sans écran
```

Soixante-trois tests, moins de deux secondes.

## Représentation du cube

Les 54 stickers sont rangés dans un repère fixe, neuf par face, dans l'ordre
blanche, jaune, bleue, rouge, verte, orange. Chaque face est numérotée de 0 à 8,
de gauche à droite puis de haut en bas.

Le joueur, lui, tient le cube face à l'une des quatre faces latérales : c'est
l'attribut `repere`, un entier de 0 à 3. `U` et `D` ne dépendent pas de cette
orientation, mais `F`, `R`, `B` et `L` désignent une face physique différente
selon l'endroit où l'on se place.

La tranche horizontale `E` est réalisée comme `U' D` suivi d'un changement de
repère — c'est la convention retenue en 2019, et c'est elle qui donne les
flèches affichées à l'écran. Elle est exacte : `U' D` équivaut bien à `E` suivie
d'une rotation du cube entier, que le changement de repère compense.

## Les deux méthodes de résolution

La résolution optimale est proposée d'office — sauf si son module n'est pas
installé, auquel cas le programme se rabat sans rien dire sur la méthode
d'origine.

Chaque méthode ramène le point de départ sur le réglage qui lui convient : la
méthode humaine commence par la croix blanche et gagne à la recevoir toute
faite, l'autre s'en moque. L'avertissement sur la croix non optimisée
n'apparaît donc que là où il a un sens.

La méthode CFOP d'origine reproduit ce qu'un humain apprend et sait refaire :
la croix, les paires, l'orientation, la permutation. Elle donne une centaine de
mouvements, ramenés à environ soixante-quinze après raccourcissement, et chaque
étape a un sens.

L'algorithme deux phases en donne une vingtaine, mais la suite obtenue n'a
aucune logique visible : elle ne s'explique pas, elle s'exécute. Le choix se
fait dans les paramètres.

Le premier calcul optimal construit des tables de recherche — plusieurs
minutes, une seule fois. Elles sont rangées dans le dossier de cache de
l'utilisateur, et non dans le répertoire courant comme le fait le paquet par
défaut : elles seraient sinon reconstruites à chaque changement de dossier.

## La reconnaissance des couleurs

La version d'origine décidait sticker par sticker, en comparant la teinte à des
plages fixes. C'est fragile : un cube montré face à l'écran reçoit des reflets
et des ombres très inégaux.

Le programme n'analyse plus rien pendant la capture. Il enregistre les 54
mesures brutes, puis les classe toutes ensemble, en s'appuyant sur trois choses
sûres :

- **le centre de chaque face donne sa propre référence**, photographiée sous
  exactement le même éclairage que les huit gommettes qui l'entourent ;
- **chaque couleur apparaît exactement neuf fois**, ce qui fait de la
  classification une affectation sous contrainte plutôt que six décisions
  indépendantes : une gommette douteuse est tranchée par le fait que sa couleur
  la plus probable a déjà ses neuf représentants ;
- **la luminosité ne porte aucune information** : chaque mesure est projetée
  sur un plan teinte × saturation, où un reflet et une ombre sur la même
  gommette se retrouvent au même endroit.

L'affectation optimale est calculée exactement, par flot de coût minimal, en
quelques millisecondes. Sur des mesures simulées avec gain par face, dégradé
d'éclairage, reflets et bruit de capteur :

| Perturbation | Gommettes justes | Cubes parfaits |
|---|---|---|
| modérée | 99,7 % | 39/40 |
| forte | 97,9 % | 25/40 |

Si le cube lu reste incohérent, la lecture s'affiche quand même dans l'écran de
saisie, accompagnée du message d'erreur : il suffit de corriger les cases
douteuses à la main.

## Ce qui a changé depuis la version de 2019

La logique de résolution est **identique**. Elle a été vérifiée par test
différentiel : sur 800 mélanges de longueurs variées, l'ancien et le nouveau
solveur produisent exactement la même suite de mouvements.

Ce qui a changé, c'est la forme et quelques défauts :

**Structure.** Un fichier de 5 514 lignes est devenu une vingtaine de modules.
Les 1 820 lignes des douze fonctions de mouvement se réduisent à six
permutations en notation par cycles, extraites automatiquement de l'ancien code
puis vérifiées sticker par sticker. Le suivi des pièces, qui était maintenu à la
main par quatre boucles dans chacune de ces fonctions, est recalculé depuis
l'état du cube. Les quatre blocs de F2L recopiés à la main deviennent une
fonction paramétrée par l'orientation ; les vingt fonctions de sauvegarde et les
six fonctions de choix de couleur deviennent des boucles.

**Corrections.**

- `test_position` écrivait `erreur = 1` au lieu de `erreurs = 1` : les erreurs de
  placement des coins n'étaient jamais signalées.
- `verifier_f2l` testait deux fois `fb[7]` et jamais `fb[8]`.
- La boucle finale de `resoudre_pll` comptait jusqu'à cinq sans jamais tourner
  la face du haut : un dernier ajustement nécessaire aurait été déclaré
  impossible.
- Le dictionnaire des teintes de la webcam contenait deux fois la clé `rouge`,
  ce qui faisait perdre la première plage.
- Le tirage du mélange comparait le dernier mouvement à `liste[-2]`, donc à
  lui-même tant que la liste n'avait qu'un élément.
- Le chronomètre remettait son origine à zéro à l'arrêt et perdait le temps
  écoulé.
- `iconbitmap` avec un fichier `.ico` et `wm_state('zoomed')` n'existent que sous
  Windows : ils faisaient échouer le démarrage sous Linux. `cv2.CAP_DSHOW`, de
  même, pour la webcam.
- Le découpage des fichiers de sauvegarde se faisait par tranches de caractères
  codées en dur, ce qui cassait dès qu'une couleur s'écrivait sur trois chiffres.
- Les chemins étaient relatifs au répertoire courant.
- Les mouvements ajoutaient leur nom à la liste de résolution, y compris pendant
  le rejeu de l'affichage, qui gonflait donc la liste indéfiniment.
- Le retour en arrière appelait trois fois de suite la fonction d'affichage pour
  retomber sur ses pieds ; les états intermédiaires sont maintenant calculés une
  fois pour toutes.
- La soixantaine de `try: … except: pass` masquait les vraies erreurs. Les cas
  attendus sont traités explicitement, et une image manquante donne un bouton
  texte au lieu de faire tomber la fenêtre.
- La fenêtre de la webcam n'avait pas le focus : il fallait cliquer dedans pour
  que la barre d'espace réponde. L'aperçu est maintenant affiché dans une
  fenêtre tkinter, ce qui règle aussi l'erreur `NULL guiReceiver` que
  provoquait `getWindowProperty` sur une fenêtre déjà fermée.
- Le repérage de la webcam réutilisait la liste des centres rangée en haut,
  gauche, bas, droite pour la dessiner en haut, droite, bas, gauche : la gauche
  et la droite s'y trouvaient inversées par rapport au patron affiché partout
  ailleurs. OpenCV ne renverse pas l'image ; l'ordre est rétabli.
- Une face mal lue obligeait à recommencer les six : le retour arrière permet
  maintenant de refaire la précédente.
- Rouvrir la webcam après l'avoir fermée échouait sur `grab failed: window not
  viewable` : la saisie exclusive du clavier était demandée avant que le
  gestionnaire de fenêtres ait présenté la fenêtre. Elle est maintenant
  réclamée en différé, et plusieurs fois s'il le faut.
- Le plein écran ne prenait pas toujours au démarrage : l'attribut `-zoomed`
  ne signale rien quand il échoue. Le résultat est vérifié, et la taille de
  l'écran imposée à défaut. L'accueil est également passé en plein écran, et
  ses éléments centrés verticalement dans une grille plutôt qu'empilés en haut.
- La fenêtre des paramètres pouvait afficher un fond corrompu : le canevas qui
  porte l'illustration était redimensionné après y avoir déjà dessiné l'image.
  Les boutons radio suivent `config.ECHELLE` (liée à la hauteur de l'écran),
  un facteur indépendant de celui propre à cette fenêtre ; une mesure de texte
  à taille fixe sous-estimait leur largeur réelle sur certains écrans, ce qui
  déclenchait ce redimensionnement tardif. Tout est maintenant mesuré avec la
  police réellement utilisée avant de dessiner quoi que ce soit : le canevas
  est créé directement à sa taille finale. Vérifié sur seize résolutions
  d'écran, de 800×600 à la 4K, à plusieurs valeurs de `config.ECHELLE`.
- Le bouton « + » (Fonctions supplémentaires) ne trouvait jamais son image :
  le fichier avait perdu son caractère `+` lors d'un transfert (`_png` au lieu
  de `+.png`). Un alias le retrouve désormais.
- La grille de réglages recouvrait le titre « Infos » de l'illustration. Ce
  canevas est opaque : haut de 280 px en 2019, il s'arrêtait juste au-dessus du
  titre ; agrandi, il le masquait. La cause profonde : les boutons radio
  suivaient `config.ECHELLE`, un facteur global lié à la hauteur de l'écran,
  alors que l'illustration et les boutons posés dessus suivaient le facteur
  propre à la fenêtre. Deux échelles indépendantes gouvernaient la même mise en
  page, et divergeaient dès que l'écran était large et court. Toute la fenêtre
  n'obéit plus qu'à un seul facteur, celui de l'illustration ; un test vérifie
  d'ailleurs que `config.ECHELLE` n'a plus aucun effet sur elle.
- La fenêtre laissait une mince bande grise entre l'image de fond et son bord,
  et pouvait aussi légèrement déborder selon l'écran. `REFERENCE_COMPLETE` et
  `REFERENCE_REDUITE` — les dimensions supposées des deux fichiers JPEG —
  étaient des valeurs approchées (1275×630) plutôt que les dimensions réelles
  (1288×644, dans un rapport exactement 2:1) : un écart de rapport d'aspect
  suffisant pour que la largeur réellement obtenue après redimensionnement ne
  corresponde plus tout à fait à la largeur attendue. Les constantes portent
  maintenant les dimensions exactes des fichiers, et le canevas se cale de
  toute façon sur la largeur réellement chargée plutôt que sur un calcul
  théorique — deux filets de sécurité plutôt qu'un.
- Le choix de la méthode de résolution, ajouté dans un bandeau sous
  l'illustration, a rejoint la grille de réglages elle-même : plus d'étiquette
  « Méthode de résolution : », juste les deux boutons, sur la dernière ligne
  d'une grille à cinq lignes pleines (croix, langue, explication, style,
  méthode) — sans plus aucune ligne vide d'espacement.

**Affichage.** Les widgets étaient placés à des coordonnées fixes multipliées
par le rapport entre l'écran et un écran de référence de 1366 × 768, ce qui
décalait la mise en page dès que les proportions changeaient. Les écrans sont
maintenant construits en grille : le cube reste centré, le dessin suit la taille
de la fenêtre et les polices s'adaptent à la hauteur de l'écran.

Deux exceptions assumées. La fenêtre des paramètres garde ses coordonnées
absolues, parce que sa mise en page est portée par une image de fond qui
contient les titres des sections ; elle est simplement réduite d'un même facteur
si l'écran ne suffit pas. Et les flèches de la résolution sont posées à leur
taille naturelle sur un carré de 500 pixels, comme à l'origine : elles sont donc
toutes mises à l'échelle par un seul et même facteur, ce qui conserve leurs
proportions relatives — une flèche de tour couvre la face entière, une flèche de
colonne n'en couvre qu'un tiers.

Les boutons inactifs sont estompés. L'état `disabled` de tkinter ne change que
la couleur du texte, ce qui se remarquait à peine sur un fond vif. Le liseré
clair que tkinter dessine autour de chaque bouton est supprimé d'un seul
réglage, par la base d'options de Tk.

Dans la saisie des couleurs, les flèches gauche et droite du clavier font la
même chose que les deux boutons de navigation — et ne font rien lorsque
ceux-ci sont inaccessibles.

La fenêtre des paramètres se dimensionne sur son contenu : les libellés des
boutons radio sont plus larges que la zone prévue par les coordonnées de 2019,
et leur largeur dépend de la police du système. Le choix de la méthode de
résolution est posé dans un bandeau sous l'illustration, dont les titres de
section occupent déjà toute la hauteur.
