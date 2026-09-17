#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OCR de la copie dactylographiée du journal de Baudin (BnF, SG MS4-33).

Tesseract lit correctement la prose de ce typescript mais confond 3 et 5 dans
cette fonte : les chiffres ne sont pas exploitables sans relecture. Le script
produit donc deux sorties :

  - le texte brut de chaque vue (ocr/fNNN.txt), pour le récit ;
  - la position en pixels des lignes de date et de position (lignes.json),
    qui sert à découper ces lignes pour relecture à l'œil.

La machine à écrire n'a pas de touche « 1 » : le dactylographe frappe un I
majuscule. La correction est faite ici, mais seulement dans un contexte
numérique, pour ne pas abîmer les mots.

Usage : python3 scripts/ocr_baudin_bnf.py <dossier_images> [--depuis N]
"""
import json, os, re, subprocess, sys

VENV = None            # rempli par main() : python du venv (Pillow)

PREP = r'''
import sys
from PIL import Image, ImageOps, ImageFilter
src, dst = sys.argv[1], sys.argv[2]
im = Image.open(src).convert('L')
w, h = im.size
im = im.crop((int(w*0.10), int(h*0.05), int(w*0.95), int(h*0.95)))
# Les vues ne font pas toutes la même taille : on ramène tout à 1800 px de
# large, ce qui suffit à la fonte de la machine à écrire et borne le temps
# de traitement.
if im.width != 1800:
    im = im.resize((1800, round(im.height * 1800 / im.width)), Image.LANCZOS)
im = ImageOps.autocontrast(im, cutoff=(2, 20))
im = im.point(lambda p: 255 if p > 175 else int(p * 0.6))
im.save(dst, optimize=False, compress_level=1)
'''

# En-tête d'entrée : « Du 30 au I de Ventose an 9 de la République. »
MOIS_REP = ('vendemiaire|vendémiaire|brumaire|frimaire|nivose|nivôse|pluviose|'
            'pluviôse|ventose|ventôse|germinal|floreal|floréal|prairial|'
            'messidor|thermidor|fructidor')
ENTETE = re.compile(r'\bDu\s+[IVX\d]{1,3}\s+au\s+[IVX\d]{1,3}\s+(?:de\s+)?(?:' + MOIS_REP + r')\b', re.I)
# Ligne de position : « A midi la latitude fut observée de … »
POSITION = re.compile(r'latitude\s+(?:fut\s+)?observ|longitude\s+(?:de\s+nos\s+)?montres|'
                      r'Latitude\s+Sud\s+(?:estim|observ)', re.I)


def corrige_chiffres(t):
    """Le I majuscule tient lieu de 1 : ne le remplacer qu'entre chiffres."""
    for _ in range(3):
        t = re.sub(r'(?<=\d)I', '1', t)
        t = re.sub(r'I(?=\d)', '1', t)
    # « I8°6' », « N°3I », « II8° »
    t = re.sub(r'\bI(?=\d*[°\'"])', '1', t)
    t = re.sub(r'(?<=[°\'])I\b', '1', t)
    return t


def ocr_page(chemin, sortie, tmp):
    subprocess.run([VENV, '-c', PREP, chemin, tmp], check=True)
    # la taille de la vue préparée est enregistrée avec les lignes : c'est elle
    # qui permet de revenir aux coordonnées de l'image d'origine
    taille = subprocess.run([VENV, '-c',
        'import sys;from PIL import Image;im=Image.open(sys.argv[1]);'
        'print(im.width, im.height)', tmp],
        capture_output=True, text=True).stdout.split()
    r = subprocess.run(['tesseract', tmp, 'stdout', '-l', 'fra', '--psm', '6',
                        'tsv'], capture_output=True, text=True)
    lignes, texte = [], []
    courante, boite = [], None
    for ligne in r.stdout.splitlines()[1:]:
        c = ligne.split('\t')
        if len(c) < 12:
            continue
        niveau, gauche, haut, larg, haut_px, conf, mot = (
            c[0], c[6], c[7], c[8], c[9], c[10], c[11])
        if niveau == '5' and mot.strip():
            courante.append(mot)
            g, h_, w_, hh = int(gauche), int(haut), int(larg), int(haut_px)
            boite = (min(boite[0], g), min(boite[1], h_),
                     max(boite[2], g + w_), max(boite[3], h_ + hh)) if boite else (g, h_, g + w_, h_ + hh)
        elif niveau == '4' and courante:
            texte.append(' '.join(courante))
            lignes.append({'texte': ' '.join(courante), 'boite': boite})
            courante, boite = [], None
    if courante:
        texte.append(' '.join(courante))
        lignes.append({'texte': ' '.join(courante), 'boite': boite})
    brut = corrige_chiffres('\n'.join(texte))
    open(sortie, 'w', encoding='utf-8').write(brut)
    for l in lignes:
        l['prep'] = [int(taille[0]), int(taille[1])]
    return lignes


def ecrit_index(racine, index):
    """Chaque flux écrit son propre index : ils tournent en parallèle."""
    if not index:
        return
    chemin = os.path.join(racine, 'lignes_%d.json' % os.getpid())
    json.dump(index, open(chemin, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)


def main():
    global VENV
    dossier = sys.argv[1]
    racine = os.path.dirname(dossier.rstrip('/'))
    VENV = os.path.join(racine, '..', 'venv', 'bin', 'python')
    VENV = os.path.normpath(VENV)
    if not os.path.exists(VENV):
        VENV = sys.executable
    ocr = os.path.join(racine, 'ocr')
    os.makedirs(ocr, exist_ok=True)
    tmp = os.path.join(racine, '_prep.png')
    index = {}
    traites = 0
    # vues déjà présentes dans un index écrit par un autre flux
    import glob as _glob
    deja = set()
    for f in _glob.glob(os.path.join(racine, 'lignes_*.json')):
        try:
            deja |= set(json.load(open(f, encoding='utf-8')))
        except Exception:
            pass
    fichiers = sorted(f for f in os.listdir(dossier) if f.endswith('.jpg'))
    depuis = int(sys.argv[sys.argv.index('--depuis') + 1]) if '--depuis' in sys.argv else 0
    for i, nom in enumerate(fichiers):
        if i < depuis:
            continue
        sortie = os.path.join(ocr, nom[:-4] + '.txt')
        # --index-seul : refait la passe uniquement pour retrouver la position
        # des lignes, sans réécrire le texte déjà océrisé
        if (os.path.exists(sortie) and os.path.getsize(sortie)
                and '--index-seul' not in sys.argv):
            continue
        if nom[:-4] in deja:
            continue
        try:
            lignes = ocr_page(os.path.join(dossier, nom), sortie, tmp)
        except Exception as e:
            print('ECHEC %s : %s' % (nom, e))
            continue
        interet = [l for l in lignes
                   if ENTETE.search(l['texte']) or POSITION.search(l['texte'])]
        if interet:
            index[nom[:-4]] = interet
        traites += 1
        if traites % 10 == 0:              # index écrit au fil de l'eau
            print('  %d vues traitées' % traites, flush=True)
            ecrit_index(racine, index)
    ecrit_index(racine, index)
    print('OCR terminé : %d vues, %d avec ligne de date ou de position'
          % (len(fichiers), len(index)))


if __name__ == '__main__':
    main()
