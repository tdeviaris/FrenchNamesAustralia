#!/usr/bin/env python3
"""
Script pour fusionner les pages FR/EN des ressources en pages uniques avec traductions
"""

import re
import sys
from pathlib import Path

def read_file(filepath):
    """Lit un fichier et retourne son contenu"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def extract_title(content):
    """Extrait le titre de la page"""
    match = re.search(r'<title>([^<]+)</title>', content)
    return match.group(1) if match else ""

def extract_nav(content):
    """Extrait le bloc de navigation"""
    match = re.search(r'<nav>.*?</nav>', content, re.DOTALL)
    return match.group(0) if match else ""

def extract_main_content(content):
    """Extrait le contenu principal (entre <main> et </main>)"""
    match = re.search(r'<main[^>]*>(.*?)</main>', content, re.DOTALL)
    return match.group(1).strip() if match else ""

def merge_pages(fr_file, en_file, output_file, page_key):
    """
    Fusionne deux pages FR/EN en une page unique

    Args:
        fr_file: Chemin vers le fichier français
        en_file: Chemin vers le fichier anglais
        output_file: Chemin du fichier de sortie
        page_key: Clé de base pour les traductions (ex: 'glossary')
    """
    print(f"📄 Fusion de {fr_file.name} et {en_file.name} → {output_file}")

    # Lire les deux fichiers
    fr_content = read_file(fr_file)
    en_content = read_file(en_file)

    # Extraire les titres
    fr_title = extract_title(fr_content)
    en_title = extract_title(en_content)

    print(f"  Titre FR: {fr_title}")
    print(f"  Titre EN: {en_title}")

    # Extraire le contenu principal
    fr_main = extract_main_content(fr_content)
    en_main = extract_main_content(en_content)

    print(f"  ✅ Contenus extraits")

    # Pour l'instant, on génère juste un rapport
    # La fusion réelle nécessite une analyse plus fine du contenu HTML

    return {
        'fr_title': fr_title,
        'en_title': en_title,
        'fr_main_length': len(fr_main),
        'en_main_length': len(en_main)
    }


if __name__ == "__main__":
    # Configuration des paires de fichiers à fusionner
    pairs = [
        ('glossaryF.html', 'glossaryE.html', 'glossary.html', 'glossary'),
        ('acteursF.html', 'acteursE.html', 'actors.html', 'actors'),
        ('cartesF.html', 'cartesE.html', 'maps.html', 'maps'),
        ('SourcesF.html', 'SourcesE.html', 'sources.html', 'sources'),
    ]

    base_dir = Path('/Users/tdeviaris/Desktop/Toponymes/FrenchNamesAustralia')

    for fr_name, en_name, out_name, key in pairs:
        fr_file = base_dir / fr_name
        en_file = base_dir / en_name
        out_file = base_dir / out_name

        if not fr_file.exists() or not en_file.exists():
            print(f"❌ Fichiers manquants pour {key}")
            continue

        result = merge_pages(fr_file, en_file, out_file, key)
        print(f"   FR main: {result['fr_main_length']} chars")
        print(f"   EN main: {result['en_main_length']} chars")
        print()
