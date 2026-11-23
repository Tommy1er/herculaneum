# H001 — Détection d'encre par méthodes légères

**Statut :** protocole révisé par ChatGPT (T05, 2026-11-23). **Aucun score expérimental n'est encore validé.** Exécution bloquée jusqu'à validation des données en T06.

## Question et portée

Sur un fragment d'Herculanum possédant des annotations d'encre fiables et correctement alignées, quelles performances obtiennent des méthodes classiques (sans réseau neuronal) par rapport à des références triviales ?

**H001 est d'abord une étude de faisabilité et d'apprentissage des données.** L'encre carbonée est difficile à distinguer du papyrus au scanner. Aucun gain sur les modèles d'IA récents n'est présumé ; un résultat négatif doit être conservé.

## Porte d'entrée : validation des données (T06)

Ne calculer **aucun score** avant d'avoir consigné dans un manifeste versionné :
1. Identifiants exacts du fragment, du scan et de la surface/segmentation ; URLs officielles, licence et date d'accès.
2. Résolution/espacement des voxels, dimensions (Z, Y, X), plage de profondeur sélectionnée, prétraitement des intensités et orientation des axes.
3. Origine des masques d'encre et de validité (pixels annotés, hors papyrus et incertains) ; convention de codage. Un pixel non annoté n'est **pas** automatiquement « pas encre ».
4. Alignement géométrique des masques avec l'entrée CT (mêmes coordonnées, taille, orientation et résolution) ; contrôler des repères et documenter toute transformation. Ne pas interpoler des étiquettes binaires en valeurs flottantes.
5. Taille de l'extrait et mémoire maximale estimée (Lenovo Ryzen 3, 12 Go RAM) ; accès par petits blocs, sans versionner les grands volumes.
6. Comptages avant découpage : pixels valides, positifs et négatifs ; vérifier qu'il existe des pixels valides des deux classes dans les sous-ensembles destinés à être évalués.

Partir de `manifest.template.json` ; archiver ensuite une copie renseignée (sans identifiants secrets ni données privées). Si l'alignement ou le statut des annotations n'est pas établi, **suspendre H001** et documenter le blocage. Ne jamais inventer un masque de référence.

## Séparation spatiale et anti-fuite

- Utiliser `herculaneum.tiles.spatial_split` pour séparer les **régions spatiales** de réglage et de test, jamais des pixels aléatoires. Tous les plans Z d'une même position (Y, X) appartiennent à une seule partition.
- Fixer **avant toute inspection du test** : taille des tuiles, axe, fraction test, graine si applicable, séparation physique et règles d'exclusion. La valeur par défaut `gap=0` du code ne suffit pas à garantir une indépendance spatiale ; choisir un `gap > 0` adapté au rayon maximal des filtres et à la corrélation spatiale, et consigner la justification.
- Exclure de l'évaluation les zones tampons et les tuiles incomplètes. Vérifier par programme que réglage et test ne se recouvrent pas et contiennent des données annotées des deux classes.
- Paramètres appris de l'image (normalisation statistique, seuils, profondeur, taille de filtre, choix de méthode et de polarité) : ajuster **uniquement sur réglage**, ou fixer a priori sans regarder les étiquettes du test. Ne pas recalibrer après observation des résultats test.
- Si l'extrait est trop petit pour produire deux régions fiables avec tampon, choisir un autre extrait ou déclarer le test non valable. Ne pas réduire arbitrairement l'écart après avoir vu les résultats.

Une partition spatiale **dans un seul fragment** mesure seulement une généralisation locale : ne pas extrapoler à d'autres rouleaux. Les tests inter-fragments sont une expérience ultérieure distincte.

## Méthodes fixées avant test

| Code | Méthode | Responsable |
|---|---|---|
| B0a | Prédire « pas encre » partout (sur pixels valides) | Claude |
| B0b | Prédire « encre » partout (sur pixels valides) | Claude |
| B1 | Seuil global sur l'intensité moyenne d'une fenêtre Z fixée ; seuil et sens appris sur réglage | Claude |
| C1 | Contraste local et/ou combinaison de profondeurs ; paramètres limités et fixés sur réglage | Claude |
| Q1 | Méthode indépendante, définie avant l'ouverture des résultats de test | Qwen / GLM 5.3 |

**Important :** pour `binary_scores`, fournir une prédiction **déjà binarisée** (`bool` ou 0/1), jamais une carte de probabilités brute : la fonction convertit actuellement toute valeur non nulle en `True`. La revue indépendante T04 doit vérifier ce contrat ainsi que les cas limites. Toute modification au code fait l'objet d'une PR distincte.

## Évaluation

- Calculer TP, FP, FN et TN sur l'intersection : **région test ET masque valide**. Reporter le nombre exact de pixels et la prévalence positive.
- Reporter précision, rappel, **F1**, **F0.5** (métrique historique de détection d'encre du challenge) ; agréger les comptes des tuiles d'abord, calculer les ratios ensuite (**micro**), ne pas moyenner naïvement les F-scores.
- Sur référence/prédiction dégénérée, expliciter les dénominateurs nuls (la fonction retourne zéro par convention). Rejeter un test sans pixel valide ou sans classe positive pour l'évaluation principale.
- À titre exploratoire, donner aussi les résultats **par tuile** pour évaluer l'hétérogénéité. Les pixels voisins sont corrélés : pas d'intervalle de confiance naïf supposant les pixels indépendants.
- Évaluer le jeu test **une seule fois** après gel des paramètres. Ne pas choisir le « gagnant » en comparant de nombreux essais sur le test. La comparaison n'est **pas** directement un score officiel du concours.

## Procédure et livraison

1. **T06 :** récupérer un extrait réel, le masque valide et la vérité terrain alignés ; remplir le manifeste.
2. Construire et figer le découpage spatial, les paramètres et les commandes dans un fichier de configuration versionné.
3. **T07 / T08 :** développer B0/B1/C1 et Q1 sur les régions de réglage. L'autre IA relit le code et la séparation.
4. Geler les méthodes, puis calculer une fois les métriques sur test.
5. Déposer sous `results/` un petit fichier JSON/CSV par méthode, avec : ID de données/manifeste, méthode, paramètres, hash Git, commandes exactes, dépendances, effectifs, compte TP/FP/FN/TN, métriques et limites. Ajouter les résultats négatifs ; ne pas committer de gros scans, masques sous licence restrictive, secrets ou environnements virtuels.

## Conditions de clôture

H001 ne sera considéré **exécuté** que lorsque : données réellement vérifiées, tests automatisés réussis, zéro fuite identifiée, méthodes gelées avant le test et résultats reproductibles publiés. La révision du protocole **ne vaut pas résultat scientifique**.
