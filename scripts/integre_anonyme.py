#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Intègre le journal anonyme du Naturaliste dans data/journaux/baudin_fr.json.

Le rattachement se faisait autrefois dans le GeoJSON, par un script retiré du
dépôt en septembre 2026 : les journaux vivent désormais dans data/journaux/ et
le parcours ne porte plus que les positions. C'est map.html qui décide, par
SOURCES_JOURNAUX, à quel bâtiment chaque journal appartient -- celui-ci est
tenu à bord du Naturaliste et ne s'affiche que sur lui.

Le retour vers la France étant maintenant tracé (scripts/retour_naturaliste.py),
le journal est rattaché jusqu'à sa dernière entrée.

Usage : python3 scripts/integre_anonyme.py [--ecrire]
"""
import json, sys

PARCOURS = 'data/baudin_parcours.geojson'
JOURNAL  = 'data/journal_anonyme.json'
CIBLE    = 'data/journaux/baudin_fr.json'
CHAMP    = 'journal_anonyme'


def main():
    geo = json.load(open(PARCOURS, encoding='utf-8'))
    dates = {f['properties']['date'] for f in geo['features']
             if f['geometry']['type'] == 'Point' and f['properties'].get('date')}

    textes = json.load(open(JOURNAL, encoding='utf-8'))
    cible = json.load(open(CIBLE, encoding='utf-8'))
    for v in cible.values():
        v.pop(CHAMP, None)

    retenu = {d: t for d, t in textes.items() if d in dates}
    for d, t in retenu.items():
        cible.setdefault(d, {})[CHAMP] = t

    print('entrées du journal : %d' % len(textes))
    print('  retenues (date au parcours) : %d' % len(retenu))
    print('  écartées                    : %d' % (len(textes) - len(retenu)))
    ap = [d for d in retenu if d > '1802-11-20']
    print('  dont retour vers la France  : %d' % len(ap))

    if '--ecrire' in sys.argv:
        cible = {k: v for k, v in cible.items() if v}
        json.dump(cible, open(CIBLE, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1, sort_keys=True)
        print('écrit : %s (%d dates)' % (CIBLE, len(cible)))


if __name__ == '__main__':
    main()
