# Chatbot de Navigation Menu

![Tests](https://github.com/meriem200512365/Chat-boot-cegedim/actions/workflows/tests.yml/badge.svg)

> Projet realise dans le cadre d'un stage chez Cegedim : assistant de
> navigation pour l'application interne de gestion d'assurance
> **Activ'Premium**.

Chatbot qui resout une question en langage naturel (ex : *"je veux gerer
les actes RO"*) vers le chemin exact de navigation dans le menu de
l'application desktop (ex : *"Prestations > Referentiel > Actes > Gestion
des Actes RO"*), extrait directement du fichier `menu.xml` (MMB converti).

Voir [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) pour le detail des
choix techniques et un schema du pipeline.

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

# Copier le fichier d'exemple et renseigner ta cle Groq (necessaire
# uniquement pour le mode "reponse redigee" / RAG + LLM)
cp .env.example .env

python scripts/index_data.py     # premiere indexation
uvicorn src.api.app:app --reload
```

## Tests

```bash
pytest -v
```

Les tests couvrent le parsing XML, la reconstruction des chemins (cas
nominal, lien casse, menu orphelin, boucle), la generation des JSON, et
la logique de decision du chatbot (reponse directe / ambigue / aucun
resultat). Ils tournent sur des donnees factices en memoire, pas sur le
vrai `menu.xml`, et n'appellent jamais le vrai modele d'embeddings ni
ChromaDB. Un workflow GitHub Actions (`.github/workflows/tests.yml`)
les relance automatiquement a chaque push.

## Structure

```
chatbot-menu-path/
├── data/
│   ├── menu.xml                  # XML source
│   ├── chemins/
│   │   ├── menu_index.json       # base de connaissance {id, label, chemin}
│   │   └── liens_casses.json     # rapport d'anomalies du menu
│   └── chroma_db/                # base vectorielle persistante (non versionnee)
├── src/
│   ├── config.py                 # chemins et parametres centralises
│   ├── extraction/                # XML -> chemins -> JSON
│   ├── embedding/                 # texte -> vecteurs
│   ├── database/                  # acces ChromaDB
│   ├── search/                    # recherche Top-K
│   ├── chatbot/                   # formulation reponse + ambiguite
│   ├── generation/                 # variante RAG + LLM (Groq)
│   ├── ui/                        # interface de demo Streamlit
│   └── api/                       # FastAPI
├── scripts/
│   ├── index_data.py             # lance toute l'indexation
│   └── update_index.py           # reindexation apres modif XML
├── tests/                        # tests unitaires (pytest)
├── docs/
│   └── ARCHITECTURE.md           # choix techniques + schema du pipeline
├── .github/workflows/tests.yml   # CI : lance pytest a chaque push
├── .env.example                  # variables d'environnement necessaires
└── requirements.txt
```

## Resultats sur le menu reel (MENU_PREMIUM)

- 182 blocs `<Menu>`
- 1383 chemins de navigation valides extraits
- 0 lien casse, 0 menu orphelin detecte
