#!/usr/bin/env python3
"""
Vérifie les pages ressources bilingues (sans suffixe E/F).

Depuis le nettoyage du repo, les pages ressources (glossaire, acteurs, cartes, sources)
sont des pages uniques contenant deux blocs :
- data-lang="en"
- data-lang="fr"
Le switch de langue s'appuie sur l'attribut <html lang="..."> (piloté par js/main.js).
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

def extract_lang_block(content, lang):
    match = re.search(rf'<div\\s+data-lang=\"{lang}\">(.*?)</div>', content, re.DOTALL)
    return match.group(1).strip() if match else ""


def inspect_bilingual_page(filepath):
    content = read_file(filepath)
    title = extract_title(content)
    fr_block = extract_lang_block(content, "fr")
    en_block = extract_lang_block(content, "en")

    ok = bool(fr_block) and bool(en_block)
    return {
        "title": title,
        "ok": ok,
        "fr_chars": len(fr_block),
        "en_chars": len(en_block),
    }


if __name__ == "__main__":
    pages = [
        Path("glossary.html"),
        Path("actors.html"),
        Path("maps.html"),
        Path("sources.html"),
    ]

    for page in pages:
        if not page.exists():
            print(f"❌ Fichier manquant: {page}")
            continue
        result = inspect_bilingual_page(page)
        status = "✅" if result["ok"] else "❌"
        print(f"{status} {page} — {result['title']}")
        print(f"   EN block: {result['en_chars']} chars")
        print(f"   FR block: {result['fr_chars']} chars")
        print()
