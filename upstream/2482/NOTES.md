# villa #2482 — reproduction et lecture du code sur `main` actuel

**Commit `villa` :** `e5707e413e61fc3e67af6b98ea5bd713fe0110d1` (2026-11-23).

## Reproduction exécutée (T11)

`vc_reader` officiel compilé depuis `villa` sur GitHub Actions (Ubuntu 24.04, Python 3.12), puis `repro.py` sur une surface tifxyz synthétique 12 × 12.
Run : https://github.com/Tommy1er/herculaneum/actions/runs/45170426160 — résultats : [`results-e5707e4.json`](results-e5707e4.json).

| Valeur du pixel de masque | Sommet valide selon `vc_reader` | Règle documentée (≥ 255) |
|---------------------------|---------------------------------|--------------------------|
| 0 | non | non |
| 1 | **oui** | non |
| 128 | **oui** | non |
| 254 | **oui** | non |
| 255 | oui | oui |

Masque 9 × 9 sur une grille 12 × 12 : **erreur** `ValueError: tifxyz mask shape (9, 9) does not match the coordinate grid`. La documentation `lasagna` dit que ce masque devrait être ignoré.

Relancer : onglet *Actions* → *repro-villa-2482* → *Run workflow* (on peut choisir une autre branche ou un autre commit de `villa`).

## Lecture du code : deux lecteurs C++ appliquent deux règles opposées, et chacune est testée

| Source | Règle pour une valeur de pixel | Masque de taille non multiple de la grille |
|--------|--------------------------------|-------------------------------------------|
| `vc_reader/src/cpp/tifxyz/tifxyz.cpp`, `applyMask` (l. 107-121) — utilisé par `load_quad_from_tifxyz`, donc VC3D et `vc_tifxyz2obj` | Sommet invalide **seulement si un pixel vaut 0** | Erreur (`maskGridOf`, l. 97-103) |
| `vc_reader/tests/test_tifxyz.py`, `test_reads_other_writers_and_mask` (l. 43-69) | **Teste qu'un masque à 1 est valide** (`np.ones`, puis `mask[3, 4] = 0`) | Teste l'erreur (`match='mask shape'`) |
| `vc_reader/include/vc_reader/tifxyz.hpp`, l. 68 (commentaire) | « nonzero where allowed » | — |
| `vc_object_store/src/geometry/TypedGeometry.cpp`, l. 55 | Sommet invalide si un pixel est **< 255** | — (non lu) |
| `vc_object_store/tests/cpp/test_object_store_surface_tifxyz.cpp`, l. 72 | **Teste qu'un pixel à 128 invalide le sommet** | — |
| `vc_object_store/docs/ingestion.md`, l. 74-77 | Valide seulement si tous les pixels couverts sont ≥ 255 | **Rejeté** |
| `lasagna/tifxyz_format.md`, l. 83 et l. 143 | < 255 invalide | Masque **ignoré** |

Conséquence : un même `mask.tif` contenant des valeurs entre 1 et 254 donne des sommets **valides dans VC3D** et **invalides à l'ingestion dans l'object store**.

Ce n'est donc pas seulement un écart entre code et documentation : les **tests** des deux modules fixent des règles contraires. Une correction dans un sens casserait un test dans l'autre, ce qui confirme qu'il faut d'abord une décision des mainteneurs.

## Questions à poser aux mainteneurs (avant toute correction)

1. La règle voulue est-elle « 0 invalide » (`vc_reader`, son commentaire et son test) ou « < 255 invalide » (`vc_object_store`, son test et les deux documentations) ?
2. Pour un masque sur plusieurs octets (uint16, RGB), que signifie la règle ? Aujourd'hui, `vc_reader` exige que tous les octets soient nuls.
3. Un masque de taille non multiple doit-il être rejeté (les deux lecteurs) ou ignoré (documentation `lasagna`) ?

## Projet de commentaire sur l'issue (à poster par Abdoulaye, en anglais)

> Independent reproduction on `main` (`e5707e4`) with `vc_reader` built from source and a synthetic 12×12 tifxyz: mask values 1, 128 and 254 keep the vertex valid, only 0 invalidates; a 9×9 mask raises `ValueError: tifxyz mask shape (9, 9) does not match the coordinate grid`. Script and CI log: https://github.com/Tommy1er/herculaneum/tree/main/upstream/2482
>
> The two C++ readers also disagree with each other, and both rules are pinned by tests: `vc_reader/tests/test_tifxyz.py` (l. 49) treats a mask value of 1 as valid, while `vc_object_store/tests/cpp/test_object_store_surface_tifxyz.cpp` (l. 72) expects 128 to invalidate. So the same `mask.tif` gives different valid vertices in VC3D and in object-store ingestion.
>
> Which rule is intended — "0 invalidates" or "< 255 invalidates"? And should a non-multiple mask be rejected (both readers) or ignored (`lasagna/tifxyz_format.md`)? Happy to send a PR aligning code, tests and docs once the rule is settled.
