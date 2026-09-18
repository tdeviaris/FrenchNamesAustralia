#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Découpe les vues du typescript de Baudin en bandes prêtes à transcrire.

Une image envoyée au modèle est ramenée à 1568 pixels sur son grand côté. Une
page entière (2000 x 2627) y perd la moitié de sa largeur utile : il ne reste
qu'une douzaine de pixels par caractère, et c'est là que naissent les coquilles.

En rognant aux marges du bloc de texte, puis en coupant la page en deux bandes
horizontales, la largeur devient le grand côté : le texte est rendu sur 1568
pixels au lieu de 1194, et la hauteur de ligne double. Les deux bandes se
recouvrent de quelques lignes pour qu'aucune ne soit perdue à la couture.

Usage : python3 scripts/bandes_baudin.py <dossier> [vue ...] [--toutes]
"""
import os, sys

from PIL import Image, ImageOps

# le bloc de texte, en fraction de la page : on garde un peu de marge pour les
# notes portées à la main dans les blancs
GAUCHE, DROITE = 0.060, 0.996
HAUT, BAS = 0.030, 0.975
RECOUVREMENT = 0.045          # environ deux lignes, de part et d'autre de la couture


def bandes(chemin, sortie, vue):
    im = Image.open(chemin).convert('L')
    w, h = im.size
    bloc = im.crop((int(w * GAUCHE), int(h * HAUT),
                    int(w * DROITE), int(h * BAS)))
    # un rehaussement léger : le modèle lit mieux un gris naturel qu'un noir
    # et blanc seuillé, qui mange les jambages pâles de cette machine
    bloc = ImageOps.autocontrast(bloc, cutoff=(1, 12))
    lb, hb = bloc.size
    milieu, marge = hb // 2, int(hb * RECOUVREMENT)
    decoupes = [('a', 0, milieu + marge), ('b', milieu - marge, hb)]
    noms = []
    for suffixe, y0, y1 in decoupes:
        nom = os.path.join(sortie, 'f%03d%s.jpg' % (vue, suffixe))
        bloc.crop((0, y0, lb, y1)).save(nom, quality=92, optimize=True)
        noms.append(nom)
    return noms


def main():
    dossier = sys.argv[1].rstrip('/')
    img = os.path.join(dossier, 'img')
    sortie = os.path.join(dossier, 'bandes')
    os.makedirs(sortie, exist_ok=True)
    if '--toutes' in sys.argv:
        vues = sorted(int(n[1:-4]) for n in os.listdir(img)
                      if n.endswith('.jpg'))
    else:
        vues = [int(a) for a in sys.argv[2:] if a.isdigit()]
    for vue in vues:
        chemin = os.path.join(img, 'f%03d.jpg' % vue)
        if not os.path.exists(chemin):
            print('f%03d : image absente' % vue)
            continue
        noms = bandes(chemin, sortie, vue)
        t = Image.open(noms[0]).size
        print('f%03d -> %s  (%d x %d par bande)'
              % (vue, ', '.join(os.path.basename(n) for n in noms), *t))


if __name__ == '__main__':
    main()
