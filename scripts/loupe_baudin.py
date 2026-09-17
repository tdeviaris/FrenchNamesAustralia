#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Découpe sur l'image d'origine la ligne d'une vue, pour la relire à l'œil.

La datation du typescript repose sur une reconnaissance optique qui lit mal les
chiffres de cette fonte. Là où elle contredit le compte des journées, il faut
retourner à l'image. Ce script refait la reconnaissance sur une seule vue, y
retrouve la ligne cherchée, et la découpe en pleine largeur à la résolution de
l'image, quelques lignes de contexte comprises.

Usage : python3 scripts/loupe_baudin.py <dossier> <vue> [<vue> ...] [--motif RE]
"""
import os, re, subprocess, sys, tempfile

PREP = r'''
import sys
from PIL import Image, ImageOps
src, dst = sys.argv[1], sys.argv[2]
im = Image.open(src).convert('L')
w, h = im.size
im = im.crop((int(w*0.10), int(h*0.05), int(w*0.95), int(h*0.95)))
if im.width != 1800:
    im = im.resize((1800, round(im.height*1800/im.width)), Image.LANCZOS)
im = ImageOps.autocontrast(im, cutoff=(2, 20))
im = im.point(lambda p: 255 if p > 175 else int(p*0.6))
im.save(dst)
print(im.width, im.height)
'''
DECOUPE = r'''
import sys
from PIL import Image
src, dst, x0, y0, x1, y1 = sys.argv[1], sys.argv[2], *map(int, sys.argv[3:7])
im = Image.open(src)
im.crop((x0, y0, x1, y1)).save(dst)
'''
MOTIF = re.compile(r'^[\W_]{0,6}[dbp]u\s', re.I)


def python_venv(racine):
    v = os.path.normpath(os.path.join(racine, '..', 'venv', 'bin', 'python'))
    return v if os.path.exists(v) else sys.executable


def lignes_de(py, image, tmp):
    """Les lignes reconnues sur la vue préparée, avec leur cadre."""
    r = subprocess.run([py, '-c', PREP, image, tmp],
                       capture_output=True, text=True, check=True)
    lp, hp = map(int, r.stdout.split())
    t = subprocess.run(['tesseract', tmp, 'stdout', '-l', 'fra', '--psm', '6',
                        'tsv'], capture_output=True, text=True).stdout
    lignes, mots, cadre = [], [], None
    for ligne in t.splitlines()[1:]:
        c = ligne.split('\t')
        if len(c) < 12:
            continue
        if c[0] == '5' and c[11].strip():
            g, h_, w_, hh = (int(c[6]), int(c[7]), int(c[8]), int(c[9]))
            mots.append(c[11])
            cadre = ((min(cadre[0], g), min(cadre[1], h_),
                      max(cadre[2], g + w_), max(cadre[3], h_ + hh))
                     if cadre else (g, h_, g + w_, h_ + hh))
        elif c[0] == '4' and mots:
            lignes.append((' '.join(mots), cadre))
            mots, cadre = [], None
    if mots:
        lignes.append((' '.join(mots), cadre))
    return lignes, (lp, hp)


def main():
    dossier = sys.argv[1].rstrip('/')
    motif = (re.compile(sys.argv[sys.argv.index('--motif') + 1], re.I)
             if '--motif' in sys.argv else MOTIF)
    vues = [int(a) for a in sys.argv[2:] if a.isdigit()]
    py = python_venv(os.path.join(dossier, 'img'))
    sortie = os.path.join(dossier, 'loupe')
    os.makedirs(sortie, exist_ok=True)

    for vue in vues:
        image = os.path.join(dossier, 'img', 'f%03d.jpg' % vue)
        if not os.path.exists(image):
            print('f%03d : image absente' % vue)
            continue
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as t:
            tmp = t.name
        lignes, (lp, hp) = lignes_de(py, image, tmp)
        # de la vue préparée à l'image d'origine : même rognage, même échelle
        taille = subprocess.run(
            [py, '-c', 'import sys;from PIL import Image;'
                       'print(*Image.open(sys.argv[1]).size)', image],
            capture_output=True, text=True).stdout.split()
        W, H = int(taille[0]), int(taille[1])
        x0r, y0r = int(W * 0.10), int(H * 0.05)
        k = (int(W * 0.95) - x0r) / float(lp)

        n = 0
        for i, (texte, cadre) in enumerate(lignes):
            if not cadre or not motif.search(texte):
                continue
            haut = cadre[1] - (cadre[3] - cadre[1])
            bas = cadre[3] + 2 * (cadre[3] - cadre[1])
            nom = os.path.join(sortie, 'f%03d_%d.png' % (vue, i))
            subprocess.run([py, '-c', DECOUPE, image, nom,
                            str(x0r), str(int(y0r + haut * k)),
                            str(int(W * 0.95)), str(int(y0r + bas * k))],
                           check=True)
            print('f%03d  %-46s -> %s' % (vue, texte[:46], os.path.basename(nom)))
            n += 1
        if not n:
            print('f%03d : rien qui corresponde au motif' % vue)
        os.unlink(tmp)


if __name__ == '__main__':
    main()
