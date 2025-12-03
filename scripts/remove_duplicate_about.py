#!/usr/bin/env python3
"""
Script pour supprimer les doublons du menu 'À propos'
"""

import re
from pathlib import Path

# Liste des fichiers à traiter
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

base_dir = Path('/Users/tdeviaris/Desktop/Toponymes/FrenchNamesAustralia')

for filename in files:
    filepath = base_dir / filename
    if not filepath.exists():
        print(f"⚠️  {filename} n'existe pas, ignoré")
        continue

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Compter les occurrences de la ligne nav-about
    about_line = r'\s*<li><a href="presentation\.html" id="nav-about" data-i18n="nav-about">À propos</a></li>'
    matches = list(re.finditer(about_line, content))

    if len(matches) > 1:
        # Garder seulement la première occurrence
        # Remplacer toutes les occurrences sauf la première par une chaîne vide
        new_content = content
        for match in reversed(matches[1:]):  # Partir de la fin pour ne pas décaler les indices
            new_content = new_content[:match.start()] + new_content[match.end():]

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"✅ {filename} - {len(matches)} occurrences → 1 occurrence")
    else:
        print(f"✓  {filename} - déjà correct (1 occurrence)")

print("\n✅ Nettoyage des doublons terminé!")
