"""
profil_view.py
---------------
Page "Mon profil" -- informations du compte connecte et consommation
de tokens du mois. Reutilise les fonctions existantes
(user_manager.obtenir_quota_tokens, history_manager.get_consommation_mois_courant)
deja utilisees dans la barre superieure de chat_view.py -- pas de
nouvelle logique de calcul ici, juste un affichage dedie.

Navigue via src/ui/streamlit_app.py (le routeur). Ne pas lancer
directement.
"""

import sys
import os
import yaml

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config import AUTH_CONFIG_PATH
from src.admin.user_manager import obtenir_quota_tokens, obtenir_role, bloquer_si_inactif
from src.database.history_manager import init_db, get_consommation_mois_courant
from src.ui.theme import inject_theme

init_db()
inject_theme()

with open(AUTH_CONFIG_PATH) as f:
    auth_config = yaml.safe_load(f)

if st.session_state.get("authentication_status") is not True:
    st.warning("Merci de te connecter depuis la page principale.")
    st.stop()

username = st.session_state["username"]
name = st.session_state.get("name", username)
email = auth_config["credentials"]["usernames"].get(username, {}).get("email", "")
bloquer_si_inactif(username)

role = obtenir_role(username)
quota = obtenir_quota_tokens(username)
consommation = get_consommation_mois_courant(username)
tokens_total = consommation["tokens_total"]

st.markdown(f"""
<div class="cg-hero" style="text-align:left; padding-left:2px;">
    <div class="cg-hero-greeting">👤 Mon profil</div>
</div>
""", unsafe_allow_html=True)

with st.container(border=True):
    initiale = (name or username)[:1].upper()
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:16px; padding:6px 4px;">
        <div style="width:56px; height:56px; border-radius:50%; background:var(--cg-accent);
                    color:#04131f; font-weight:800; font-size:1.4rem; display:flex;
                    align-items:center; justify-content:center;">{initiale}</div>
        <div>
            <div style="font-weight:700; font-size:1.1rem; color:var(--cg-text);">{name}</div>
            <div style="font-size:0.85rem; color:var(--cg-text-dim);">{email or "—"}</div>
            <div style="font-size:0.78rem; color:var(--cg-accent); margin-top:2px;">
                {"🛠️ Administrateur" if role == "admin" else "Utilisateur"}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="cg-section-title">Consommation de tokens (mois en cours)</div>', unsafe_allow_html=True)

with st.container(border=True):
    if quota:
        ratio = min(tokens_total / quota, 1.0) if quota else 0
        st.progress(ratio, text=f"{tokens_total:,} / {quota:,} tokens".replace(",", " "))
    else:
        st.markdown(f"**{tokens_total:,} tokens** consommés ce mois (aucun quota défini).".replace(",", " "))
    st.caption(
        f"Entrée : {consommation.get('tokens_input', 0):,} · "
        f"Sortie : {consommation.get('tokens_output', 0):,}".replace(",", " ")
    )