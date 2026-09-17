#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assemble l'OCR de la copie dactylographiée du journal de Baudin.

Produit deux fichiers :
  - data/journal_baudin_bnf.txt   le journal suivi, vue par vue
  - data/journal_baudin_bnf.json  le même texte découpé par journée

AVERTISSEMENT porté en tête du txt : Tesseract lit la prose de ce typescript
mais confond 3 et 5 dans cette fonte, et la machine à écrire tape un I majuscule
à la place du 1. Les chiffres — dates, latitudes, longitudes, sondes — ne sont
donc pas fiables tant qu'ils n'ont pas été relus à l'œil sur l'image.

Usage : python3 scripts/assemble_baudin_bnf.py <dossier> [--ecrire]
"""
import json, os, re, sys

MOIS_REP = ('vend[eé]miaire|brumaire|frimaire|niv[oô]se|pluvi[oô]se|vent[oô]se|'
            'germinal|flor[eé]al|prairial|messidor|thermidor|fructidor')
# « - Du 23 au 24 Floréal - », « Du 30 au I de Ventose an 9 », « - Du I5 Messidor an 9 - »
# Le nom du mois est souvent abîmé par l'OCR : on se contente du squelette
# « Du <n> au <n> » sur une ligne courte, et on récupère le mois s'il est lisible.
ENTETE = re.compile(r'\bDu\s+([IVXO\d]{1,3})\s+au\s+([IVXO\d]{1,3})\b', re.I)
MOIS_LIGNE = re.compile(MOIS_REP, re.I)
# un en-tête tient sur une ligne courte et centrée ; la prose déborde
LIGNE_COURTE = 58

AVERTISSEMENT = """\
JOURNAL DE BORD DU COMMANDANT BAUDIN
Copie dactylographiée, février 1801 - août 1803
Bibliothèque nationale de France, département Société de Géographie,
SG MS4-33 (1149) — ark:/12148/btv1b55013925h, 737 vues, 733 feuillets.

Ce fichier est la sortie brute d'une reconnaissance optique (Tesseract 5, fra)
faite sur les images de Gallica. Il n'a pas été relu intégralement.

DEUX RÉSERVES IMPORTANTES SUR LES CHIFFRES :

1. La machine à écrire du dactylographe n'a pas de touche « 1 » : il frappe un
   I majuscule. « Du 30 au I de Ventose », « 33°I'45" », « N°3I », « 2I°9' ».
   La conversion I -> 1 a été faite automatiquement dans les contextes
   numériques, mais elle ne peut pas être garantie partout.

2. Tesseract confond 3 et 5 dans cette fonte : il lit « 56 brasses à 59 » là où
   le texte porte « 36 brasses à 39 », et « I8°6'54" » pour 18°6'34".

En conséquence : la prose est utilisable, les chiffres ne le sont pas tant
qu'ils n'ont pas été relus sur l'image. Le numéro de vue est indiqué en tête de
chaque page pour permettre cette vérification :
https://gallica.bnf.fr/ark:/12148/btv1b55013925h/fNNN.item

"""


def main():
    dossier = sys.argv[1].rstrip('/')
    ocr = os.path.join(dossier, 'ocr')
    vues = sorted(f for f in os.listdir(ocr) if f.endswith('.txt'))

    morceaux, journees, courante, date = [], {}, [], None
    for nom in vues:
        vue = nom[:-4]
        texte = open(os.path.join(ocr, nom), encoding='utf-8').read().strip()
        if not texte:
            continue
        morceaux.append('\n\n===== vue %s =====\n\n%s' % (vue[1:], texte))
        for ligne in texte.split('\n'):
            m = ENTETE.search(ligne) if len(ligne.strip()) <= LIGNE_COURTE else None
            if m:
                if date and courante:
                    journees.setdefault(date, []).append('\n'.join(courante))
                mo = MOIS_LIGNE.search(ligne)
                date = '%s %s (vue %s)' % (m.group(2),
                                           mo.group(0) if mo else '?', vue[1:])
                courante = []
            else:
                courante.append(ligne)
    if date and courante:
        journees.setdefault(date, []).append('\n'.join(courante))

    print('vues assemblées : %d' % len(vues))
    print('en-têtes de journée repérés : %d' % len(journees))
    total = sum(len(t) for t in morceaux)
    print('caractères : %d' % total)

    if '--ecrire' in sys.argv:
        with open('data/journal_baudin_bnf.txt', 'w', encoding='utf-8') as f:
            f.write(AVERTISSEMENT)
            f.write(''.join(morceaux))
        print('écrit : data/journal_baudin_bnf.txt')
        with open('data/journal_baudin_bnf.json', 'w', encoding='utf-8') as f:
            json.dump({k: '\n'.join(v) for k, v in journees.items()}, f,
                      ensure_ascii=False, indent=1, sort_keys=True)
        print('écrit : data/journal_baudin_bnf.json')


if __name__ == '__main__':
    main()
