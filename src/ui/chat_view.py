"""
chat_view.py
-------------
Interface de chat (vue) -- affichée via le routeur src/ui/streamlit_app.py,
qui gère l'authentification et le menu de navigation selon le rôle.
Ne pas lancer ce fichier directement.

Design :
    - Barre supérieure fixe : salutation + date, sélecteur de mode en
      pilules (Chemin direct / Réponse rédigée), horloge live, compteur
      de tokens du mois avec mini barre de progression.
    - Sidebar épurée : logo Cegedim + description du mode actif, bouton
      "Nouvelle conversation", recherche, historique -- puis, ancres en
      bas : bouton de déconnexion + nom/email de l'utilisateur.
    - Chat input natif avec pièce jointe intégrée (PDF/Excel/CSV/code/image).
    - Feedback pouce haut/bas interactif sur chaque réponse de l'assistant.
"""

import sys
import os
import json
import yaml
import base64
from datetime import datetime

import streamlit as st

# Configuration du chemin d'accès aux modules
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

FICHIERS_ACCEPTES = ["pdf", "xlsx", "xls", "csv", "txt", "py", "js", "json", "xml", "md", "sql", "png", "jpg", "jpeg"]
EXT_IMAGE = ("png", "jpg", "jpeg")

MODE_DIRECT = "⚡ Chemin direct"
MODE_RAG = "🧠 Réponse rédigée (RAG + LLM)"

LOGO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "assets", "cegedim_logo.png",
)

# Initialisation DB
init_db()

st.set_page_config(layout="wide", page_title="Cegedim Chat Assistant", page_icon="🧭")

# ------------------------------------------------------------------
# Style -- Palette Cegedim moderne & composants épurés
# ------------------------------------------------------------------
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
    :root {
        --cg-bg: #0b1220;
        --cg-surface: #111a2b;
        --cg-surface-2: #162135;
        --cg-border: rgba(255, 255, 255, 0.08);
        --cg-text: #e7edf5;
        --cg-text-dim: #8b98ac;
        --cg-accent: #38bdf8;
        --cg-accent-dim: #0ea5e9;
        --cg-accent-soft: rgba(56, 189, 248, 0.12);
        --cg-success: #22c55e;
        --cg-warn: #f59e0b;
        --cg-danger: #f87171;
    }

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    /* Masquer les barres d'outils Streamlit sur les composants */
    [data-testid="stElementToolbar"] { display: none !important; }
    
    .block-container { 
        padding-top: 1.2rem !important; 
        padding-bottom: 6rem !important; 
        max-width: 950px; 
    }

    h1, h2, h3 { font-weight: 800 !important; color: var(--cg-text); letter-spacing: -0.01em; }
    ::placeholder { color: var(--cg-text-dim) !important; opacity: 0.8; }

    /* ---------- Barre supérieure ---------- */
    .cg-greeting { font-size: 1.25rem; font-weight: 800; color: var(--cg-text); line-height: 1.2; }
    .cg-date { font-size: 0.82rem; color: var(--cg-text-dim); font-weight: 500; }

    .cg-badge {
        display: inline-flex; align-items: center; gap: 7px;
        background: var(--cg-accent-soft); color: var(--cg-accent);
        font-weight: 600; font-size: 0.82rem;
        padding: 6px 14px; border-radius: 999px; white-space: nowrap;
        border: 1px solid rgba(56,189,248,0.25);
    }
    .cg-token-wrap { display: flex; flex-direction: column; gap: 6px; align-items: flex-end; }
    .cg-token-bar { width: 100%; max-width: 190px; height: 6px; border-radius: 999px; background: rgba(255,255,255,0.08); overflow: hidden; }
    .cg-token-bar-fill { height: 100%; border-radius: 999px; background: linear-gradient(90deg, var(--cg-accent-dim), var(--cg-accent)); transition: width 0.4s ease; }
    .cg-token-bar-fill.warn { background: linear-gradient(90deg, #d97706, var(--cg-warn)); }
    .cg-token-bar-fill.danger { background: linear-gradient(90deg, #b91c1c, var(--cg-danger)); }

    .cg-topbar-divider { border: none; border-top: 1px solid var(--cg-border); margin: 14px 0 16px 0; }

    /* ---------- Sélecteur de mode (Segmented Control) ---------- */
    div[data-testid="stSegmentedControl"] {
        background: var(--cg-surface); border: 1px solid var(--cg-border);
        padding: 4px; border-radius: 12px; display: flex; justify-content: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    div[data-testid="stSegmentedControl"] label {
        border-radius: 8px !important; font-weight: 600 !important; font-size: 0.88rem !important;
        padding: 8px 16px !important; white-space: nowrap !important; transition: all 0.2s ease;
    }

    /* ---------- Sidebar ---------- */
    section[data-testid="stSidebar"] { background: var(--cg-surface); border-right: 1px solid var(--cg-border); }
    section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] {
        display: flex; flex-direction: column; height: 100vh; overflow-y: auto; padding-bottom: 0 !important;
    }

    .cg-sidebar-logo-row { display: flex; align-items: center; gap: 12px; padding: 4px 2px 8px 2px; }
    .cg-sidebar-logo-row img { border-radius: 8px; }
    .cg-brand-name { font-weight: 800; font-size: 1.1rem; color: var(--cg-text); line-height: 1.1; }
    .cg-brand-sub { font-size: 0.73rem; color: var(--cg-text-dim); }

    .cg-mode-hint {
        margin: 4px 2px 14px 2px; font-size: 0.78rem; font-weight: 500; font-style: italic;
        color: var(--cg-accent); line-height: 1.3; opacity: 0.95;
    }

    .cg-section-label {
        font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;
        color: var(--cg-text-dim); margin: 16px 2px 6px 2px;
    }

    div[data-testid="stSidebarUserContent"] .stButton > button {
        text-align: left; justify-content: flex-start; border-radius: 10px;
    }

    /* ---------- Pied de sidebar ancré ---------- */
    section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] > div:last-child {
        position: sticky; bottom: 0; z-index: 5;
        background: var(--cg-surface);
        padding-top: 10px; padding-bottom: 14px; margin-top: auto;
        border-top: 1px solid var(--cg-border);
    }
    .cg-user-footer {
        display: flex; align-items: center; gap: 10px; padding: 8px 2px 2px 2px;
    }
    .cg-user-avatar {
        width: 36px; height: 36px; border-radius: 50%;
        background: linear-gradient(135deg, var(--cg-accent), var(--cg-accent-dim)); 
        color: #04131f; font-weight: 800;
        display: flex; align-items: center; justify-content: center; font-size: 0.95rem; flex-shrink: 0;
    }
    .cg-user-name { font-weight: 700; font-size: 0.85rem; color: var(--cg-text); line-height: 1.15; }
    .cg-user-email { font-size: 0.72rem; color: var(--cg-text-dim); word-break: break-all; }

    /* ---------- Zone de Chat & Feedback ---------- */
    [data-testid="stChatMessage"] { border-radius: 16px; padding: 10px 14px; margin-bottom: 8px; }
    
    .feedback-row { display: flex; gap: 8px; margin-top: 6px; }
    .feedback-row .stButton > button {
        padding: 2px 10px !important; font-size: 0.75rem !important; 
        border: 1px solid var(--cg-border) !important; background: var(--cg-surface-2) !important; 
        color: var(--cg-text-dim) !important; border-radius: 8px !important;
    }
    .feedback-row .stButton > button:hover { 
        border-color: var(--cg-accent) !important; color: var(--cg-accent) !important; 
    }

    [data-testid="stChatInput"] { border-radius: 16px !important; }
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------
# Authentification & Sessions
# ------------------------------------------------------------------
with open(AUTH_CONFIG_PATH) as f:
    auth_config = yaml.safe_load(f)

authenticator = st.session_state.get("authenticator")

if st.session_state.get("authentication_status") is False:
    st.error("Nom d'utilisateur ou mot de passe incorrect.")
    st.stop()
elif st.session_state.get("authentication_status") is None:
    st.warning("Merci de vous connecter pour accéder à l'application.")
    st.stop()

username = st.session_state["username"]
name = st.session_state.get("name", username)
email = auth_config["credentials"]["usernames"].get(username, {}).get("email", "")

bloquer_si_inactif(username)
if not st.session_state.get(f"_login_enregistre_{username}"):
    enregistrer_derniere_connexion(username)
    st.session_state[f"_login_enregistre_{username}"] = True


# ------------------------------------------------------------------
# Cache des fonctions lourdes (LLM / RAG)
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
# Initialisation du Session State
# ------------------------------------------------------------------
if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "mode_reponse" not in st.session_state:
    st.session_state.mode_reponse = MODE_DIRECT


# ------------------------------------------------------------------
# Calculs & Métriques utilisateur
# ------------------------------------------------------------------
quota = obtenir_quota_tokens(username)
consommation = get_consommation_mois_courant(username)
tokens_total = consommation.get("tokens_total", 0)

if quota and quota > 0:
    ratio = min(tokens_total / quota, 1.0)
    bar_class = "danger" if ratio >= 1.0 else ("warn" if ratio >= 0.8 else "")
    token_pct = round(ratio * 100)
else:
    ratio, bar_class, token_pct = 0, "", 0

premier_prenom = name.split(" ")[0] if name else username
aujourdhui = datetime.now().strftime("%A %d %B %Y").capitalize()

# ------------------------------------------------------------------
# Barre Supérieure
# ------------------------------------------------------------------
col_greet, col_clock, col_tokens = st.columns([2.6, 1.4, 2.2], vertical_alignment="center")

with col_greet:
    st.markdown(f"""
    <div class="cg-greeting">Bonjour, {premier_prenom} 👋</div>
    <div class="cg-date">{aujourdhui}</div>
    """, unsafe_allow_html=True)

with col_clock:
    st.iframe("""
    <html><head><style>
        html, body { margin:0; padding:0; overflow:hidden; background:transparent; }
    </style></head><body>
    <div style="font-family:'Plus Jakarta Sans',sans-serif;font-weight:700;font-size:0.82rem;
                color:#38bdf8;background:rgba(56,189,248,0.12);border:1px solid rgba(56,189,248,0.25);
                padding:7px 14px;border-radius:999px;display:flex;align-items:center;justify-content:center;
                gap:6px;white-space:nowrap;box-sizing:border-box;width:fit-content;margin:0 auto;">
        <span>🕒</span><span id="cg-clock-time">--:--:--</span>
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
    """, height=44)

with col_tokens:
    if quota:
        st.markdown(f"""
        <div class="cg-token-wrap">
            <div class="cg-badge">⚡ {tokens_total:,} / {quota:,} tokens</div>
            <div class="cg-token-bar"><div class="cg-token-bar-fill {bar_class}" style="width:{token_pct}%;"></div></div>
        </div>
        """.replace(",", " "), unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="cg-token-wrap"><div class="cg-badge">⚡ {tokens_total:,} tokens ce mois</div></div>
        """.replace(",", " "), unsafe_allow_html=True)

st.markdown('<hr class="cg-topbar-divider"/>', unsafe_allow_html=True)

# Sélecteur de Mode
_, col_mode_center, _ = st.columns([1, 2.4, 1])
with col_mode_center:
    mode = st.segmented_control(
        "Mode de réponse",
        options=[MODE_DIRECT, MODE_RAG],
        label_visibility="collapsed",
        key="mode_reponse",
        width="stretch",
    )
    if mode is None:
        mode = MODE_DIRECT

st.markdown('<div style="height:6px;"></div>', unsafe_allow_html=True)


# ------------------------------------------------------------------
# Sidebar (Barre Latérale)
# ------------------------------------------------------------------
with st.sidebar:
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()
        st.markdown(f"""
        <div class="cg-sidebar-logo-row">
            <img src="data:image/png;base64,{logo_b64}" width="38" />
            <div>
                <div class="cg-brand-name">Cegedim</div>
                <div class="cg-brand-sub">Navigation Assistant</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="cg-sidebar-logo-row">
            <div class="cg-brand-name">🧭 Cegedim</div>
        </div>
        """, unsafe_allow_html=True)

    phrase_mode = "Trouver le bon chemin dans le menu" if mode == MODE_DIRECT else "AI Problem Solver & RAG"
    st.markdown(f'<div class="cg-mode-hint">{phrase_mode}</div>', unsafe_allow_html=True)

    if st.button("➕ Nouvelle conversation", use_container_width=True, type="primary"):
        nouvelle_conversation()
        st.rerun()

    recherche = st.text_input(
        "Rechercher une conversation",
        placeholder="🔍 Rechercher...",
        label_visibility="collapsed",
    )

    st.markdown('<div class="cg-section-label">Historique</div>', unsafe_allow_html=True)

    conversations = get_conversations(username, recherche=recherche or None)

    if conversations:
        for conv in conversations:
            col_titre, col_suppr = st.columns([5, 1])
            est_active = conv["id"] == st.session_state.current_conversation_id
            label = ("▸ " if est_active else "") + conv["titre"]
            
            with col_titre:
                if st.button(label, key=f"conv_{conv['id']}", use_container_width=True):
                    charger_conversation(conv["id"])
                    st.rerun()
            with col_suppr:
                if st.button("🗑️", key=f"del_{conv['id']}"):
                    supprimer_conversation(conv["id"])
                    if est_active:
                        nouvelle_conversation()
                    st.rerun()
    else:
        st.caption("Aucune conversation." if not recherche else "Aucun résultat.")

    # Zone utilisateur fixe en bas
    with st.container():
        if authenticator:
            authenticator.logout("🚪 Se déconnecter", "sidebar", use_container_width=True)

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
# Affichage de l'Historique des Messages
# ------------------------------------------------------------------
assistant_avatar = LOGO_PATH if os.path.exists(LOGO_PATH) else "🧭"


def afficher_feedback(msg):
    """Affiche des badges interactifs pouce haut/bas sous un message assistant."""
    if not msg.get("id"):
        return
    
    msg_id = msg["id"]
    current_fb = msg.get("feedback")
    
    col1, col2, _ = st.columns([0.2, 0.2, 0.6])
    
    with col1:
        label_up = "👍 Utile" if current_fb == "up" else "👍"
        if st.button(label_up, key=f"fb_up_{msg_id}"):
            nouveau = None if current_fb == "up" else "up"
            definir_feedback(msg_id, nouveau)
            msg["feedback"] = nouveau
            st.rerun()

    with col2:
        label_down = "👎 Inutile" if current_fb == "down" else "👎"
        if st.button(label_down, key=f"fb_down_{msg_id}"):
            nouveau = None if current_fb == "down" else "down"
            definir_feedback(msg_id, nouveau)
            msg["feedback"] = nouveau
            st.rerun()


# Écran d'accueil si pas de messages
if not st.session_state.messages:
    st.markdown(f"""
    <div style="text-align:center; padding: 40px 16px 20px 16px;">
        <div style="font-size:2.5rem; margin-bottom: 8px;">🧭</div>
        <div style="font-size:1.3rem; font-weight:800; color:var(--cg-text);">
            Comment puis-je vous aider aujourd'hui ?
        </div>
        <div style="font-size:0.9rem; color:var(--cg-text-dim); margin-top:6px; max-width: 500px; margin-left: auto; margin-right: auto;">
            Posez votre question en langage naturel pour obtenir le chemin exact dans l'application ou analyser des documents.
        </div>
    </div>
    """, unsafe_allow_html=True)

# Affichage des messages enregistrés
for msg in st.session_state.messages:
    avatar = assistant_avatar if msg["role"] == "assistant" else None
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            afficher_feedback(msg)


# ------------------------------------------------------------------
# Saisie Utilisateur & Traitement
# ------------------------------------------------------------------
class _PromptPreRempli:
    def __init__(self, texte):
        self.text = texte

    def __getitem__(self, cle):
        return [] if cle == "files" else None


_prefill = st.session_state.pop("prefill_question", None)
if _prefill:
    prompt = _PromptPreRempli(_prefill)
else:
    prompt = st.chat_input(
        "Ex : Je veux gérer les actes RO...",
        accept_file=True,
        file_type=FICHIERS_ACCEPTES,
    )

if prompt:
    question = prompt.text or ""
    fichier_joint = prompt["files"][0] if prompt["files"] else None

    if not question and fichier_joint:
        question = f"Analyse du fichier : {fichier_joint.name}"

    if fichier_joint and mode != MODE_RAG:
        st.toast(
            "⚠️ Fichier ignoré : les pièces jointes nécessitent le mode 'Réponse rédigée (RAG + LLM)'.",
            icon="⚠️",
        )
        fichier_joint = None

    # Création d'une nouvelle conversation si nécessaire
    if st.session_state.current_conversation_id is None:
        st.session_state.current_conversation_id = creer_conversation(username, question)

    conv_id = st.session_state.current_conversation_id

    # Enregistrement & affichage du message utilisateur
    st.session_state.messages.append({"role": "user", "content": question, "id": None, "feedback": None})
    ajouter_message(conv_id, "user", question)
    
    with st.chat_message("user"):
        st.markdown(question)
        if fichier_joint:
            st.caption(f"📎 {fichier_joint.name}")

    # Réponse de l'assistant
    with st.chat_message("assistant", avatar=assistant_avatar):
        mode_rag = (mode == MODE_RAG)
        resultat = None

        if mode_rag:
            with st.spinner("Analyse approfondie en cours..."):
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
                            doc_text = extrait["text"] if not extrait["error"] else None
                            if extrait["error"]:
                                st.warning(extrait["error"])

                            repondre_rag = get_rag_fn()
                            resultat = repondre_rag(question, document_context=doc_text)
                    else:
                        repondre_rag = get_rag_fn()
                        resultat = repondre_rag(question)

                except Exception as e:
                    st.error(f"Erreur lors de l'exécution du mode RAG : {e}")
                    st.caption("Vérifiez la configuration de la clé API dans votre fichier `.env`.")
                    st.stop()

            if resultat:
                st.markdown(resultat["reponse"])
                if resultat.get("chemins_sources"):
                    with st.expander("📄 Sources utilisées"):
                        for s in resultat["chemins_sources"]:
                            st.markdown(f"- `{s['path_str']}` *(pertinence: {1 - s['distance']:.2f})*")

                chemin = resultat["chemins_sources"][0]["path_str"] if resultat.get("chemins_sources") else None
                usage = resultat.get("usage") or {}
                
                mid = ajouter_message(
                    conv_id, "assistant", resultat["reponse"], mode="rag", chemin_menu=chemin,
                    tokens_input=usage.get("tokens_input"), tokens_output=usage.get("tokens_output"),
                )
                msg_obj = {"role": "assistant", "content": resultat["reponse"], "id": mid, "feedback": None}
                st.session_state.messages.append(msg_obj)
                afficher_feedback(msg_obj)

        else:
            with st.spinner("Recherche du chemin dans les menus..."):
                try:
                    reponse = call_chatbot(question)
                except Exception as e:
                    st.error(f"Erreur du service de navigation : {e}")
                    st.stop()

            if reponse:
                texte_final = reponse["message"]
                chemin = None

                if reponse["type"] == "reponse_directe":
                    chemin = reponse["resultats"][0]["path_str"]
                    texte_final += f"\n\n```text\n{chemin}\n```"
                    st.success(reponse["message"])
                    st.code(chemin, language=None)

                elif reponse["type"] == "ambigu":
                    liste_chemins = "\n".join(f"- `{r['path_str']}`" for r in reponse["resultats"])
                    texte_final += f"\n\n{liste_chemins}"
                    st.warning(reponse["message"])
                    for r in reponse["resultats"]:
                        st.markdown(f"- `{r['path_str']}`")
                else:
                    st.info(reponse["message"])

                mid = ajouter_message(conv_id, "assistant", texte_final, mode="direct", chemin_menu=chemin)
                msg_obj = {"role": "assistant", "content": texte_final, "id": mid, "feedback": None}
                st.session_state.messages.append(msg_obj)
                afficher_feedback(msg_obj)