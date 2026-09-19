#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rend leur mouillage aux positions qu'une interpolation avait jetées au large.

Quand un journal porte une entrée pour un jour où les tables ne relèvent aucune
position, le point a été créé par interpolation entre les deux relevés qui
l'encadrent. Le procédé ne vaut que si ces deux relevés sont proches dans le
temps. Il devient absurde quand le navire disparaît des tables pendant des
mois — ce qui arrive à chaque escale, et surtout quand il repart de conserve et
se trouve dès lors consigné sous un autre libellé.

C'est le cas du Naturaliste à Timor. Ses propres relevés s'arrêtent au 21
septembre 1801, jour où il mouille en baie de Coupang, et ne reprennent que le
8 mars 1802 dans le détroit de Banks, en Tasmanie : entre les deux il navigue
avec le Géographe, sous le libellé « les corvettes ». L'entrée du 12 novembre
1801 s'est donc vu attribuer un point à mi-chemin de cette droite — au milieu
du désert du Tanami, à 534 kilomètres de toute côte.

Les journaux disent ce qu'il en était. Le 12 novembre, l'anonyme du Naturaliste
décrit le séjour à Coupang : gréement visité, eau faite, provisions embarquées.
Le 13 : « À cinq heures du matin nous avons appareillé ». Le navire était au
mouillage, là où il l'était depuis sept semaines.

Usage : python3 scripts/corrige_mouillages.py [--ecrire]
"""
import io, json, os, sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEOJSON = os.path.join(RACINE, 'data', 'baudin_parcours.geojson')

# Escales pendant lesquelles la position doit être tenue, non interpolée.
# Chaque entrée porte le relevé qui fait foi et de quoi il est tiré.
MOUILLAGES = [
    {
        'navire': 'le Naturaliste',
        'du': '1801-09-22', 'au': '1801-11-12',
        'lon': 123.5917, 'lat': -10.1467,
        'lieu': 'rade de Coupang, île de Timor',
        'appui': "relevé du 21 septembre 1801, « Mouillé dans la baie de "
                 "Coupang » ; appareillage le 13 novembre à cinq heures",
    },
    {
        # Meme defaut, au debut du voyage : « les corvettes » n'a aucun releve
        # entre le 4 juin et le 23 aout 1801, si bien que les trois journees
        # que les tables sautent ont ete interpolees vers Timor. Les corvettes
        # mouillaient dans la baie du Geographe, canots a terre : c'est la
        # recherche de Vasse.
        'navire': 'les corvettes',
        'du': '1801-06-05', 'au': '1801-06-08',
        'lon': 115.408, 'lat': -33.500,
        'lieu': 'baie du Géographe, côte occidentale de la Nouvelle-Hollande',
        'appui': "relevés du Géographe les 4 et 7 juin 1801, « Au mouillage "
                 "dans la baie du Géographe » et « Appareillé à 8 h. du matin, "
                 "remis à l'ancre à 11 h. » ; le journal anonyme décrit les "
                 "canots envoyés à terre ces jours-là",
    },
]


def main():
    gj = json.load(io.open(GEOJSON, encoding='utf-8'))
    corriges = []
    for f in gj['features']:
        if f['geometry']['type'] != 'Point':
            continue
        p = f['properties']
        date, navire = p.get('date'), p.get('navire')
        for m in MOUILLAGES:
            if navire != m['navire'] or not date:
                continue
            if not (m['du'] <= date <= m['au']):
                continue
            avant = list(f['geometry']['coordinates'])
            if abs(avant[0] - m['lon']) < 1e-6 and abs(avant[1] - m['lat']) < 1e-6:
                continue                      # déjà corrigé
            f['geometry']['coordinates'] = [m['lon'], m['lat']]
            p['extrapole'] = True
            # Le lieu est connu et date : la fiche ne doit pas annoncer une
            # position extrapolee.
            p['mouillage'] = True
            p['alerte'] = ('position tenue au mouillage : %s (%s)'
                           % (m['lieu'], m['appui']))
            corriges.append((date, navire, avant, m['lieu']))

    print('points ramenés à leur mouillage : %d' % len(corriges))
    for date, navire, avant, lieu in corriges:
        print('   %s  %-14s  %8.3f,%7.3f  ->  %s' % (date, navire, avant[0], avant[1], lieu))

    if '--ecrire' in sys.argv:
        json.dump(gj, io.open(GEOJSON, 'w', encoding='utf-8'), ensure_ascii=False)
        print('\n-> %s mis à jour' % os.path.relpath(GEOJSON, RACINE))
    else:
        print('\n(simulation — relancer avec --ecrire)')


if __name__ == '__main__':
    main()
