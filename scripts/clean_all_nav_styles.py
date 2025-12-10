#!/usr/bin/env python3
"""
Supprime TOUS les styles de navigation inline des fichiers HTML
car ils sont maintenant centralisés dans css/nav.css
"""

import re
from pathlib import Path

FILES = [
    "glossaryF.html",
    "glossaryE.html",
    "acteursF.html",
    "acteursE.html",
    "cartesF.html",
    "cartesE.html",
    "SourcesF.html",
    "SourcesE.html",
    "resources.html",
]

def clean_nav_styles(filepath):
    """Supprime les styles de navigation d'un fichier"""
    print(f"📄 Traitement de {filepath}...")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # Supprimer les lignes de styles de navigation (une par une pour être précis)
    # Format compact sur une ligne
    content = re.sub(r'\s*nav\s*\{[^}]+\}\s*', '\n', content)
    content = re.sub(r'\s*nav\s+ul\s*\{[^}]+\}\s*', '\n', content)
    content = re.sub(r'\s*nav\s+ul\s+li\s+a\s*\{[^}]+\}\s*', '\n', content)
    content = re.sub(r'\s*nav\s+ul\s+li\s+a\.active[^}]+\}\s*', '\n', content)
    content = re.sub(r'\s*nav\s+ul\s+li\s+a:hover[^}]+\}\s*', '\n', content)
    content = re.sub(r'\s*nav\s+ul\s+li\s+a\.active,\s*nav\s+ul\s+li\s+a:hover\s*\{[^}]+\}\s*', '\n', content)
    content = re.sub(r'\s*\.lang-switcher\s*\{[^}]+\}\s*', '\n', content)
    content = re.sub(r'\s*\.lang-switcher\s+button\s*\{[^}]+\}\s*', '\n', content)
    content = re.sub(r'\s*\.lang-switcher\s+button:hover\s*\{[^}]+\}\s*', '\n', content)
    content = re.sub(r'\s*\.lang-switcher\s+button\.active\s*\{[^}]+\}\s*', '\n', content)
    content = re.sub(r'\s*\.lang-switcher\s+button\.active:hover\s*\{[^}]+\}\s*', '\n', content)
    content = re.sub(r'\s*\.lang-switcher\s+button:focus-visible\s*\{[^}]+\}\s*', '\n', content)
    content = re.sub(r'\s*\.lang-switcher\s+button\s+img\s*\{[^}]+\}\s*', '\n', content)

    # Supprimer dans les media queries (chercher les lignes qui contiennent nav ou lang-switcher)
    # On va identifier les media queries et enlever les lignes nav/lang-switcher dedans

    def clean_media_query(match):
        media_content = match.group(1)
        # Supprimer les lignes nav et lang-switcher
        media_content = re.sub(r'\s*:root\s*\{\s*--nav-height:[^}]+\}\s*', '', media_content)
        media_content = re.sub(r'\s*nav\s*\{[^}]+\}\s*', '', media_content)
        media_content = re.sub(r'\s*nav\s+ul\s*\{[^}]+\}\s*', '', media_content)
        media_content = re.sub(r'\s*nav\s+ul\s+li\s+a\s*\{[^}]+\}\s*', '', media_content)
        media_content = re.sub(r'\s*\.lang-switcher\s*\{[^}]+\}\s*', '', media_content)
        media_content = re.sub(r'\s*\.lang-switcher\s+button\s*\{[^}]+\}\s*', '', media_content)
        media_content = re.sub(r'\s*\.lang-switcher\s+button\s+img\s*\{[^}]+\}\s*', '', media_content)
        media_content = re.sub(r'\s*body\s*\{\s*padding-top:\s*var\(--nav-height\)[^}]*\}\s*', '', media_content)

        # Si le media query est vide ou presque vide, le supprimer
        if re.match(r'^\s*$', media_content):
            return ''

        return f'@media {match.group(0).split("{")[0].split("@media")[1]} {{{media_content}}}'

    # Traiter les media queries
    content = re.sub(r'@media\s*\([^)]+\)\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', clean_media_query, content)

    # Nettoyer les lignes vides multiples
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✅ Nettoyé")
        return True
    else:
        print(f"  ℹ️  Aucun changement")
        return False

if __name__ == '__main__':
    count = 0
    for filename in FILES:
        filepath = Path(filename)
        if filepath.exists():
            if clean_nav_styles(filepath):
                count += 1
        else:
            print(f"  ⚠️  {filename} introuvable")

    print(f"\n✨ {count} fichiers nettoyés")
