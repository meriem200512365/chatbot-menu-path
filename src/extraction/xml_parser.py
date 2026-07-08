"""
xml_parser.py
-------------
Etape 1 du pipeline d'indexation.
Lit le fichier menu.xml et retourne une structure Python exploitable :
    - main_menu : nom du menu racine (ex: "MENU_GENERAL")
    - menus     : dict { nom_du_menu: [ {id, label, submenu, ...}, ... ] }

Rappel de la logique de liaison (voir README) :
    - <Menu Name="X"> definit un bloc de menu, reference par son nom "X".
    - <MenuItem SubMenuName="Y"> = noeud -> renvoie vers <Menu Name="Y">.
    - <MenuItem> sans SubMenuName = feuille -> ecran final (l'action reelle).
    - <MenuModule MainMenu="..."> = point d'entree racine.
"""

import xml.etree.ElementTree as ET
from src.config import XML_PATH


def parse_menu_xml(xml_path: str = XML_PATH):
    """
    Parse le fichier XML et retourne (main_menu, menus).

    menus = {
        "MENU_GENERAL": [
            {"id": "PARAMETRAGE", "label": "Parametrage",
             "submenu": "PARAMETRAGE_MENU", "command_type": None, "enabled": "true"},
            ...
        ],
        ...
    }
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    menu_module = root.find("MenuModule")
    if menu_module is None:
        raise ValueError("Balise <MenuModule> introuvable dans le XML.")

    main_menu = menu_module.get("MainMenu")
    if not main_menu:
        raise ValueError("Attribut MainMenu manquant sur <MenuModule>.")

    menus = {}
    for menu in menu_module.findall("Menu"):
        name = menu.get("Name")
        if not name:
            continue  # bloc <Menu> sans nom -> ignore (anomalie a signaler)

        items = []
        for item in menu.findall("MenuItem"):
            items.append({
                "id": item.get("Name"),
                "label": item.get("Label"),
                "submenu": item.get("SubMenuName"),   # None si feuille
                "command_type": item.get("CommandType"),
                "enabled": item.get("Enabled", "true"),
                "menu_item_type": item.get("MenuItemType"),
            })
        menus[name] = items

    return main_menu, menus


if __name__ == "__main__":
    main_menu, menus = parse_menu_xml()
    print(f"Menu racine : {main_menu}")
    print(f"Nombre de blocs <Menu> trouves : {len(menus)}")
    total_items = sum(len(v) for v in menus.values())
    print(f"Nombre total de <MenuItem> : {total_items}")
