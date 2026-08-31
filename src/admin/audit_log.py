"""
audit_log.py
-------------
Journal d'actions admin : trace QUI a fait QUOI et QUAND, pour toutes les
actions sensibles effectuees depuis le dashboard admin (gestion des
utilisateurs, du menu, des tokens, des conversations).

Utilise la meme base SQLite que l'historique des conversations
(HISTORY_DB_PATH), dans une table separee.
"""

import sqlite3
import os
from datetime import datetime
from src.config import HISTORY_DB_PATH


def _get_connection():
    os.makedirs(os.path.dirname(HISTORY_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(HISTORY_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_audit_log():
    """Cree la table si elle n'existe pas encore. A appeler une fois au demarrage
    de chaque page admin (idempotent, comme history_manager.init_db)."""
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS admin_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_username TEXT NOT NULL,
            action TEXT NOT NULL,
            cible TEXT,
            details TEXT,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def enregistrer_action(admin_username: str, action: str, cible: str = None, details: str = None):
    """
    Enregistre une action admin dans le journal.

    action : identifiant court de l'action, ex. 'creation_utilisateur',
             'suppression_utilisateur', 'modification_role',
             'reset_mot_de_passe', 'modification_quota',
             'modification_xml', 'renommage_label', 'restauration_backup',
             'reindexation', 'suppression_conversation'.
    cible : sur quoi porte l'action (ex. username concerne, nom de menu).
    details : contexte additionnel en texte libre (ex. "user -> admin").
    """
    conn = _get_connection()
    conn.execute(
        """INSERT INTO admin_audit_log (admin_username, action, cible, details, timestamp)
           VALUES (?, ?, ?, ?, ?)""",
        (admin_username, action, cible, details, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def lister_actions(limit: int = 200, filtre_admin: str = None, filtre_action: str = None) -> list:
    """Liste les actions du journal, plus recentes en premier, avec filtres optionnels."""
    conn = _get_connection()
    conditions = []
    params = []

    if filtre_admin:
        conditions.append("admin_username = ?")
        params.append(filtre_admin)
    if filtre_action:
        conditions.append("action = ?")
        params.append(filtre_action)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)

    rows = conn.execute(
        f"SELECT * FROM admin_audit_log {where} ORDER BY timestamp DESC LIMIT ?",
        params,
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def lister_admins_ayant_agi() -> list:
    """Pour peupler un filtre deroulant cote UI."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT DISTINCT admin_username FROM admin_audit_log ORDER BY admin_username ASC"
    ).fetchall()
    conn.close()
    return [r["admin_username"] for r in rows]