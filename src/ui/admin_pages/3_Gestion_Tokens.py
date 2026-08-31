"""
3_Gestion_Tokens.py
---------------------
Page reservee aux administrateurs : suivi de la consommation de tokens
(mois en cours) par utilisateur, et gestion des quotas informatifs.

IMPORTANT : les quotas sont purement INFORMATIFS. Aucun utilisateur n'est
bloque en cas de depassement -- un simple avertissement lui est affiche
dans l'interface de chat (voir src/ui/streamlit_app.py).
"""

import sys
import os
import yaml

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.config import AUTH_CONFIG_PATH
from src.admin.user_manager import obtenir_role, lister_utilisateurs, definir_quota_tokens, bloquer_si_inactif
from src.admin.audit_log import init_audit_log, enregistrer_action
from src.database.history_manager import init_db, get_consommation_tous_utilisateurs


init_db()
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

admin_username = st.session_state["username"]
bloquer_si_inactif(admin_username)

if obtenir_role(admin_username) != "admin":
    st.error("⛔ Cette page est reservee aux administrateurs.")
    st.stop()

st.title("🎟️ Gestion des tokens")
authenticator.logout("Se deconnecter", "sidebar")

st.info(
    "Les quotas definis ici sont **informatifs uniquement**. Un utilisateur qui "
    "depasse son quota voit un avertissement dans son interface, mais n'est "
    "**jamais bloque**."
)

# ------------------------------------------------------------------
# Consommation du mois en cours
# ------------------------------------------------------------------
st.subheader("📊 Consommation ce mois-ci")

consommation = get_consommation_tous_utilisateurs()
quotas = {u["username"]: u["quota_tokens"] for u in lister_utilisateurs()}

if consommation:
    for c in consommation:
        quota = quotas.get(c["username"])
        depasse = quota and c["tokens_total"] >= quota

        with st.container():
            col1, col2 = st.columns([3, 2])
            with col1:
                label = f"{'🔴' if depasse else '🟢'} **{c['username']}**"
                st.markdown(label)
                st.caption(f"input: {c['tokens_input']:,} · output: {c['tokens_output']:,}")
            with col2:
                if quota:
                    ratio = min(c["tokens_total"] / quota, 1.0)
                    st.progress(ratio, text=f"{c['tokens_total']:,} / {quota:,} tokens")
                else:
                    st.caption(f"{c['tokens_total']:,} tokens (pas de quota defini)")
else:
    st.caption("Aucune consommation enregistree ce mois-ci.")

st.markdown("---")

# ------------------------------------------------------------------
# Edition des quotas
# ------------------------------------------------------------------
st.subheader("⚙️ Quotas mensuels par utilisateur")

for u in lister_utilisateurs():
    with st.expander(f"{u['username']} — quota actuel : {u['quota_tokens']:,} tokens/mois" if u["quota_tokens"] else f"{u['username']} — pas de quota"):
        col_a, col_b = st.columns([3, 1])
        with col_a:
            nouveau_quota = st.number_input(
                "Quota mensuel (tokens)",
                min_value=0,
                value=u["quota_tokens"] or 0,
                step=10000,
                key=f"quota_{u['username']}",
                help="0 = pas de quota (pas d'avertissement affiche).",
            )
        with col_b:
            st.write("")
            st.write("")
            if st.button("💾 Enregistrer", key=f"save_quota_{u['username']}"):
                definir_quota_tokens(u["username"], nouveau_quota if nouveau_quota > 0 else None)
                enregistrer_action(
                    admin_username, "modification_quota", cible=u["username"],
                    details=f"{nouveau_quota:,} tokens/mois" if nouveau_quota > 0 else "quota retire",
                )
                st.success("Quota mis a jour.")
                st.rerun()