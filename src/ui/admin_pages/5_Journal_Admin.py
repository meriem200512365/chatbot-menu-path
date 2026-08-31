"""
5_Journal_Admin.py
---------------------
Page reservee aux administrateurs : journal de toutes les actions
sensibles effectuees depuis le dashboard admin (utilisateurs, menu,
tokens, conversations), avec qui/quoi/quand.
"""

import sys
import os
import yaml

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.config import AUTH_CONFIG_PATH
from src.admin.user_manager import obtenir_role, bloquer_si_inactif
from src.admin.audit_log import init_audit_log, lister_actions, lister_admins_ayant_agi


init_audit_log()

# ------------------------------------------------------------------
# Authentification
# ------------------------------------------------------------------
with open(AUTH_CONFIG_PATH) as f:
    auth_config = yaml.safe_load(f)

# Authentification deja geree par streamlit_app.py (le routeur) avant
# l'execution de cette page via pg.run(). On reutilise l'instance
# partagee au lieu d'en recreer une (2e CookieManager => cle Streamlit
# dupliquee 'init' => StreamlitDuplicateElementKey).
authenticator = st.session_state["authenticator"]

if st.session_state.get("authentication_status") is not True:
    st.warning("Merci de te connecter depuis la page principale.")
    st.stop()

username = st.session_state["username"]
bloquer_si_inactif(username)

if obtenir_role(username) != "admin":
    st.error("⛔ Cette page est reservee aux administrateurs.")
    st.stop()

st.title("📜 Journal d'audit")
authenticator.logout("Se deconnecter", "sidebar")

st.caption(
    "Trace toutes les actions sensibles effectuees depuis le dashboard "
    "admin : creation/suppression d'utilisateurs, changements de role, "
    "activation/desactivation, quotas de tokens, modifications du menu "
    "(synonymes, sauvegardes, reindexation), suppressions de conversations."
)

# ------------------------------------------------------------------
# Filtres
# ------------------------------------------------------------------
LABELS_ACTIONS = {
    "creation_utilisateur": "👤 Creation d'utilisateur",
    "suppression_utilisateur": "🗑️ Suppression d'utilisateur",
    "modification_role": "🔄 Changement de role",
    "reset_mot_de_passe": "🔑 Reset mot de passe",
    "activation_utilisateur": "🔓 Activation de compte",
    "desactivation_utilisateur": "🔒 Desactivation de compte",
    "modification_quota": "🎟️ Modification de quota",
    "suppression_conversation": "💬 Suppression de conversation",
    "ajout_synonyme": "🔤 Ajout de synonyme",
    "suppression_synonyme": "🔤 Suppression de synonyme",
    "restauration_backup": "♻️ Restauration de sauvegarde menu",
    "reindexation": "🔄 Reindexation du menu",
}

col_f1, col_f2 = st.columns(2)
with col_f1:
    admins = ["Tous"] + lister_admins_ayant_agi()
    filtre_admin = st.selectbox("Administrateur", options=admins)
with col_f2:
    actions_disponibles = ["Toutes"] + list(LABELS_ACTIONS.keys())
    filtre_action = st.selectbox(
        "Type d'action", options=actions_disponibles,
        format_func=lambda a: "Toutes" if a == "Toutes" else LABELS_ACTIONS.get(a, a),
    )

actions = lister_actions(
    filtre_admin=None if filtre_admin == "Tous" else filtre_admin,
    filtre_action=None if filtre_action == "Toutes" else filtre_action,
)

st.caption(f"{len(actions)} action(s) enregistree(s)")

# ------------------------------------------------------------------
# Tableau du journal
# ------------------------------------------------------------------
if actions:
    for a in actions:
        label = LABELS_ACTIONS.get(a["action"], a["action"])
        horodatage = a["timestamp"][:16].replace("T", " ")
        ligne = f"**{horodatage}** · {label} · admin : `{a['admin_username']}`"
        if a["cible"]:
            ligne += f" · cible : `{a['cible']}`"
        st.markdown(ligne)
        if a["details"]:
            st.caption(a["details"])
        st.markdown("---")
else:
    st.info("Aucune action enregistree pour ces filtres.")