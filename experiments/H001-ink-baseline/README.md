# H001 — Détection d'encre par méthodes légères

**Statut :** protocole proposé par Claude, à valider par ChatGPT (T05).

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

## Méthodes

| Code | Méthode | Responsable |
|------|---------|-------------|
| B0 | Tout « pas encre » / tout « encre » | Claude |
| B1 | Seuil global sur l'intensité moyenne des couches | Claude |
| C1 | Contraste local + seuil sur plusieurs profondeurs | Claude |
| Q1 | Méthode indépendante proposée par Qwen | Qwen |

## Mesures

Précision, rappel, F1 et F0.5 (`herculaneum.metrics`), calculés pixel par pixel sur les tuiles de test, en ignorant les pixels hors papyrus si un masque de papyrus est disponible.

## Résultats

Dans `results/` : un fichier par méthode, avec la commande exacte, le hash git du code et les scores.
