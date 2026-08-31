"""
2_Suivi_Conversations.py
--------------------------
Page reservee aux administrateurs : consultation de TOUTES les
conversations de TOUS les utilisateurs (pas seulement les siennes),
avec filtre par utilisateur, recherche, et un petit tableau de bord.
"""

import sys
import os
import yaml

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.config import AUTH_CONFIG_PATH
from src.admin.user_manager import obtenir_role, bloquer_si_inactif
from src.admin.audit_log import init_audit_log, enregistrer_action
from src.database.history_manager import (
    init_db,
    get_all_conversations,
    get_usernames_avec_conversations,
    get_messages,
    get_stats_globales,
    get_stats_feedback,
    supprimer_conversation,
)


init_db()
init_audit_log()

# ------------------------------------------------------------------
# Authentification (independante de la page principale)
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

st.title("💬 Suivi des conversations")
authenticator.logout("Se deconnecter", "sidebar")

# ------------------------------------------------------------------
# Tableau de bord
# ------------------------------------------------------------------
stats = get_stats_globales()
fb = get_stats_feedback()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Conversations totales", stats["nb_conversations"])
col2.metric("Questions posees", stats["nb_messages_utilisateur"])
col3.metric("👍 Reponses appreciees", fb["likes"])
col4.metric("👎 Reponses mal notees", fb["dislikes"])

if stats["par_mode"]:
    with st.expander("📊 Repartition par mode de reponse"):
        for mode, nb in stats["par_mode"].items():
            st.write(f"**{mode}** : {nb} reponses")

if stats["par_utilisateur"]:
    with st.expander("👥 Activite par utilisateur"):
        for u in stats["par_utilisateur"]:
            st.write(f"**{u['username']}** — {u['nb_conversations']} conversation(s), {u['nb_messages']} question(s)")

if fb["reponses_mal_notees"]:
    with st.expander(f"⚠️ Dernieres reponses mal notees ({len(fb['reponses_mal_notees'])})"):
        for r in fb["reponses_mal_notees"]:
            st.markdown(f"- {r['contenu'][:150]}{'...' if len(r['contenu']) > 150 else ''}")
            if r["chemin_menu"]:
                st.caption(f"Chemin propose : `{r['chemin_menu']}`")

st.markdown("---")

# ------------------------------------------------------------------
# Filtres
# ------------------------------------------------------------------
col_f1, col_f2 = st.columns([1, 2])

with col_f1:
    utilisateurs = ["Tous"] + get_usernames_avec_conversations()
    filtre_user = st.selectbox("Utilisateur", options=utilisateurs)

with col_f2:
    recherche = st.text_input("🔍 Rechercher dans les conversations", placeholder="mot-cle, question...")

username_filtre = None if filtre_user == "Tous" else filtre_user
conversations = get_all_conversations(recherche=recherche or None, username_filtre=username_filtre)

st.caption(f"{len(conversations)} conversation(s) trouvee(s)")

# ------------------------------------------------------------------
# Liste des conversations (accordeon, avec leurs messages)
# ------------------------------------------------------------------
for conv in conversations:
    icone_feedback = ""
    with st.expander(f"👤 {conv['username']} — {conv['titre']}  ·  {conv['updated_at'][:16]}"):
        messages = get_messages(conv["id"])
        for m in messages:
            role_label = "🧑 Utilisateur" if m["role"] == "user" else "🤖 Assistant"
            st.markdown(f"**{role_label}**")
            st.markdown(m["contenu"])
            if m["role"] == "assistant":
                badges = []
                if m.get("mode"):
                    badges.append(f"mode: {m['mode']}")
                if m.get("feedback") == "up":
                    badges.append("👍")
                elif m.get("feedback") == "down":
                    badges.append("👎")
                if badges:
                    st.caption(" · ".join(badges))
            st.markdown("---")

        if st.button("🗑️ Supprimer cette conversation", key=f"del_conv_{conv['id']}"):
            supprimer_conversation(conv["id"])
            enregistrer_action(username, "suppression_conversation", cible=conv["username"], details=conv["titre"])
            st.success("Conversation supprimee.")
            st.rerun()

if not conversations:
    st.info("Aucune conversation ne correspond a ces filtres.")