#!/usr/bin/env python3
"""
Script pour ajouter l'option 'À propos' au menu de navigation dans toutes les pages HTML
"""

import re
import os

# Liste des fichiers à modifier (excluant les backups)
files = [
    'index.html',
    'map_dentrecasteaux.html',
    'map_baudin.html',
    'resources.html',
    'expert.html',
    'glossaryF.html',
    'glossaryE.html',
    'acteursF.html',
    'acteursE.html',
    'cartesF.html',
    'cartesE.html',
    'SourcesF.html',
    'SourcesE.html'
]

for filename in files:
    if not os.path.exists(filename):
        print(f"⚠️  {filename} n'existe pas, ignoré")
        continue

    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    # Rechercher la ligne avec nav-resources et ajouter nav-about après
    pattern = r'(<li><a href="resources\.html" id="nav-resources" data-i18n="nav-resources">Ressources</a></li>)'
    replacement = r'\1\n        <li><a href="presentation.html" id="nav-about" data-i18n="nav-about">À propos</a></li>'

    new_content = re.sub(pattern, replacement, content)

    if new_content != content:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"✅ {filename} modifié")
    else:
        print(f"⚠️  {filename} - pattern non trouvé")

print("\n✅ Modification du menu terminée!")
