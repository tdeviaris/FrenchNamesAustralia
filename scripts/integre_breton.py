#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Intègre le journal de Breton dans data/journaux/baudin_fr.json.

Breton change de navire le 9 brumaire an 10 (31 octobre 1801) : le texte est
donc réparti sur deux champs, chacun portant sa propre mention de navire.

Après la séparation du 20 novembre 1802 le Naturaliste rentre en France et
n'a plus de point sur le parcours : les journées suivantes sont écartées
(le contrôle des longitudes donne 8,9° d'écart avec l'escadre restée en
Australie, contre 0,7° avant la séparation).

Usage : python3 scripts/integre_breton.py [--ecrire]
"""
import json, sys

PARCOURS   = 'data/baudin_parcours.geojson'
JOURNAL    = 'data/journal_breton.json'
CIBLE      = 'data/journaux/baudin_fr.json'
BASCULE    = '1801-10-31'      # Breton passe sur le Naturaliste
LIMITE     = '1802-11-20'      # dernier point du Naturaliste sur le parcours

CHAMP_GEO = 'journal_breton_geographe'
CHAMP_NAT = 'journal_breton_naturaliste'


def main():
    geo = json.load(open(PARCOURS, encoding='utf-8'))
    dates = {f['properties']['date'] for f in geo['features']
             if f['geometry']['type'] == 'Point' and f['properties'].get('date')}

    breton = json.load(open(JOURNAL, encoding='utf-8'))
    cible = json.load(open(CIBLE, encoding='utf-8'))

    retenu = {d: t for d, t in breton.items() if d in dates and d <= LIMITE}
    for champ in (CHAMP_GEO, CHAMP_NAT):
        for v in cible.values():
            v.pop(champ, None)

    n_geo = n_nat = 0
    for d, t in retenu.items():
        champ = CHAMP_GEO if d < BASCULE else CHAMP_NAT
        cible.setdefault(d, {})[champ] = t
        if champ == CHAMP_GEO:
            n_geo += 1
        else:
            n_nat += 1

    print('journal de Breton : %d journées extraites' % len(breton))
    print('  retenues (date au parcours, <= %s) : %d' % (LIMITE, len(retenu)))
    print('  à bord du Géographe   : %d' % n_geo)
    print('  à bord du Naturaliste : %d' % n_nat)
    print('  écartées              : %d' % (len(breton) - len(retenu)))
    print('  caractères            : %d' % sum(len(v) for v in retenu.values()))

    if '--ecrire' in sys.argv:
        with open(CIBLE, 'w', encoding='utf-8') as f:
            json.dump(cible, f, ensure_ascii=False, indent=1, sort_keys=True)
        print('écrit : %s (%d dates)' % (CIBLE, len(cible)))


if __name__ == '__main__':
    main()
