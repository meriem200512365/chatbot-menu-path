"""
embed_documents.py
-------------------
Etape finale du pipeline d'indexation (offline).
Charge menu_index.json, calcule un embedding pour chaque chemin,
et insere le tout dans ChromaDB (via database/chroma_manager.py).
"""

import json

from src.config import MENU_INDEX_JSON
from src.embedding.model import get_model
from src.database.chroma_manager import get_collection, reset_collection


def load_menu_index():
    with open(MENU_INDEX_JSON, encoding="utf-8") as f:
        return json.load(f)


def embed_and_store(batch_size: int = 64):
    kb = load_menu_index()
    model = get_model()
    collection = reset_collection()  # on repart d'une collection propre a chaque reindexation

    ids = [entry["id"] for entry in kb]
    documents = [entry["search_text"] for entry in kb]
    metadatas = [
        {
            "label": entry["label"],
            "path_str": entry["path_str"],
            "path_ids": " > ".join(entry["path_ids"]),
        }
        for entry in kb
    ]

    print(f"Encodage de {len(documents)} chemins avec le modele...")
    embeddings = model.encode(documents, batch_size=batch_size, show_progress_bar=True).tolist()

    # ChromaDB exige des IDs uniques : certains id "Name" peuvent se repeter
    # dans le XML d'origine (ex: reutilisation d'un ecran a plusieurs endroits) ->
    # on force l'unicite en suffixant avec l'index si besoin.
    seen = {}
    unique_ids = []
    for _id in ids:
        if _id not in seen:
            seen[_id] = 0
            unique_ids.append(_id)
        else:
            seen[_id] += 1
            unique_ids.append(f"{_id}__{seen[_id]}")

    collection.add(
        ids=unique_ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )

    print(f"{len(unique_ids)} chemins indexes dans ChromaDB.")
    return len(unique_ids)


if __name__ == "__main__":
    embed_and_store()
