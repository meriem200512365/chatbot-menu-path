"""
path_builder.py
----------------
Etape 2 du pipeline d'indexation.
Parcourt le graphe de menus (depuis main_menu) et reconstruit, pour
chaque FEUILLE (ecran final), le chemin complet de labels.

Detecte aussi deux types d'anomalies utiles pour ton diagnostic :
    - liens casses  : un MenuItem pointe vers un SubMenuName qui n'existe pas
    - menus orphelins : un bloc <Menu> defini mais jamais atteint depuis la racine
"""

from src.config import MAX_DEPTH


def build_paths(main_menu: str, menus: dict, max_depth: int = MAX_DEPTH):
    """
    Retourne (paths, broken_links, orphan_menus)

    paths = [
        {
            "id": "PRR_ACT_006T_1",
            "label": "Gestion des Actes RO",
            "path_labels": ["Prestations", "Referentiel", "Actes", "Gestion des Actes RO"],
            "path_ids": ["PRESTATIONS", "PRS_REF", "ACTES", "PRR_ACT_006T_1"],
            "command_type": None,
        },
        ...
    ]
    """
    paths = []
    broken_links = []
    reached_menus = set()

    def walk(menu_name, trail_ids, trail_labels, depth):
        if depth > max_depth:
            return
        items = menus.get(menu_name)
        if items is None:
            return
        reached_menus.add(menu_name)

        for item in items:
            if not item["id"] or not item["label"]:
                continue  # item incomplet -> anomalie silencieuse, ignore

            new_ids = trail_ids + [item["id"]]
            new_labels = trail_labels + [item["label"]]

            if item["submenu"]:
                if item["submenu"] not in menus:
                    broken_links.append({
                        "from_menu": menu_name,
                        "item_id": item["id"],
                        "item_label": item["label"],
                        "missing_submenu": item["submenu"],
                    })
                    continue
                walk(item["submenu"], new_ids, new_labels, depth + 1)
            else:
                paths.append({
                    "id": item["id"],
                    "label": item["label"],
                    "path_labels": new_labels,
                    "path_ids": new_ids,
                    "command_type": item["command_type"],
                })

    walk(main_menu, [], [], 0)

    orphan_menus = sorted(set(menus.keys()) - reached_menus)

    return paths, broken_links, orphan_menus


if __name__ == "__main__":
    from src.extraction.xml_parser import parse_menu_xml

    main_menu, menus = parse_menu_xml()
    paths, broken_links, orphan_menus = build_paths(main_menu, menus)

    print(f"Chemins construits (ecrans finaux) : {len(paths)}")
    print(f"Liens casses detectes              : {len(broken_links)}")
    print(f"Menus orphelins (jamais atteints)   : {len(orphan_menus)}")

    if paths:
        print("\nExemple :")
        print(" > ".join(paths[0]["path_labels"]))
