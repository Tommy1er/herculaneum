# Tâches

Une ligne = un livrable vérifiable. Statuts : `à faire`, `en cours`, `en relecture`, `fait`, `abandonné`.

| ID | Tâche | Responsable | Livrable | Statut |
|----|-------|-------------|----------|--------|
| T01 | Structure du dépôt, CI, règles | Claude | Ce dépôt, CI verte | fait |
| T02 | Vérifier le Lenovo (`python scripts/check_env.py`) | Abdoulaye | Sortie du script collée dans `docs/contexte.md` | à faire |
| T03 | Métriques et découpage spatial (`src/herculaneum`) | Claude | Code + tests | fait — contrôle indépendant à coordonner avec modifications de GLM |
| T04 | Relire T03 et intégrer la contre-expertise | GLM 5.3 (travail code) + ChatGPT/Claude (relecture indépendante si GLM modifie le code) | PR de GLM + revue croisée sans auto-validation | en cours — modifications GLM annoncées, non encore contrôlées |
| T05 | Valider le protocole H001 (`experiments/H001-ink-baseline/README.md`) | ChatGPT | Protocole révisé, `REVIEW-T05.md` et manifeste ; PR à relire | en relecture |
| T06 | Exécuter les notebooks officiels *Scroll Data Access* et *Ink Detection* sur Colab | Abdoulaye + Claude | Un petit extrait de fragment + son masque d'encre, et la procédure notée | à faire |
| T07 | Référence naïve H001 (seuils simples) | Claude | Tableau de scores dans `results/` | à faire (après T06) |
| T08 | Méthode alternative H001 indépendante | GLM 5.3 (intérim) ; Qwen à son retour si utile | Tableau de scores dans `results/` | à faire (après T06) |
| T09 | Choisir une issue `villa` pour la voie B (voir `upstream/`) — première piste : #2482 | Abdoulaye + ChatGPT | Issue choisie, vérifiée libre, comportement attendu confirmé par un mainteneur, noté dans `docs/decisions.md` | en cours |
| T11 | #2482 : reproduire l'écart C++ / documentation sur un petit masque synthétique (sans corriger) | Claude | Script de reproduction + constat, dans `upstream/2482/` | à faire (après accord T09) |
| T10 | Rejoindre le Discord Vesuvius, lire les règles des prix mensuels | Abdoulaye | Points clés résumés dans `docs/contexte.md` | à faire |

Note coordination (2026-11-23) : Qwen temporairement indisponible ; GLM 5.3 actif sur le code. PR #1 et #2 chevauchent T05 : arbitrage de déduplication avant fusion par Abdoulaye. Les modifications de GLM ne sont pas présumées livrées tant qu'un commit/une PR n'est pas vérifié.
