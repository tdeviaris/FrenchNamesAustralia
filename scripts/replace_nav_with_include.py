#!/usr/bin/env python3
"""
Remplace le HTML de navigation par un conteneur d'inclusion
dans toutes les pages principales
"""

import re
from pathlib import Path

FILES = [
    "index.html",
    "expert.html",
    "resources.html",
    "glossary.html",
    "actors.html",
    "maps.html",
    "sources.html",
]

def replace_nav(filepath):
    """Remplace le contenu du <nav> par data-include-nav"""
    print(f"📄 Traitement de {filepath}...")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # Pattern pour matcher tout le contenu entre <nav> et </nav>
    # (?s) permet au . de matcher les retours à la ligne
    pattern = r'<nav>.*?</nav>'

    # Remplacement par le conteneur d'inclusion
    replacement = '<div data-include-nav></div>'

    content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✅ Remplacé")
        return True
    else:
        print(f"  ℹ️  Aucun changement")
        return False

if __name__ == '__main__':
    count = 0
    for filename in FILES:
        filepath = Path(filename)
        if filepath.exists():
            if replace_nav(filepath):
                count += 1
        else:
            print(f"  ⚠️  {filename} introuvable")

    print(f"\n✨ {count} fichiers modifiés")
