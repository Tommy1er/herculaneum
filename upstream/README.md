# Veille sur `ScrollPrize/villa` (voie B)

Dépôt officiel : https://github.com/ScrollPrize/villa — liste des issues : https://github.com/ScrollPrize/villa/issues

## Critères pour choisir une issue

1. **Faisable sans GPU**, idéalement en Python, reproductible sur un petit jeu de données ou par un test unitaire.
2. **Libre** : pas de PR ouverte, l'auteur ne dit pas qu'il s'en occupe, personne d'assigné.
3. **Utile** : touche un outil réellement utilisé (déroulement, rendu, détection d'encre), pas un audit isolé.
4. **Livrable** = correction + test + description courte.

## Issues suivies

| # | Sujet | Ouverte | Pourquoi elle nous intéresse | Statut pour nous |
|---|-------|---------|------------------------------|------------------|
| [2458](https://github.com/ScrollPrize/villa/issues/2458) | Deux configs `lasagna` placent `tifxyz-flow-gate-channels` dans `base` au lieu de `args` | 2026-11-06, addisonflay | Modèle du bon type de contribution : bug concret, sans GPU, testable | **Exclue** — PR [#2463](https://github.com/ScrollPrize/villa/pull/2463) ouverte, avec tests, vérifiée par un autre contributeur (ChatGPT, 2026-11-23) |
| [2105](https://github.com/ScrollPrize/villa/issues/2105) | Erreur dans un README | — | — | **Exclue** — PR #2454 déjà ouverte (ChatGPT, 2026-11-23) |
| [2522](https://github.com/ScrollPrize/villa/issues/2522) | Optimisation CPU | — | — | **Exclue** — PR #2521 déjà ouverte (ChatGPT, 2026-11-23) |
| [2482](https://github.com/ScrollPrize/villa/issues/2482) | Un masque contenant des valeurs intermédiaires est interprété différemment par le code C++ et par sa documentation | — | Testable avec de petites données synthétiques, sans GPU | **À examiner en priorité** — aucune correction repérée ; comportement attendu à faire préciser par les mainteneurs (ChatGPT, 2026-11-23) |
| [2478](https://github.com/ScrollPrize/villa/issues/2478) | Estimer le volume à télécharger avant un rendu | — | Utile, sans GPU | **À suivre** — proposition en attente d'avis des mainteneurs (ChatGPT, 2026-11-23) |

## Anciennes candidates à vérifier (T09)

Relevé partiel de la page des issues le 2026-11-23 : la page lue ne montrait que des issues de septembre 2026, sans commentaires ni PR liées. **Chaque ligne doit être vérifiée à la main** (toujours ouverte ? PR existante ? quelqu'un dessus ?) avant d'y travailler.

| # | Sujet (résumé) | Intérêt pour nous |
|---|----------------|-------------------|
| [1776](https://github.com/ScrollPrize/villa/issues/1776) | `normal_grid_level` ignoré pour les stores à une seule échelle | Probablement testable avec un petit store synthétique |
| [1839](https://github.com/ScrollPrize/villa/issues/1839) | VC3D : la boîte « Attach Segments » échoue sur les chemins réseau (UNC) | Bug Windows — notre machine est sous Windows |
| [1846](https://github.com/ScrollPrize/villa/issues/1846) | Un échec de téléchargement d'un bloc distant au point de départ interrompt la croissance | Robustesse réseau, testable en simulant l'échec |
| [1809](https://github.com/ScrollPrize/villa/issues/1809) | `vc_render_tifxyz` plante (SIGABRT) sur un échec de téléchargement d'un bloc distant | Même famille que 1846 |
| [1765](https://github.com/ScrollPrize/villa/issues/1765) | Le README d'`optimized_inference` recommande une fenêtre de 62 couches décentrée | Petit, mais documentation seulement |

Issues écartées d'office : celles qui demandent un GPU, un Mac (ex. 1814, MPS) ou un jugement de papyrologue.
