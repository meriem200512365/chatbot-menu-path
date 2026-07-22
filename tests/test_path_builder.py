"""
test_path_builder.py
---------------------
Teste la reconstruction des chemins de navigation (build_paths) sur un
graphe de menus factice, sans dependre du vrai menu.xml.

Cas couverts :
    - chemin simple (racine -> feuille)
    - chemin imbrique sur plusieurs niveaux
    - lien casse (SubMenuName qui pointe vers un menu inexistant)
    - menu orphelin (jamais atteint depuis la racine)
"""

from src.extraction.path_builder import build_paths


def _item(id_, label, submenu=None, command_type=None):
    return {
        "id": id_,
        "label": label,
        "submenu": submenu,
        "command_type": command_type,
        "enabled": "true",
        "menu_item_type": None,
    }


def test_chemin_simple():
    menus = {
        "ROOT": [_item("A", "Alpha")],
    }
    paths, broken_links, orphan_menus = build_paths("ROOT", menus)

    assert len(paths) == 1
    assert paths[0]["path_labels"] == ["Alpha"]
    assert paths[0]["path_ids"] == ["A"]
    assert broken_links == []
    assert orphan_menus == []


def test_chemin_imbrique_plusieurs_niveaux():
    menus = {
        "ROOT": [_item("PRESTATIONS", "Prestations", submenu="PRESTATIONS_MENU")],
        "PRESTATIONS_MENU": [_item("ACTES", "Actes", submenu="ACTES_MENU")],
        "ACTES_MENU": [_item("GESTION_RO", "Gestion des Actes RO")],
    }
    paths, broken_links, orphan_menus = build_paths("ROOT", menus)

    assert len(paths) == 1
    assert paths[0]["path_labels"] == ["Prestations", "Actes", "Gestion des Actes RO"]
    assert paths[0]["path_ids"] == ["PRESTATIONS", "ACTES", "GESTION_RO"]
    assert broken_links == []


def test_lien_casse_detecte():
    menus = {
        "ROOT": [_item("X", "Menu X", submenu="MENU_INEXISTANT")],
    }
    paths, broken_links, orphan_menus = build_paths("ROOT", menus)

    assert paths == []
    assert len(broken_links) == 1
    assert broken_links[0]["missing_submenu"] == "MENU_INEXISTANT"
    assert broken_links[0]["item_id"] == "X"


def test_menu_orphelin_detecte():
    menus = {
        "ROOT": [_item("A", "Alpha")],
        "JAMAIS_ATTEINT": [_item("B", "Beta")],
    }
    paths, broken_links, orphan_menus = build_paths("ROOT", menus)

    assert orphan_menus == ["JAMAIS_ATTEINT"]
    assert len(paths) == 1


def test_item_incomplet_ignore():
    """Un MenuItem sans id ou sans label doit etre ignore silencieusement."""
    menus = {
        "ROOT": [
            _item(None, "Sans id"),
            _item("Y", None),
            _item("OK", "Complet"),
        ],
    }
    paths, broken_links, orphan_menus = build_paths("ROOT", menus)

    assert len(paths) == 1
    assert paths[0]["id"] == "OK"


def test_profondeur_max_stoppe_boucle_infinie():
    """Un cycle entre deux menus ne doit pas boucler indefiniment :
    max_depth doit stopper le parcours."""
    menus = {
        "ROOT": [_item("A", "Alpha", submenu="ROOT")],  # boucle sur lui-meme
    }
    paths, broken_links, orphan_menus = build_paths("ROOT", menus, max_depth=5)

    # Aucune feuille n'est jamais atteinte -> aucun chemin construit,
    # et surtout le test se termine (pas de recursion infinie).
    assert paths == []
