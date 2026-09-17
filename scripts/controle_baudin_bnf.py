#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vérifie la datation du typescript de la BnF par les latitudes qu'il porte.

Chaque journée de mer donne, sous son en-tête, la latitude Sud estimée puis
observée. Le parcours du projet, établi de son côté sur les tables de route
publiées, donne une position par navire et par jour. Si la datation est juste,
les deux doivent coïncider ; si elle glisse d'un mois, l'écart saute aux yeux.

Le contrôle porte sur l'écart médian : les chiffres du typescript sont lus par
une reconnaissance optique qui confond 3 et 5, quelques latitudes sont donc
aberrantes sans que la date soit en cause.

Usage : python3 scripts/controle_baudin_bnf.py [--detail]
"""
import json, os, re, statistics, sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOURNAL = os.path.join(RACINE, 'data', 'journal_baudin_bnf.json')
GEOJSON = os.path.join(RACINE, 'data', 'baudin_parcours.geojson')

# « Latitude Sud estimée 34.46.30, observée 33°3'30" », « Latit-de Sud est. »
LATITUDE = re.compile(
    r'latit[a-zé-]*[^0-9]{0,40}?(\d{1,2})\s*[.°:,;]\s*(\d{1,2})'
    r'(?:\s*[.\'’:,;]\s*(\d{1,2}))?', re.I)
# le dactylographe coupe les mots en fin de ligne : « Latitu- / de Sud »
COUPURE = re.compile(r'-\s*\n\s*')


def variantes_degre(d):
    """Le même nombre de degrés, sous les lectures que la fonte autorise."""
    formes = {str(d)}
    for _ in range(2):
        for f in list(formes):
            for a, b in (('3', '5'), ('0', '6'), ('1', '7')):
                formes.add(f.replace(a, b))
                formes.add(f.replace(b, a))
    return {int(f) for f in formes if f.isdigit() and 0 < int(f) <= 55}


def latitudes(texte, tolerant=False):
    """Les latitudes Sud lues dans les premières lignes d'une journée."""
    vues = []
    texte = COUPURE.sub('', texte)
    for m in LATITUDE.finditer(texte[:700]):
        d, mi = int(m.group(1)), int(m.group(2))
        if not (8 <= d <= 55 and mi < 60):
            continue
        for dd in (variantes_degre(d) if tolerant else {d}):
            vues.append(-(dd + mi / 60.0))
    return vues


def main():
    jour = json.load(open(JOURNAL, encoding='utf-8'))
    gj = json.load(open(GEOJSON, encoding='utf-8'))
    # Baudin est sur le Géographe ; avant la séparation les deux naviguent
    # de conserve et le parcours les porte sous « les corvettes »
    ref = {}
    for f in gj['features']:
        if f['geometry']['type'] != 'Point':
            continue
        p = f['properties']
        if p.get('navire') in ('le Géographe', 'les corvettes') and p.get('date'):
            ref.setdefault(p['date'], f['geometry']['coordinates'][1])

    ecarts, tolerants, sans_ref, sans_lat, pires = [], [], 0, 0, []
    for date in sorted(jour):
        if date not in ref:
            sans_ref += 1
            continue
        lats = latitudes(jour[date]['texte'])
        if not lats:
            sans_lat += 1
            continue
        # la plus proche des latitudes lues : l'estimée et l'observée diffèrent
        e = min(abs(l - ref[date]) for l in lats)
        ecarts.append(e)
        tol = latitudes(jour[date]['texte'], tolerant=True)
        tolerants.append(min(abs(l - ref[date]) for l in tol))
        pires.append((e, date, lats[0], ref[date]))

    print('journées du typescript      : %d' % len(jour))
    print('  hors du parcours connu    : %d' % sans_ref)
    print('  sans latitude lisible     : %d' % sans_lat)
    print('  comparées                 : %d' % len(ecarts))
    if not ecarts:
        return
    ecarts.sort()
    print('\nécart à la position du parcours, en degrés de latitude :')
    print('  médiane                   : %.3f°  (%.0f milles)'
          % (statistics.median(ecarts), statistics.median(ecarts) * 60))
    for seuil in (0.25, 0.5, 1.0, 2.0, 5.0):
        n = sum(1 for e in ecarts if e <= seuil)
        print('  à moins de %4.2f°          : %3d  (%.0f %%)'
              % (seuil, n, 100.0 * n / len(ecarts)))
    tolerants.sort()
    print('\nen admettant les confusions de la fonte sur les degrés '
          '(3 pour 5, 0 pour 6, 1 pour 7) :')
    print('  médiane                   : %.3f°  (%.0f milles)'
          % (statistics.median(tolerants), statistics.median(tolerants) * 60))
    for seuil in (0.25, 0.5, 1.0, 2.0):
        n = sum(1 for e in tolerants if e <= seuil)
        print('  à moins de %4.2f°          : %3d  (%.0f %%)'
              % (seuil, n, 100.0 * n / len(tolerants)))

    if '--detail' in sys.argv:
        pires.sort(reverse=True)
        print('\nles vingt plus grands écarts :')
        for e, d, lu, att in pires[:20]:
            print('  %s  lu %7.3f  parcours %7.3f  écart %5.2f°'
                  % (d, lu, att, e))


if __name__ == '__main__':
    main()
