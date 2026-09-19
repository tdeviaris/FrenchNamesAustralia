#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rend au Naturaliste les journées où il naviguait avec le Géographe.

Le parcours vient des tables de route de Freycinet, et l'attribution des
points a suivi le titre des tables plutôt que la navigation réelle. La table 3,
« Traversée de l'Île-de-France à la Nouvelle-Hollande », est commune aux deux
corvettes : ses points portent « les corvettes ». La table 4, « Routes à la
Terre de Leuwin, 1re campagne », porte le nom du seul Géographe : ses points
lui ont été attribués à lui seul.

Or les deux bâtiments ne se sont pas séparés au changement de table. Ils ont
vu le cap Leeuwin ensemble le 27 mai 1801, mouillé ensemble dans la baie du
Géographe, et ne se sont perdus de vue qu'à une heure du matin le 10 juin, au
plus fort du coup de vent. Sur la carte, le Naturaliste disparaissait treize
jours trop tôt.

La preuve est dans les journaux du bord, cités ci-dessous. La dernière est
sans réplique : le 11 juin, le journal de Breton écrit « On n'a pas eu
connaissance du Naturaliste depuis le 21 à 1h du matin » -- le 21 prairial an
IX est le 10 juin 1801.

Rejouable : une période déjà corrigée ne produit plus aucun changement.

Usage : python3 scripts/de_conserve.py [--ecrire]
"""
import io
import json
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEOJSON = os.path.join(RACINE, 'data', 'baudin_parcours.geojson')

# Les périodes où un point attribué à un seul bâtiment revient en réalité aux
# deux. Chacune porte ce qui l'atteste, pour qu'on puisse la contester.
DE_CONSERVE = [
    {
        'du': '1801-05-28',
        'au': '1801-06-09',
        'seul': 'le Géographe',
        'appui': "les deux corvettes reconnaissent la terre de Leeuwin de "
                 "conserve et mouillent ensemble dans la baie du Géographe ; "
                 "elles ne se perdent de vue qu'au coup de vent du 10 juin",
        # Ce que disent les journaux, jour par jour :
        #   29 mai  « Ayant joint, ensuite, le Naturaliste qui se trouvait à
        #            environ un quart de lieue… »
        #   30 mai  « Le Naturaliste en fit autant et nous ralliâmes la terre »
        #    1 juin « je prévins le Naturaliste d'en faire autant, ce qu'il
        #            exécuta »
        #    7 juin « le Naturaliste mit à la voile et vint se mouiller auprès
        #            de nous à petite distance »
        #    9 juin « Sur les quatre heures, le Naturaliste nous avait presque
        #            rallié »
        #   10 juin « nous n'eûmes point connaissance du Naturaliste »
        #   11 juin (journal Breton) « On n'a pas eu connaissance du
        #            Naturaliste depuis le 21 à 1h du matin »
    },
]

ENSEMBLE = 'les corvettes'


def main(ecrire):
    gj = json.load(io.open(GEOJSON, encoding='utf-8'))
    total = 0
    for periode in DE_CONSERVE:
        touches = []
        deja = 0
        for f in gj['features']:
            if f['geometry']['type'] != 'Point':
                continue
            p = f['properties']
            date = p.get('date')
            if not date or not (periode['du'] <= date <= periode['au']):
                continue
            if p.get('navire') == ENSEMBLE:
                deja += 1
                continue
            if p.get('navire') != periode['seul']:
                continue
            p['navire'] = ENSEMBLE
            # On dit pourquoi, sans effacer ce qui pouvait déjà être noté.
            note = ("point relevé sous le seul %s dans les tables de route, "
                    "mais %s" % (periode['seul'], periode['appui']))
            p['de_conserve'] = note
            touches.append(date)
            total += 1

        print('%s -> %s : %d point(s) rendus aux deux corvettes, %d déjà en commun'
              % (periode['du'], periode['au'], len(touches), deja))
        for date in sorted(set(touches)):
            print('     %s' % date)

    print('\nTOTAL : %d point(s)' % total)
    if not ecrire:
        print('(simulation — relancer avec --ecrire)')
        return
    if total:
        json.dump(gj, io.open(GEOJSON, 'w', encoding='utf-8'), ensure_ascii=False)
        print('-> %s mis à jour' % os.path.relpath(GEOJSON, RACINE))


if __name__ == '__main__':
    main('--ecrire' in sys.argv)
