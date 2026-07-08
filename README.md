# Chatbot de Navigation Menu

Chatbot qui resout une question en langage naturel (ex : *"je veux gerer
les actes RO"*) vers le chemin exact de navigation dans le menu de
l'application desktop (ex : *"Prestations > Referentiel > Actes > Gestion
des Actes RO"*), extrait directement du fichier `menu.xml` (MMB converti).

## Principe de liaison label <-> menu/sous-menu

Le XML n'est **pas imbrique** : chaque `<Menu Name="X">` est une definition
independante, referencee par nom via `SubMenuName` sur les `<MenuItem>`.

- `<MenuItem SubMenuName="Y">` -> noeud, renvoie vers `<Menu Name="Y">`
- `<MenuItem>` sans `SubMenuName` -> feuille (ecran final reel)
- `<MenuModule MainMenu="...">` -> racine de l'arbre

## Pipeline

### Indexation (offline, a relancer a chaque modification de menu.xml)

```
menu.xml -> xml_parser.py -> path_builder.py -> generate_json.py
         -> menu_index.json -> embed_documents.py -> ChromaDB
```

```bash
python scripts/index_data.py
```

### Recherche (au runtime, via l'API)

```
Utilisateur -> API FastAPI -> Sentence Transformer -> Embedding de la question
            -> ChromaDB -> Top-K resultats -> chatbot.py (formulation + gestion ambiguite)
            -> Chemin du menu
```

```bash
uvicorn src.api.app:app --reload --port 8000
```

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "je veux gerer les actes RO"}'
```

## Installation

```bash
pip install -r requirements.txt
python scripts/index_data.py     # premiere indexation
uvicorn src.api.app:app --reload
```

## Structure

```
chatbot-menu-path/
├── data/
│   ├── menu.xml                  # XML source
│   ├── chemins/
│   │   ├── menu_index.json       # base de connaissance {id, label, chemin}
│   │   └── liens_casses.json     # rapport d'anomalies du menu
│   └── chroma_db/                # base vectorielle persistante
├── src/
│   ├── config.py                 # chemins et parametres centralises
│   ├── extraction/                # XML -> chemins -> JSON
│   ├── embedding/                 # texte -> vecteurs
│   ├── database/                  # acces ChromaDB
│   ├── search/                    # recherche Top-K
│   ├── chatbot/                   # formulation reponse + ambiguite
│   └── api/                       # FastAPI
├── scripts/
│   ├── index_data.py             # lance toute l'indexation
│   └── update_index.py           # reindexation apres modif XML
├── tests/
└── requirements.txt
```

## Resultats sur le menu reel (MENU_PREMIUM)

- 182 blocs `<Menu>`
- 1383 chemins de navigation valides extraits
- 0 lien casse, 0 menu orphelin detecte
