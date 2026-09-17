#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ajoute au parcours Baudin la route de retour du Naturaliste.

Les points viennent des journaux du bord (data/retour_naturaliste.json), pas
des tables de Freycinet : ils portent la propriété `position_journal` pour que
la fiche le dise au lecteur.

Usage : python3 scripts/injecte_retour.py [--ecrire]
"""
import json, sys

PARCOURS = 'data/baudin_parcours.geojson'
TRACE    = 'data/retour_naturaliste.json'
NAVIRE   = 'le Naturaliste'

SOURCE = {'anonyme': 'journal anonyme à bord du Naturaliste',
          'breton':  'journal de Breton'}


def main():
    geo = json.load(open(PARCOURS, encoding='utf-8'))
    trace = json.load(open(TRACE, encoding='utf-8'))

    # on repart d'un parcours sans les points de retour déjà posés
    avant = len(geo['features'])
    geo['features'] = [f for f in geo['features']
                       if not f['properties'].get('position_journal')]
    retires = avant - len(geo['features'])

    existant = {(f['properties'].get('navire'), f['properties'].get('date'))
                for f in geo['features'] if f['geometry']['type'] == 'Point'}

    ajoutes = 0
    for t in trace:
        if (NAVIRE, t['date']) in existant:
            continue
        props = {'navire': NAVIRE, 'date': t['date'], 'position_journal': True}
        if t.get('extrapole'):
            props['extrapole'] = True
            props['alerte'] = t['motif']
        else:
            alerte = ('position relevée dans le %s ; longitude comptée du '
                      'méridien de Paris' % SOURCE[t['source']])
            if t.get('invraisemblable'):
                alerte += (' ; route journalière invraisemblable (%d km/j)'
                           % t['km_j'])
            props['alerte'] = alerte
        geo['features'].append({
            'type': 'Feature',
            'geometry': {'type': 'Point', 'coordinates': [t['lon'], t['lat']]},
            'properties': props,
        })
        ajoutes += 1

    pts = [f for f in geo['features'] if f['geometry']['type'] == 'Point'
           and f['properties'].get('navire') == NAVIRE]
    dates = sorted(f['properties']['date'] for f in pts)
    print('points de retour retirés puis reposés : %d -> %d' % (retires, ajoutes))
    print('le Naturaliste : %d points, %s -> %s' % (len(pts), dates[0], dates[-1]))

    if '--ecrire' in sys.argv:
        json.dump(geo, open(PARCOURS, 'w', encoding='utf-8'),
                  ensure_ascii=False, separators=(', ', ': '))
        print('écrit : %s' % PARCOURS)


if __name__ == '__main__':
    main()
