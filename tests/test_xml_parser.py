"""
test_xml_parser.py
--------------------
Teste le parsing du XML sur un menu.xml minimal (genere en memoire),
sans dependre du vrai fichier data/menu.xml (qui peut changer/grossir).
"""

import pytest

from src.extraction.xml_parser import parse_menu_xml

XML_MINIMAL = """<?xml version="1.0" encoding="UTF-8"?>
<Root>
    <MenuModule MainMenu="MENU_GENERAL">
        <Menu Name="MENU_GENERAL">
            <MenuItem Name="PARAM" Label="Parametrage" SubMenuName="MENU_PARAM" Enabled="true"/>
            <MenuItem Name="ACCUEIL" Label="Accueil" CommandType="OPEN_SCREEN" Enabled="true"/>
        </Menu>
        <Menu Name="MENU_PARAM">
            <MenuItem Name="DEVIS" Label="Devis Web" CommandType="OPEN_SCREEN" Enabled="true"/>
        </Menu>
    </MenuModule>
</Root>
"""


@pytest.fixture
def xml_file(tmp_path):
    path = tmp_path / "menu_test.xml"
    path.write_text(XML_MINIMAL, encoding="utf-8")
    return str(path)


def test_main_menu_detecte(xml_file):
    main_menu, menus = parse_menu_xml(xml_file)
    assert main_menu == "MENU_GENERAL"


def test_nombre_de_blocs_menu(xml_file):
    _, menus = parse_menu_xml(xml_file)
    assert set(menus.keys()) == {"MENU_GENERAL", "MENU_PARAM"}


def test_item_noeud_vs_feuille(xml_file):
    _, menus = parse_menu_xml(xml_file)
    items = {item["id"]: item for item in menus["MENU_GENERAL"]}

    # noeud : a un SubMenuName
    assert items["PARAM"]["submenu"] == "MENU_PARAM"

    # feuille : pas de SubMenuName
    assert items["ACCUEIL"]["submenu"] is None
    assert items["ACCUEIL"]["command_type"] == "OPEN_SCREEN"


def test_menu_module_absent_leve_erreur(tmp_path):
    path = tmp_path / "invalide.xml"
    path.write_text("<Root></Root>", encoding="utf-8")

    with pytest.raises(ValueError):
        parse_menu_xml(str(path))


def test_main_menu_attr_manquant_leve_erreur(tmp_path):
    path = tmp_path / "invalide2.xml"
    path.write_text('<Root><MenuModule></MenuModule></Root>', encoding="utf-8")

    with pytest.raises(ValueError):
        parse_menu_xml(str(path))
