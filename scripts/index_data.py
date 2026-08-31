"""
index_data.py
-------------
Lance le pipeline d'indexation complet (offline), dans l'ordre du schema
valide :

    menu.xml -> xml_parser -> path_builder -> generate_json
             -> menu_index.json -> embed_documents -> ChromaDB

A relancer a chaque fois que menu.xml change (voir update_index.py).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.extraction.generate_json import generate_menu_index
from src.embedding.embed_documents import embed_and_store


def main():
    print("=== ETAPE 1/2 : extraction (XML -> JSON) ===")
    kb, report = generate_menu_index()
    print(f"  -> {len(kb)} chemins extraits")
    print(f"  -> {report['nb_liens_casses']} liens casses detectes")
    print(f"  -> {report['nb_menus_orphelins']} menus orphelins detectes")

    print("\n=== ETAPE 2/2 : embedding + indexation ChromaDB ===")
    nb_indexed = embed_and_store()
    print(f"  -> {nb_indexed} chemins indexes dans ChromaDB")

    print("\nIndexation terminee avec succes.")


if __name__ == "__main__":
    main()
