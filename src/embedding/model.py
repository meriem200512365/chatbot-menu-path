"""
model.py
--------
Chargement (une seule fois, mis en cache) du modele SentenceTransformer
utilise pour transformer du texte en vecteurs.

Modele choisi : paraphrase-multilingual-MiniLM-L12-v2
    - supporte le francais (et 50+ langues)
    - leger (~470 Mo) et rapide sur CPU
    - bon compromis qualite/vitesse pour une recherche de type FAQ/menu
"""

from functools import lru_cache
from sentence_transformers import SentenceTransformer

from src.config import EMBEDDING_MODEL_NAME


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    """Retourne une instance unique (singleton) du modele d'embeddings."""
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


if __name__ == "__main__":
    model = get_model()
    vec = model.encode("je veux gerer les actes RO")
    print(f"Modele charge : {EMBEDDING_MODEL_NAME}")
    print(f"Dimension du vecteur : {len(vec)}")
