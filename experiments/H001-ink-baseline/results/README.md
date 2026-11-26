# H001 — résultats sur données réelles (2026-11-26)

## En une phrase

Sur un extrait réel de PHerc. Paris 4, un simple seuil sur la luminosité moyenne des couches (B1) fait **à peine mieux** que de déclarer « encre » partout (F0.5 = 0,234 contre 0,212), et le contraste local (C1) **n'apporte rien**. C'est le résultat négatif attendu pour une encre au carbone : les méthodes classiques ne suffisent pas, ce qui justifie l'apprentissage automatique.

## Données (T06)

| Élément | Valeur |
|---------|--------|
| Rouleau / segment | PHerc. Paris 4, `w00_20231016151002` ([tutoriel officiel](https://scrollprize.org/tutorial5)) |
| Source | `hf://buckets/scrollprize/datasets/ink/phercparis4/w00_20231016151002` (zarr, niveau 0) |
| Fenêtre | lignes 3 584–5 632, colonnes 24 192–27 264, les 65 couches (2 048 × 3 072 pixels) |
| Règle de choix | première fenêtre alignée sur les blocs de 128 px, en ordre ligne par ligne, avec une couverture maximale du masque de supervision (100 %). **Les étiquettes d'encre n'ont pas servi.** Une première recherche qui filtrait sur la proportion d'encre a été écartée pour cette raison. |
| Étiquettes | stockées sur la couche 32 seulement (vérifié par le script) ; 255 = encre, 0 = pas d'encre, utilisable seulement où la supervision vaut 255 |
| Provenance | annotations issues du travail de lecture de ce rouleau ; aucun masque de validation séparé n'est fourni |
| Détails, sommes SHA-256 | [`data-manifest.json`](data-manifest.json) |

Récupérer la même fenêtre (≈ 300 Mo, fonctionne sur le Lenovo) :

```
python scripts/fetch_crop.py --y0 3584 --x0 24192 --height 2048 --width 3072 --out data/phercparis4_w00_y3584_x24192.npz
```

## Contrôle de superposition (réglage uniquement)

[`alignment_tune.png`](alignment_tune.png), [`alignment_tune_zoom.png`](alignment_tune_zoom.png).
Les étiquettes sont de **grands contours lisses** (zones de lettres, pas des traits), et l'encre est invisible à l'œil dans le scanner. Le contrôle visuel **ne peut donc pas confirmer** l'alignement ; il exclut seulement un décalage grossier. Les étiquettes et le volume partagent la même grille zarr, sans transformation.

## Découpage et gel

- `spatial_split` : tuiles de 128 px, bande de test à droite (25 % des colonnes), marge de 32 px de chaque côté de la frontière (rayon maximal de C1 : 3 × 8 = 24 px).
- Réglage : 272 tuiles, prévalence de l'encre 21,6 %. Test : 80 tuiles, 1 310 720 pixels, prévalence 17,8 %.
- 40 configurations candidates listées dans l'ordre (5 fenêtres de couches × 2 polarités pour B1 ; × 3 tailles de filtre pour C1), seuil choisi parmi les centiles 1 à 99 des scores de réglage, critère F0.5 sur le réglage.
- Configurations gelées dans [`frozen.json`](frozen.json), **commit `ac373c4`, avant tout score de test**. Le test a été évalué une seule fois ensuite.

## Scores sur le test

| Méthode | Configuration retenue | Précision | Rappel | F1 | F0.5 |
|---------|-----------------------|----------:|-------:|---:|-----:|
| B0 tout « pas encre » | — | 0 | 0 | 0 | 0 |
| B0 tout « encre » | — | 0,178 | 1,000 | 0,301 | 0,212 |
| **B1** seuil global | couches 24–40, encre plus sombre | **0,198** | 0,842 | 0,321 | **0,234** |
| C1 contraste local | couches 30–34, σ = 8, encre plus claire | 0,178 | 0,992 | 0,302 | 0,213 |

Effectifs complets (VP, FP, FN, VN) : [`scores.json`](scores.json). B0 « pas encre » n'a aucune prédiction positive : sa précision vaut 0 par convention (dénominateur nul).

## Lecture

- B1 marque encore 84 % des pixels comme encre : il est proche de « tout encre ». Sa précision dépasse la prévalence de 2 points, donc il contient un **faible** signal (encre légèrement plus sombre en moyenne sur les couches 24–40).
- C1 choisit un seuil qui déclare presque tout « encre » : aucun signal utile.
- Ces chiffres décrivent **cette bande de ce fragment** ; ils ne se généralisent pas.
- Le critère F0.5 avec des seuils au centile pousse vers « presque tout encre » quand la méthode est faible. C'est un constat sur le protocole, pas une raison de modifier ce résultat : toute variante doit être évaluée sur une **nouvelle** région réservée.

## Reproduire

```
cd experiments/H001-ink-baseline
python run_h001.py freeze   --data ../../data/phercparis4_w00_y3584_x24192.npz --out results/frozen.json
python run_h001.py evaluate --data ../../data/phercparis4_w00_y3584_x24192.npz --frozen results/frozen.json --out results/scores.json
```

Environnement : Linux, Python 3.12, numpy/scipy selon `frozen.json`.
