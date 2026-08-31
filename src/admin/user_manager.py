"""
user_manager.py
----------------
Gestion des utilisateurs (lecture/ecriture de config/auth_config.yaml).
Utilise par la page d'administration Streamlit.

Chaque utilisateur a : name/email/password (hash), role ("admin"/"user"),
quota_tokens (informatif), actif (bool, desactivation sans supprimer le
compte), derniere_connexion (horodatage ISO, mis a jour a chaque login
reussi -- voir enregistrer_derniere_connexion).
"""

import yaml
import streamlit as st
import streamlit_authenticator as stauth
from datetime import datetime

from src.config import AUTH_CONFIG_PATH


def _charger() -> dict:
    with open(AUTH_CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _sauvegarder(config: dict):
    with open(AUTH_CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, default_flow_style=False, allow_unicode=True)


def lister_utilisateurs() -> list:
    """Retourne la liste des utilisateurs avec leurs infos (sans le hash du mdp)."""
    config = _charger()
    return [
        {
            "username": username,
            "name": infos.get("name", ""),
            "email": infos.get("email", ""),
            "role": infos.get("role", "user"),
            "quota_tokens": infos.get("quota_tokens"),       # None = pas de quota defini
            "actif": infos.get("actif", True),               # True par defaut (comptes existants)
            "derniere_connexion": infos.get("derniere_connexion"),  # None si jamais connecte
        }
        for username, infos in config["credentials"]["usernames"].items()
    ]


def obtenir_quota_tokens(username: str):
    """Retourne le quota mensuel informatif de l'utilisateur, ou None si non defini."""
    config = _charger()
    return config["credentials"]["usernames"].get(username, {}).get("quota_tokens")


def definir_quota_tokens(username: str, quota):
    """quota : entier (nb de tokens/mois), ou None pour retirer le quota.
    PUREMENT INFORMATIF : ne bloque jamais l'utilisateur, sert seulement
    a afficher un avertissement quand la consommation le depasse."""
    config = _charger()
    if username not in config["credentials"]["usernames"]:
        raise ValueError(f"L'utilisateur '{username}' n'existe pas.")

    config["credentials"]["usernames"][username]["quota_tokens"] = quota
    _sauvegarder(config)


def utilisateur_existe(username: str) -> bool:
    config = _charger()
    return username in config["credentials"]["usernames"]


def obtenir_role(username: str) -> str:
    config = _charger()
    return config["credentials"]["usernames"].get(username, {}).get("role", "user")


def est_actif(username: str) -> bool:
    """Un compte absent du fichier est considere inactif (supprime)."""
    config = _charger()
    infos = config["credentials"]["usernames"].get(username)
    if infos is None:
        return False
    return infos.get("actif", True)


def definir_statut_actif(username: str, actif: bool):
    """Desactive/reactive un compte SANS le supprimer (garde son historique,
    ses conversations et son role intacts, juste l'acces bloque)."""
    config = _charger()
    if username not in config["credentials"]["usernames"]:
        raise ValueError(f"L'utilisateur '{username}' n'existe pas.")

    config["credentials"]["usernames"][username]["actif"] = actif
    _sauvegarder(config)


def enregistrer_derniere_connexion(username: str):
    """A appeler juste apres un login reussi (voir src/ui/streamlit_app.py)."""
    config = _charger()
    if username in config["credentials"]["usernames"]:
        config["credentials"]["usernames"][username]["derniere_connexion"] = datetime.now().isoformat()
        _sauvegarder(config)


def bloquer_si_inactif(username: str):
    """Coupe l'acces a la page courante si le compte a ete desactive par
    un admin. A appeler juste apres l'authentification, sur chaque page
    (chat principal + toutes les pages admin)."""
    if not est_actif(username):
        st.error("⛔ Ton compte a ete desactive. Contacte un administrateur.")
        st.stop()


def ajouter_utilisateur(username: str, name: str, email: str, mot_de_passe: str, role: str = "user"):
    if not username or not mot_de_passe:
        raise ValueError("Username et mot de passe sont obligatoires.")

    config = _charger()
    if username in config["credentials"]["usernames"]:
        raise ValueError(f"L'utilisateur '{username}' existe deja.")

    config["credentials"]["usernames"][username] = {
        "name": name or username,
        "email": email or "",
        "password": stauth.Hasher.hash(mot_de_passe),
        "role": role,
        "actif": True,
        "derniere_connexion": None,
    }
    _sauvegarder(config)


def reinitialiser_mot_de_passe(username: str, nouveau_mot_de_passe: str):
    config = _charger()
    if username not in config["credentials"]["usernames"]:
        raise ValueError(f"L'utilisateur '{username}' n'existe pas.")

    config["credentials"]["usernames"][username]["password"] = stauth.Hasher.hash(nouveau_mot_de_passe)
    _sauvegarder(config)


def modifier_role(username: str, role: str):
    config = _charger()
    if username not in config["credentials"]["usernames"]:
        raise ValueError(f"L'utilisateur '{username}' n'existe pas.")

    config["credentials"]["usernames"][username]["role"] = role
    _sauvegarder(config)


def supprimer_utilisateur(username: str):
    config = _charger()
    if username not in config["credentials"]["usernames"]:
        raise ValueError(f"L'utilisateur '{username}' n'existe pas.")

    del config["credentials"]["usernames"][username]
    _sauvegarder(config)