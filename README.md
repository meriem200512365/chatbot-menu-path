# Chatbot de Navigation Menu

![Tests](https://github.com/meriem200512365/chatbot-menu-path/actions/workflows/tests.yml/badge.svg)

> Projet realise dans le cadre d'un stage chez Cegedim : assistant de
> navigation pour l'application interne de gestion d'assurance
> **Activ'Premium**.

Chatbot qui resout une question en langage naturel (ex : *"je veux gerer
les actes RO"*) vers le chemin exact de navigation dans le menu de
l'application desktop (ex : *"Prestations > Referentiel > Actes > Gestion
des Actes RO"*), extrait directement du fichier `menu.xml` (MMB converti).

Voir [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) et
[`rapport.md`](rapport.md) pour le detail des choix techniques.

## Fonctionnalites

- **Recherche semantique** du chemin de menu a partir d'une question en
  langage naturel (ChromaDB + SentenceTransformer multilingue).
- **Deux modes de reponse** : chemin direct (rapide, deterministe) ou
  reponse redigee par un LLM (RAG, assistant generaliste + resolution de
  chemin quand pertinent).
- **Upload de fichier** (PDF, Excel, CSV, code...) ou d'**image** en
  contexte supplementaire pour le mode RAG (analyse vision via Groq).
- **Authentification** (streamlit-authenticator) et **page
  d'administration** dediee (creation d'utilisateurs, reset mot de passe,
  gestion des roles), sans toucher au fichier de credentials a la main.
- **Historique par conversations** (comme un chatbot classique) :
  creation, recherche, suppression, reprise d'une conversation passee.
- **Feedback 👍/👎** sur chaque reponse, stocke en base pour analyse
  ulterieure des questions mal repondues.
- **Diagnostic du menu source** : detection automatique des liens casses
  et menus orphelins dans `menu.xml`.

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

### Recherche (au runtime)

Deux points d'entree possibles :

- **Interface Streamlit** (usage courant, avec auth/historique/upload) :
  ```bash
  streamlit run src/ui/streamlit_app.py
  ```
- **API FastAPI** (pour une integration externe, ex. depuis l'appli
  desktop Activ'Premium elle-meme) :
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
git clone https://github.com/meriem200512365/chatbot-menu-path.git
cd chatbot-menu-path
python -m venv venv
venv\Scripts\Activate.ps1        # Windows (PowerShell)
# source venv/bin/activate       # Mac/Linux

pip install -r requirements.txt

# Variables d'environnement (cle Groq + modeles LLM)
cp .env.example .env
# -> editer .env et renseigner GROQ_API_KEY (voir console.groq.com/keys)

# Premiere indexation du menu
python scripts/index_data.py

# Config de l'authentification : creer le premier compte admin
python scripts/generate_password.py
# -> coller le hash genere dans config/auth_config.yaml (role: admin)

# Lancer l'interface
streamlit run src/ui/streamlit_app.py
```

⚠️ `config/auth_config.yaml` et `.env` contiennent des secrets (mots de
passe hashes, cle API, cle de signature des cookies) : ils sont dans
`.gitignore` et ne doivent **jamais** etre commit.

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
├── assets/
│   └── cegedim_logo.png          # logo affiche dans l'interface
├── config/
│   └── auth_config.yaml          # comptes utilisateurs (non versionne)
├── data/
│   ├── menu.xml                  # XML source
│   ├── chemins/
│   │   ├── menu_index.json       # base de connaissance {id, label, chemin}
│   │   └── liens_casses.json     # rapport d'anomalies du menu
│   ├── chroma_db/                # base vectorielle persistante (non versionnee)
│   └── history.db                # historique des conversations (non versionne)
├── src/
│   ├── config.py                 # chemins, seuils et parametres centralises
│   ├── extraction/               # XML -> chemins -> JSON
│   ├── embedding/                # texte -> vecteurs
│   ├── database/                 # acces ChromaDB + historique SQLite
│   ├── search/                   # recherche Top-K
│   ├── chatbot/                  # formulation reponse + ambiguite (mode direct)
│   ├── generation/                # RAG + LLM (Groq) + analyse d'images (vision)
│   ├── files/                    # extraction de texte depuis fichiers uploades
│   ├── admin/                    # gestion des utilisateurs (creation, reset mdp, roles)
│   ├── ui/                       # interface Streamlit (chat + page Administration)
│   └── api/                      # FastAPI (integration externe)
├── scripts/
│   ├── index_data.py             # lance toute l'indexation
│   ├── update_index.py           # reindexation apres modif XML
│   └── generate_password.py      # genere un hash bcrypt pour un nouvel utilisateur
├── tests/                        # tests unitaires (pytest)
├── notebooks/                    # exploration et evaluation (executes sur Google Colab)
├── docs/
│   └── ARCHITECTURE.md           # choix techniques + schema du pipeline
├── rapport.md                    # rapport detaille du projet (stage)
├── .github/workflows/tests.yml   # CI : lance pytest a chaque push
├── .env.example                  # variables d'environnement necessaires
└── requirements.txt
```

## Resultats sur le menu reel (MENU_PREMIUM)

- 182 blocs `<Menu>`
- 1383 chemins de navigation valides extraits
- 0 lien casse, 0 menu orphelin detecte