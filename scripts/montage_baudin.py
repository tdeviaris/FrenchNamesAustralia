#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prépare la relecture à l'œil des lignes sensibles du journal de Baudin.

Tesseract lit la prose de ce dactylogramme mais se trompe régulièrement sur
les chiffres : il confond 3 et 5, et la machine à écrire tape un I majuscule
à la place du 1. Les dates et les positions doivent donc être relues.

Plutôt que de rouvrir 737 pages entières, on découpe dans l'image d'origine
les seules lignes qui portent une date ou une position, et on les empile par
paquets : une image de montage permet d'en contrôler vingt d'un coup.

Usage : python3 scripts/montage_baudin.py <dossier> [--par 20] [--quoi entetes|positions]
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image

# mêmes constantes que le prétraitement de l'OCR : il faut pouvoir revenir
# des coordonnées de la vue préparée à celles de l'image d'origine
ROGNE_X, ROGNE_Y, ROGNE_X2, ROGNE_Y2 = 0.10, 0.05, 0.95, 0.95
LARGEUR_PREP = 1800

MOIS_REP = ('vend[eé]miaire|brumaire|frimaire|niv[oô]se|pluvi[oô]se|vent[oô]se|'
            'germinal|flor[eé]al|prairial|messidor|thermidor|fructidor')
ENTETE = re.compile(r'\bDu\s+\S{1,4}\s+au\s+\S{1,4}\s+(?:de\s+)?(?:' + MOIS_REP + r')\b', re.I)
POSITION = re.compile(r'latitude\s+(?:fut\s+)?observ|Latitude\s+Sud\s+(?:estim|observ)', re.I)


def vers_origine(boite, taille, prep):
    """Ramène une boîte de la vue préparée aux coordonnées de l'image source."""
    L, H = taille
    x0, y0 = ROGNE_X * L, ROGNE_Y * H
    echelle = prep[0] / ((ROGNE_X2 - ROGNE_X) * L)
    return tuple(int(v) for v in (x0 + boite[0] / echelle, y0 + boite[1] / echelle,
                                  x0 + boite[2] / echelle, y0 + boite[3] / echelle))


def main():
    dossier = sys.argv[1].rstrip('/')
    par = int(sys.argv[sys.argv.index('--par') + 1]) if '--par' in sys.argv else 20
    quoi = sys.argv[sys.argv.index('--quoi') + 1] if '--quoi' in sys.argv else 'entetes'
    motif = ENTETE if quoi == 'entetes' else POSITION

    # les flux d'OCR écrivent chacun leur index : on les fusionne ici
    import glob
    index = {}
    for f in sorted(glob.glob(os.path.join(dossier, 'lignes_*.json'))):
        index.update(json.load(open(f, encoding='utf-8')))
    print('%d vues indexées' % len(index))
    sortie = os.path.join(dossier, 'montages_' + quoi)
    os.makedirs(sortie, exist_ok=True)

    retenues = []
    for vue in sorted(index):
        lignes = index[vue]
        # un en-tête de journée est court et centré : sa boîte est bien plus
        # étroite qu'une ligne de texte courant. C'est le meilleur moyen de
        # écarter les « du … au … » qui ne sont que de la prose.
        large = max((l['boite'][2] - l['boite'][0]) for l in lignes) if lignes else 0
        for ligne in lignes:
            if not motif.search(ligne['texte']):
                continue
            if quoi == 'entetes' and large:
                w = ligne['boite'][2] - ligne['boite'][0]
                if w > 0.72 * large:
                    continue
            retenues.append((vue, ligne))
    print('%d lignes « %s » à relire' % (len(retenues), quoi))

    bande = 10
    lot, n = [], 0
    for vue, ligne in retenues:
        chemin = os.path.join(dossier, 'img', vue + '.jpg')
        if not os.path.exists(chemin):
            continue
        im = Image.open(chemin)
        x1, y1, x2, y2 = vers_origine(ligne['boite'], im.size,
                                      ligne.get('prep', [LARGEUR_PREP, 0]))
        # bande sur toute la largeur utile de la page et d'une ligne et demie
        # de haut : la ligne visée reste lisible même si le repérage dérive
        h = max(20, y2 - y1)
        bout = im.crop((int(im.width * 0.08), max(0, int(y1 - h * 0.9)),
                        int(im.width * 0.97), min(im.height, int(y2 + h * 0.9))))
        cible = 1450
        if bout.width != cible:
            bout = bout.resize((cible, max(1, round(bout.height * cible / bout.width))),
                               Image.LANCZOS)
        lot.append((vue, bout))
        if len(lot) == par:
            n += 1
            ecrit(lot, os.path.join(sortie, 'm%03d.png' % n), bande)
            lot = []
    if lot:
        n += 1
        ecrit(lot, os.path.join(sortie, 'm%03d.png' % n), bande)
    print('%d montages écrits dans %s' % (n, sortie))


def ecrit(lot, chemin, bande):
    from PIL import ImageDraw
    largeur = max(b.width for _, b in lot) + 170
    hauteur = sum(b.height + bande for _, b in lot) + bande
    page = Image.new('RGB', (largeur, hauteur), 'white')
    dessin = ImageDraw.Draw(page)
    y = bande
    for vue, bout in lot:
        page.paste(bout, (165, y))
        dessin.text((8, y + bout.height // 2 - 6), vue, fill='black')
        dessin.line([(0, y - bande // 2), (largeur, y - bande // 2)], fill='#bbbbbb')
        y += bout.height + bande
    page.save(chemin)


if __name__ == '__main__':
    main()
