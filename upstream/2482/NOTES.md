# villa #2482 — reproduction à deux lecteurs

**Commit `villa` le plus récent testé :** `659e2fadb836d44063ed831d85517154ec852f11` (2026-11-25). Le seul changement de `tifxyz.cpp` depuis `e5707e4` concerne les chemins UTF-8, pas la règle de masque.

## Reproduction exécutée (T11)

Les deux lecteurs officiels sont compilés depuis `villa` sur GitHub Actions (Ubuntu 24.04, Python 3.12), puis `repro.py` leur donne **les mêmes fichiers** : une surface tifxyz synthétique 12 × 12, un pixel de masque par valeur testée sur la diagonale, tous les autres à 255.

- **Lecteur A** : `vc_reader.tifxyz.read` (utilisé par VC3D et `vc_tifxyz2obj`).
- **Lecteur B** : ingestion `vc_object_store` (`vc_object_ingest`), puis `vc_object_export --valid-only`, qui écrit les sommets invalides comme points manquants, relus avec `vc_reader`.

Run : https://github.com/Tommy1er/herculaneum/actions/runs/45866382414 — résultats : [`results-659e2fa.json`](results-659e2fa.json) (run précédent, lecteur A seul sur `e5707e4` : [`results-e5707e4.json`](results-e5707e4.json)).

| Valeur du pixel de masque | Valide — `vc_reader` (VC3D) | Valide — `vc_object_store` | Règle documentée (≥ 255) |
|---------------------------|-----------------------------|----------------------------|--------------------------|
| 0 (témoin) | non | non | non |
| 1 | **oui** | non | non |
| 128 | **oui** | non | non |
| 254 | **oui** | non | non |
| 255 (témoin) | oui | oui | oui |

Les 139 autres sommets sont valides et identiques dans les deux lecteurs : l'écart porte uniquement sur les valeurs intermédiaires.

Masque 9 × 9 sur une grille 12 × 12 : **refusé par les deux lecteurs** (`vc_reader` : `ValueError … does not match the coordinate grid` ; `vc_object_store` : `mask.tif must be a whole multiple of the points grid`). Seule la documentation `lasagna` dit qu'un tel masque est ignoré.

Relancer : onglet *Actions* → *repro-villa-2482* → *Run workflow* (on peut choisir une autre branche ou un autre commit de `villa`). En local : `python upstream/2482/repro.py --vos-bin <dossier des binaires>`.

## Sources (lignes au commit `e5707e4`, vérifiées aussi par ChatGPT)

| Source | Valeur de pixel | Masque de taille non multiple |
|--------|-----------------|-------------------------------|
| `vc_reader/src/cpp/tifxyz/tifxyz.cpp`, `applyMask` (l. 107-121) | invalide **seulement si 0** | erreur (`maskGridOf`, l. 97-103) |
| `vc_reader/tests/test_tifxyz.py`, l. 43-69 | **teste qu'un masque à 1 est valide** | teste l'erreur (`match='mask shape'`) |
| `vc_reader/include/vc_reader/tifxyz.hpp`, l. 68 (commentaire) | « nonzero where allowed » | — |
| `vc_object_store/src/geometry/TypedGeometry.cpp`, `validityFromMask` (l. 45-58) | invalide si **< 255** (l. 55) | erreur explicite (l. 48-50) |
| `vc_object_store/tests/cpp/test_object_store_surface_tifxyz.cpp` | **teste qu'un pixel à 128 invalide le sommet** (l. 72) | teste le rejet (l. 142-144) |
| `vc_object_store/docs/ingestion.md`, l. 74-77 | valide seulement si ≥ 255 | rejeté |
| `lasagna/tifxyz_format.md`, l. 83 et 143 ; l. 94 | < 255 invalide | « mask may effectively be skipped » (l. 94) |

## Conclusion pour l'issue

1. Les deux lecteurs C++ du dépôt appliquent des règles opposées aux valeurs 1 à 254, et **chaque règle est fixée par un test**. Une correction d'un côté casserait le test de l'autre : il faut une décision des mainteneurs.
2. Pour la taille non multiple, le code est cohérent (refus) : c'est la documentation `lasagna` (l. 94) qui est en retard. Ce point peut être corrigé sans attendre.

## Questions pour les mainteneurs

1. Règle voulue : « 0 invalide » (`vc_reader`) ou « < 255 invalide » (`vc_object_store` et les deux documentations) ?
2. Pour un masque sur plusieurs octets (uint16, RGB), que signifie la règle ? Aujourd'hui `vc_reader` exige que tous les octets soient nuls.
3. D'accord pour corriger `lasagna/tifxyz_format.md` (l. 94) afin qu'il dise que ce masque est refusé ?

## Projet de commentaire sur l'issue (à poster par Abdoulaye)

> Independent reproduction on `main` (`659e2fa`), with both readers built from source and fed the **same** synthetic 12×12 tifxyz (one probe vertex per mask value, all other pixels 255):
>
> | mask value | vc_reader (VC3D, vc_tifxyz2obj) | vc_object_store ingest |
> |---|---|---|
> | 0 | invalid | invalid |
> | 1 / 128 / 254 | **valid** | invalid |
> | 255 | valid | valid |
>
> All other vertices agree. Both rules are pinned by tests: `vc_reader/tests/test_tifxyz.py` treats a mask value of 1 as valid, while `vc_object_store/tests/cpp/test_object_store_surface_tifxyz.cpp` (l. 72) expects 128 to invalidate. So the same `mask.tif` yields different valid vertices in VC3D and in object-store ingestion.
>
> For the 9×9 mask on a 12×12 grid, both readers reject it (`does not match the coordinate grid` / `must be a whole multiple of the points grid`); only `lasagna/tifxyz_format.md` (l. 94) says it is skipped.
>
> Script, CI workflow and JSON results: https://github.com/Tommy1er/herculaneum/tree/main/upstream/2482
>
> Which rule is intended — "0 invalidates" or "< 255 invalidates"? Happy to send a PR aligning code, tests and docs once it is settled, and a doc-only PR for the non-multiple case now if that helps.
