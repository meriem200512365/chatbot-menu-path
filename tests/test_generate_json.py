"""
test_generate_json.py
-----------------------
Teste generate_menu_index() de bout en bout, mais sur un graphe de menus
factice (via monkeypatch de parse_menu_xml) et en ecrivant dans un
dossier temporaire (tmp_path) pour ne jamais toucher aux vrais fichiers
data/chemins/*.json.
"""

import json

import src.extraction.generate_json as generate_json_module


def fake_parse_menu_xml():
    main_menu = "ROOT"
    menus = {
        "ROOT": [
            {"id": "A", "label": "Alpha", "submenu": None,
             "command_type": "OPEN_SCREEN", "enabled": "true", "menu_item_type": None},
            {"id": "B", "label": "Beta", "submenu": "MENU_INEXISTANT",
             "command_type": None, "enabled": "true", "menu_item_type": None},
        ],
    }
    return main_menu, menus


def test_generate_menu_index_ecrit_les_deux_fichiers(tmp_path, monkeypatch):
    chemins_dir = tmp_path / "chemins"
    menu_index_json = chemins_dir / "menu_index.json"
    liens_casses_json = chemins_dir / "liens_casses.json"

    monkeypatch.setattr(generate_json_module, "parse_menu_xml", fake_parse_menu_xml)
    monkeypatch.setattr(generate_json_module, "CHEMINS_DIR", str(chemins_dir))
    monkeypatch.setattr(generate_json_module, "MENU_INDEX_JSON", str(menu_index_json))
    monkeypatch.setattr(generate_json_module, "LIENS_CASSES_JSON", str(liens_casses_json))

    kb, report = generate_json_module.generate_menu_index()

    assert menu_index_json.exists()
    assert liens_casses_json.exists()

    # kb : un seul chemin valide (Alpha), Beta pointe vers un lien casse
    assert len(kb) == 1
    assert kb[0]["label"] == "Alpha"
    assert kb[0]["path_str"] == "Alpha"

    # rapport d'anomalies
    assert report["nb_liens_casses"] == 1
    assert report["liens_casses"][0]["missing_submenu"] == "MENU_INEXISTANT"

    # verifie que le contenu ecrit sur disque correspond bien
    with open(menu_index_json, encoding="utf-8") as f:
        assert json.load(f) == kb
