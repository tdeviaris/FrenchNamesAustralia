#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Corrige des chiffres manifestement fautifs dans les relevés des tables.

À la différence de scripts/corrige_mouillages.py, qui répare un calcul, ce
script touche à une valeur publiée. On ne le fait donc que sur une évidence :
un chiffre que ses voisins immédiats démentent, et que le récit du jour
contredit. Chaque correction porte l'ancienne valeur, la nouvelle, la table
d'où elle vient et la raison, pour qu'on puisse toujours revenir en arrière.

La fonte de ces tables se prête à ces confusions : c'est le même 5 pris pour un
2 ou pour un 3 qui a fait trébucher la reconnaissance optique du journal.

Usage : python3 scripts/corrige_releves.py [--ecrire]
"""
import io, json, os, sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEOJSON = os.path.join(RACINE, 'data', 'baudin_parcours.geojson')

CORRECTIONS = [
    {
        'date': '1802-04-13',
        'navire': 'le Géographe',
        'lon': 138.3094, 'lat_avant': -32.2000, 'lat_apres': -35.2000,
        'table': '14 - Routes du Géographe à la Terre Napoléon, 1re campagne, p. 499',
        'motif': "latitude portée 32°12' S ; les quatre relevés voisins vont de "
                 "35°03' à 35°40' et la remarque de la veille dit « Entré dans "
                 "le golfe Joséphine ». 32°12' placerait le navire à 350 km "
                 "dans les terres. Le 5 a été lu 2",
    },
]


def main():
    gj = json.load(io.open(GEOJSON, encoding='utf-8'))
    faits = []
    for f in gj['features']:
        if f['geometry']['type'] != 'Point':
            continue
        p = f['properties']
        for c in CORRECTIONS:
            if p.get('date') != c['date'] or p.get('navire') != c['navire']:
                continue
            lon, lat = f['geometry']['coordinates']
            if abs(lat - c['lat_apres']) < 1e-6:
                continue                      # déjà corrigé
            if abs(lat - c['lat_avant']) > 1e-3:
                print('  ATTENTION %s : latitude %.4f, attendue %.4f — laissé tel quel'
                      % (c['date'], lat, c['lat_avant']))
                continue
            f['geometry']['coordinates'] = [lon, c['lat_apres']]
            p['releve_corrige'] = ('latitude %.4f corrigée en %.4f — %s (%s)'
                                   % (c['lat_avant'], c['lat_apres'],
                                      c['motif'], c['table']))
            faits.append(c)

    print('relevés corrigés : %d' % len(faits))
    for c in faits:
        print('   %s  %-14s  lat %.4f -> %.4f' % (c['date'], c['navire'],
                                                  c['lat_avant'], c['lat_apres']))

    if '--ecrire' in sys.argv:
        json.dump(gj, io.open(GEOJSON, 'w', encoding='utf-8'), ensure_ascii=False)
        print('\n-> %s mis à jour' % os.path.relpath(GEOJSON, RACINE))
    else:
        print('\n(simulation — relancer avec --ecrire)')


if __name__ == '__main__':
    main()
