# Résultats H001 — démonstration synthétique (issue #3)

Fichiers produits par `experiments/H001-ink-baseline/run_synthetic_demo.py`
sur des données **synthétiques** (graine 42). Ils valident la chaîne de
traitement ; ils ne préjugent d'aucune performance sur les scans réels du
Vesuvius Challenge (le contraste réel encre/papyrus est bien plus faible).

| Fichier | Contenu |
|---|---|
| `metrics_synthetic.json` | zones, tuilage, justification de la séparation spatiale, seuils et métriques (P, R, F1, F0.5) par méthode et par critère, AP, références triviales, versions, commande |
| `scores_chart.svg` | figure vectorielle commise : F1 / F0.5 / AP par méthode (critère initial, zone de test) |
| `map_synthetic.svg` | carte 3 panneaux (image, probabilité, vérité terrain) — **régénérée localement** par le script, non commise (données raster volumineuses embarquées) ; IDs stables (`svg.hashsalt`) et sans horodatage, la régénération est byte-identique |

## Reproduction

```
python experiments/H001-ink-baseline/run_synthetic_demo.py
```

Graine 42 ; image 256×640 ; zones validation [0, 200) / écart [200, 440) /
test [440, 640) ; tuiles 128×128, recouvrement 48×48 (≥ rayon 4σ = 24 px du
noyau gaussien le plus large). La commande et les versions exactes sont
enregistrées dans le JSON.

## Deux critères de seuil, réglés sur la zone de validation uniquement

- **`initial_criterion`** (protocole d'origine du prototype GLM) : maximiser
  F1, égalité départagée par le seuil le plus élevé. Ses chiffres de test
  sont ceux annoncés sur l'issue #3 (F1 0.749 / 0.466 / 0.870, AP 0.812 /
  0.362 / 0.940, tout-encre 0.036).
- **`t05_criterion`** (révision T05, PR #1) : maximiser F0.5, égalité
  départagée par la première configuration consignée (ici le seuil le plus
  élevé de l'ordre décroissant). Pour `texture_energy` il choisit un autre
  seuil (0.4938 au lieu de 0.4675) et améliore le point de fonctionnement
  (F1 0.4672, F0.5 0.4022 contre 0.3685) ; pour les deux autres méthodes le
  seuil retenu est identique.

L'AP est sans seuil : elle est identique sous les deux critères.

## Provenance

- **Statut : essai de développement** (revue de l'issue #3, 2026-11-23). La
  scène et ces chiffres de la graine 42 ont servi à mettre la chaîne au point
  (le choix du générateur et un ajustement de la méthode texture ont été
  faits en consultant les résultats de la bande de test). Ils ne constituent
  PAS une évaluation indépendante : voir `multiseed/` pour celle-ci.
- Le prototype d'origine (archive de la session GLM) écrivait ses sorties
  dans `outputs/` ; la convention du dépôt (AGENTS.md) est `results/`.
- Le code intégré (`synth.py`, `baselines.py`, `blockwise.py`,
  `metrics.average_precision`) reprend la logique du prototype à
  l'identique ; commentaires et identifiants traduits en anglais
  (AGENTS.md). Les chiffres annoncés se reproduisent à l'identique — voir le
  test `test_demo_reproduces_the_announced_numbers`.
- Les figures sont au format SVG (texte). La carte 3 panneaux embarque des
  données raster volumineuses : elle est régénérée localement et non commise ;
  le graphique de scores est purement vectoriel et est commis.
