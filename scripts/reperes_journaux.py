#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dresse la liste des journées où un point de parcours existe, et pour quelle coque.

Le Q&R renvoie vers la fiche d'une journée de journal — date et navire. Avant
d'afficher le lien, la page doit savoir si ce point existe : un renvoi vers une
journée sans relevé n'ouvrirait rien.

Charger les trois fichiers de parcours pour cela coûterait près d'un méga-octet
de coordonnées sur une page qui n'affiche aucune carte. On en tire donc, une
fois pour toutes, un index d'une cinquantaine de kilo-octets : une date, les
coques qui ont un relevé ce jour-là.

Les corvettes naviguant de conserve ne donnent qu'un point, marqué « les
corvettes ». On le rend explicitement au Géographe et au Naturaliste, sans quoi
un renvoi vers le journal de Baudin le 26 janvier 1801 serait refusé alors que
le point existe.

Usage : python3 scripts/reperes_journaux.py [--ecrire]
"""
import json
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SORTIE = os.path.join(RACINE, 'data', 'journaux_reperes.json')

PARCOURS = ('baudin_parcours.geojson',
            'flinders_parcours.geojson',
            'dentrecasteaux_parcours.geojson')

# Une coque nommée pour deux : le relevé vaut pour les deux journaux du bord.
DE_CONSERVE = {'les corvettes': ('le Géographe', 'le Naturaliste')}


def reperes():
    par_date = {}
    for fichier in PARCOURS:
        chemin = os.path.join(RACINE, 'data', fichier)
        if not os.path.exists(chemin):
            print(f'  ⚠️  absent : {fichier}')
            continue
        donnees = json.load(open(chemin, encoding='utf-8'))
        for trait in donnees.get('features', []):
            props = trait.get('properties') or {}
            date = (props.get('date') or '').strip()
            if not date:
                continue
            navire = (props.get('navire') or '').strip()
            coques = set(DE_CONSERVE.get(navire.lower(), (navire,) if navire else ()))
            if navire:
                coques.add(navire)
            if not coques:
                continue
            par_date.setdefault(date, set()).update(coques)
    return {d: sorted(c) for d, c in sorted(par_date.items())}


def main():
    index = reperes()
    jours = len(index)
    couples = sum(len(v) for v in index.values())
    texte = json.dumps(index, ensure_ascii=False, separators=(',', ':'))
    print(f'{jours} journées, {couples} couples date-navire, {len(texte) / 1024:.0f} Ko')

    if '--ecrire' not in sys.argv:
        print('\nEssai à blanc. Relancer avec --ecrire pour écrire '
              + os.path.relpath(SORTIE, RACINE))
        premiers = list(index.items())[:3]
        for d, c in premiers:
            print(f'   {d} : {", ".join(c)}')
        return

    with open(SORTIE, 'w', encoding='utf-8') as f:
        f.write(texte)
    print(f'✅ {os.path.relpath(SORTIE, RACINE)} écrit')


if __name__ == '__main__':
    main()
