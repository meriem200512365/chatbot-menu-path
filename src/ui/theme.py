"""
theme.py
--------
Styles partages pour les NOUVELLES pages (home_view, dashboard admin,
profil, parametres). Reprend exactement les memes variables CSS que
chat_view.py (palette navy/cyan, typographie Plus Jakarta Sans) pour
que l'identite visuelle reste identique partout, sans dupliquer ni
toucher au fichier chat_view.py existant.

Usage :
    from src.ui.theme import inject_theme
    inject_theme()
"""

import streamlit as st

_CSS = """
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

    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif !important; }
    [data-testid="stElementToolbar"] { display: none !important; }
    .block-container { padding-top: 1.5rem !important; padding-bottom: 4rem !important; max-width: 1000px; }
    h1, h2, h3 { font-weight: 800 !important; color: var(--cg-text); letter-spacing: -0.01em; }

    /* ---------- Hero d'accueil ---------- */
    .cg-hero { text-align: center; padding: 28px 16px 8px 16px; }
    .cg-hero-greeting { font-size: 2rem; font-weight: 800; color: var(--cg-text); margin-bottom: 4px; }
    .cg-hero-sub { font-size: 1.05rem; color: var(--cg-text-dim); margin-bottom: 28px; }

    /* Barre de recherche "hero" -- le champ st.text_input est stylise
       pour ressembler a une grande pilule de recherche */
    div[data-testid="stTextInput"] input {
        background: var(--cg-surface) !important;
        border: 1.5px solid var(--cg-border) !important;
        border-radius: 18px !important;
        padding: 18px 20px !important;
        font-size: 1.02rem !important;
        color: var(--cg-text) !important;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: var(--cg-accent) !important;
        box-shadow: 0 0 0 3px var(--cg-accent-soft) !important;
    }

    /* ---------- Cartes generiques (suggestions, stats, gestion, recents) ---------- */
    .cg-card {
        background: var(--cg-surface); border: 1px solid var(--cg-border);
        border-radius: 16px; padding: 18px 20px; height: 100%;
        transition: transform 0.15s ease, border-color 0.15s ease;
    }
    .cg-card:hover { transform: translateY(-2px); border-color: var(--cg-accent-dim); }

    .cg-card-icon { font-size: 1.4rem; margin-bottom: 6px; }
    .cg-card-title { font-weight: 700; font-size: 0.98rem; color: var(--cg-text); margin-bottom: 2px; }
    .cg-card-sub { font-size: 0.8rem; color: var(--cg-text-dim); }

    .cg-stat-value { font-size: 1.9rem; font-weight: 800; color: var(--cg-accent); line-height: 1; }
    .cg-stat-label { font-size: 0.82rem; color: var(--cg-text-dim); margin-top: 6px; }

    .cg-recent-card { display: flex; flex-direction: column; gap: 2px; }
    .cg-recent-q { font-weight: 600; font-size: 0.9rem; color: var(--cg-text); }
    .cg-recent-a { font-size: 0.78rem; color: var(--cg-accent); font-family: monospace; }

    .cg-section-title {
        font-size: 0.95rem; font-weight: 700; color: var(--cg-text-dim);
        text-transform: uppercase; letter-spacing: 0.05em;
        margin: 30px 0 14px 0;
    }

    /* Les cartes "cliquables" sont en fait des st.button transparents
       superposes visuellement -- on les restyle pour qu'ils ressemblent
       a des cartes plutot qu'a des boutons Streamlit par defaut. */
    div[data-testid="stVerticalBlockBorderWrapper"] .stButton > button {
        width: 100%; text-align: left; background: var(--cg-surface) !important;
        border: 1px solid var(--cg-border) !important; border-radius: 16px !important;
        padding: 16px 18px !important; color: var(--cg-text) !important;
        font-weight: 600 !important; white-space: pre-line !important;
        transition: transform 0.15s ease, border-color 0.15s ease !important;
    }
    .cg-login-hero { text-align: center; padding: 40px 16px 8px 16px; }
    .cg-login-logo { font-size: 2.6rem; margin-bottom: 8px; }
    .cg-login-title { font-size: 1.6rem; font-weight: 800; color: var(--cg-text); margin-bottom: 4px; }
    .cg-login-sub { font-size: 0.95rem; color: var(--cg-text-dim); margin-bottom: 8px; }

    /* Carte de connexion -- englobe le formulaire natif de
       streamlit-authenticator (qui utilise st.text_input/st.form en
       interne) pour lui donner un cadre soigne sans toucher au code
       d'authentification. */
    div[data-testid="stForm"] {
        background: var(--cg-surface) !important;
        border: 1px solid var(--cg-border) !important;
        border-radius: 20px !important;
        padding: 32px 32px 24px 32px !important;
        box-shadow: 0 8px 32px rgba(0,0,0,0.35);
    }
    div[data-testid="stForm"] label { color: var(--cg-text-dim) !important; font-weight: 600 !important; font-size: 0.85rem !important; }
    div[data-testid="stForm"] .stButton > button {
        width: 100%; background: var(--cg-accent) !important; color: #04131f !important;
        font-weight: 700 !important; border-radius: 12px !important; border: none !important;
        padding: 12px !important; margin-top: 8px !important; transition: background 0.15s ease;
    }
    div[data-testid="stForm"] .stButton > button:hover { background: var(--cg-accent-dim) !important; }
</style>
"""


def inject_theme():
    st.markdown(_CSS, unsafe_allow_html=True)