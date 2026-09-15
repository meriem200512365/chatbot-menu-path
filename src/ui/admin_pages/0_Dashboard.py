"""
0_Dashboard.py
---------------
Page d'accueil admin (Administration Dashboard) -- remplace le renvoi
direct vers la page Assistant pour un admin. Prefixee "0_" pour rester
en premiere position dans admin_pages/, et enregistree comme page
`default=True` pour le role admin dans streamlit_app.py.

Toutes les statistiques viennent de fonctions DEJA existantes
(history_manager.get_stats_globales, user_manager.lister_utilisateurs)
-- rien n'est invente ni duplique, cette page ne fait qu'assembler des
donnees reelles deja calculees ailleurs.
"""

import sys
import os
import yaml

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.config import AUTH_CONFIG_PATH
from src.admin.user_manager import lister_utilisateurs, obtenir_role, bloquer_si_inactif
from src.database.history_manager import init_db, get_stats_globales
from src.ui.theme import inject_theme

init_db()
inject_theme()

# ------------------------------------------------------------------
# Authentification + verification du role (meme pattern que les autres
# pages admin existantes, ex. 1_Administration.py)
# ------------------------------------------------------------------
with open(AUTH_CONFIG_PATH) as f:
    auth_config = yaml.safe_load(f)

authenticator = st.session_state["authenticator"]

if st.session_state.get("authentication_status") is not True:
    st.warning("Merci de te connecter depuis la page principale.")
    st.stop()

username = st.session_state["username"]
name = st.session_state.get("name", username)
bloquer_si_inactif(username)

if obtenir_role(username) != "admin":
    st.error("⛔ Cette page est reservee aux administrateurs.")
    st.stop()

premier_prenom = name.split(" ")[0] if name else username

# ------------------------------------------------------------------
# En-tete
# ------------------------------------------------------------------
st.markdown(f"""
<div class="cg-hero" style="text-align:left; padding-left:2px;">
    <div class="cg-hero-greeting">Bonjour, {premier_prenom} 👋</div>
    <div class="cg-hero-sub">Bienvenue dans l'espace d'administration.</div>
</div>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# Cartes statistiques -- donnees reelles
# ------------------------------------------------------------------
nb_utilisateurs = len(lister_utilisateurs())
stats = get_stats_globales()
nb_conversations = stats["nb_conversations"]
nb_recherches = stats["nb_messages_utilisateur"]

col1, col2, col3 = st.columns(3)
for col, icon, valeur, label in [
    (col1, "👥", nb_utilisateurs, "Utilisateurs"),
    (col2, "💬", nb_conversations, "Conversations"),
    (col3, "🔎", nb_recherches, "Recherches"),
]:
    with col:
        with st.container(border=True):
            st.markdown(f"""
            <div class="cg-card">
                <div class="cg-card-icon">{icon}</div>
                <div class="cg-stat-value">{valeur:,}</div>
                <div class="cg-stat-label">{label}</div>
            </div>
            """.replace(",", " "), unsafe_allow_html=True)

# ------------------------------------------------------------------
# Gestion rapide -- raccourcis vers les pages admin EXISTANTES
# (aucune nouvelle logique de gestion ici, juste des liens)
# ------------------------------------------------------------------
st.markdown('<div class="cg-section-title">Gestion rapide</div>', unsafe_allow_html=True)

RACCOURCIS = [
    ("👥", "Utilisateurs", "Créer / modifier les utilisateurs", "admin_pages/1_Administration.py"),
    ("🗂️", "Gestion du menu", "Gérer les chemins et l'indexation", "admin_pages/4_Gestion_Menu.py"),
    ("📊", "Statistiques", "Utilisation du chatbot", "admin_pages/2_Suivi_Conversations.py"),
    ("📝", "Journal Admin", "Activités admin", "admin_pages/5_Journal_Admin.py"),
]

cols = st.columns(2)
for i, (icon, titre, sous_titre, page_path) in enumerate(RACCOURCIS):
    with cols[i % 2]:
        with st.container(border=True):
            if st.button(f"{icon}  {titre}\n{sous_titre}   [ Ouvrir → ]",
                         key=f"raccourci_{titre}", use_container_width=True):
                st.switch_page(page_path)