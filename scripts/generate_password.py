"""
generate_password.py
---------------------
Genere le hash bcrypt d'un mot de passe a coller dans config/auth_config.yaml
Usage : python scripts/generate_password.py
"""

import streamlit_authenticator as stauth

mot_de_passe = input("Mot de passe a hasher : ")
hash_genere = stauth.Hasher.hash(mot_de_passe)
print(f"\nColle ceci dans auth_config.yaml :\n{hash_genere}")