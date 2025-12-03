#!/usr/bin/env python3
"""
Script pour supprimer les styles de navigation redondants des fichiers HTML
après l'ajout de css/nav.css
"""

import re
import sys

def remove_nav_styles_from_file(filepath):
    """Supprime les styles de navigation d'un fichier HTML"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Patterns à supprimer (styles de navigation)
        patterns_to_remove = [
            r':root\s*\{\s*--nav-height:\s*[^}]+\}\s*',
            r'nav\s*\{[^}]+\}\s*',
            r'nav\s+ul\s*\{[^}]+\}\s*',
            r'nav\s+ul\s+li\s+a\s*\{[^}]+\}\s*',
            r'nav\s+ul\s+li\s+a\.active[^}]+\}\s*',
            r'nav\s+ul\s+li\s+a:hover[^}]+\}\s*',
            r'nav\s+ul\s+li\s+a\.active,\s*nav\s+ul\s+li\s+a:hover\s*\{[^}]+\}\s*',
            r'\.lang-switcher\s*\{[^}]+\}\s*',
            r'\.lang-switcher\s+button\s*\{[^}]+\}\s*',
            r'\.lang-switcher\s+button:hover\s*\{[^}]+\}\s*',
            r'\.lang-switcher\s+button\.active\s*\{[^}]+\}\s*',
            r'\.lang-switcher\s+button\.active:hover\s*\{[^}]+\}\s*',
            r'\.lang-switcher\s+button:focus-visible\s*\{[^}]+\}\s*',
            r'\.lang-switcher\s+button\s+img\s*\{[^}]+\}\s*',
        ]

        # Supprimer dans les @media queries aussi
        media_patterns = [
            r'@media\s*\([^)]+\)\s*\{[^}]*(?:nav|lang-switcher)[^}]*\}',
        ]

        for pattern in patterns_to_remove:
            content = re.sub(pattern, '', content, flags=re.MULTILINE | re.DOTALL)

        # Nettoyer les lignes vides multiples
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)

        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Styles supprimés de {filepath}")
            return True
        else:
            print(f"ℹ️  Aucun changement dans {filepath}")
            return False

    except Exception as e:
        print(f"❌ Erreur avec {filepath}: {e}")
        return False

if __name__ == '__main__':
    files = [
        'index.html',
        'expert.html',
        'resources.html',
        'glossaryF.html',
        'glossaryE.html',
        'acteursF.html',
        'acteursE.html',
        'cartesF.html',
        'cartesE.html',
        'SourcesF.html',
        'SourcesE.html',
        'map_baudin.html',
        'map_dentrecasteaux.html',
    ]

    modified_count = 0
    for filepath in files:
        if remove_nav_styles_from_file(filepath):
            modified_count += 1

    print(f"\n✨ {modified_count} fichiers modifiés")
