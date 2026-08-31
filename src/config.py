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

# Modele fine-tune sur le domaine metier Cegedim (voir dataset/, models/,
# notebooks/fine_tuning_menu_model.ipynb pour le detail de l'entrainement).
# Ancien modele (avant fine-tuning), garde ici pour reference/rollback :
#   EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_MODEL_NAME = os.path.join(BASE_DIR, "models", "cegedim-menu-embedding")

# --- Racine du menu XML ---
MAIN_MENU_ATTR = "MainMenu"  # attribut sur <MenuModule>

# --- Recherche ---
TOP_K = 3                 # nombre de resultats a retourner
MAX_DEPTH = 20             # profondeur max de parcours (garde-fou anti boucle infinie)

# --- Seuils de confiance de la recherche semantique (distance cosinus, 0 = identique) ---
# UTILISES A LA FOIS par src/chatbot/chatbot.py et src/generation/rag_chatbot.py :
# ne PAS dupliquer ces valeurs ailleurs, toujours importer depuis ce fichier.
#   - distance < SEUIL_DISTANCE_CONFIANT  -> reponse tres confiante
#   - distance < SEUIL_DISTANCE_FIABLE    -> encore considere comme fiable
#   - distance >= SEUIL_DISTANCE_FIABLE   -> pas fiable / hors sujet
SEUIL_DISTANCE_CONFIANT = 0.30
SEUIL_DISTANCE_FIABLE = 0.55
ECART_AMBIGUITE = 0.05  # si le 2e resultat est tres proche du 1er -> ambigu


# --- Historique des conversations ---
HISTORY_DB_PATH = os.path.join(BASE_DIR, "data", "history.db")

# --- Authentification ---
AUTH_CONFIG_PATH = os.path.join(BASE_DIR, "config", "auth_config.yaml")

# --- Dictionnaire de synonymes / alias metier (gere depuis l'admin) ---
SYNONYMES_JSON = os.path.join(BASE_DIR, "data", "synonymes.json")

# --- Generation (LLM - couche RAG) ---
# La cle est lue depuis une variable d'environnement, JAMAIS codee en dur ici.
# Definis-la avant de lancer l'appli :
#   Windows (PowerShell) : $env:GROQ_API_KEY="ta_cle"
#   Mac/Linux            : export GROQ_API_KEY="ta_cle"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
# Configurable via .env pour ne pas avoir a modifier le code quand Groq
# deprecie/renomme un modele. Verifie les modeles disponibles sur :
# https://console.groq.com/docs/models
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
# ATTENTION : au 18/08/2026, Groq ne liste plus aucun modele vision dans son
# catalogue de production/preview. Cette valeur par defaut n'est peut-etre
# plus valide -- verifie via `curl https://api.groq.com/openai/v1/models`
# avant de compter sur le mode "joindre une image".
GROQ_VISION_MODEL = os.environ.get("GROQ_VISION_MODEL", "qwen/qwen3.6-27b")
RAG_TOP_K = 5              # nb de chemins fournis en contexte au LLM (plus que TOP_K du simple retrieval)