# HERCULANUM — La mission expliquée simplement

*État vérifié au 23 novembre 2026 — note pour le directeur du projet, Claude, ChatGPT, GLM 5.3 et Qwen à son retour.*

## La phrase qui résume tout

Nous voulons aider les chercheurs à **retrouver les lettres réellement écrites sur des papyrus carbonisés d'Herculanum, sans ouvrir physiquement les rouleaux**. Notre contribution vise les outils informatiques, pas à inventer des traductions antiques.

## Le parcours d'un rouleau

1. **Scanner** : les rayons X donnent une reconstruction tridimensionnelle, composée de petits cubes (voxels).
2. **Suivre les couches** : le logiciel identifie quelle partie du volume correspond à une feuille de papyrus, même froissée ou déformée.
3. **Aplatir virtuellement** : la surface 3D suivie devient un rendu 2D, comparable à une page.
4. **Retrouver l'encre** : l'encre carbonée et le support carbonisé ont un contraste très faible. Un modèle d'IA cherche de minuscules indices physiques et produit une carte de probabilité d'encre, pas une transcription.
5. **Lire** : des spécialistes du grec ancien examinent les traits visibles et reconstituent lettres, mots, phrases et œuvres.

**Règle scientifique :** un trait doit être justifié par les données du scanner. Nous ne devons pas produire des lettres simplement parce qu'elles paraissent plausibles à un LLM.

## Ce que nous faisons aujourd'hui : deux voies complémentaires

### A. Apprendre à évaluer les méthodes de détection d'encre (H001)

Claude a commencé une base de code Python pour découper les images et mesurer les résultats. ChatGPT a proposé une révision du protocole de contrôle. GLM travaille sur des modifications de code d'après le directeur, mais leur publication GitHub doit encore être vérifiée. Qwen participe plus tard.

**L'expérience H001** n'essaie pas encore de retrouver un livre. Nous voulons d'abord obtenir un petit extrait réel dont l'emplacement de l'encre est déjà connu, par exemple un fragment possédant un masque de référence. Nous faisons des prédictions simples (tout encre, rien, seuil, contraste local), puis comparons aux annotations pour connaître nos erreurs.

- **Précision** : parmi les pixels que nous déclarons « encre », quelle proportion correspond effectivement à de l'encre connue ?
- **Rappel** : parmi les pixels d'encre connus, quelle proportion retrouvons-nous ?
- **F1 / F0.5** : synthèses des deux dimensions ; F0.5 privilégie la précision.
- **Séparation réglage/test** : les zones utilisées pour choisir les paramètres ne doivent pas être voisines, confondues ou réutilisées pour prouver la performance. Un algorithme qui a vu une réponse ne l'a pas découverte.

H001 peut très bien démontrer que les méthodes simples sont médiocres : ce sera tout de même une mesure utile et une base de comparaison. Les données et leur alignement ne sont pas encore validés au 23/11 : **aucun score scientifique réel ne doit être annoncé**.

### B. Aider les outils officiels (priorité à court terme)

Les chercheurs ont besoin de programmes fiables pour tracer, aplatir, afficher et traiter des feuilles. Corriger un logiciel ne déchiffre pas directement une phrase, mais rend le travail possible, reproductible et moins sujet aux erreurs.

Première candidate examinée : [issue ScrollPrize/villa #2482](https://github.com/ScrollPrize/villa/issues/2482). Le code C++ et sa documentation ne semblent pas définir de la même manière quels pixels du masque sont valides. Notre démarche : reproduire sur un tout petit jeu artificiel, exposer le désaccord, demander l'intention des mainteneurs, corriger **seulement ensuite** et joindre un test. Ne pas reprendre des issues déjà traitées en PR.

## Comment les IA se répartissent le travail

| Acteur | Travail attendu | Preuve livrée |
|---|---|---|
| ChatGPT | Explications, protocoles, contrôle de validité des conclusions | Note technique et revue versionnées, PR |
| Claude | Implémentation Python/C++, tests, extraction de données, reproductibilité | Code, commande, tests et PR |
| GLM 5.3 | Développement de variantes, recherche d'erreurs, contre-expertise | Branche propre, tests, PR ; revue indépendante de son code |
| Qwen (retour différé) | Méthodes alternatives ou relecture indépendante | Même format GitHub quand il sera disponible |
| Directeur | Choix, arbitrages, soumissions au challenge, fusion | Décision sur PR et échange avec communauté |

Une IA ne doit pas approuver son propre correctif sans relecture indépendante. Le dépôt commun rend les travaux visibles ; les agents n'échangent pas automatiquement leurs espaces privés.

## Nos jalons — sans promesse artificielle de date

- **Jalon 1 :** environnement Python reproductible, tests de base, protocole H001 compris.
- **Jalon 2 :** données publiques réelles + annotations alignées + résultats de référence et leurs limites.
- **Jalon 3 :** première amélioration logicielle utile dans `ScrollPrize/villa`, avec test et discussion des mainteneurs.
- **Jalon 4 :** si les mesures le justifient, tester des méthodes plus avancées sur des données indépendantes et éventuellement contribuer directement aux cartes d'encre.
- **Vision finale :** accélérer, même modestement, la découverte de **vrais caractères** à l'intérieur de rouleaux encore illisibles.

Les deux premières PR HERCULANUM au 23/11 (#1 et #2) couvrent toutes deux le protocole H001 ; il faut dédupliquer leurs apports avant de fusionner. Les modifications GLM annoncées ne sont pas encore vérifiées sur le dépôt public au moment de cette note.

## Matériel et budget

Machine personnelle : Lenovo IdeaPad, Ryzen 3 + Radeon Vega, 12 Go RAM. **Pas d'achat de GPU NVIDIA prévu**. Les petits extraits, tests et outils CPU sont compatibles avec l'objectif. Les calculs 3D très lourds pourraient un jour nécessiter des ressources distantes, mais ce n'est pas un prérequis à notre première contribution.

## Comment informer le directeur sans l'obliger à lire le code

Pour chaque avancée significative, les IA doivent pouvoir répondre en quatre phrases ordinaires : **« Qu'avons-nous tenté ? Qu'avons-nous vraiment obtenu ? Quelle preuve est disponible ? Quelle est la prochaine difficulté ? »** Le lien GitHub sert de preuve, pas de substitut à une explication.

## Sources communes

- [Vesuvius Challenge — Pipeline officiel](https://scrollprize.org/tutorial)
- [Tutoriel officiel — Détection d'encre](https://scrollprize.org/tutorial5)
- [Conditions officielles des prix](https://scrollprize.org/prizes)
- [Dépôt officiel ScrollPrize/villa](https://github.com/ScrollPrize/villa)
- [Notre suivi des tâches](../TASKS.md)
