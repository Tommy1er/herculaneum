# HERCULANUM

Équipe indépendante qui contribue au [Vesuvius Challenge](https://scrollprize.org) : lire les rouleaux carbonisés d'Herculanum sans les dérouler.

**Objectif :** produire des contributions **utiles et vérifiables** au projet officiel, avec du matériel modeste et sans budget.

## Deux voies de travail

| Voie | Quoi | Pourquoi |
|------|------|----------|
| **A — Expériences** | Petites expériences mesurées sur de vraies données (H001 : détection d'encre par méthodes légères) | Apprendre les données, établir des références chiffrées |
| **B — Logiciel officiel** | Corriger des problèmes réels du dépôt [`ScrollPrize/villa`](https://github.com/ScrollPrize/villa), avec tests | Faisable sans GPU, utile aux chercheurs, récompensé par les prix mensuels |

La voie B est la priorité dès qu'une issue adaptée est identifiée. La voie A sert d'abord à apprendre.

## L'équipe

| Membre | Rôle |
|--------|------|
| Abdoulaye (Tommy1er) | Directeur : priorités, décisions, soumissions, Discord |
| ChatGPT | Méthode scientifique, protocoles, contrôle statistique |
| Claude | Ingénierie : code, tests, CI, préparation des PR |
| Qwen | Contre-expertise : relecture, méthodes alternatives |

Règles de travail : voir [`AGENTS.md`](AGENTS.md). Tâches en cours : [`TASKS.md`](TASKS.md).

## Organisation du dépôt

```
AGENTS.md            Règles pour les IA (à lire avant toute contribution)
TASKS.md             Tâches : une ligne = un livrable vérifiable
docs/
  contexte.md        Faits vérifiés sur le challenge, les données, notre matériel
  decisions.md       Journal court des décisions
experiments/
  H001-ink-baseline/ Protocole + résultats de l'expérience 001
src/herculaneum/     Code Python partagé (métriques, découpage spatial…)
tests/               Tests automatiques (pytest)
scripts/             Outils (vérification de l'environnement…)
upstream/            Veille sur le dépôt officiel villa (voie B)
notebooks/           Notebooks Colab / Kaggle
data/                Données locales — jamais versionnées
```

## Démarrage (Windows, PowerShell)

```powershell
git clone https://github.com/Tommy1er/herculaneum.git
cd herculaneum
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/check_env.py
pytest
```

## Matériel de référence

Lenovo IdeaPad, AMD Ryzen 3, Radeon Vega intégrée, 12 Go de RAM.
Tout le calcul local se fait **sur le processeur** (la Vega n'est pas utilisable par PyTorch sous Windows).
Le calcul GPU, quand il est nécessaire, passe par Google Colab ou Kaggle.
