#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare deux transcriptions d'une même page, mot à mot.

Sert d'abord à mesurer ce que vaut un modèle contre un autre sur le pilote,
puis, en production, à confronter la transcription au texte de l'OCR : les
erreurs d'un modèle de vision et celles d'un OCR classique ne se ressemblent
pas, et là où les deux divergent il y a une faute quelque part.

Les écarts qui portent sur un chiffre sont comptés à part : ce sont les seuls
qui corrompent une donnée — latitude, longitude, sonde, relèvement.

Usage : python3 scripts/compare_transcriptions.py <dossierA> <dossierB> [--muet]
"""
import difflib, os, re, sys, unicodedata

CHIFFRE = re.compile(r'\d')
ENTETE = re.compile(r'^(Vue|Folio|Date|En-tête)\s*:', re.M)


def corps(chemin):
    """Le texte de la page, sans les lignes d'en-tête du fichier."""
    lignes = open(chemin, encoding='utf-8').read().split('\n')
    return '\n'.join(l for l in lignes if not ENTETE.match(l))


def mots(texte):
    return texte.split()


def pliage(m):
    """La forme sous laquelle on juge deux mots identiques ou non."""
    return unicodedata.normalize('NFC', m)


def compare(a, b):
    ma, mb = mots(a), mots(b)
    s = difflib.SequenceMatcher(None, [pliage(x) for x in ma],
                                [pliage(x) for x in mb], autojunk=False)
    ecarts = []
    for op, i1, i2, j1, j2 in s.get_opcodes():
        if op == 'equal':
            continue
        ga, gb = ' '.join(ma[i1:i2]), ' '.join(mb[j1:j2])
        ecarts.append((op, ga, gb))
    return len(ma), len(mb), ecarts


def main():
    da, db = sys.argv[1].rstrip('/'), sys.argv[2].rstrip('/')
    pages = sorted(set(os.listdir(da)) & set(os.listdir(db)))
    pages = [p for p in pages if p.endswith('.txt')]
    if not pages:
        sys.exit('aucune page commune entre %s et %s' % (da, db))

    tot_mots = tot_ecarts = tot_chiffres = 0
    for p in pages:
        na, nb, ecarts = compare(corps(os.path.join(da, p)),
                                 corps(os.path.join(db, p)))
        nchif = sum(1 for _, ga, gb in ecarts
                    if CHIFFRE.search(ga) or CHIFFRE.search(gb))
        tot_mots += na
        tot_ecarts += len(ecarts)
        tot_chiffres += nchif
        print('%s : %d mots / %d ; %d écarts dont %d sur des chiffres'
              % (p[:-4], na, nb, len(ecarts), nchif))
        if '--muet' in sys.argv:
            continue
        for op, ga, gb in ecarts:
            marque = '!' if (CHIFFRE.search(ga) or CHIFFRE.search(gb)) else ' '
            if op == 'replace':
                print('   %s A: %-44s B: %s' % (marque, ga[:44], gb[:44]))
            elif op == 'delete':
                print('   %s A: %-44s B: —' % (marque, ga[:44]))
            else:
                print('   %s A: %-44s B: %s' % (marque, '—', gb[:44]))
        print()

    print('-' * 70)
    print('total : %d mots, %d écarts (%.1f %%), dont %d touchant un chiffre'
          % (tot_mots, tot_ecarts, 100.0 * tot_ecarts / max(tot_mots, 1),
             tot_chiffres))


if __name__ == '__main__':
    main()
