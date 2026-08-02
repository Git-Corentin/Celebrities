# Soludoku

Jeu de sudoku et solveur, en Python 3 et tkinter.
Version 1 : Corentin Nicodème, 28/02/2020 — réorganisation : 2026.

## Installation

Le code ne dépend que de la bibliothèque standard, mais tkinter n'est pas
toujours installé avec Python sous Linux :

```bash
sudo apt install python3-tk      # Debian / Ubuntu
```

## Lancement

```bash
python3 main.py          # depuis n'importe quel répertoire
```

Les tests (sans interface graphique) :

```bash
python3 -m unittest discover -s tests -v
```

## Organisation du code

| Fichier | Rôle |
| --- | --- |
| `main.py` | point d'entrée |
| `soludoku/config.py` | chemins, couleurs, polices, géométrie |
| `soludoku/modele/regles.py` | lignes, colonnes, carrés, voisins, conflits |
| `soludoku/modele/grille.py` | classe `Grille` : l'état d'une partie |
| `soludoku/modele/solveur.py` | résolution par retour sur trace |
| `soludoku/modele/generateur.py` | les cinq grilles et leur brassage |
| `soludoku/modele/sauvegarde.py` | lecture et écriture de `Grille.txt` |
| `soludoku/interface/application.py` | fenêtre principale et navigation |
| `soludoku/interface/page.py` | classe de base des pages |
| `soludoku/interface/page_accueil.py` | écran d'accueil |
| `soludoku/interface/page_jeu.py` | la partie |
| `soludoku/interface/page_solveur.py` | le solveur |
| `soludoku/interface/vue_grille.py` | le canevas de la grille |
| `soludoku/interface/widgets.py` | sélecteur de chiffres, boutons |
| `soludoku/interface/ressources.py` | chargement des images |

Le dossier `modele/` n'importe jamais tkinter : toute la logique du jeu est
testable sans écran, et c'est ce qui permet aux 29 tests du modèle de tourner
en moins d'une seconde.

## Une grille en mémoire

Les quatre listes globales de la v1 (`grille_depart`, `grille_finie`,
`grille`, `grille_test`) sont réunies dans la classe `Grille` :

```python
grille.depart      # l'énoncé, immuable
grille.solution    # la solution complète
grille.valeurs     # ce qui est écrit à l'écran
grille.brouillon   # les indices écrits au crayon gris
```

Une case vide vaut `0` et non `''`, ce qui évite d'avoir à mélanger chaînes et
entiers dans la même liste. Le crayon gris est un **ensemble d'indices** et non
une cinquième grille de chiffres dupliqués : les deux ne peuvent plus se
désynchroniser.

### Améliorations

* **Brassage des chiffres.** La v1 permutait lignes, colonnes, blocs et
  rotations, mais jamais les chiffres eux-mêmes : une grille déjà vue se
  reconnaissait tout de suite. Avec la permutation des neuf chiffres, chaque
  niveau offre 9! × 3!⁸ × 2 présentations différentes.
* **Solveur plus bavard.** Il distingue une grille sans solution d'une grille
  à solutions multiples, surligne les doublons de la saisie, et affiche en
  bleu les chiffres qu'il a trouvés — les tiens restent en noir.
* **Images manquantes tolérées.** Si un PNG est introuvable, le chiffre est
  dessiné en texte de la bonne couleur au lieu de faire planter le programme.
* **Case survolée en surbrillance**, pour viser plus facilement.

## Pistes pour la suite

* Générer des grilles à la volée : avec `solveur.solution_unique()`, il suffit
  de partir d'une grille complète tirée au hasard
  (`solveur.grille_complete_aleatoire()`) et de retirer des cases tant que la
  solution reste unique.
* Mesurer la difficulté réelle (nombre de techniques nécessaires) plutôt que
  de se fier au nombre d'indices.
* Proposer un indice : `regles.possibilites(valeurs, case)` donne déjà les
  candidats d'une case.
