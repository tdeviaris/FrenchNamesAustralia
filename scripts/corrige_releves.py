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

def annotation(c):
    """La note portée sur le point, telle que la fiche l'affichera."""
    if c.get('nature') == 'ramene':
        return ('position ramenée dans l’eau, de %s à %s — %s (table %s)'
                % (sexagesimal(c['lat_avant']), sexagesimal(c['lat_apres']),
                   c['motif'], c['table']))
    return ('latitude %s corrigée en %s — %s (table %s)'
            % (sexagesimal(c['lat_avant']), sexagesimal(c['lat_apres']),
               c['motif'], c['table']))


# Deux natures de retouche, qui ne se disent pas de la meme facon :
#   'chiffre' un caractere de la table est faux, et ses voisins le prouvent ;
#   'ramene'  la valeur est juste a la precision de l'epoque pres, mais tombe
#             de quelques centaines de metres du mauvais cote du trait de cote.
CORRECTIONS = [
    {
        'date': '1802-04-13',
        'navire': 'le Géographe',
        'lon': 138.3094, 'lat_avant': -32.2000, 'lat_apres': -35.2000,
        'nature': 'chiffre',
        'table': '14, p. 499',
        'motif': "les quatre relevés voisins vont de 35°03\u2032 à 35°40\u2032 et "
                 "la remarque de la veille dit « Entré dans le golfe Joséphine » ; "
                 "la valeur portée placerait le navire à 350 km dans les terres. "
                 "Le 5 a été lu 2",
    },
    {
        'date': '1803-01-02',
        'navire': 'les corvettes',
        'nature': 'ramene',
        'lon': 137.9200, 'lon_avant': 137.9286,
        'lat_avant': -35.8747, 'lat_apres': -35.8819,
        'table': '18, p. 513',
        'motif': "Baudin observe lui-même ce jour-là une latitude de 35°52'6\u2033, "
                 "qui confirme la table ; c'est la longitude, tirée de la montre, "
                 "qui manque l'eau. Le récit place l'île des Kangourous au Nord "
                 "et la côte rangée « à deux milles et souvent moins » : le "
                 "relevé est ramené de 1,1 km vers le Sud, dans l'eau la plus "
                 "proche du côté où se tenait le navire",
    },
]


def sexagesimal(lat):
    """La latitude comme la porte une table : degrés, minutes, hémisphère."""
    hemisphere = 'S' if lat < 0 else 'N'
    minutes = round(abs(lat) * 60)
    return '%d°%02d\u2032 %s' % (minutes // 60, minutes % 60, hemisphere)


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
            attendu_lon = c.get('lon_avant', c['lon'])
            # La longitude est comparee au millieme de degre : les tables
            # ne la donnent pas plus finement.
            if abs(lat - c['lat_apres']) < 1e-6 and abs(lon - c['lon']) < 1e-3:
                # Déjà corrigé : on rafraîchit seulement la note, qui a pu
                # changer de formulation.
                p['releve_corrige'] = annotation(c)
                continue
            if abs(lat - c['lat_avant']) > 1e-3 or abs(lon - attendu_lon) > 1e-3:
                print('  ATTENTION %s : latitude %.4f, attendue %.4f — laissé tel quel'
                      % (c['date'], lat, c['lat_avant']))
                continue
            f['geometry']['coordinates'] = [c['lon'], c['lat_apres']]
            p['releve_corrige'] = annotation(c)
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
