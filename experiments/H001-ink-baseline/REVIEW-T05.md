# T05 — Revue scientifique indépendante du protocole H001

**Date :** 2026-11-23  
**Auteur :** ChatGPT  
**Périmètre lu :** `AGENTS.md`, `TASKS.md`, `experiments/H001-ink-baseline/README.md`, `src/herculaneum/{metrics,tiles}.py` et tests existants sur `main`.  
**Verdict :** protocole corrigé et **acceptable sous conditions** ; pas encore exécutable faute de données/labels/alignement vérifiés (T06). Aucun modèle, scan ni notebook n'a été exécuté dans cette revue.

## Constats précis

| Importance | Emplacement | Constat | Traitement |
|---|---|---|---|
| Bloquant | README d'origine, « Données » | Aucune identité exacte de volume, masque de vérité terrain, validité ou alignement. Risque de compter les pixels inconnus comme négatifs. | Manifeste et vérification obligatoires avant le score. |
| Bloquant | `tiles.py::spatial_split(gap=0)` | Le défaut n'impose aucun tampon ; la séparation par bandes seule ne garantit pas l'absence de corrélation entre filtres/voisins. | Gap positif justifié, partition figée, vérifier non-vacuité et support spatial. |
| Important | README d'origine, « Mesures » | Manque la définition de l'agrégation, effectifs et dégénérescences. Des moyennes de F-score par tuile seraient trompeuses. | Agrégation micro par comptes ; prévalence et valeurs dégénérées explicites. |
| Important / T04 | `metrics.py::binary_scores` | `np.asarray(pred).astype(bool)` convertit, par exemple, un score de 0.01 en prédiction d'encre. Une carte continue doit être binarisée explicitement. | Contrat précisé ; demander à Qwen/GLM une revue et des tests sur entrées non binaires. |
| Important | README d'origine, « Découpage » | L'évaluation « une fois » n'est pas suffisante si l'extrait ou les hyperparamètres changent après lecture du test. | Gel préalable des paramètres, labels test non consultés, changement = nouvelle expérience clairement distincte. |
| Méthodologique | Question de recherche | Comparer des filtres traditionnels ne représente pas une découverte d'encre nouvelle ni un benchmark inter-fragments. | Limiter la conclusion à une baseline locale et publier aussi les résultats négatifs. |

## Points vérifiés dans le code (inspection statique)

- `binary_scores` calcule TP/FP/FN/TN et F0.5 selon une formule cohérente pour des entrées booléennes ; renvoie zéro lorsque les dénominateurs sont nuls. **Non vérifié par exécution ici**.
- `spatial_split` renvoie des tuiles entières en deux bandes en retirant les tuiles traversant les limites du tampon ; une vraie distance entre les bandes dépend du `gap` fourni. **Non vérifié par exécution ici**.
- Les tests unitaires existants vérifient plusieurs cas usuels, mais ne vérifient ni les cartes continues passées à `binary_scores` ni l'échec d'un split sans échantillons suffisants. **T04 doit examiner ces limites indépendamment**.

## Décision

**T05 : protocole validé dans la PR #1.** Conditions d'ouverture de T07/T08 : T06 avec masque fiable + alignement vérifié, split figé et non vide, métriques sur données binaires, CI verte. Le protocole modifié figure dans le README voisin.

Aucune mesure quantitative de performance scientifique n'est revendiquée.
