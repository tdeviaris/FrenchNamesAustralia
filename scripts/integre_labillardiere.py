#!/usr/bin/env python3
"""Verse la Relation de Labillardière (transcription intégrale, septembre 2026)
dans le parcours d'Entrecasteaux.

Entrée : data/journal_labillardiere.json, une entrée par journée (texte du
récit, position retenue : relevé de Rossel en mer, mouillage en relâche).
Produit :
  - data/journaux/entrecasteaux_fr.json : {date: {"journal_labillardiere": texte}}
  - dans data/dentrecasteaux_parcours.geojson, un point pour chaque journée du
    récit que les tables de Rossel ne relèvent pas (relâches surtout), marqué
    "ajout": "labillardiere". Le script retire ses propres ajouts avant de les
    reposer : il est rejouable.
Archive de méthode : ne plus le relancer. Depuis la première intégration, le
GeoJSON a été retouché à la main (champ alerte_en : nom anglais des
mouillages), ce qu'il effacerait. Corriger directement les données.
Usage : python3 scripts/integre_labillardiere.py [--ecrire]
"""
import json, os, sys, datetime as dt

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(RACINE, 'data', *p)


def main():
    journal = json.load(open(D('journal_labillardiere.json'), encoding='utf-8'))
    gj = json.load(open(D('dentrecasteaux_parcours.geojson'), encoding='utf-8'))
    gj['features'] = [f for f in gj['features'] if f['properties'].get('ajout') != 'labillardiere']
    releves = {f['properties'].get('date') for f in gj['features']
               if f['geometry']['type'] == 'Point'}
    textes = {d: {'journal_labillardiere': v['texte']} for d, v in journal.items()}
    ajouts = []
    for d, v in sorted(journal.items()):
        if d in releves or v.get('lat') is None:
            continue
        mouillage = v.get('station') not in ('mer', '', None)
        props = {'date': d, 'section': '', 'alerte': (v.get('station_libelle') or '') if mouillage
                 else "position de la veille ou du lendemain (Rossel), faute de relevé ce jour-là",
                 'extrapole': True, 'ajout': 'labillardiere'}
        props['mouillage' if mouillage else 'interpole'] = True
        ajouts.append({'type': 'Feature',
                       'geometry': {'type': 'Point', 'coordinates': [round(v['lon'], 4), round(v['lat'], 4)]},
                       'properties': props})
    # Les points s'intercalent par date parmi les relevés.
    pts = [f for f in gj['features'] if f['geometry']['type'] == 'Point'] + ajouts
    autres = [f for f in gj['features'] if f['geometry']['type'] != 'Point']
    pts.sort(key=lambda f: f['properties'].get('date', ''))
    gj['features'] = pts + autres
    print(f'{len(textes)} journées de récit, {len(ajouts)} points ajoutés '
          f'({sum(1 for a in ajouts if a["properties"].get("mouillage"))} au mouillage)')
    if '--ecrire' not in sys.argv:
        print('Essai à blanc : relancer avec --ecrire.')
        return
    json.dump(textes, open(D('journaux', 'entrecasteaux_fr.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, separators=(',', ':'))
    json.dump(gj, open(D('dentrecasteaux_parcours.geojson'), 'w', encoding='utf-8'),
              ensure_ascii=False, separators=(',', ':'))
    print('✅ écrit')


if __name__ == '__main__':
    main()
