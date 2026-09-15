"""
parametres_view.py
--------------------
Page "Parametres". Volontairement sobre : l'application n'a pas
(encore) de table de preferences utilisateur persistees en base, donc
cette page ne propose que ce qui est reellement actionnable des
maintenant (le mode de reponse par defaut pour la session en cours),
plutot que d'afficher des reglages qui ne feraient rien concretement.

Navigue via src/ui/streamlit_app.py (le routeur). Ne pas lancer
directement.
"""

import sys
import os
import yaml

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config import AUTH_CONFIG_PATH
from src.admin.user_manager import bloquer_si_inactif
from src.ui.theme import inject_theme

inject_theme()

with open(AUTH_CONFIG_PATH) as f:
    auth_config = yaml.safe_load(f)

if st.session_state.get("authentication_status") is not True:
    st.warning("Merci de te connecter depuis la page principale.")
    st.stop()

username = st.session_state["username"]
bloquer_si_inactif(username)

st.markdown("""
<div class="cg-hero" style="text-align:left; padding-left:2px;">
    <div class="cg-hero-greeting">⚙️ Paramètres</div>
</div>
""", unsafe_allow_html=True)

MODE_DIRECT = "\u26a1 Chemin direct"
MODE_RAG = "\U0001f9e0 R\u00e9ponse r\u00e9dig\u00e9e (RAG + LLM)"

if "mode_reponse" not in st.session_state:
    st.session_state.mode_reponse = MODE_DIRECT

with st.container(border=True):
    st.markdown("**Mode de réponse par défaut**")
    st.caption("S'applique pour le reste de cette session (jusqu'à déconnexion).")
    st.segmented_control(
        "Mode de réponse par défaut",
        options=[MODE_DIRECT, MODE_RAG],
        key="mode_reponse",
        label_visibility="collapsed",
    )

st.caption(
    "D'autres préférences (thème, langue, notifications) pourront être "
    "ajoutées ici une fois qu'une table de préférences utilisateur "
    "persistées existera côté base de données."
)