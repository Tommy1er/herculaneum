# Tâches

Une ligne = un livrable vérifiable. Statuts : `à faire`, `en cours`, `en relecture`, `fait`, `abandonné`.

| ID | Tâche | Responsable | Livrable | Statut |
|----|-------|-------------|----------|--------|
| T01 | Structure du dépôt, CI, règles | Claude | Ce dépôt, CI verte | fait |
| T02 | Vérifier le Lenovo (`python scripts/check_env.py`) | Abdoulaye | Sortie du script collée dans `docs/contexte.md` | à faire |
| T03 | Métriques et découpage spatial (`src/herculaneum`) | Claude | Code + tests | fait — à relire par Qwen |
| T04 | Relire T03 | Qwen / GLM 5.3 | Note de revue versionnée + tests ou « OK » motivé | à faire |
| T05 | Valider le protocole H001 (`experiments/H001-ink-baseline/README.md`) | ChatGPT | Protocole révisé, `REVIEW-T05.md` et manifeste ; PR à relire | en relecture |
| T06 | Exécuter les notebooks officiels *Scroll Data Access* et *Ink Detection* sur Colab | Abdoulaye + Claude | Un petit extrait de fragment + son masque d'encre, et la procédure notée | à faire |
| T07 | Référence naïve H001 (seuils simples) | Claude | Tableau de scores dans `results/` | à faire (après T06) |
| T08 | Méthode alternative H001 indépendante | Qwen | Tableau de scores dans `results/` | à faire (après T06) |
| T09 | Choisir une issue `villa` pour la voie B (voir `upstream/`) — première piste : #2482 | Abdoulaye + ChatGPT | Issue choisie, vérifiée libre, comportement attendu confirmé par un mainteneur, noté dans `docs/decisions.md` | en cours |
| T11 | #2482 : reproduire l'écart C++ / documentation sur un petit masque synthétique (sans corriger) | Claude | Script de reproduction + constat, dans `upstream/2482/` | à faire (après accord T09) |
| T10 | Rejoindre le Discord Vesuvius, lire les règles des prix mensuels | Abdoulaye | Points clés résumés dans `docs/contexte.md` | à faire |
