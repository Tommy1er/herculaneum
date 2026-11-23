# H001 — Détection d'encre par méthodes légères

**Statut :** protocole révisé (T05), en relecture. T06 fournira les données.

## Question

Sur un fragment dont l'encre est connue, quelle performance atteignent des méthodes de traitement d'image classiques, sans apprentissage profond, comparées à des références naïves ?

## Hypothèse

Les méthodes classiques obtiendront des scores faibles (l'encre carbonée contraste peu avec le papyrus). L'expérience mesure cet écart ; elle ne présume pas battre les modèles actuels.

## Données (à préciser à T06)

- Un fragment avec masque d'encre de référence.
- Un petit sous-volume autour de la surface du papyrus (quelques dizaines de couches).
- Noter : identifiant du fragment, résolution, couches utilisées, source exacte (URL S3), date de téléchargement.

## Découpage

- Le fragment est découpé en tuiles ; les tuiles sont réparties en **réglage** et **test** par bandes spatiales (`herculaneum.tiles.spatial_split`), avec une marge de séparation pour éviter que des pixels voisins se retrouvent des deux côtés.
- Tous les paramètres (seuils, couches, tailles de filtres) sont choisis **uniquement** sur les tuiles de réglage.
- Les tuiles de test ne sont évaluées qu'**une fois**, à la fin.

Avant d’examiner les annotations de test, enregistrer l’origine du recadrage (x, y, z), ses dimensions, l’ordre des axes, la correspondance entre couches et masques, et les sommes SHA-256 des entrées. Choisir l’extrait et l’orientation de la bande par une règle géométrique indépendante de la présence d’encre. Vérifier l’alignement sur le réglage.

Fixer les arguments de `spatial_split` (taille de tuile, axe, fraction de test, marge en pixels) et sauvegarder les rectangles obtenus. La fonction écarte les tuiles partielles et applique la marge de chaque côté de la frontière. Vérifier que les deux ensembles contiennent des pixels évaluables. Publier leur effectif réel.

Pour chaque méthode, déterminer le rayon maximal de contexte en x/y, filtres successifs compris. Utiliser une marge positive au moins égale au plus grand rayon des méthodes pour que les pixels bruts lus de part et d’autre soient disjoints. Si un traitement a une portée globale, l’exécuter séparément par zone. Estimer les paramètres de normalisation sur le réglage et les figer pour le test.

## Méthodes

| Code | Méthode | Responsable |
|------|---------|-------------|
| B0 | Tout « pas encre » / tout « encre » | Claude |
| B1 | Seuil global sur l'intensité moyenne des couches | Claude |
| C1 | Contraste local + seuil sur plusieurs profondeurs | Claude |
| Q1 | Méthode indépendante proposée par Qwen | Qwen |

Avant le test, consigner pour B1, C1 et Q1 les couches, polarités, seuils et autres paramètres candidats. Choisir la configuration qui maximise F0.5 sur le réglage. En cas d’égalité, retenir la première dans l’ordre consigné. Si le réglage ne contient aucune encre annotée, suspendre la sélection. Geler toutes les configurations avant de révéler un seul score de test.

## Mesures

Évaluer toutes les méthodes sur les mêmes pixels annotés et valides de papyrus. Distinguer le fond, les pixels non annotés et l’absence d’encre. Vérifier l’encodage avant conversion en booléen. Sans masque du support, utiliser une région documentée entièrement sur papyrus avec annotation exhaustive, ou différer le score principal.

Cumuler VP, FP, FN et VN sur ces pixels, puis calculer précision, rappel, F1 et F0.5 avec `herculaneum.metrics.binary_scores` (un seul appel sur le masque d’évaluation complet convient). Une moyenne des scores par tuile donnerait un autre résultat. Publier les quatre effectifs, la prévalence et les deux B0 séparément. La fonction renvoie zéro pour un dénominateur nul : signaler ce cas. Si le test est vide, aucun score ; s’il est dépourvu d’encre, le signaler et ne pas conclure sur la capacité de détection.

Contrôle arithmétique : avec 20 pixels d’encre parmi 100 valides, « tout encre » donne VP=20, FP=80, FN=VN=0, précision=0,20, rappel=1 et F0.5≈0,2381.

## Résultats

Dans `results/` : un fichier par méthode, avec la commande exacte, le hash git du code, les versions des dépendances, les paramètres retenus, la graine si nécessaire, le manifeste des données et du découpage, et les scores. L’écart de F0.5 avec B1 décrit cette bande de ce fragment. Toute adaptation inspirée du test exige une nouvelle région réservée pour une évaluation indépendante.
