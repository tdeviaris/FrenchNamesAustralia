#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prépare l'onglet « Flinders » du classeur Toponymes.

Jusqu'ici data/flinders.json était fabriqué par toponymes_flinders.py depuis
« Flinders nomenclature.xls ». Dany veut désormais relire et corriger ces
textes à la main, comme elle le fait déjà pour Baudin et d'Entrecasteaux dans
le classeur Toponymes. Le classeur devient donc la source, et ce script ne
sert qu'une fois : à l'amorcer.

Il écrit un CSV de 351 lignes et 37 colonnes, à verser dans un onglet
« Flinders » placé derrière « Source ». Les vingt-quatre premières colonnes
portent les mêmes intitulés que dans « Source », pour que Dany retrouve ses
repères ; les treize suivantes sont propres à Flinders.

Sur ces treize, une précision utile : le site n'en lit que deux, « Crédit
image » et « Source image ». Les onze autres — le bâtiment, la date, le
secteur, la typologie du choix de nom, la planche, les notes — sont les
données de recherche de Dany. Elles ne changent rien à l'affichage, mais
elles voyagent avec le fichier et personne ne veut les perdre.

Le CSV s'importe par Fichier > Importer > Insérer une nouvelle feuille, en
séparateur virgule. Les retours à la ligne des textes longs sont protégés par
les guillemets : ne pas ouvrir le fichier dans un tableur intermédiaire, qui
les abîmerait.

Usage : python3 scripts/flinders_vers_classeur.py [chemin de sortie]
"""
import csv
import io
import json
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(RACINE, 'data', 'flinders.json')
DEFAUT = os.path.join(RACINE, 'output', 'flinders_onglet.csv')

# (intitulé de la colonne, clé dans le JSON). L'ordre fait foi : c'est celui
# des colonnes de l'onglet, et le script d'export s'y réfère par l'intitulé,
# jamais par le rang -- une colonne déplacée ne doit rien casser.
COLONNES = [
    # --- les vingt-quatre communes aux trois expéditions, intitulées comme
    # --- dans l'onglet « Source »
    ('Code',                              'code'),
    ('Expedition',                        'expedition'),
    ('State',                             'state'),
    ('French name',                       'frenchName'),
    ('Variant and other historical name', 'variantName'),
    ('Australian name',                   'ausEName'),
    ('Aboriginal name',                   'indigenousName'),
    ('Aboriginal language group',         'indigenousLanguage'),
    ('latitude South',                    'lat'),
    ('longitude East',                    'lon'),
    ('Caracteristiques (FR)',             'characteristic_fr'),
    ('Characteristic (EN)',               'characteristic'),
    ('Histoire (FR)',                     'history_fr'),
    ('Story (EN)',                        'history'),
    ('URL WIKI FR',                       'wiki_fr'),
    ('URL WIKi EN',                       'wiki_en'),
    ('URL IMG',                           'imgUrl'),
    ('URL DIV',                           'other_link'),
    ('URL Carte',                         'mapUrl'),
    ('Titre Carte (FR)',                  'mapTitle_fr'),
    ('Map title (EN)',                    'mapTitle_en'),
    ('Origine du nom version initiale',   'origin_fr'),
    ('fiche detaillee F',                 'detailsLink'),
    ('detailed information sheet E',      'detailsLink_en'),
    # --- les treize propres à Flinders
    ('Navire',                            'navire'),
    ('Date',                              'date'),
    ('Campagne',                          'campagne'),
    ('Secteur',                           'secteur'),
    ('Categorie',                         'categorie'),
    ('Sous-categorie',                    'sousCategorie'),
    ('Classe',                            'classe'),
    ('Planche',                           'planche'),
    ('Commentaire',                       'commentaire'),
    ('Incertain',                         'incertain'),
    ('Credit image',                      'imgCredit'),
    ('Source image',                      'imgSource'),
    ('Sujet image',                       'imgSujet'),
]


def cellule(valeur):
    """Une valeur de cellule : le classeur ne connaît que du texte.

    Deux pièges. Un nombre rendu par str() garderait la notation Python, et
    les coordonnées doivent rester lisibles telles qu'elles. Un booléen
    deviendrait « True » : on écrit VRAI/FAUX, ce que Google Sheets reconnaît
    et ce que le script d'export relit sans hésiter.
    """
    if valeur is None:
        return ''
    if isinstance(valeur, bool):
        return 'VRAI' if valeur else 'FAUX'
    if isinstance(valeur, str) and valeur in ('True', 'False'):
        return 'VRAI' if valeur == 'True' else 'FAUX'
    if isinstance(valeur, float):
        # repr() donnerait 115.13580000000001 sur certaines valeurs
        return ('%.6f' % valeur).rstrip('0').rstrip('.')
    return str(valeur)


def main(sortie):
    lieux = json.load(io.open(SOURCE, encoding='utf-8'))
    if isinstance(lieux, dict):
        lieux = list(lieux.values())[0]

    connues = {cle for _, cle in COLONNES}
    oubliees = sorted({k for lieu in lieux for k in lieu} - connues)
    if oubliees:
        print('ATTENTION : %d champ(s) du JSON sans colonne, rien n\'est ecrit'
              % len(oubliees))
        for k in oubliees:
            print('   %s' % k)
        return 1

    os.makedirs(os.path.dirname(sortie), exist_ok=True)
    with io.open(sortie, 'w', encoding='utf-8-sig', newline='') as fh:
        # utf-8-sig : sans la marque d'ordre, Google Sheets lit parfois le
        # fichier en latin-1 et les accents partent en fumée.
        ecrivain = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator='\r\n')
        ecrivain.writerow([intitule for intitule, _ in COLONNES])
        for lieu in lieux:
            ecrivain.writerow([cellule(lieu.get(cle)) for _, cle in COLONNES])

    remplis = {intitule: sum(1 for l in lieux if str(l.get(cle) or '').strip())
               for intitule, cle in COLONNES}
    print('%d lieux, %d colonnes -> %s'
          % (len(lieux), len(COLONNES), os.path.relpath(sortie, RACINE)))
    print('   %d octets' % os.path.getsize(sortie))
    vides = [i for i, n in remplis.items() if n == 0]
    if vides:
        print('   colonnes entierement vides (normales, a remplir a la main) : %s'
              % ', '.join(vides))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else DEFAUT))
