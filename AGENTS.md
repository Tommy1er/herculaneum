# Règles de collaboration — à lire par chaque IA avant de contribuer

Ce fichier s'adresse à ChatGPT, Claude et Qwen. Il est court exprès.

## Le principe

Nous ne sommes pas un comité. Nous sommes trois assistants au service d'un directeur de projet (Abdoulaye).
Si l'idée d'un autre est meilleure, on la prend. Si la sienne est mauvaise, on la retire. Pas de débat long : une vérité, des preuves.

## Ce qui compte comme travail

Un travail est fait quand il existe **un livrable vérifiable** :
- du code qui tourne, avec un test ;
- un résultat chiffré, avec la commande qui le reproduit ;
- une relecture qui pointe une ligne précise et dit ce qui est faux.

Ne comptent pas : les plans de plans, les registres de décisions, les identifiants de tickets internes, les procédures de validation à plusieurs étapes.

## Comment on travaille

1. **Une tâche = une ligne dans `TASKS.md`** avec un responsable et un livrable.
2. **Une branche par tâche** : `<ia>/<id-tâche>-<sujet>` (ex. `claude/T03-metrics`, `qwen/T04-baseline-alt`).
3. **Pull request vers `main`**, relue par une autre IA avant fusion. Abdoulaye fusionne.
4. **Les tests doivent passer** (`pytest`, et la CI GitHub Actions).
5. **Les résultats vont dans `experiments/<id>/results/`**, avec la commande exacte et la version du code (hash git).
6. **Une décision importante = 3 lignes dans `docs/decisions.md`** : date, décision, raison. Rien de plus.

## Rigueur scientifique (expériences)

- Les régions de test sont **spatialement séparées** des régions de réglage (`src/herculaneum/tiles.py`). Jamais de pixels voisins dans les deux ensembles.
- On rapporte précision, rappel, F1 **et F0.5** (métrique historique de la détection d'encre du challenge).
- On compare toujours à une référence naïve (tout « encre », tout « pas encre », seuil simple).
- Un résultat négatif est un résultat. On le publie.

## Contributions au dépôt officiel (`ScrollPrize/villa`)

- Avant de travailler sur une issue : vérifier qu'aucune PR n'est déjà ouverte et que l'auteur ne s'en occupe pas. En cas de doute, demander sur l'issue ou sur Discord.
- C'est Abdoulaye qui soumet. Toute PR doit être compréhensible par lui : description courte, cause, correction, test.
- Les organisateurs veulent des contributions qui améliorent le déroulement, la détection d'encre ou les outils réellement utilisés — pas des outils d'audit isolés.

## Langue

Documentation de l'équipe en français. Code, commentaires, messages de commit et PR vers `villa` en anglais.

## Rôles

| Membre | Fait | Ne fait pas |
|--------|------|-------------|
| ChatGPT | Protocoles, hypothèses, contrôle statistique, relecture méthodologique | Ne bloque pas une PR pour une préférence de style |
| Claude | Code, tests, CI, préparation des PR | Ne fusionne pas dans `main` |
| Qwen | Relecture de code, méthode alternative indépendante | Ne réécrit pas le code d'un autre sans PR séparée |
| Abdoulaye | Priorités, fusion, soumissions, Discord | — |

## Traçabilité des livrables IA (directive du 2026-11-23)

**Tous les livrables utiles de ChatGPT, Claude et Qwen ou GLM 5.3 doivent être enregistrés sur GitHub** : code, tests, protocoles, résultats positifs **et négatifs**, relectures et conclusions. Un message en conversation ne tient pas lieu de livraison.

- Utiliser sa branche de tâche, puis une PR vers `main` ; ne pas pousser directement sur `main`. Abdoulaye garde la décision de fusion.
- Pour une expérience : conserver les commandes, le hash Git, les références exactes des données, les paramètres, les métriques et les limites dans `experiments/<id>/results/`.
- Pour un audit ou une relecture : déposer une note Markdown avec fichiers/sections concernés, sévérité, preuves, limites et décisions proposées ; ne pas déclarer avoir exécuté un test non réalisé.
- Les sorties conversationnelles brutes ne sont pas obligatoires : **le livrable vérifiable** l'est. Ne jamais versionner tokens, mots de passe, informations privées, modèles volumineux ou grands scans.
- Si un modèle ne peut pas écrire directement dans le dépôt, il livre un patch ou fichier à transmettre pour commit ; une livraison sans commit/PR reste **en attente**, pas « faite ».
