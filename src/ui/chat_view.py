"""
chat_view.py
-------------
Interface de chat (vue) -- affichee via le routeur src/ui/streamlit_app.py,
qui gere l'authentification et le menu de navigation selon le role.
Ne pas lancer ce fichier directement.

Design :
    - Barre superieure fixe : salutation + date, selecteur de mode en
      pilules (Chemin direct / Reponse redigee), horloge live, compteur
      de tokens du mois avec mini barre de progression.
    - Sidebar epuree : logo Cegedim + description du mode actif, bouton
      "Nouvelle conversation", recherche, historique -- puis, ancres en
      bas : bouton de deconnexion + nom/email de l'utilisateur.
    - Chat input natif avec piece jointe integree (PDF/Excel/CSV/code/
      image) au lieu d'un champ separe -- comportement type ChatGPT/Claude.
    - Feedback pouce haut/bas sur chaque reponse de l'assistant.
"""

import sys
import os
import json
import yaml
from datetime import datetime

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config import AUTH_CONFIG_PATH
from src.files.document_reader import read_document
from src.generation.vision_client import analyser_image
from src.database.history_manager import (
    init_db,
    creer_conversation,
    ajouter_message,
    get_conversations,
    get_messages,
    supprimer_conversation,
    definir_feedback,
    get_consommation_mois_courant,
)
from src.admin.user_manager import obtenir_quota_tokens, bloquer_si_inactif, enregistrer_derniere_connexion

USE_API = False
API_URL = "http://localhost:8000/chat"

FICHIERS_ACCEPTES = ["pdf", "xlsx", "xls", "csv", "txt", "py", "js", "json", "xml",
                      "md", "sql", "png", "jpg", "jpeg"]
EXT_IMAGE = ("png", "jpg", "jpeg")

MODE_DIRECT = "\u26a1 Chemin direct"
MODE_RAG = "\U0001f9e0 R\u00e9ponse r\u00e9dig\u00e9e (RAG + LLM)"

LOGO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "assets", "cegedim_logo.png",
)

init_db()

st.set_page_config(layout="wide")

# ------------------------------------------------------------------
# Style -- palette Cegedim, typographie moderne, composants "maison"
# ------------------------------------------------------------------
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
    :root {
        --cg-bg: #0b1220;
        --cg-surface: #111a2b;
        --cg-surface-2: #16213570;
        --cg-border: rgba(255,255,255,0.08);
        --cg-text: #e7edf5;
        --cg-text-dim: #8b98ac;
        --cg-accent: #38bdf8;
        --cg-accent-dim: #0ea5e9;
        --cg-accent-soft: rgba(56,189,248,0.12);
        --cg-success: #22c55e;
        --cg-warn: #f59e0b;
        --cg-danger: #f87171;
    }

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

   
    /* Streamlit affiche une petite barre d'outils (plein ecran, etc.) au
       survol de certains elements (iframe, images...) -- on la masque
       pour garder une interface epuree. */
    [data-testid="stElementToolbar"] { display: none !important; }
    .block-container { padding-top: 1rem !important; padding-bottom: 6rem !important; max-width: 1000px; }

    h1, h2, h3 { font-weight: 800 !important; color: var(--cg-text); letter-spacing: -0.01em; }
    ::placeholder { color: var(--cg-text-dim) !important; opacity: 0.8; }

    /* ---------- Barre superieure ---------- */
    .cg-greeting { font-size: 1.2rem; font-weight: 700; color: var(--cg-text); line-height: 1.15; }
    .cg-date { font-size: 0.8rem; color: var(--cg-text-dim); text-transform: capitalize; }

    .cg-badge {
        display: inline-flex; align-items: center; gap: 7px;
        background: var(--cg-accent-soft); color: var(--cg-accent);
        font-weight: 600; font-size: 0.82rem;
        padding: 8px 16px; border-radius: 999px; white-space: nowrap;
        border: 1px solid rgba(56,189,248,0.25);
    }
    .cg-token-wrap { display: flex; flex-direction: column; gap: 5px; align-items: flex-end; }
    .cg-token-bar { width: 100%; max-width: 190px; height: 5px; border-radius: 999px; background: rgba(255,255,255,0.08); overflow: hidden; }
    .cg-token-bar-fill { height: 100%; border-radius: 999px; background: linear-gradient(90deg, var(--cg-accent-dim), var(--cg-accent)); transition: width 0.4s ease; }
    .cg-token-bar-fill.warn { background: linear-gradient(90deg, #d97706, var(--cg-warn)); }
    .cg-token-bar-fill.danger { background: linear-gradient(90deg, #b91c1c, var(--cg-danger)); }

    .cg-topbar-divider { border: none; border-top: 1px solid var(--cg-border); margin: 16px 0 4px 0; }

    /* ---------- Selecteur de mode (pilules type "Cowork") ---------- */
    div[data-testid="stSegmentedControl"] {
        background: var(--cg-surface); border: 1px solid var(--cg-border);
        padding: 5px; border-radius: 14px; display: flex; justify-content: center;
    }
    div[data-testid="stSegmentedControl"] label {
        border-radius: 10px !important; font-weight: 600 !important; font-size: 0.92rem !important;
        padding: 10px 20px !important; white-space: nowrap !important;
    }

    /* ---------- Sidebar ---------- */
    section[data-testid="stSidebar"] { background: var(--cg-surface); border-right: 1px solid var(--cg-border); }
    section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] {
        display: flex; flex-direction: column; height: 100vh; overflow-y: auto; padding-bottom: 0 !important;
    }

    .cg-sidebar-logo-row { display: flex; align-items: center; gap: 10px; padding: 4px 2px 0 2px; }
    .cg-sidebar-logo-row img { border-radius: 8px; }
    .cg-brand-name { font-weight: 800; font-size: 1.02rem; color: var(--cg-text); line-height: 1.1; }
    .cg-brand-sub { font-size: 0.72rem; color: var(--cg-text-dim); }

    .cg-mode-hint {
        margin: 8px 2px 18px 2px; font-size: 0.78rem; font-weight: 500; font-style: italic;
        color: var(--cg-accent); line-height: 1.3; opacity: 0.9;
    }

    .cg-section-label {
        font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em;
        color: var(--cg-text-dim); margin: 16px 2px 6px 2px;
    }

    div[data-testid="stSidebarUserContent"] .stButton > button {
        text-align: left; justify-content: flex-start; border-radius: 10px;
    }
    div[data-testid="stSidebarUserContent"] .stTextInput input { border-radius: 10px; }

    /* ---------- Pied de sidebar epingle en bas (toujours visible) ---------- */
    /* Le dernier bloc de la sidebar (with st.container(): logout + user
       info) est colle en bas grace a position:sticky, et reste visible
       meme si l'historique au-dessus devient long et scrollable. */
    section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] > div:last-child {
        position: sticky; bottom: 0; z-index: 5;
        background: var(--cg-surface);
        padding-top: 10px; padding-bottom: 14px; margin-top: 10px;
        border-top: 1px solid var(--cg-border);
    }
    .cg-user-footer {
        display: flex; align-items: center; gap: 10px; padding: 8px 2px 2px 2px;
    }
    .cg-user-avatar {
        width: 34px; height: 34px; border-radius: 50%;
        background: var(--cg-accent); color: #04131f; font-weight: 700;
        display: flex; align-items: center; justify-content: center; font-size: 0.9rem; flex-shrink: 0;
    }
    .cg-user-name { font-weight: 700; font-size: 0.85rem; color: var(--cg-text); line-height: 1.15; }
    .cg-user-email { font-size: 0.72rem; color: var(--cg-text-dim); word-break: break-all; }

    /* ---------- Chat ---------- */
    [data-testid="stChatMessage"] { border-radius: 16px; padding: 6px 4px; }
    .feedback-row .stButton > button {
        padding: 0.1rem 0.45rem; font-size: 0.82rem; border: none; background: transparent; color: var(--cg-text-dim);
    }
    .feedback-row .stButton > button:hover { background: var(--cg-accent-soft); color: var(--cg-accent); }

    [data-testid="stChatInput"] { border-radius: 16px !important; }
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------
# Authentification -- deja geree UNE SEULE FOIS par streamlit_app.py
# (le routeur) avant que cette vue ne soit executee via pg.run().
# Ne PAS recreer stauth.Authenticate() ni rappeler .login() ici : ca
# instancierait un 2e CookieManager avec la meme cle Streamlit ("init")
# que celui du routeur et ferait planter l'app avec
# StreamlitDuplicateElementKey. On reutilise l'instance partagee et les
# valeurs de session_state deja renseignees par streamlit_app.py.
# ------------------------------------------------------------------
with open(AUTH_CONFIG_PATH) as f:
    auth_config = yaml.safe_load(f)

authenticator = st.session_state["authenticator"]

if st.session_state.get("authentication_status") is False:
    st.error("Nom d'utilisateur ou mot de passe incorrect.")
    st.stop()
elif st.session_state.get("authentication_status") is None:
    st.warning("Merci de te connecter.")
    st.stop()

username = st.session_state["username"]
name = st.session_state["name"]
email = auth_config["credentials"]["usernames"].get(username, {}).get("email", "")

bloquer_si_inactif(username)
if not st.session_state.get(f"_login_enregistre_{username}"):
    enregistrer_derniere_connexion(username)
    st.session_state[f"_login_enregistre_{username}"] = True


# ------------------------------------------------------------------
# Chargement mis en cache
# ------------------------------------------------------------------
@st.cache_resource
def get_chatbot_fn():
    from src.chatbot.chatbot import repondre
    return repondre


@st.cache_resource
def get_rag_fn():
    from src.generation.rag_chatbot import repondre_rag
    return repondre_rag


def call_chatbot(question: str) -> dict:
    if USE_API:
        import requests
        resp = requests.post(API_URL, json={"question": question}, timeout=10)
        resp.raise_for_status()
        return resp.json()
    else:
        repondre = get_chatbot_fn()
        return repondre(question)


def charger_conversation(conv_id):
    """Charge les messages d'une conversation depuis la DB dans la session."""
    st.session_state.current_conversation_id = conv_id
    st.session_state.messages = [
        {"role": m["role"], "content": m["contenu"], "id": m["id"], "feedback": m["feedback"]}
        for m in get_messages(conv_id)
    ]


def nouvelle_conversation():
    st.session_state.current_conversation_id = None
    st.session_state.messages = []


# ------------------------------------------------------------------
# Init session state
# ------------------------------------------------------------------
if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "mode_reponse" not in st.session_state:
    st.session_state.mode_reponse = MODE_DIRECT


# ------------------------------------------------------------------
# Donnees pour la barre superieure (tokens / quota)
# ------------------------------------------------------------------
quota = obtenir_quota_tokens(username)
consommation = get_consommation_mois_courant(username)
tokens_total = consommation["tokens_total"]

if quota:
    ratio = min(tokens_total / quota, 1.0) if quota else 0
    bar_class = "danger" if ratio >= 1 else ("warn" if ratio >= 0.8 else "")
    token_pct = round(ratio * 100)
else:
    ratio, bar_class, token_pct = 0, "", 0

premier_prenom = name.split(" ")[0] if name else username
aujourdhui = datetime.now().strftime("%A %d %B %Y").capitalize()

# ------------------------------------------------------------------
# Barre superieure -- ligne 1 : salutation | horloge | tokens
#                     ligne 2 : selecteur de mode, large et centre
# ------------------------------------------------------------------
col_greet, col_clock, col_tokens = st.columns([2.6, 1.4, 2.2], vertical_alignment="center")

with col_greet:
    st.markdown(f"""
    <div class="cg-greeting">Bonjour, {premier_prenom} \U0001f44b</div>
    <div class="cg-date">{aujourdhui}</div>
    """, unsafe_allow_html=True)

with col_clock:
    # html/body sans marge + overflow:hidden : sans ca, la marge par
    # defaut du navigateur depasse la hauteur de l'iframe et fait
    # apparaitre une scrollbar / des fleches parasites autour de l'heure.
    st.iframe("""
    <html><head><style>
        html, body { margin:0; padding:0; overflow:hidden; background:transparent; }
    </style></head><body>
    <div style="font-family:'Plus Jakarta Sans',sans-serif;font-weight:700;font-size:0.85rem;
                color:#38bdf8;background:rgba(56,189,248,0.12);border:1px solid rgba(56,189,248,0.25);
                padding:9px 16px;border-radius:999px;display:flex;align-items:center;justify-content:center;
                gap:7px;white-space:nowrap;box-sizing:border-box;width:fit-content;margin:0 auto;">
        <span>\U0001f550</span><span id="cg-clock-time">--:--:--</span>
    </div>
    <script>
        function cgTick() {
            const el = document.getElementById('cg-clock-time');
            if (el) { el.textContent = new Date().toLocaleTimeString('fr-FR'); }
        }
        cgTick();
        setInterval(cgTick, 1000);
    </script>
    </body></html>
    """, height=40)

with col_tokens:
    if quota:
        st.markdown(f"""
        <div class="cg-token-wrap">
            <div class="cg-badge">\u26a1 {tokens_total:,} / {quota:,} tokens</div>
            <div class="cg-token-bar"><div class="cg-token-bar-fill {bar_class}" style="width:{token_pct}%;"></div></div>
        </div>
        """.replace(",", " "), unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="cg-token-wrap"><div class="cg-badge">\u26a1 {tokens_total:,} tokens ce mois</div></div>
        """.replace(",", " "), unsafe_allow_html=True)

st.markdown('<hr class="cg-topbar-divider"/>', unsafe_allow_html=True)

_, col_mode_center, _ = st.columns([1, 2.4, 1])
with col_mode_center:
    # Pas de `default=` ici : la valeur initiale est deja pre-semee dans
    # st.session_state["mode_reponse"] plus haut. Passer default= ET key=
    # sur la meme valeur declenche une StreamlitAPIException.
    mode = st.segmented_control(
        "Mode de reponse",
        options=[MODE_DIRECT, MODE_RAG],
        label_visibility="collapsed",
        key="mode_reponse",
        width="stretch",
    )
    if mode is None:
        mode = MODE_DIRECT

st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)


# ------------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------------
with st.sidebar:
    if os.path.exists(LOGO_PATH):
        import base64
        with open(LOGO_PATH, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()
        st.markdown(f"""
        <div class="cg-sidebar-logo-row">
            <img src="data:image/png;base64,{logo_b64}" width="40" />
            <div>
                <div class="cg-brand-name">Cegedim</div>
                <div class="cg-brand-sub">Assistant Navigation Menu</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="cg-sidebar-logo-row">
            <div class="cg-brand-name">\U0001f9ed Cegedim</div>
        </div>
        """, unsafe_allow_html=True)

    # Uniquement la phrase decrivant le mode actif -- pas de rappel du nom
    # du mode (deja visible dans le selecteur en haut de la page).
    phrase_mode = "Trouver le bon chemin en quelques secondes" if mode == MODE_DIRECT else "AI probl\u00e8me solver"
    st.markdown(f'<div class="cg-mode-hint">{phrase_mode}</div>', unsafe_allow_html=True)

    if st.button("\u2795 Nouvelle conversation", use_container_width=True, type="primary"):
        nouvelle_conversation()
        st.rerun()

    recherche = st.text_input(
        "Rechercher une conversation",
        placeholder="\U0001f50d Rechercher...",
        label_visibility="collapsed",
    )

    st.markdown('<div class="cg-section-label">Historique</div>', unsafe_allow_html=True)

    conversations = get_conversations(username, recherche=recherche or None)

    if conversations:
        for conv in conversations:
            col_titre, col_suppr = st.columns([5, 1])
            est_active = conv["id"] == st.session_state.current_conversation_id
            label = ("\u25b8 " if est_active else "") + conv["titre"]
            with col_titre:
                if st.button(label, key=f"conv_{conv['id']}", use_container_width=True):
                    charger_conversation(conv["id"])
                    st.rerun()
            with col_suppr:
                if st.button("\U0001f5d1", key=f"del_{conv['id']}"):
                    supprimer_conversation(conv["id"])
                    if est_active:
                        nouvelle_conversation()
                    st.rerun()
    else:
        st.caption("Aucune conversation pour l'instant." if not recherche else "Aucun r\u00e9sultat.")

    # Ce bloc est le DERNIER element de la sidebar -> le CSS le cible via
    # ":last-child" et l'epingle en bas (position: sticky) : deconnexion
    # + nom/email restent toujours visibles, meme si l'historique
    # au-dessus devient long et scrollable.
    with st.container():
        authenticator.logout("\U0001f6aa Se d\u00e9connecter", "sidebar", use_container_width=True)

        initiale = (name or username)[:1].upper()
        st.markdown(f"""
        <div class="cg-user-footer">
            <div class="cg-user-avatar">{initiale}</div>
            <div>
                <div class="cg-user-name">{name}</div>
                <div class="cg-user-email">{email}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ------------------------------------------------------------------
# Corps principal : historique de la conversation
# ------------------------------------------------------------------
assistant_avatar = LOGO_PATH if os.path.exists(LOGO_PATH) else "\U0001f9ed"


def afficher_feedback(msg):
    """Affiche les boutons pouce haut/bas sous un message assistant."""
    if not msg.get("id"):
        return
    with st.container():
        st.markdown('<div class="feedback-row">', unsafe_allow_html=True)
        col1, col2, col_rest = st.columns([0.6, 0.6, 8])
        with col1:
            actif = "\U0001f44d" if msg.get("feedback") == "up" else "\U0001f90d\U0001f44d"
            if st.button(actif, key=f"fb_up_{msg['id']}"):
                nouveau = None if msg.get("feedback") == "up" else "up"
                definir_feedback(msg["id"], nouveau)
                msg["feedback"] = nouveau
                st.rerun()
        with col2:
            actif = "\U0001f44e" if msg.get("feedback") == "down" else "\U0001f90d\U0001f44e"
            if st.button(actif, key=f"fb_down_{msg['id']}"):
                nouveau = None if msg.get("feedback") == "down" else "down"
                definir_feedback(msg["id"], nouveau)
                msg["feedback"] = nouveau
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


if not st.session_state.messages:
    st.markdown(f"""
    <div style="text-align:center; padding: 48px 16px 24px 16px; color:var(--cg-grey);">
        <div style="font-size:2.2rem;">\U0001f9ed</div>
        <div style="font-size:1.15rem; font-weight:700; color:var(--cg-ink); margin-top:6px;">
            Comment puis-je t'aider aujourd'hui ?
        </div>
        <div style="font-size:0.88rem; margin-top:4px;">
            Pose ta question en langage naturel, je te donne le chemin exact dans le menu.
        </div>
    </div>
    """, unsafe_allow_html=True)

for msg in st.session_state.messages:
    avatar = assistant_avatar if msg["role"] == "assistant" else None
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            afficher_feedback(msg)


# ------------------------------------------------------------------
# Saisie -- chat input natif avec piece jointe integree
# ------------------------------------------------------------------
prompt = st.chat_input(
    "Ex : je veux g\u00e9rer les actes RO",
    accept_file=True,
    file_type=FICHIERS_ACCEPTES,
)

if prompt:
    question = prompt.text
    fichier_joint = prompt["files"][0] if prompt["files"] else None

    if not question and fichier_joint:
        question = f"Analyse ce fichier : {fichier_joint.name}"

    if fichier_joint and mode != MODE_RAG:
        st.toast(
            "\U0001f4ce Les fichiers joints ne sont utilis\u00e9s qu'en mode "
            "\"R\u00e9ponse r\u00e9dig\u00e9e (RAG + LLM)\" -- ce fichier a \u00e9t\u00e9 ignor\u00e9.",
            icon="\u26a0\ufe0f",
        )
        fichier_joint = None

    if st.session_state.current_conversation_id is None:
        st.session_state.current_conversation_id = creer_conversation(username, question)

    conv_id = st.session_state.current_conversation_id

    st.session_state.messages.append({"role": "user", "content": question, "id": None, "feedback": None})
    ajouter_message(conv_id, "user", question)
    with st.chat_message("user"):
        st.markdown(question)
        if fichier_joint:
            st.caption(f"\U0001f4ce {fichier_joint.name}")

    with st.chat_message("assistant", avatar=assistant_avatar):
        mode_rag = (mode == MODE_RAG)

        if mode_rag:
            with st.spinner("Analyse en cours..."):
                try:
                    if fichier_joint is not None:
                        ext = fichier_joint.name.split(".")[-1].lower()
                        file_bytes = fichier_joint.getvalue()

                        if ext in EXT_IMAGE:
                            reponse_texte, usage = analyser_image(
                                file_bytes, mime_type=f"image/{ext}", question=question,
                            )
                            resultat = {"reponse": reponse_texte, "chemins_sources": [], "type": "rag_reponse", "usage": usage}
                        else:
                            extrait = read_document(fichier_joint.name, file_bytes)
                            doc_text = None
                            if extrait["error"]:
                                st.warning(extrait["error"])
                            else:
                                doc_text = extrait["text"]

                            repondre_rag = get_rag_fn()
                            resultat = repondre_rag(question, document_context=doc_text)
                    else:
                        repondre_rag = get_rag_fn()
                        resultat = repondre_rag(question)

                except Exception as e:
                    st.error(f"Erreur lors de l'appel au RAG : {e}")
                    st.caption(
                        "V\u00e9rifie que GROQ_API_KEY est bien d\u00e9fini dans ton fichier .env "
                        "(obligatoire pour le mode RAG, pas pour le mode Chemin direct)."
                    )
                    st.stop()

            if resultat:
                st.markdown(resultat["reponse"])
                if resultat["chemins_sources"]:
                    with st.expander("\U0001f4c4 Chemins utilis\u00e9s comme source"):
                        for s in resultat["chemins_sources"]:
                            st.markdown(f"- `{s['path_str']}`  (pertinence: {1 - s['distance']:.2f})")

                chemin = resultat["chemins_sources"][0]["path_str"] if resultat["chemins_sources"] else None
                usage = resultat.get("usage") or {}
                mid = ajouter_message(
                    conv_id, "assistant", resultat["reponse"], mode="rag", chemin_menu=chemin,
                    tokens_input=usage.get("tokens_input"), tokens_output=usage.get("tokens_output"),
                )
                st.session_state.messages.append(
                    {"role": "assistant", "content": resultat["reponse"], "id": mid, "feedback": None}
                )

        else:
            with st.spinner("Recherche du chemin..."):
                try:
                    reponse = call_chatbot(question)
                except Exception as e:
                    st.error(f"Erreur lors de l'appel au chatbot : {e}")
                    st.stop()

            if reponse:
                if reponse["type"] == "reponse_directe":
                    st.success(reponse["message"])
                    st.code(reponse["resultats"][0]["path_str"], language=None)
                    chemin = reponse["resultats"][0]["path_str"]

                elif reponse["type"] == "ambigu":
                    st.warning(reponse["message"])
                    for r in reponse["resultats"]:
                        st.markdown(f"- `{r['path_str']}`")
                    chemin = None

                else:
                    st.info(reponse["message"])
                    chemin = None

                texte_final = reponse["message"]
                if reponse["type"] == "reponse_directe":
                    texte_final += f"\n\n`{reponse['resultats'][0]['path_str']}`"
                elif reponse["type"] == "ambigu":
                    liste_chemins = "\n".join(f"- `{r['path_str']}`" for r in reponse["resultats"])
                    texte_final += f"\n\n{liste_chemins}"

                mid = ajouter_message(conv_id, "assistant", texte_final, mode="direct", chemin_menu=chemin)
                st.session_state.messages.append(
                    {"role": "assistant", "content": texte_final, "id": mid, "feedback": None}
                )

    st.rerun()