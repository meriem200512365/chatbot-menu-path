"""
1_Administration.py
--------------------
Page reservee aux administrateurs : creer/supprimer des utilisateurs,
reinitialiser un mot de passe, changer un role, activer/desactiver un
compte. Chaque action est tracee dans le journal d'audit (voir
src/admin/audit_log.py et src/ui/pages/5_Journal_Admin.py).
"""

import sys
import os
import yaml

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.config import AUTH_CONFIG_PATH
from src.admin.user_manager import (
    lister_utilisateurs,
    ajouter_utilisateur,
    reinitialiser_mot_de_passe,
    modifier_role,
    supprimer_utilisateur,
    definir_statut_actif,
    obtenir_role,
    bloquer_si_inactif,
)
from src.admin.audit_log import init_audit_log, enregistrer_action
from src.database.history_manager import init_db, get_conversations

init_audit_log()
init_db()


# ------------------------------------------------------------------
# Authentification (independante de la page principale : on relit le
# cookie pour que ca marche meme si on arrive directement sur cette page)
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

# ------------------------------------------------------------------
# Verification du role admin
# ------------------------------------------------------------------
if obtenir_role(username) != "admin":
    st.error("⛔ Cette page est reservee aux administrateurs.")
    st.stop()

st.title("🛠️ Administration des utilisateurs")
authenticator.logout("Se deconnecter", "sidebar")

# ------------------------------------------------------------------
# Liste des utilisateurs existants
# ------------------------------------------------------------------
st.subheader("Utilisateurs existants")

utilisateurs = lister_utilisateurs()

for u in utilisateurs:
    nb_conversations = len(get_conversations(u["username"], limit=1000))
    statut_icone = "🟢" if u["actif"] else "⚪"
    role_icone = "👑" if u["role"] == "admin" else "👤"

    with st.expander(f"{statut_icone} {role_icone} {u['username']} — {u['name']}"):
        col_info, col_stats = st.columns(2)
        with col_info:
            st.write(f"**Email :** {u['email'] or '(non renseigne)'}")
            st.write(f"**Role :** {u['role']}")
            st.write(f"**Statut :** {'Actif' if u['actif'] else 'Desactive'}")
        with col_stats:
            st.write(f"**Conversations :** {nb_conversations}")
            derniere = u["derniere_connexion"]
            st.write(f"**Derniere connexion :** {derniere[:16].replace('T', ' ') if derniere else 'Jamais'}")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            nouveau_role = "user" if u["role"] == "admin" else "admin"
            if st.button(f"➜ {nouveau_role}", key=f"role_{u['username']}", help="Changer le role"):
                if u["username"] == username and nouveau_role == "user":
                    st.error("Tu ne peux pas te retirer tes propres droits admin.")
                else:
                    modifier_role(u["username"], nouveau_role)
                    enregistrer_action(
                        username, "modification_role", cible=u["username"],
                        details=f"{u['role']} -> {nouveau_role}",
                    )
                    st.success(f"Role change en {nouveau_role}.")
                    st.rerun()

        with col2:
            with st.popover("🔑 Reset mdp"):
                nouveau_mdp = st.text_input(
                    "Nouveau mot de passe", type="password", key=f"pwd_{u['username']}"
                )
                if st.button("Valider", key=f"pwd_valider_{u['username']}"):
                    if len(nouveau_mdp) < 6:
                        st.error("6 caracteres minimum.")
                    else:
                        reinitialiser_mot_de_passe(u["username"], nouveau_mdp)
                        enregistrer_action(username, "reset_mot_de_passe", cible=u["username"])
                        st.success("Mot de passe reinitialise.")

        with col3:
            label_statut = "🔒 Desactiver" if u["actif"] else "🔓 Activer"
            if st.button(label_statut, key=f"toggle_actif_{u['username']}"):
                if u["username"] == username and u["actif"]:
                    st.error("Tu ne peux pas desactiver ton propre compte.")
                else:
                    nouveau_statut = not u["actif"]
                    definir_statut_actif(u["username"], nouveau_statut)
                    enregistrer_action(
                        username, "activation_utilisateur" if nouveau_statut else "desactivation_utilisateur",
                        cible=u["username"],
                    )
                    st.success(f"Compte {'active' if nouveau_statut else 'desactive'}.")
                    st.rerun()

        with col4:
            if st.button("🗑️ Supprimer", key=f"del_{u['username']}"):
                if u["username"] == username:
                    st.error("Tu ne peux pas supprimer ton propre compte.")
                else:
                    supprimer_utilisateur(u["username"])
                    enregistrer_action(username, "suppression_utilisateur", cible=u["username"])
                    st.success(f"Utilisateur '{u['username']}' supprime.")
                    st.rerun()

st.markdown("---")

# ------------------------------------------------------------------
# Creation d'un nouvel utilisateur
# ------------------------------------------------------------------
st.subheader("➕ Creer un utilisateur")

with st.form("nouvel_utilisateur", clear_on_submit=True):
    col_a, col_b = st.columns(2)
    with col_a:
        new_username = st.text_input("Username (identifiant de connexion)")
        new_name = st.text_input("Nom affiche")
    with col_b:
        new_email = st.text_input("Email")
        new_role = st.selectbox("Role", options=["user", "admin"])

    new_password = st.text_input("Mot de passe initial", type="password")

    submitted = st.form_submit_button("Creer l'utilisateur")

    if submitted:
        try:
            if len(new_password) < 6:
                st.error("Le mot de passe doit faire au moins 6 caracteres.")
            else:
                ajouter_utilisateur(new_username, new_name, new_email, new_password, new_role)
                enregistrer_action(username, "creation_utilisateur", cible=new_username, details=f"role={new_role}")
                st.success(f"Utilisateur '{new_username}' cree avec succes.")
                st.rerun()
        except ValueError as e:
            st.error(str(e))