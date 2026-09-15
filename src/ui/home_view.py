"""
home_view.py
-------------
Page d'accueil affichee par defaut apres connexion pour un utilisateur
NORMAL (pas admin). Objectif : eviter d'envoyer l'utilisateur direct
dans un chat vide -- on lui propose une grande barre de recherche, des
raccourcis par categorie, des exemples de questions, et ses recherches
recentes (reutilisation intelligente de l'historique deja existant en
base, pas une nouvelle fonctionnalite de stockage).

Cliquer sur la recherche / une suggestion / une recherche recente
bascule vers la page Assistant (chat_view.py) avec la question deja
prete a etre traitee (voir le petit ajout dans chat_view.py qui lit
st.session_state["prefill_question"]).

Navigue via src/ui/streamlit_app.py (le routeur). Ne pas lancer
directement.
"""

import sys
import os
import yaml
from datetime import datetime

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config import AUTH_CONFIG_PATH
from src.admin.user_manager import bloquer_si_inactif
from src.database.history_manager import init_db, get_conversations, get_messages
from src.ui.theme import inject_theme

LOGO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "cegedim_logo.png",
)

init_db()
inject_theme()

# ------------------------------------------------------------------
# Authentification -- deja geree par streamlit_app.py (le routeur).
# On relit juste les valeurs de session_state deja renseignees, sans
# recreer d'instance Authenticate (voir le meme commentaire dans
# chat_view.py pour la raison exacte : StreamlitDuplicateElementKey).
# ------------------------------------------------------------------
with open(AUTH_CONFIG_PATH) as f:
    auth_config = yaml.safe_load(f)

if st.session_state.get("authentication_status") is not True:
    st.warning("Merci de te connecter depuis la page principale.")
    st.stop()

username = st.session_state["username"]
name = st.session_state["name"]
bloquer_si_inactif(username)

premier_prenom = name.split(" ")[0] if name else username

# ------------------------------------------------------------------
# Suggestions rapides par categorie -- chaque carte pre-remplit une
# question type dans l'Assistant. Les 4 categories reprennent les
# grandes familles visibles dans le menu reel (Actes, Facturation /
# Cotisations, Parametrage, Referentiel).
# ------------------------------------------------------------------
SUGGESTIONS = [
    ("📋", "Actes", "Trouver un écran", "je veux gérer les actes RO"),
    ("💳", "Facturation", "Trouver un écran", "je veux gérer la facturation"),
    ("⚙️", "Paramétrage", "Trouver un écran", "comment paramétrer les couleurs de l'appli"),
    ("📑", "Référentiel", "Trouver un écran", "je veux accéder au référentiel"),
]

EXEMPLES = [
    "Je veux gérer les actes RO",
    "Où trouver le paramétrage des contrats ?",
    "Comment accéder à la gestion des assurés ?",
]


def aller_vers_assistant(question: str):
    """Pre-remplit la question et bascule sur la page Assistant."""
    st.session_state["prefill_question"] = question
    st.switch_page("chat_view.py")


def ouvrir_conversation(conv_id: int):
    """Charge une conversation existante puis bascule sur l'Assistant,
    exactement comme le fait charger_conversation() dans chat_view.py."""
    st.session_state.current_conversation_id = conv_id
    st.session_state.messages = [
        {"role": m["role"], "content": m["contenu"], "id": m["id"], "feedback": m["feedback"]}
        for m in get_messages(conv_id)
    ]
    st.switch_page("chat_view.py")


# ------------------------------------------------------------------
# Hero : salutation + grande barre de recherche
# ------------------------------------------------------------------
st.markdown(f"""
<div class="cg-hero">
    <div class="cg-hero-greeting">Bonjour, {premier_prenom} 👋</div>
    <div class="cg-hero-sub">Que souhaitez-vous trouver aujourd'hui ?</div>
</div>
""", unsafe_allow_html=True)

col_l, col_c, col_r = st.columns([1, 4, 1])
with col_c:
    with st.form("recherche_accueil", clear_on_submit=False, border=False):
        col_input, col_btn = st.columns([6, 1], vertical_alignment="bottom")
        with col_input:
            requete = st.text_input(
                "Recherche",
                placeholder='🔎  Ex : "Je veux gérer les actes RO"',
                label_visibility="collapsed",
            )
        with col_btn:
            lance = st.form_submit_button("➤", use_container_width=True)
    if lance and requete.strip():
        aller_vers_assistant(requete.strip())

# ------------------------------------------------------------------
# Suggestions rapides
# ------------------------------------------------------------------
st.markdown('<div class="cg-section-title">Suggestions rapides</div>', unsafe_allow_html=True)

cols = st.columns(4)
for col, (icon, titre, sous_titre, question) in zip(cols, SUGGESTIONS):
    with col:
        with st.container(border=True):
            if st.button(f"{icon}  {titre}\n{sous_titre}", key=f"sugg_{titre}", use_container_width=True):
                aller_vers_assistant(question)

# ------------------------------------------------------------------
# Exemples de questions
# ------------------------------------------------------------------
st.markdown('<div class="cg-section-title">💡 Exemples de questions</div>', unsafe_allow_html=True)
for ex in EXEMPLES:
    st.markdown(f"- {ex}")

# ------------------------------------------------------------------
# Recherches recentes -- reutilisation directe de l'historique deja
# stocke en base (history_manager), pas de nouveau systeme de suivi.
# ------------------------------------------------------------------
st.markdown('<div class="cg-section-title">🕘 Recherches récentes</div>', unsafe_allow_html=True)

conversations_recentes = get_conversations(username, limit=3)

if conversations_recentes:
    for conv in conversations_recentes:
        messages = get_messages(conv["id"])
        premiere_reponse = next((m for m in messages if m["role"] == "assistant"), None)
        chemin = premiere_reponse.get("chemin_menu") if premiere_reponse else None

        with st.container(border=True):
            col_txt, col_btn = st.columns([5, 1], vertical_alignment="center")
            with col_txt:
                st.markdown(f"""
                <div class="cg-recent-card">
                    <div class="cg-recent-q">🔎 {conv['titre']}</div>
                    <div class="cg-recent-a">{chemin or "— (pas de chemin unique, reponse redigee)"}</div>
                </div>
                """, unsafe_allow_html=True)
            with col_btn:
                if st.button("Ouvrir →", key=f"ouvrir_{conv['id']}", use_container_width=True):
                    ouvrir_conversation(conv["id"])
else:
    st.caption("Aucune recherche pour l'instant -- lancez-vous avec la barre ci-dessus.")