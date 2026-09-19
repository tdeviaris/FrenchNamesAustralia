#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Remet à l'eau les positions que le trait de côte place à terre.

Le fond de carte emploie le littoral de Natural Earth au 1/10 000 000. À cette
échelle un port n'est pas dessiné : Sydney Cove, la rade de Sainte-Croix de
Ténériffe, le canal d'Entrecasteaux tombent dans le polygone terrestre. Les
navires y mouillaient pourtant, et la position est juste — c'est le trait de
côte qui est grossier.

Une position à terre gâte deux choses : le marqueur paraît posé dans les
terres, et toute route qui en part traverse la presqu'île. On la décale donc
jusqu'à l'eau la plus proche, de quelques kilomètres, en le disant dans la
fiche.

Deux garde-fous :

  - un décalage qui dépasse le seuil n'est pas une affaire de résolution mais
    une position douteuse : on ne la touche pas, on la signale ;
  - deux journées au même mouillage se décalent ensemble, sinon une escale
    immobile se mettrait à frémir d'un jour à l'autre.

Rejouable : un parcours déjà renfloué ne produit plus aucun déplacement.

Usage : python3 scripts/renfloue.py [--ecrire]
"""
import io
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from littoral import Terre, km, RACINE

DATA = os.path.join(RACINE, 'data')
FICHIERS = ['baudin_parcours.geojson',
            'dentrecasteaux_parcours.geojson',
            'flinders_parcours.geojson']

# Au-delà, ce n'est plus la résolution du littoral qui est en cause.
SEUIL_KM = 30.0
# On cherche en anneaux, du plus serré au plus large.
RAYONS_KM = [2, 4, 6, 9, 13, 18, 24, 30]
DIRECTIONS = 48


def vers_leau(terre, point):
    """L'eau la plus proche, ou None si elle est trop loin pour être un artefact."""
    lon, lat = point[0], point[1]
    coslat = max(math.cos(math.radians(lat)), 1e-6)
    for rayon in RAYONS_KM:
        meilleur = None
        for i in range(DIRECTIONS):
            a = 2 * math.pi * i / DIRECTIONS
            m = [round(lon + rayon * math.cos(a) / (111.32 * coslat), 4),
                 round(lat + rayon * math.sin(a) / 111.32, 4)]
            if terre.contient(m):
                continue
            d = km(point, m)
            if meilleur is None or d < meilleur[0]:
                meilleur = (d, m)
        if meilleur:
            return meilleur[1], meilleur[0]
    return None, None


NOTE = ("position décalée de {d:.0f} km vers le large : le trait de côte "
        "employé par la carte, au 1/10 000 000, ne dessine pas ce mouillage, "
        "et la position relevée y tombait en pleine terre. Le relevé lui-même "
        "n'est pas en cause")


def main(ecrire):
    terre = Terre()
    total_bouges = total_suspects = 0
    for fichier in FICHIERS:
        chemin = os.path.join(DATA, fichier)
        if not os.path.exists(chemin):
            continue
        gj = json.load(io.open(chemin, encoding='utf-8'))
        points = [f for f in gj['features'] if f['geometry']['type'] == 'Point']
        # Un mouillage tenu plusieurs jours porte la même position : on ne la
        # calcule qu'une fois, et toutes ses journées la suivent.
        aterre = {}
        for f in points:
            c = tuple(f['geometry']['coordinates'][:2])
            if c not in aterre and terre.contient(list(c)):
                aterre[c] = None
        bouges = suspects = []
        bouges, suspects = [], []
        for c in aterre:
            neuf, d = vers_leau(terre, list(c))
            if neuf is None:
                suspects.append(c)
            else:
                aterre[c] = (neuf, d)
                bouges.append((c, neuf, d))
        n = 0
        for f in points:
            c = tuple(f['geometry']['coordinates'][:2])
            if aterre.get(c):
                neuf, d = aterre[c]
                f['geometry']['coordinates'] = list(neuf)
                f['properties']['renfloue'] = NOTE.format(d=d)
                n += 1
        print('%-34s %4d points, %2d mouillages à terre, %3d journées décalées'
              % (fichier, len(points), len(aterre), n))
        for c, neuf, d in sorted(bouges, key=lambda x: -x[2])[:6]:
            print('     %8.3f %8.3f  ->  %8.3f %8.3f   %4.1f km'
                  % (c[0], c[1], neuf[0], neuf[1], d))
        for c in suspects:
            print('     %8.3f %8.3f  : eau trop loin, position laissée telle quelle'
                  % c)
        total_bouges += n
        total_suspects += len(suspects)
        if ecrire and n:
            json.dump(gj, io.open(chemin, 'w', encoding='utf-8'), ensure_ascii=False)
            print('     -> %s mis à jour' % fichier)
    print('\nTOTAL : %d journées remises à l’eau, %d positions douteuses laissées'
          % (total_bouges, total_suspects))
    if not ecrire:
        print('(simulation — relancer avec --ecrire)')


if __name__ == '__main__':
    main('--ecrire' in sys.argv)
