"""
config.py
---------
Configuration centralisee du projet : tous les chemins et parametres
sont definis ici, pour eviter de les coder en dur dans chaque script.
"""

import os

# Racine du projet (dossier parent de src/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Donnees source ---
XML_PATH = os.path.join(BASE_DIR, "data", "menu.xml")

# --- Donnees generees (extraction) ---
CHEMINS_DIR = os.path.join(BASE_DIR, "data", "chemins")
MENU_INDEX_JSON = os.path.join(CHEMINS_DIR, "menu_index.json")
LIENS_CASSES_JSON = os.path.join(CHEMINS_DIR, "liens_casses.json")

# --- Base vectorielle ---
CHROMA_DB_DIR = os.path.join(BASE_DIR, "data", "chroma_db")
CHROMA_COLLECTION_NAME = "menu_premium"

# --- Modele d'embeddings ---
# Modele multilingue leger, adapte au francais, bon compromis taille/qualite
EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# --- Racine du menu XML ---
MAIN_MENU_ATTR = "MainMenu"  # attribut sur <MenuModule>

# --- Recherche ---
TOP_K = 3                 # nombre de resultats a retourner
MAX_DEPTH = 20             # profondeur max de parcours (garde-fou anti boucle infinie)

# --- Generation (LLM - couche RAG) ---
# La cle est lue depuis une variable d'environnement, JAMAIS codee en dur ici.
# Definis-la avant de lancer l'appli :
#   Windows (PowerShell) : $env:GROQ_API_KEY="ta_cle"
#   Mac/Linux            : export GROQ_API_KEY="ta_cle"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"
RAG_TOP_K = 5              # nb de chemins fournis en contexte au LLM (plus que TOP_K du simple retrieval)
