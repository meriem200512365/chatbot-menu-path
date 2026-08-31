# day2_model_testing

Dossier de **test isolé** pour le modèle fine-tuné du Jour 1
(`models/cegedim-menu-embedding`), avant toute intégration dans
l'application de production.

## Pourquoi un dossier séparé ?

Ce dossier ne modifie **aucun fichier** de `src/` (`chatbot.py`,
`semantic_search.py`, `src/api/app.py`, `src/ui/`, la base ChromaDB de
production). Il lit uniquement :

- `../dataset/menu_paths_clean.json` (corpus des 1382 chemins)
- `../models/cegedim-menu-embedding/` (modèle fine-tuné du Jour 1)

et charge en plus, à la volée, le modèle de base
(`paraphrase-multilingual-MiniLM-L12-v2`) pour comparaison — sans
jamais toucher à ChromaDB ni à l'API de prod.

## Contenu

| Fichier | Rôle |
|---|---|
| `test_api.py` | API FastAPI + interface web intégrée (comparaison A/B en direct dans le navigateur) |
| `batch_compare.py` | Script autonome, sans serveur, pour comparer une liste de questions en ligne de commande |
| `requirements_test.txt` | Dépendances propres à ce dossier de test |

## Installation

```powershell
cd day2_model_testing
pip install -r requirements_test.txt
```

## Option 1 — Interface web (recommandé pour la démo à l'encadrant)

```powershell
uvicorn test_api:app --reload --port 8010
```

Puis ouvrir **http://127.0.0.1:8010** dans le navigateur : un champ de
recherche affiche, côte à côte, le top-5 du modèle de base et du
modèle fine-tuné pour n'importe quelle question tapée.

Endpoints disponibles :
- `GET /` — interface web
- `GET /health` — vérifie que les modèles et le corpus sont bien chargés
- `POST /api/search` — `{"question": "...", "top_k": 5}` → JSON avec les deux jeux de résultats

## Option 2 — Script en ligne de commande (rapide, sans navigateur)

```powershell
python batch_compare.py
```

Modifiez la liste `QUESTIONS_TEST` dans le fichier pour tester vos
propres formulations.

## Que vérifier pendant les tests

1. Le modèle fine-tuné retrouve-t-il le bon chemin en position 1 plus
   souvent que le modèle de base, en particulier sur des formulations
   **éloignées** du libellé exact ?
2. Le cas connu `path_id 152` ("Gestion des Variables", ambigu entre
   plusieurs branches) — comment se comporte-t-il avec des questions
   plus contextualisées (ex. en précisant la catégorie) ?
3. La latence (`base_model_latency_ms` / `finetuned_model_latency_ms`)
   reste-t-elle compatible avec un usage interactif (quelques dizaines
   de ms attendues sur CPU) ?

## Après validation

Une fois les tests concluants, l'intégration réelle dans
`src/embedding/` et `chroma_db/` de production se fera dans un commit
séparé et réversible — ce dossier de test n'est pas modifié pour ça,
il continue de servir de référence de comparaison.