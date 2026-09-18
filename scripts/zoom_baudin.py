#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Grossit un mot du typescript de Baudin, pour trancher un accent ou un chiffre.

Une bande entière est rendue sur 1568 pixels de large : à cette échelle, le
circonflexe de « fûmes » et l'absence d'accent de « fumes » se ressemblent. Le
seul remède est de ne montrer qu'un mot à la fois, qui occupe alors toute la
largeur et se lit sans hésitation.

L'outil cherche le mot dans la vue, découpe quelques caractères autour de lui à
la résolution de l'original, et écrit l'image agrandie.

Usage : python3 scripts/zoom_baudin.py <dossier> <vue> <mot> [<mot> ...]
"""
import difflib, importlib.util, os, re, sys, tempfile, unicodedata

from PIL import Image

LARGEUR = 1500          # largeur visée pour le morceau découpé
CARACTERES = 14         # largeur de la fenêtre, en caractères de la machine


def module(nom):
    chemin = os.path.join(os.path.dirname(os.path.abspath(__file__)), nom)
    spec = importlib.util.spec_from_file_location(nom[:-3], chemin)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


L = module('loupe_baudin.py')


def nu(s):
    """Le mot sans accents ni ponctuation : la reconnaissance les perd."""
    s = ''.join(c for c in unicodedata.normalize('NFD', s.lower())
                if unicodedata.category(c) != 'Mn')
    return re.sub(r"[^a-z0-9']", '', s)


def mots_de(py, image, tmp):
    """Les mots reconnus sur la vue, avec leur cadre dans l'image préparée."""
    subprocess = __import__('subprocess')
    r = subprocess.run([py, '-c', L.PREP, image, tmp],
                       capture_output=True, text=True, check=True)
    lp, hp = map(int, r.stdout.split())
    t = subprocess.run(['tesseract', tmp, 'stdout', '-l', 'fra', '--psm', '6',
                        'tsv'], capture_output=True, text=True).stdout
    mots = []
    for ligne in t.splitlines()[1:]:
        c = ligne.split('\t')
        if len(c) < 12 or c[0] != '5' or not c[11].strip():
            continue
        g, h, w, hh = int(c[6]), int(c[7]), int(c[8]), int(c[9])
        mots.append((c[11], (g, h, g + w, h + hh)))
    return mots, lp


def main():
    dossier = sys.argv[1].rstrip('/')
    vue = int(sys.argv[2])
    cherches = [a for a in sys.argv[3:] if not a.startswith('--')]
    if not cherches:
        sys.exit('indiquer au moins un mot à grossir')
    image = os.path.join(dossier, 'img', 'f%03d.jpg' % vue)
    if not os.path.exists(image):
        sys.exit('f%03d : image absente' % vue)
    py = L.python_venv(os.path.join(dossier, 'img'))
    sortie = os.path.join(dossier, 'zoom')
    os.makedirs(sortie, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as t:
        tmp = t.name
    try:
        mots, lp = mots_de(py, image, tmp)
    finally:
        os.unlink(tmp)

    # la chasse de la machine : largeur moyenne d'un caractère, mesurée sur
    # les mots courts, que la reconnaissance ne fusionne pas
    largeurs = [(bo[2] - bo[0]) / float(len(m)) for m, bo in mots
                if 3 <= len(m) <= 8]
    largeurs.sort()
    chasse = largeurs[len(largeurs) // 2] if largeurs else 24.0

    im = Image.open(image).convert('L')
    W, H = im.size
    x0, y0 = int(W * 0.10), int(H * 0.05)
    k = (int(W * 0.95) - x0) / float(lp)

    for cherche in cherches:
        cible = max(mots, key=lambda m: difflib.SequenceMatcher(
            None, nu(m[0]), nu(cherche)).ratio())
        score = difflib.SequenceMatcher(None, nu(cible[0]), nu(cherche)).ratio()
        if score < 0.55:
            print('%-16s : rien d’approchant sur la vue %d' % (cherche, vue))
            continue
        # Les cadres que donne la reconnaissance fusionnent parfois plusieurs
        # mots : on ne s'y fie pas pour la largeur. On prend une fenêtre de
        # onze caractères centrée sur le mot, la machine frappant toutes ses
        # lettres à la même chasse.
        # le cadre fusionné déborde vers la droite : son bord gauche marque
        # le début du mot cherché, on centre donc à partir de là
        g, h, d, b = cible[1]
        centre = g + len(cible[0]) * chasse / 2.0
        demi = CARACTERES * chasse / 2.0
        hauteur = b - h
        boite = (max(0, int(x0 + (centre - demi) * k)),
                 max(0, int(y0 + (h - hauteur * 0.8) * k)),
                 min(W, int(x0 + (centre + demi) * k)),
                 min(H, int(y0 + (b + hauteur * 0.8) * k)))
        bout = im.crop(boite)
        if bout.width and bout.width != LARGEUR:
            f = LARGEUR / float(bout.width)
            bout = bout.resize((LARGEUR, max(1, round(bout.height * f))),
                               Image.LANCZOS)
        nom = os.path.join(sortie, 'f%03d_%s.png'
                           % (vue, re.sub(r'\W', '', cherche)[:20]))
        bout.save(nom)
        print('%-16s : lu « %s » -> %s' % (cherche, cible[0], nom))


if __name__ == '__main__':
    main()
