"""
chroma_manager.py
------------------
Point d'acces unique a ChromaDB : creation du client persistant,
recuperation/creation/reset de la collection.

On utilise embedding_function=None car on fournit nous-memes les
vecteurs (calcules par sentence-transformers) -> ca evite que ChromaDB
telecharge/utilise son propre modele par defaut en interne.
"""

import chromadb

from src.config import CHROMA_DB_DIR, CHROMA_COLLECTION_NAME


def get_client():
    return chromadb.PersistentClient(path=CHROMA_DB_DIR)


def get_collection():
    client = get_client()
    return client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},  # similarite cosinus, adaptee aux embeddings de phrases
    )


def reset_collection():
    """Supprime puis recree la collection (utile avant une reindexation complete)."""
    client = get_client()
    try:
        client.delete_collection(CHROMA_COLLECTION_NAME)
    except Exception:
        pass  # la collection n'existait pas encore, pas grave
    return client.create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


if __name__ == "__main__":
    collection = get_collection()
    print(f"Collection '{CHROMA_COLLECTION_NAME}' prete. Nb elements : {collection.count()}")
