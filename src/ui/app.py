"""
streamlit_app.py
-----------------
Interface utilisateur du chatbot de navigation menu.

Lancement :
    streamlit run src/ui/streamlit_app.py

Deux modes possibles (voir USE_API plus bas) :
    - False (par defaut) : appelle directement src.chatbot.chatbot.repondre()
      -> plus simple, pas besoin de lancer l'API a part.
    - True  : appelle l'API FastAPI via HTTP (utile si le vrai chatbot
      tourne sur un autre serveur / sera integre a l'appli desktop plus tard).
"""

import sys
import os
import json

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config import LIENS_CASSES_JSON, MENU_INDEX_JSON

USE_API = False
API_URL = "http://localhost:8000/chat"


# ------------------------------------------------------------------
# Configuration generale de la page
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Assistant Navigation Menu",
    page_icon="🧭",
    layout="centered",
)


# ------------------------------------------------------------------
# Chargement mis en cache (evite de recharger le modele a chaque interaction)
# ------------------------------------------------------------------
@st.cache_resource
def get_chatbot_fn():
    """Charge la fonction repondre() une seule fois (le modele d'embedding
    et la connexion ChromaDB sont geres en interne avec leurs propres caches)."""
    from src.chatbot.chatbot import repondre
    return repondre


@st.cache_resource
def get_rag_fn():
    """Charge la fonction RAG (retrieval + generation LLM) une seule fois."""
    from src.generation.rag_chatbot import repondre_rag
    return repondre_rag


@st.cache_data
def get_stats():
    """Charge les statistiques d'indexation pour les afficher dans la sidebar."""
    stats = {"nb_chemins": None, "nb_liens_casses": None, "nb_menus_orphelins": None}
    try:
        with open(MENU_INDEX_JSON, encoding="utf-8") as f:
            stats["nb_chemins"] = len(json.load(f))
    except FileNotFoundError:
        pass
    try:
        with open(LIENS_CASSES_JSON, encoding="utf-8") as f:
            report = json.load(f)
            stats["nb_liens_casses"] = report.get("nb_liens_casses")
            stats["nb_menus_orphelins"] = report.get("nb_menus_orphelins")
    except FileNotFoundError:
        pass
    return stats


def call_chatbot(question: str) -> dict:
    if USE_API:
        import requests
        resp = requests.post(API_URL, json={"question": question}, timeout=10)
        resp.raise_for_status()
        return resp.json()
    else:
        repondre = get_chatbot_fn()
        return repondre(question)


# ------------------------------------------------------------------
# Sidebar : infos sur l'index (utile pour ton rapport / demo au jury)
# ------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 📊 Etat de l'index")
    stats = get_stats()
    if stats["nb_chemins"] is not None:
        st.metric("Chemins indexes", stats["nb_chemins"])
        st.metric("Liens casses detectes", stats["nb_liens_casses"])
        st.metric("Menus orphelins", stats["nb_menus_orphelins"])
    else:
        st.warning(
            "Aucun index trouve. Lance d'abord :\n\n"
            "`python scripts/index_data.py`"
        )

    st.markdown("---")
    mode = st.radio(
        "Mode de reponse",
        options=["Chemin direct (rapide)", "Reponse redigee (RAG + LLM)"],
        help=(
            "Chemin direct : retrieval seul, renvoie juste le chemin exact.\n\n"
            "Reponse redigee : retrieval + LLM (Groq), redige une explication "
            "en langage naturel a partir des chemins trouves."
        ),
    )

    st.markdown("---")
    st.markdown(
        "**Exemples de questions :**\n"
        "- je veux gerer les actes RO\n"
        "- comment annuler un cheque\n"
        "- parametrage des devis web"
    )


# ------------------------------------------------------------------
# Corps principal : interface de chat
# ------------------------------------------------------------------
st.title("🧭 Assistant Navigation Menu")
st.caption("Pose ta question en langage naturel, je te donne le chemin exact dans le menu.")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Affiche l'historique de la conversation
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Zone de saisie utilisateur
question = st.chat_input("Ex : je veux gerer les actes RO")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        mode_rag = mode.startswith("Reponse")

        if mode_rag:
            with st.spinner("Recherche + redaction de la reponse (LLM)..."):
                try:
                    repondre_rag = get_rag_fn()
                    resultat = repondre_rag(question)
                except Exception as e:
                    st.error(f"Erreur lors de l'appel au RAG : {e}")
                    resultat = None

            if resultat:
                if resultat["type"] == "rag_reponse":
                    st.markdown(resultat["reponse"])
                    with st.expander("📄 Chemins utilises comme source"):
                        for s in resultat["chemins_sources"]:
                            st.markdown(f"- `{s['path_str']}`  (pertinence: {1 - s['distance']:.2f})")
                else:  # rag_hors_contexte
                    st.info(resultat["reponse"])

                st.session_state.messages.append({"role": "assistant", "content": resultat["reponse"]})

        else:
            with st.spinner("Recherche du chemin..."):
                try:
                    reponse = call_chatbot(question)
                except Exception as e:
                    st.error(f"Erreur lors de l'appel au chatbot : {e}")
                    reponse = None

            if reponse:
                if reponse["type"] == "reponse_directe":
                    st.success(reponse["message"])
                    st.code(reponse["resultats"][0]["path_str"], language=None)

                elif reponse["type"] == "ambigu":
                    st.warning(reponse["message"])
                    for r in reponse["resultats"]:
                        st.markdown(f"- `{r['path_str']}`")

                else:  # aucun_resultat
                    st.info(reponse["message"])

                # Sauvegarde du texte affiche dans l'historique
                texte_final = reponse["message"]
                if reponse["type"] == "reponse_directe":
                    texte_final += f"\n\n`{reponse['resultats'][0]['path_str']}`"
                st.session_state.messages.append({"role": "assistant", "content": texte_final})


# Bouton pour reinitialiser la conversation
if st.session_state.messages:
    if st.button("🗑️ Effacer la conversation"):
        st.session_state.messages = []
        st.rerun()
