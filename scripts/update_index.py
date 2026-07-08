"""
update_index.py
-----------------
A executer chaque fois que data/menu.xml a ete modifie (nouvelle version
du menu exportee depuis l'appli). Relance simplement le pipeline complet
(reset_collection() dans embed_documents garantit qu'on ne duplique pas
les anciennes donnees).
"""

from index_data import main

if __name__ == "__main__":
    print("Reindexation suite a une mise a jour de menu.xml...\n")
    main()
