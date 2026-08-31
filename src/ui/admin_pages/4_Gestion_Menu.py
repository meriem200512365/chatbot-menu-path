"""
4_Gestion_Menu.py
--------------------
Page reservee aux administrateurs : etat de l'index, dictionnaire de
synonymes/alias metier, sauvegardes/restauration, reindexation en un clic.

NOTE DE CONCEPTION : l'edition directe de menu.xml depuis l'interface a
ete retiree volontairement (trop risque -- c'est la source de verite du
menu reel d'Activ Premium). A la place, le jargon metier (acronymes comme
"RO", "RC") est gere via un dictionnaire de synonymes stocke a part
(data/synonymes.json, voir src/search/synonyms.py), qui enrichit la
question de l'utilisateur avant la recherche/le LLM sans jamais toucher
au XML source.
"""

import sys
import os
import json
import yaml

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.config import AUTH_CONFIG_PATH, MENU_INDEX_JSON, LIENS_CASSES_JSON
from src.admin.user_manager import obtenir_role, bloquer_si_inactif
from src.admin.audit_log import init_audit_log, enregistrer_action
from src.admin.menu_manager import lister_backups, restaurer_backup, relancer_indexation
from src.search.synonyms import lire_synonymes, ajouter_synonyme, supprimer_synonyme
from src.extraction.xml_parser import parse_menu_xml


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

st.title("🗂️ Gestion du menu Premium")
authenticator.logout("Se deconnecter", "sidebar")

# ------------------------------------------------------------------
# Etat actuel de l'index
# ------------------------------------------------------------------
st.subheader("📊 Etat actuel de l'index")

col1, col2, col3 = st.columns(3)
try:
    with open(MENU_INDEX_JSON, encoding="utf-8") as f:
        nb_chemins = len(json.load(f))
    with open(LIENS_CASSES_JSON, encoding="utf-8") as f:
        rapport = json.load(f)
    col1.metric("Chemins indexes", nb_chemins)
    col2.metric("Liens casses", rapport.get("nb_liens_casses", "?"))
    col3.metric("Menus orphelins", rapport.get("nb_menus_orphelins", "?"))
except FileNotFoundError:
    st.info("Aucun index trouve pour l'instant. Lance une reindexation ci-dessous.")

if st.button("🔄 Relancer l'indexation (XML -> JSON -> ChromaDB)", type="primary"):
    with st.spinner("Reindexation en cours..."):
        try:
            resultat = relancer_indexation()
            enregistrer_action(
                username, "reindexation",
                details=f"{resultat['nb_chemins']} chemins, {resultat['nb_indexed']} indexes",
            )
            st.success(
                f"Termine : {resultat['nb_chemins']} chemins extraits, "
                f"{resultat['nb_indexed']} indexes dans ChromaDB "
                f"({resultat['nb_liens_casses']} liens casses, "
                f"{resultat['nb_menus_orphelins']} menus orphelins)."
            )
        except Exception as e:
            st.error(f"Echec de la reindexation : {e}")

st.markdown("---")

# ------------------------------------------------------------------
# Onglets
# ------------------------------------------------------------------
tab_parcourir, tab_synonymes, tab_backups = st.tabs(
    ["🔍 Parcourir le menu", "🔤 Synonymes / Alias metier", "💾 Sauvegardes"]
)

# --- Parcourir (lecture seule) ---
with tab_parcourir:
    try:
        main_menu, menus = parse_menu_xml()
        st.caption(f"Menu racine : `{main_menu}` · {len(menus)} blocs de menu")

        recherche = st.text_input("🔍 Filtrer par nom de menu ou de label", key="recherche_menu")

        for nom_menu, items in menus.items():
            if recherche and recherche.lower() not in nom_menu.lower() and not any(
                recherche.lower() in (it["label"] or "").lower() for it in items
            ):
                continue
            with st.expander(f"{nom_menu}  ({len(items)} items)"):
                for it in items:
                    type_icone = "📁" if it["submenu"] else "📄"
                    st.markdown(
                        f"{type_icone} **{it['label']}** — `{it['id']}`"
                        + (f" → `{it['submenu']}`" if it["submenu"] else " *(feuille)*")
                    )
    except Exception as e:
        st.error(f"Impossible de lire le menu actuel : {e}")

# --- Synonymes / alias metier ---
with tab_synonymes:
    st.caption(
        "Resout le jargon metier (acronymes, abreviations Cegedim) sans "
        "toucher a menu.xml. Quand un utilisateur ecrit un terme reconnu "
        "ici, sa question est automatiquement enrichie de l'expansion "
        "avant la recherche et avant l'appel au LLM."
    )

    synonymes = lire_synonymes()

    if synonymes:
        for terme, expansion in sorted(synonymes.items()):
            col_terme, col_expansion, col_suppr = st.columns([2, 4, 1])
            with col_terme:
                st.markdown(f"**{terme}**")
            with col_expansion:
                st.write(expansion)
            with col_suppr:
                if st.button("🗑️", key=f"del_syn_{terme}"):
                    supprimer_synonyme(terme)
                    enregistrer_action(username, "suppression_synonyme", cible=terme)
                    st.rerun()
    else:
        st.caption("Aucun synonyme defini pour l'instant.")

    st.markdown("---")
    st.markdown("**➕ Ajouter un synonyme**")

    with st.form("nouveau_synonyme", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        with col_a:
            nouveau_terme = st.text_input("Terme / acronyme", placeholder="ex : RO")
        with col_b:
            nouvelle_expansion = st.text_input("Expansion", placeholder="ex : Regime Obligatoire")

        if st.form_submit_button("Ajouter"):
            try:
                ajouter_synonyme(nouveau_terme, nouvelle_expansion)
                enregistrer_action(
                    username, "ajout_synonyme", cible=nouveau_terme, details=f"-> {nouvelle_expansion}",
                )
                st.success(f"'{nouveau_terme}' -> '{nouvelle_expansion}' ajoute.")
                st.rerun()
            except ValueError as e:
                st.error(str(e))

# --- Sauvegardes ---
with tab_backups:
    st.caption(
        "Sauvegardes automatiques de menu.xml (creees lors d'une future "
        "mise a jour du fichier source). Permet de revenir a une version "
        "anterieure si le fichier fourni par Activ Premium change."
    )
    backups = lister_backups()
    if not backups:
        st.caption("Aucune sauvegarde disponible pour l'instant.")
    else:
        st.caption(f"{len(backups)} sauvegarde(s) disponible(s), plus recente en premier.")
        for nom in backups:
            col_nom, col_restore = st.columns([4, 1])
            with col_nom:
                st.write(f"📄 {nom}")
            with col_restore:
                if st.button("♻️ Restaurer", key=f"restore_{nom}"):
                    try:
                        restaurer_backup(nom)
                        enregistrer_action(username, "restauration_backup", cible=nom)
                        st.success(f"'{nom}' restaure comme menu.xml actuel.")
                        st.info("N'oublie pas de relancer l'indexation ci-dessus.")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))