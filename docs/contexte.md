# Contexte — faits vérifiés

Chaque fait porte sa date de vérification et sa source. Un fait non vérifié est marqué *(à vérifier)*.

## Le challenge (vérifié le 2026-11-23)

- Cagnotte ouverte : **2 140 000 $**. Grand Prix (1 M$ au total, dont 2e/3e/4e places) : date limite **25 juin 2027**. — [scrollprize.org/prizes](https://scrollprize.org/prizes)
- Prix « First Letters » : 50 000 $ pour rendre lisibles 10 lettres dans un rouleau éligible (10 prix). — [blog, juillet 2026](https://scrollprize.substack.com/p/335k-awarded-in-july)
- **Prix de progrès mensuels** (objectif : améliorer les outils et méthodes). Exemples : 33 500 $ en juillet 2026, 31 000 $ en août 2026. — [scrollprize.org/winners](https://scrollprize.org/winners)
- Exemple parlant pour la voie B : 20 000 $ pour quatre corrections fusionnées rendant `fit_spiral` fonctionnel sous Windows et transformant des pertes silencieusement nulles en erreurs explicites. — [scrollprize.org/winners](https://scrollprize.org/winners)
- Les organisateurs découragent les outils d'audit autonomes ; ils veulent des améliorations du déroulement, de la détection d'encre ou des logiciels utilisés. *(source : plan initial ChatGPT — à vérifier sur la page des prix)*

## Les données

- Données ouvertes sur S3 : `s3://vesuvius-challenge-open-data/` (lisible avec AWS CLI, boto3, s3fs), [navigable ici](https://vesuvius-challenge-open-data.s3.us-east-1.amazonaws.com/index.html). — [scrollprize.org/llms-full.txt](https://scrollprize.org/llms-full.txt)
- Format OME-Zarr permettant de lire de petits morceaux d'un volume sans tout télécharger. *(à vérifier)*
- Masques d'encre de référence (`ink-labels`) pour certains fragments. *(à vérifier — T06)*
- Notebooks officiels *Scroll Data Access* et *Ink Detection* dans [`villa/vesuvius`](https://github.com/ScrollPrize/villa/tree/main/vesuvius). *(à vérifier — T06)*

## Point physique à garder en tête

L'encre d'Herculanum est à base de carbone : sa densité au scanner est très proche de celle du papyrus carbonisé.
C'est pour cela que la détection d'encre a nécessité de l'apprentissage automatique.
**Conséquence pour H001 :** des filtres classiques devraient donner des scores faibles. L'expérience sert à mesurer cet écart et à apprendre les données, pas à battre l'état de l'art.

## Notre matériel

| Élément | Valeur |
|---------|--------|
| Machine | Lenovo IdeaPad (PC personnel) |
| CPU | AMD Ryzen 3 *(modèle exact : T02)* |
| GPU | Radeon Vega intégrée — **non utilisable pour PyTorch sous Windows** |
| RAM | 12 Go (4 soudés + 8 ajoutés) |
| Disque libre | *(T02)* |
| Python / Git | *(T02)* |

Calcul GPU gratuit : Google Colab, Kaggle (quotas variables, à vérifier au moment de l'usage).

### Sortie de `scripts/check_env.py`

```
(à coller ici — T02)
```
