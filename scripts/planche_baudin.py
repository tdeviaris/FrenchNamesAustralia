#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Empile sur une même planche les lignes d'en-tête à relire à l'œil.

Les journées où la date lue contredit le calcul se règlent presque toutes en
regardant la ligne sur l'image : la fonte de cette machine fait confondre 3 et
5 à la reconnaissance, mais pas à l'œil. Plutôt que d'ouvrir cinquante-cinq
images, on découpe chaque ligne litigieuse à la résolution de l'original et on
les empile par sept, ce qui tient en une planche et se lit d'un regard.

Usage : python3 scripts/planche_baudin.py <dossier> [--genre chiffre] [--par 7]
"""
import difflib, importlib.util, json, os, subprocess, sys, tempfile

from PIL import Image, ImageDraw

LARGEUR = 1600          # largeur commune des bandeaux empilés
MARGE = 26              # hauteur de l'étiquette portée à gauche de chaque ligne


def loupe():
    chemin = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          'loupe_baudin.py')
    spec = importlib.util.spec_from_file_location('loupe', chemin)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


L = loupe()


def bandeau(dossier, py, vue, attendu):
    """Le morceau d'image qui porte la ligne cherchée, avec son contexte."""
    image = os.path.join(dossier, 'img', 'f%03d.jpg' % vue)
    if not os.path.exists(image):
        return None
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as t:
        tmp = t.name
    try:
        lignes, (lp, hp) = L.lignes_de(py, image, tmp)
    finally:
        os.unlink(tmp)
    if not lignes:
        return None
    # la ligne dont le texte reconnu ressemble le plus à celui qu'on cherche
    cible = max(lignes, key=lambda x: difflib.SequenceMatcher(
        None, x[0], attendu).ratio())
    texte, cadre = cible
    if not cadre:
        return None
    im = Image.open(image)
    W, H = im.size
    x0, y0 = int(W * 0.10), int(H * 0.05)
    k = (int(W * 0.95) - x0) / float(lp)
    h = cadre[3] - cadre[1]
    haut = max(0, int(y0 + (cadre[1] - h) * k))
    bas = min(H, int(y0 + (cadre[3] + h) * k))
    bande = im.crop((x0, haut, int(W * 0.95), bas)).convert('L')
    if bande.width != LARGEUR:
        bande = bande.resize(
            (LARGEUR, max(1, round(bande.height * LARGEUR / bande.width))),
            Image.LANCZOS)
    return bande


def main():
    dossier = sys.argv[1].rstrip('/')
    genre = (sys.argv[sys.argv.index('--genre') + 1]
             if '--genre' in sys.argv else 'chiffre')
    par = int(sys.argv[sys.argv.index('--par') + 1]) if '--par' in sys.argv else 7
    liste = json.load(open(os.path.join(dossier, 'a_verifier.json'),
                           encoding='utf-8'))
    lot = [d for d in liste if d['genre'] == genre]
    py = L.python_venv(os.path.join(dossier, 'img'))
    sortie = os.path.join(dossier, 'planches')
    os.makedirs(sortie, exist_ok=True)

    faits, n = [], 0
    for d in lot:
        b = bandeau(dossier, py, d['vue'], d['ligne'])
        if b is None:
            print('f%03d : ligne introuvable' % d['vue'])
            continue
        faits.append((d, b))
        n += 1
        if len(faits) == par:
            ecrit(sortie, faits, len(faits) and (n - 1) // par + 1)
            faits = []
    if faits:
        ecrit(sortie, faits, (n - 1) // par + 1)
    print('\n%d lignes découpées, planches dans %s' % (n, sortie))


def ecrit(sortie, faits, numero):
    hauteur = sum(b.height + MARGE for _, b in faits)
    planche = Image.new('L', (LARGEUR, hauteur), 255)
    d = ImageDraw.Draw(planche)
    y = 0
    print('\n--- planche %02d' % numero)
    for entree, b in faits:
        etiquette = ('f%03d   calcul : %s   (%s)'
                     % (entree['vue'], entree['date'], entree['republicain']))
        d.text((8, y + 6), etiquette, fill=0)
        d.line((0, y + MARGE - 3, LARGEUR, y + MARGE - 3), fill=160)
        planche.paste(b, (0, y + MARGE))
        print('   %s   | OCR : %s' % (etiquette, entree['ligne'][:46]))
        y += b.height + MARGE
    planche.save(os.path.join(sortie, 'p%02d.png' % numero))


if __name__ == '__main__':
    main()
