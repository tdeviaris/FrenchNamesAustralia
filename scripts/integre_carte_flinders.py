#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verse au parcours de Flinders les positions relevées sur sa carte de 1814.

Flinders a porté sur sa carte générale de 1814 les dates de son trajet, jalon
par jalon. Ces repères comblent les journées où son récit publié ne donne pas
de position — et le récit donne rarement la sienne pendant les levés côtiers,
où il relève surtout les terres qu'il reconnaît.

Deux sources, deux poids. Une latitude observée et publiée dans le récit est un
relevé de Flinders lui-même : elle prime. Une position lue sur la gravure est
le tracé de son graveur, restitué à une douzaine de kilomètres près par le
géoréférencement. On ne l'emploie donc que là où le récit se tait, et la fiche
le dit.

Usage : python3 scripts/integre_carte_flinders.py [--ecrire]
"""
import io, json, os, sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RELEVES = os.path.join(RACINE, 'data', 'flinders_carte_releves.json')
PARCOURS = os.path.join(RACINE, 'data', 'flinders_parcours.geojson')
CARTE = ("Matthew Flinders, General chart of Terra Australis or Australia, "
         "Londres, 1814")


def main():
    src = json.load(io.open(RELEVES, encoding='utf-8'))
    gj = json.load(io.open(PARCOURS, encoding='utf-8'))
    # Une même date peut appartenir à deux bâtiments : le 4 novembre 1802 est
    # celui de l'Investigator dans le golfe de Carpentarie, le 4 novembre 1803
    # celui de la Cumberland en mer de Timor. La clé porte donc le navire.
    connues = {(f['properties'].get('date'), f['properties'].get('navire'))
               for f in gj['features']}

    ajoutes, confirment = [], []
    for r in src['releves']:
        if (r['date'], r['navire']) in connues:
            confirment.append(r)
            continue
        gj['features'].append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [r['lon'], r['lat']]},
            "properties": {
                "date": r['date'],
                "navire": r['navire'],
                "expedition": "Flinders",
                "table": CARTE,
                "releve_carte": (
                    "position relevée sur la carte générale que Flinders a dressée "
                    "en 1814, au repère qu'il y a %s « %s » — %s. Lue sur la "
                    "gravure et non observée : le géoréférencement la restitue à "
                    "une douzaine de kilomètres près"
                    % ('nommé' if r.get('nature') == 'lieu' else 'daté',
                       r['libelle'], r['note'])),
            }})
        ajoutes.append(r)

    gj['features'].sort(key=lambda f: (str(f['properties'].get('date', '')),
                                       f['properties'].get('navire', '')))
    from collections import Counter
    print('relevés de la carte      : %d  %s'
          % (len(src['releves']), dict(Counter(r['navire'] for r in src['releves']))))
    print('  ajoutés au parcours    : %d' % len(ajoutes))
    print('  déjà donnés par le récit : %d' % len(confirment))
    dates = sorted(f['properties']['date'] for f in gj['features'])
    print('parcours : %d points, du %s au %s' % (len(dates), dates[0], dates[-1]))

    if '--ecrire' in sys.argv:
        json.dump(gj, io.open(PARCOURS, 'w', encoding='utf-8'), ensure_ascii=False)
        print('\n-> %s' % os.path.relpath(PARCOURS, RACINE))
    else:
        print('\n(simulation — relancer avec --ecrire)')


if __name__ == '__main__':
    main()
