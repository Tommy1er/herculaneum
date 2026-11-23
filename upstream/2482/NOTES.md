# villa #2482 — lecture du code sur `main` actuel

**Commit lu :** `e5707e413e61fc3e67af6b98ea5bd713fe0110d1` (2026-11-23).
**Méthode :** lecture du code source uniquement. Rien n'a été compilé ni exécuté : la compilation de `vc_reader` a échoué dans l'espace de travail de Claude (Boost absent, paquets système impossibles à installer).

## Constat principal : deux lecteurs C++ du même dépôt appliquent deux règles différentes

| Source | Règle pour une valeur de pixel | Masque de taille non multiple de la grille |
|--------|--------------------------------|-------------------------------------------|
| `vc_reader/src/cpp/tifxyz/tifxyz.cpp`, `applyMask` (l. 107-121) — utilisé par `load_quad_from_tifxyz`, donc VC3D et `vc_tifxyz2obj` | Sommet invalide **seulement si un pixel vaut 0** (tous les octets nuls). 1 à 254 → valide | Erreur (`maskGridOf`, l. 97-103) |
| `vc_object_store/src/geometry/TypedGeometry.cpp`, l. 55 | Sommet invalide si un pixel est **< 255** | — (non lu) |
| `vc_object_store/tests/cpp/test_object_store_surface_tifxyz.cpp`, l. 72 | Teste explicitement qu'un pixel à 128 invalide le sommet | — |
| `vc_object_store/docs/ingestion.md`, l. 74-77 | Valide seulement si tous les pixels couverts sont ≥ 255 | **Rejeté** |
| `lasagna/tifxyz_format.md`, l. 83 et l. 143 | < 255 invalide | Masque **ignoré** (« si l'échelle est un multiple entier ») |
| `vc_reader/include/vc_reader/tifxyz.hpp`, l. 68 (commentaire) | « nonzero where allowed » | — |

Conséquence : un même `mask.tif` contenant des valeurs entre 1 et 254 donne des sommets **valides dans VC3D** et **invalides à l'ingestion dans l'object store**.

## Ce que cela ajoute à l'issue

L'issue compare `vc_tifxyz2obj` à `lasagna/tifxyz_format.md`. Le code montre que l'écart est aussi **entre deux implémentations C++** du dépôt, et que la règle « < 255 » est appliquée et testée dans `vc_object_store`. La majorité des sources (deux documents, un lecteur et son test) va dans le sens « < 255 invalide ».

Pour la taille non multiple, les deux lecteurs rejettent le masque ; seule la documentation `lasagna` dit qu'il est ignoré. C'est probablement la documentation qui est en retard.

## Questions à poser aux mainteneurs (avant toute correction)

1. La règle voulue est-elle « 0 invalide » (comme `vc_reader`, commentaire l. 68) ou « < 255 invalide » (comme `vc_object_store` et la documentation) ?
2. Pour un masque sur plusieurs octets (uint16, RGB), que signifie la règle ? Aujourd'hui, `vc_reader` exige que tous les octets soient nuls.
3. Un masque de taille non multiple doit-il être rejeté (code actuel) ou ignoré (documentation `lasagna`) ?

## Prochaine étape (T11)

Reproduction exécutable sur `main` : un workflow GitHub Actions (Ubuntu, où les dépendances système s'installent) qui compile `vc_reader` depuis `villa`, écrit une surface tifxyz synthétique 12 × 12 avec des pixels à 0, 128, 254 et 255, et affiche quels sommets restent valides. À lancer une fois T09 décidé.
