"""
streamlit_app.py
-----------------
Point d'entree de l'application. Gere l'authentification UNE SEULE FOIS
ici, puis construit le menu de navigation SELON LE ROLE avec
st.navigation() :
    - utilisateur normal : ne voit et n'atteint QUE le chat.
    - admin : voit en plus les 5 pages d'administration.

st.navigation() remplace la decouverte automatique du dossier pages/ de
Streamlit (qui, elle, affiche toutes les pages a tout le monde sans
condition). C'est pourquoi les pages admin ont ete deplacees dans
src/ui/admin_pages/ -- un dossier nomme "pages" a cote de ce fichier
serait redecouvert automatiquement par Streamlit et recasserait le
controle par role.

Lancement :
    streamlit run src/ui/streamlit_app.py
"""

import sys
import os
import yaml

import streamlit as st
import streamlit_authenticator as stauth

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config import AUTH_CONFIG_PATH
from src.admin.user_manager import obtenir_role, bloquer_si_inactif

LOGO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "cegedim_logo.png",
)

# set_page_config DOIT etre le tout premier appel Streamlit du run -- donc
# avant meme l'authentification (le formulaire de login est lui-meme un
# appel Streamlit). C'est pour ca qu'il vit ici, dans le routeur, et nulle
# part ailleurs (chaque page vue individuelle a eu le sien retire).
st.set_page_config(
    page_title="Assistant Navigation Menu",
    page_icon=LOGO_PATH if os.path.exists(LOGO_PATH) else "🧭",
    layout="wide",
)

if os.path.exists(LOGO_PATH):
    st.logo(LOGO_PATH)

# ------------------------------------------------------------------
# Authentification
# ------------------------------------------------------------------
with open(AUTH_CONFIG_PATH) as f:
    auth_config = yaml.safe_load(f)

# Une seule instance d'Authenticate pour tout le run (elle cree en interne
# un CookieManager avec une cle Streamlit fixe -- l'instancier une 2e fois
# ailleurs, par ex. dans chat_view.py, provoque un
# StreamlitDuplicateElementKey(key='init')). On la stocke donc dans
# session_state pour que les pages/vues suivantes la reutilisent au lieu
# d'en recreer une.
if "authenticator" not in st.session_state:
    st.session_state["authenticator"] = stauth.Authenticate(
        auth_config["credentials"],
        auth_config["cookie"]["name"],
        auth_config["cookie"]["key"],
        auth_config["cookie"]["expiry_days"],
    )

authenticator = st.session_state["authenticator"]

authenticator.login()

if st.session_state.get("authentication_status") is False:
    st.error("Nom d'utilisateur ou mot de passe incorrect.")
    st.stop()
elif st.session_state.get("authentication_status") is None:
    st.warning("Merci de te connecter.")
    st.stop()

username = st.session_state["username"]
bloquer_si_inactif(username)

role = obtenir_role(username)

# ------------------------------------------------------------------
# Menu de navigation, construit selon le role
# ------------------------------------------------------------------
pages = [st.Page("chat_view.py", title="Assistant", icon="🧭", default=True)]

if role == "admin":
    pages += [
        st.Page("admin_pages/1_Administration.py", title="Administration", icon="🛠️"),
        st.Page("admin_pages/2_Suivi_Conversations.py", title="Suivi Conversations", icon="💬"),
        st.Page("admin_pages/3_Gestion_Tokens.py", title="Gestion Tokens", icon="🎟️"),
        st.Page("admin_pages/4_Gestion_Menu.py", title="Gestion Menu", icon="🗂️"),
        st.Page("admin_pages/5_Journal_Admin.py", title="Journal Admin", icon="📜"),
    ]

pg = st.navigation(pages)
pg.run()