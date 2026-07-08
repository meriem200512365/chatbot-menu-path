"""
generate_json.py
-----------------
Etape 3 du pipeline d'indexation.
Prend les chemins construits par path_builder et les sauvegarde en JSON :
    - menu_index.json    : la base de connaissance (utilisee par l'embedding)
    - liens_casses.json  : le rapport d'anomalies (utile pour ton diagnostic)
"""

import json
import os

from src.config import MENU_INDEX_JSON, LIENS_CASSES_JSON, CHEMINS_DIR
from src.extraction.xml_parser import parse_menu_xml
from src.extraction.path_builder import build_paths


def generate_menu_index():
    os.makedirs(CHEMINS_DIR, exist_ok=True)

    main_menu, menus = parse_menu_xml()
    paths, broken_links, orphan_menus = build_paths(main_menu, menus)

    # --- menu_index.json : ce que le chatbot va utiliser pour repondre ---
    kb = []
    for p in paths:
        kb.append({
            "id": p["id"],
            "label": p["label"],
            "path_labels": p["path_labels"],
            "path_ids": p["path_ids"],
            "path_str": " > ".join(p["path_labels"]),
            "command_type": p["command_type"],
            # texte utilise pour generer l'embedding : chemin complet,
            # ca donne du contexte au modele (pas juste le dernier label)
            "search_text": " > ".join(p["path_labels"]),
        })

    with open(MENU_INDEX_JSON, "w", encoding="utf-8") as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

    # --- liens_casses.json : rapport d'anomalies ---
    report = {
        "nb_menus_total": len(menus),
        "nb_chemins_valides": len(paths),
        "nb_liens_casses": len(broken_links),
        "nb_menus_orphelins": len(orphan_menus),
        "liens_casses": broken_links,
        "menus_orphelins": orphan_menus,
    }
    with open(LIENS_CASSES_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return kb, report


if __name__ == "__main__":
    kb, report = generate_menu_index()
    print(f"menu_index.json genere   : {len(kb)} chemins  -> {MENU_INDEX_JSON}")
    print(f"liens_casses.json genere : {report['nb_liens_casses']} liens casses, "
          f"{report['nb_menus_orphelins']} menus orphelins -> {LIENS_CASSES_JSON}")
