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
import base64
import yaml

import streamlit as st
import streamlit_authenticator as stauth

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config import AUTH_CONFIG_PATH
from src.admin.user_manager import obtenir_role, bloquer_si_inactif
from src.ui.theme import inject_theme

LOGO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "cegedim_logo.png",
)

# set_page_config DOIT etre le tout premier appel Streamlit du run -- donc
# avant meme l'authentification (l'ecran de login est lui-meme fait
# d'appels Streamlit). C'est pour ca qu'il vit ici, dans le routeur, et
# nulle part ailleurs (chaque page vue individuelle a eu le sien retire).
st.set_page_config(
    page_title="Assistant Navigation Menu",
    page_icon=LOGO_PATH if os.path.exists(LOGO_PATH) else "🧭",
    layout="wide",
)

inject_theme()

if os.path.exists(LOGO_PATH):
    st.logo(LOGO_PATH)


def _logo_base64() -> str:
    if not os.path.exists(LOGO_PATH):
        return ""
    with open(LOGO_PATH, "rb") as logo_file:
        return base64.b64encode(logo_file.read()).decode()


# ------------------------------------------------------------------
# Ecran de connexion
#
# Parti pris : un split-screen. A gauche, un panneau de marque qui
# illustre litteralement ce que fait l'outil -- un chemin en pointilles
# entre des reperes, puisque l'app existe pour aider a "naviguer" vers
# la bonne fonctionnalite sans se perdre dans les menus. A droite, le
# formulaire, pose directement sur le fond (pas de carte flottante en
# plus du split -- ca ferait deux effets de "conteneur" qui se
# concurrencent).
#
# Une seule couleur d'accent (l'or du dernier repere) porte tout le
# "moment fort" visuel ; le reste (bouton, champs) reste sobre.
# ------------------------------------------------------------------

_LOGIN_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

[data-testid="stAppViewContainer"] { background: #FAFAF8; }
[data-testid="stHeader"] { background: transparent; }
.block-container { padding: 0 !important; max-width: 100% !important; }
[data-testid="stHorizontalBlock"] { gap: 0 !important; align-items: stretch !important; }
[data-testid="stHorizontalBlock"] > div { padding: 0 !important; }

/* -------- Panneau de marque (gauche) -------- */
.st-key-cg_panel_brand {
    min-height: 100vh;
    background: linear-gradient(165deg, #0B1220 0%, #101A30 55%, #0B1220 100%);
    padding: 3.2rem 3.4rem;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    position: relative;
    overflow: hidden;
}

.cg-mark {
    width: 42px; height: 42px;
    border-radius: 10px;
    background: #F7F8FA;
    background-image: url('data:image/png;base64,__LOGO_B64__');
    background-size: 68%;
    background-repeat: no-repeat;
    background-position: center;
}

.cg-headline {
    font-family: 'Sora', sans-serif;
    font-weight: 600;
    font-size: clamp(1.7rem, 2.6vw, 2.35rem);
    line-height: 1.22;
    color: #F5F6FA;
    max-width: 15ch;
    margin-top: 2.6rem;
}

.cg-subhead {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.98rem;
    line-height: 1.6;
    color: rgba(224, 229, 245, 0.60);
    max-width: 30ch;
    margin-top: 0.9rem;
}

.cg-route { margin-top: 2.6rem; }

.cg-foot {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.8rem;
    color: rgba(224, 229, 245, 0.4);
    line-height: 1.5;
}

.cg-node { opacity: 0; animation: cg-fade-in 0.5s ease-out forwards; }
.cg-node-1 { animation-delay: 0.15s; }
.cg-node-2 { animation-delay: 0.55s; }
.cg-node-3 { animation-delay: 0.95s; }
.cg-path {
    stroke-dasharray: 320;
    stroke-dashoffset: 320;
    animation: cg-draw 1.1s ease-out 0.15s forwards;
}
@keyframes cg-fade-in { to { opacity: 1; } }
@keyframes cg-draw { to { stroke-dashoffset: 0; } }
@media (prefers-reduced-motion: reduce) {
    .cg-node, .cg-path { animation: none !important; opacity: 1 !important; stroke-dashoffset: 0 !important; }
}

/* -------- Panneau de formulaire (droite) -------- */
.st-key-cg_panel_form {
    min-height: 100vh;
    background: #FAFAF8;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 3rem 2.5rem;
}
.st-key-cg_panel_form > div { width: 100%; max-width: 360px; margin: 0 auto; }

.cg-form-title {
    font-family: 'Sora', sans-serif;
    font-weight: 600;
    font-size: 1.55rem;
    color: #12172B;
    margin-bottom: 0.3rem;
}
.cg-form-sub {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.92rem;
    color: #667085;
    margin-bottom: 1.8rem;
}
.cg-alert {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.86rem;
    color: #B3261E;
    background: rgba(229, 72, 77, 0.08);
    border: 1px solid rgba(229, 72, 77, 0.3);
    border-radius: 8px;
    padding: 0.65rem 0.85rem;
    margin-bottom: 1.4rem;
}
.cg-form-foot {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.8rem;
    color: #8A93A6;
    margin-top: 1.7rem;
}

.st-key-cg_panel_form [data-testid="stForm"] { border: none; padding: 0; background: transparent; }
.st-key-cg_panel_form label {
    font-family: 'IBM Plex Sans', sans-serif;
    font-weight: 500;
    font-size: 0.82rem;
    color: #4A5468 !important;
}
.st-key-cg_panel_form input {
    background: transparent !important;
    border: none !important;
    border-bottom: 1.5px solid #D8DCE6 !important;
    border-radius: 0 !important;
    color: #12172B !important;
    padding: 0.55rem 0.05rem !important;
    font-family: 'IBM Plex Sans', sans-serif;
}
.st-key-cg_panel_form input:focus {
    border-bottom-color: #F2B705 !important;
    box-shadow: none !important;
    outline: none;
}
.st-key-cg_panel_form [data-testid="stFormSubmitButton"] button {
    width: 100%;
    margin-top: 1.6rem;
    background: #0B1220;
    color: #F7F8FA;
    border: none;
    border-radius: 8px;
    padding: 0.68rem 0;
    font-family: 'Sora', sans-serif;
    font-weight: 600;
    transition: background 0.15s ease;
}
.st-key-cg_panel_form [data-testid="stFormSubmitButton"] button:hover {
    background: #1C2B4A;
    color: #F7F8FA;
}
.st-key-cg_panel_form [data-testid="stFormSubmitButton"] button:focus-visible {
    outline: 2px solid #F2B705;
    outline-offset: 2px;
}

/* -------- Repli mobile -------- */
@media (max-width: 900px) {
    [data-testid="stHorizontalBlock"] { flex-direction: column !important; }
    .st-key-cg_panel_brand { min-height: auto; padding: 2.2rem 1.8rem 2.6rem; }
    .cg-route { display: none; }
    .st-key-cg_panel_form { min-height: auto; padding: 2.4rem 1.8rem 3rem; }
}
</style>
"""


def _route_svg() -> str:
    """Petit visuel de reperes relies par un chemin -- illustre le
    principe meme de l'outil (retrouver son chemin vers une
    fonctionnalite), sans etre une simple decoration abstraite."""
    return """
    <svg width="220" height="90" viewBox="0 0 220 90" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path class="cg-path" d="M10 70 C 60 70, 70 20, 110 30 S 170 65, 210 20"
              stroke="rgba(224,229,245,0.35)" stroke-width="1.5" stroke-dasharray="4 6" />
        <circle class="cg-node cg-node-1" cx="10" cy="70" r="4.5" fill="rgba(224,229,245,0.55)" />
        <circle class="cg-node cg-node-2" cx="110" cy="30" r="4.5" fill="rgba(224,229,245,0.55)" />
        <circle class="cg-node cg-node-3" cx="210" cy="20" r="7" fill="#F2B705" />
    </svg>
    """


def _render_login_screen(auth_status) -> None:
    st.markdown(_LOGIN_CSS.replace("__LOGO_B64__", _logo_base64()), unsafe_allow_html=True)

    col_brand, col_form = st.columns([1, 1], gap="small")

    with col_brand:
        with st.container(key="cg_panel_brand"):
            st.markdown(f"""
            <div class="cg-mark"></div>
            <div>
                <div class="cg-headline">Chaque fonctionnalité Cegedim, sans se perdre dans les menus.</div>
                <div class="cg-subhead">Posez votre question à l'assistant et retrouvez directement l'outil ou la page qu'il vous faut.</div>
                <div class="cg-route">{_route_svg()}</div>
            </div>
            <div class="cg-foot">Assistant Navigation Menu<br>Outil interne Cegedim</div>
            """, unsafe_allow_html=True)

    with col_form:
        with st.container(key="cg_panel_form"):
            st.markdown("""
            <div class="cg-form-title">Connexion</div>
            <div class="cg-form-sub">Utilisez vos identifiants Cegedim habituels.</div>
            """, unsafe_allow_html=True)

            if auth_status is False:
                st.markdown(
                    '<div class="cg-alert">Nom d\'utilisateur ou mot de passe incorrect. Vérifiez vos identifiants et réessayez.</div>',
                    unsafe_allow_html=True,
                )

            authenticator.login(
                location="main",
                fields={
                    "Form name": "",
                    "Username": "Nom d'utilisateur",
                    "Password": "Mot de passe",
                    "Login": "Se connecter",
                },
            )

            st.markdown(
                '<div class="cg-form-foot">Besoin d\'aide ? Contactez votre administrateur informatique.</div>',
                unsafe_allow_html=True,
            )


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

if st.session_state.get("authentication_status") is not True:
    _render_login_screen(st.session_state.get("authentication_status"))
else:
    authenticator.login(location="unrendered")

if st.session_state.get("authentication_status") in (False, None):
    st.stop()

username = st.session_state["username"]
bloquer_si_inactif(username)

role = obtenir_role(username)

# ------------------------------------------------------------------
# Menu de navigation, construit selon le role
#
# Utilisateur normal : atterrit sur l'Accueil (home_view.py) plutot que
# directement dans un chat vide -- barre de recherche, suggestions,
# recherches recentes. L'Assistant, le profil et les parametres restent
# accessibles depuis la sidebar.
#
# Admin : atterrit sur le Dashboard (admin_pages/0_Dashboard.py), avec
# des cartes de statistiques reelles et des raccourcis vers les pages
# de gestion existantes. Garde acces a l'Assistant pour pouvoir le
# tester, comme n'importe quel utilisateur.
# ------------------------------------------------------------------
if role == "admin":
    pages = [
        st.Page("admin_pages/0_Dashboard.py", title="Dashboard", icon="🏠", default=True),
        st.Page("chat_view.py", title="Assistant", icon="🤖"),
        st.Page("admin_pages/1_Administration.py", title="Administration", icon="🛠️"),
        st.Page("admin_pages/2_Suivi_Conversations.py", title="Suivi Conversations", icon="💬"),
        st.Page("admin_pages/3_Gestion_Tokens.py", title="Gestion Tokens", icon="🎟️"),
        st.Page("admin_pages/4_Gestion_Menu.py", title="Gestion Menu", icon="🗂️"),
        st.Page("admin_pages/5_Journal_Admin.py", title="Journal Admin", icon="📜"),
        st.Page("profil_view.py", title="Mon profil", icon="👤"),
        st.Page("parametres_view.py", title="Paramètres", icon="⚙️"),
    ]
else:
    pages = [
        st.Page("home_view.py", title="Accueil", icon="🏠", default=True),
        st.Page("chat_view.py", title="Assistant", icon="🤖"),
        st.Page("profil_view.py", title="Mon profil", icon="👤"),
        st.Page("parametres_view.py", title="Paramètres", icon="⚙️"),
    ]

pg = st.navigation(pages)
pg.run()