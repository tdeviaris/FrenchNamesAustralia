#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Intègre le journal de Hamelin, commandant du Naturaliste, dans data/journaux/baudin_fr.json.

Deux sources, deux champs :
  - journal_hamelin            cahier 1 (juillet 1800 - 17 août 1801), transcription
                               de Dany Bréelle (Hamelin_vol1_2023), découpée par journée ;
  - journal_hamelin_manuscrit  cahier 2 (18 août 1801 - 7 juin 1803, AN Marine 5JJ 42),
                               lecture automatique du manuscrit (septembre 2026), non relue.

Datation : Hamelin tient le jour marin, « Du 27 au 28 vendémiaire » courant de midi à
midi ; l'entrée est rattachée à la date de fin (le 28), celle du point de midi des
tables -- même convention que le journal anonyme du Naturaliste. En relâche, « Le 26
germinal » est rattaché au jour même. Contrôle : sur 484 journées du cahier 2 où
Hamelin porte en marge la date grégorienne, 481 concordent, les 3 autres étant
illisibles.

Le journal est rattaché dans son intégralité. Une journée sans point au parcours
en reçoit un, marqué `ajout: "hamelin"` pour pouvoir être retiré :
  - en relâche (le relevé d'avant et celui d'après à moins de 15 km), le point est
    tenu au mouillage, comme dans scripts/corrige_mouillages.py ;
  - en mer, il est interpolé entre les deux relevés qui encadrent la lacune ;
  - deux mouillages que le parcours n'avait pas sont posés d'après le journal :
    Port-Louis (3-8 février 1803) et le port du Havre (7 juin 1803).
Après la séparation de l'île King (8 décembre 1802), « les corvettes » désignent le
Géographe et le Casuarina : seuls les points du Naturaliste servent alors d'appui.

Archive de méthode : ne plus le relancer. Depuis, les points ajoutés ont été
retouchés à la main dans le GeoJSON : `alerte` porte le nom du mouillage (ou
« en mer, entre les relevés du … »), `alerte_en` sa version anglaise, et la note
technique d'origine est gardée dans `origine_position`. Une nouvelle exécution
effacerait ces retouches.

Usage : python3 scripts/integre_hamelin.py [--ecrire]
        puis python3 scripts/reperes_journaux.py --ecrire
"""
import datetime as dt
import io
import json
import math
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARCOURS = os.path.join(RACINE, 'data', 'baudin_parcours.geojson')
CIBLE = os.path.join(RACINE, 'data', 'journaux', 'baudin_fr.json')
SOURCES = [(os.path.join(RACINE, 'data', 'journal_hamelin.json'), 'journal_hamelin'),
           (os.path.join(RACINE, 'data', 'journal_hamelin_cahier2.json'), 'journal_hamelin_manuscrit')]
SEPARATION = '1802-12-08'

# Mouillages absents du parcours, nommés par le journal.
MOUILLAGES = [
    {'du': '1803-02-03', 'au': '1803-02-08', 'lon': 57.498, 'lat': -20.158,
     'lieu': 'Port Nord-Ouest (Port-Louis), île de France',
     'appui': "journal de Hamelin, 13-14 pluviôse an 11 : « mouillé à 1 heure, près l'île aux Tonneliers »"},
    {'du': '1803-06-07', 'au': '1803-06-07', 'lon': 0.107, 'lat': 49.487,
     'lieu': 'port du Havre',
     'appui': "journal de Hamelin, 17-18 prairial an 11 : « À 23 ½ heures entré dans le port du Havre »"},
]


def km(a, b):
    return math.hypot((a[0] - b[0]) * 111.32 * math.cos(math.radians(a[1])), (a[1] - b[1]) * 111.32)


def appui(p):
    n, d = p.get('navire'), p.get('date', '')
    if d >= SEPARATION:
        return n == 'le Naturaliste'
    return n in ('le Naturaliste', 'les corvettes')


def point(date, lon, lat, navire, alerte, mouillage):
    props = {'date': date, 'date_republicaine': '', 'navire': navire, 'table': '', 'page': '',
             'remarque': '', 'vents_etat_du_ciel': '', 'barometre_hpa': '', 'obs_latitude': '',
             'obs_longitude': '', 'thermometre': '', 'alerte': alerte, 'extrapole': True,
             'ajout': 'hamelin'}
    if mouillage:
        props['mouillage'] = True
    else:
        props['interpole'] = True
    return {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [round(lon, 4), round(lat, 4)]},
            'properties': props}


def main():
    gj = json.load(io.open(PARCOURS, encoding='utf-8'))
    avant = len(gj['features'])
    gj['features'] = [f for f in gj['features'] if f['properties'].get('ajout') != 'hamelin']
    retires = avant - len(gj['features'])

    textes = {}
    for chemin, champ in SOURCES:
        for d, t in json.load(io.open(chemin, encoding='utf-8')).items():
            textes.setdefault(d, {})[champ] = t

    pts = sorted((f['properties']['date'], f['geometry']['coordinates'], f['properties'].get('navire'))
                 for f in gj['features']
                 if f['geometry']['type'] == 'Point' and f['properties'].get('date') and appui(f['properties']))
    dates = {d for d, _, _ in pts}
    manquants = sorted(d for d in textes if d not in dates)

    ajouts = []
    for d in manquants:
        m = next((m for m in MOUILLAGES if m['du'] <= d <= m['au']), None)
        if m:
            ajouts.append(point(d, m['lon'], m['lat'], 'le Naturaliste',
                                'point ajouté pour une entrée du journal de Hamelin ; position tenue au mouillage : %s (%s)'
                                % (m['lieu'], m['appui']), True))
            continue
        prec = [x for x in pts if x[0] < d]
        suiv = [x for x in pts if x[0] > d]
        if not prec:
            continue
        p = prec[-1]
        s = suiv[0] if suiv else None
        navire = p[2] if (p[2] == 'les corvettes' and d < SEPARATION) else 'le Naturaliste'
        if s is None or km(p[1], s[1]) < 15:
            ajouts.append(point(d, p[1][0], p[1][1], navire,
                                'point ajouté pour une entrée du journal de Hamelin ; position tenue au mouillage '
                                'du relevé du %s' % p[0], True))
        else:
            d0, d1, dd = (dt.date.fromisoformat(x) for x in (p[0], s[0], d))
            t = (dd - d0).days / (d1 - d0).days
            lon = p[1][0] + (s[1][0] - p[1][0]) * t
            lat = p[1][1] + (s[1][1] - p[1][1]) * t
            ajouts.append(point(d, lon, lat, navire,
                                'point ajouté pour une entrée du journal de Hamelin ; position interpolée entre '
                                'les relevés du %s et du %s' % (p[0], s[0]), False))
    gj['features'].extend(ajouts)

    cible = json.load(io.open(CIBLE, encoding='utf-8'))
    for v in cible.values():
        v.pop('journal_hamelin', None)
        v.pop('journal_hamelin_manuscrit', None)
    for d, champs in textes.items():
        cible.setdefault(d, {}).update(champs)

    print('journées du journal de Hamelin : %d (cahier 1 : %d, cahier 2 : %d)' % (
        len(textes), sum('journal_hamelin' in v for v in textes.values()),
        sum('journal_hamelin_manuscrit' in v for v in textes.values())))
    print('points retirés (ajouts précédents) : %d' % retires)
    print('points ajoutés : %d  (au mouillage : %d, interpolés : %d)' % (
        len(ajouts), sum(1 for a in ajouts if a['properties'].get('mouillage')),
        sum(1 for a in ajouts if a['properties'].get('interpole'))))
    if '--ecrire' in sys.argv:
        json.dump(gj, io.open(PARCOURS, 'w', encoding='utf-8'), ensure_ascii=False)
        cible = {k: v for k, v in cible.items() if v}
        json.dump(cible, io.open(CIBLE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, sort_keys=True)
        print('écrit : %s et %s' % (os.path.relpath(PARCOURS, RACINE), os.path.relpath(CIBLE, RACINE)))
    else:
        print('(simulation — relancer avec --ecrire)')


if __name__ == '__main__':
    main()
