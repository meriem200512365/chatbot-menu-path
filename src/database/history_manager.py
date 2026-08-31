"""
history_manager.py
-------------------
Gere l'historique sous forme de CONVERSATIONS (threads), chacune contenant
plusieurs messages (comme ChatGPT), avec un feedback optionnel (like/dislike)
par message assistant.

Schema :
    conversations(id, username, titre, created_at, updated_at)
    messages(id, conversation_id, role, contenu, mode, chemin_menu, feedback, timestamp)
"""

import sqlite3
import os
from datetime import datetime
from src.config import HISTORY_DB_PATH


def _get_connection():
    os.makedirs(os.path.dirname(HISTORY_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(HISTORY_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Cree les tables si elles n'existent pas encore. A appeler une fois au demarrage."""
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            titre TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,             -- 'user' ou 'assistant'
            contenu TEXT NOT NULL,
            mode TEXT,                      -- 'direct', 'rag', ou NULL pour les messages user
            chemin_menu TEXT,
            feedback TEXT,                  -- 'up', 'down' ou NULL (pas encore note)
            tokens_input INTEGER,
            tokens_output INTEGER,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
    """)
    # Migration douce : si la base existe deja sans ces colonnes, on les ajoute.
    colonnes = [r["name"] for r in conn.execute("PRAGMA table_info(messages)").fetchall()]
    if "feedback" not in colonnes:
        conn.execute("ALTER TABLE messages ADD COLUMN feedback TEXT")
    if "tokens_input" not in colonnes:
        conn.execute("ALTER TABLE messages ADD COLUMN tokens_input INTEGER")
    if "tokens_output" not in colonnes:
        conn.execute("ALTER TABLE messages ADD COLUMN tokens_output INTEGER")
    conn.commit()
    conn.close()


def creer_conversation(username: str, titre: str) -> int:
    """Cree une nouvelle conversation et retourne son id."""
    now = datetime.now().isoformat()
    conn = _get_connection()
    cur = conn.execute(
        "INSERT INTO conversations (username, titre, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (username, titre[:60], now, now),
    )
    conn.commit()
    conv_id = cur.lastrowid
    conn.close()
    return conv_id


def ajouter_message(
    conversation_id: int,
    role: str,
    contenu: str,
    mode: str = None,
    chemin_menu: str = None,
    tokens_input: int = None,
    tokens_output: int = None,
) -> int:
    """Ajoute un message a une conversation existante, met a jour sa date de modif,
    et retourne l'id du message cree (utile pour attacher un feedback ensuite).
    tokens_input/tokens_output : consommation reelle renvoyee par l'API Groq
    (voir src/generation/llm_client.py et vision_client.py), None pour les
    messages 'user' ou pour le mode direct (pas d'appel LLM)."""
    now = datetime.now().isoformat()
    conn = _get_connection()
    cur = conn.execute(
        """INSERT INTO messages (conversation_id, role, contenu, mode, chemin_menu, tokens_input, tokens_output, timestamp)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (conversation_id, role, contenu, mode, chemin_menu, tokens_input, tokens_output, now),
    )
    conn.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id))
    conn.commit()
    message_id = cur.lastrowid
    conn.close()
    return message_id


def definir_feedback(message_id: int, feedback: str):
    """feedback doit etre 'up', 'down', ou None pour retirer la note."""
    if feedback not in ("up", "down", None):
        raise ValueError("feedback doit etre 'up', 'down' ou None")
    conn = _get_connection()
    conn.execute("UPDATE messages SET feedback = ? WHERE id = ?", (feedback, message_id))
    conn.commit()
    conn.close()


def get_conversations(username: str, recherche: str = None, limit: int = 50) -> list:
    """
    Liste les conversations d'un utilisateur, plus recentes en premier.
    Si `recherche` est fourni, filtre sur le titre ET le contenu des messages.
    """
    conn = _get_connection()
    if recherche:
        motif = f"%{recherche}%"
        rows = conn.execute(
            """SELECT DISTINCT c.* FROM conversations c
               LEFT JOIN messages m ON m.conversation_id = c.id
               WHERE c.username = ? AND (c.titre LIKE ? OR m.contenu LIKE ?)
               ORDER BY c.updated_at DESC
               LIMIT ?""",
            (username, motif, motif, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT * FROM conversations
               WHERE username = ?
               ORDER BY updated_at DESC
               LIMIT ?""",
            (username, limit),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_messages(conversation_id: int) -> list:
    """Retourne tous les messages d'une conversation, dans l'ordre chronologique."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id ASC",
        (conversation_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def supprimer_conversation(conversation_id: int):
    """Supprime une conversation et tous ses messages (cascade)."""
    conn = _get_connection()
    conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
    conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    conn.commit()
    conn.close()


def renommer_conversation(conversation_id: int, nouveau_titre: str):
    """Renomme une conversation."""
    conn = _get_connection()
    conn.execute(
        "UPDATE conversations SET titre = ? WHERE id = ?",
        (nouveau_titre[:60], conversation_id),
    )
    conn.commit()
    conn.close()


def get_all_conversations(recherche: str = None, username_filtre: str = None, limit: int = 200) -> list:
    """
    VUE ADMIN : liste les conversations de TOUS les utilisateurs, plus
    recentes en premier. `username_filtre` restreint a un seul utilisateur,
    `recherche` filtre sur le titre ET le contenu des messages.
    """
    conn = _get_connection()
    conditions = []
    params = []

    if username_filtre:
        conditions.append("c.username = ?")
        params.append(username_filtre)

    if recherche:
        motif = f"%{recherche}%"
        conditions.append("(c.titre LIKE ? OR m.contenu LIKE ?)")
        params.extend([motif, motif])

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)

    rows = conn.execute(
        f"""SELECT DISTINCT c.* FROM conversations c
            LEFT JOIN messages m ON m.conversation_id = c.id
            {where}
            ORDER BY c.updated_at DESC
            LIMIT ?""",
        params,
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_usernames_avec_conversations() -> list:
    """Retourne la liste des usernames distincts ayant au moins une conversation
    (pour peupler un filtre deroulant cote admin)."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT DISTINCT username FROM conversations ORDER BY username ASC"
    ).fetchall()
    conn.close()
    return [r["username"] for r in rows]


def get_stats_globales() -> dict:
    """Petit tableau de bord : volumes globaux, par utilisateur, et par mode."""
    conn = _get_connection()

    nb_conversations = conn.execute("SELECT COUNT(*) c FROM conversations").fetchone()["c"]
    nb_messages = conn.execute("SELECT COUNT(*) c FROM messages WHERE role = 'user'").fetchone()["c"]

    par_utilisateur = conn.execute("""
        SELECT c.username, COUNT(DISTINCT c.id) nb_conversations, COUNT(m.id) nb_messages
        FROM conversations c
        LEFT JOIN messages m ON m.conversation_id = c.id AND m.role = 'user'
        GROUP BY c.username
        ORDER BY nb_conversations DESC
    """).fetchall()

    par_mode = conn.execute("""
        SELECT mode, COUNT(*) c
        FROM messages
        WHERE role = 'assistant' AND mode IS NOT NULL
        GROUP BY mode
    """).fetchall()

    conn.close()
    return {
        "nb_conversations": nb_conversations,
        "nb_messages_utilisateur": nb_messages,
        "par_utilisateur": [dict(r) for r in par_utilisateur],
        "par_mode": {r["mode"]: r["c"] for r in par_mode},
    }


def get_consommation_mois_courant(username: str) -> dict:
    """Somme des tokens consommes par un utilisateur depuis le debut du mois en cours."""
    debut_mois = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    conn = _get_connection()
    row = conn.execute(
        """SELECT COALESCE(SUM(m.tokens_input), 0) AS total_input,
                  COALESCE(SUM(m.tokens_output), 0) AS total_output
           FROM messages m
           JOIN conversations c ON c.id = m.conversation_id
           WHERE c.username = ? AND m.timestamp >= ?""",
        (username, debut_mois),
    ).fetchone()
    conn.close()
    return {
        "tokens_input": row["total_input"],
        "tokens_output": row["total_output"],
        "tokens_total": row["total_input"] + row["total_output"],
    }


def get_consommation_tous_utilisateurs() -> list:
    """Vue admin : consommation du mois en cours, groupee par utilisateur."""
    debut_mois = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    conn = _get_connection()
    rows = conn.execute(
        """SELECT c.username,
                  COALESCE(SUM(m.tokens_input), 0) AS total_input,
                  COALESCE(SUM(m.tokens_output), 0) AS total_output
           FROM conversations c
           JOIN messages m ON m.conversation_id = c.id AND m.timestamp >= ?
           GROUP BY c.username
           ORDER BY (total_input + total_output) DESC""",
        (debut_mois,),
    ).fetchall()
    conn.close()
    return [
        {
            "username": r["username"],
            "tokens_input": r["total_input"],
            "tokens_output": r["total_output"],
            "tokens_total": r["total_input"] + r["total_output"],
        }
        for r in rows
    ]


def get_stats_feedback() -> dict:
    """Petit resume utile pour un futur tableau de bord admin :
    nombre de likes/dislikes, et les questions les moins bien notees."""
    conn = _get_connection()
    up = conn.execute("SELECT COUNT(*) c FROM messages WHERE feedback = 'up'").fetchone()["c"]
    down = conn.execute("SELECT COUNT(*) c FROM messages WHERE feedback = 'down'").fetchone()["c"]
    mal_notes = conn.execute("""
        SELECT m.contenu, m.chemin_menu, m.timestamp
        FROM messages m
        WHERE m.feedback = 'down'
        ORDER BY m.timestamp DESC
        LIMIT 20
    """).fetchall()
    conn.close()
    return {"likes": up, "dislikes": down, "reponses_mal_notees": [dict(r) for r in mal_notes]}


if __name__ == "__main__":
    init_db()
    cid = creer_conversation("meriem", "je veux gerer les actes RO")
    ajouter_message(cid, "user", "je veux gerer les actes RO")
    mid = ajouter_message(cid, "assistant", "Prestations > Actes > Gestion RO", mode="direct", chemin_menu="Prestations > Actes > Gestion RO")
    definir_feedback(mid, "up")
    print(get_stats_feedback())