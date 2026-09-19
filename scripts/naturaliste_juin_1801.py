#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rend au Naturaliste les dix-huit journées qui suivent la séparation.

Les corvettes se perdent de vue à une heure du matin le 10 juin 1801, dans le
coup de vent qui suit la perte de la chaloupe en baie du Géographe. Le premier
relevé du Naturaliste dans les tables de Freycinet est du 28 juin : entre les
deux, la carte le laissait disparaître dix-huit jours.

Les tables se taisent, mais le journal anonyme tenu à son bord parle tous les
jours. Il ne donne pas de latitude : il donne des relèvements, des sondes et
le récit des canots. Cela suffit à placer le navire, inégalement selon les
périodes -- et le fichier le dit, journée par journée.

Du 15 au 27 juin : le mouillage, solidement établi
--------------------------------------------------
Treize jours au même endroit, en rade de Gage, entre l'île Rottnest et
l'embouchure de la rivière des Cygnes. Le journal montre un navire immobile :
canots envoyés reconnaître Rottnest le 15, pavillon national planté sur une
colline, grand canot expédié six jours pour remonter la rivière des Cygnes le
17, Heirisson en rapportant une bouteille d'eau douce le 23, la chaloupe
échouée puis réparée et remise à l'eau le 23. La corvette chasse sur son ancre
les 16 et 20 et mouille son ancre de veille.

Trois indices concordants fixent le lieu :

  - c'est le rendez-vous que Baudin lui avait assigné. Son journal du 14 juin :
    « je pense qu'il se sera rendu à l'île Rottnest que je lui ai indiqué pour
    premier rendez-vous en cas de séparation » ;
  - le journal du Naturaliste aperçoit le Géographe « dans le SSO […] à 24
    milles ». Depuis cette rade, le Géographe du 18 juin se trouve au SSO à 18
    milles marins. Ces journaux se tenant de midi à midi, l'écart d'un jour est
    attendu ;
  - le premier relevé de Freycinet, au 28 juin, tombe à 25 km au nord-ouest,
    ce qui correspond à un appareillage à sept heures ce matin-là.

Du 10 au 14 juin : une estime
------------------------------
Le 10 seul repose sur une mesure. Le journal relève « la pointe strib du
golphe en entrant » -- le cap Naturaliste, pour qui entre dans la baie du
Géographe par l'ouest -- au N78°O à dix milles, puis au N86°O à huit milles.
Les deux relèvements donnent le navire à un peu plus de 115°10' de longitude,
par 33°34' de latitude sud.

Les quatre jours suivants sont une route estimée entre ce point et le
mouillage. Le journal raconte un navire qui vire lof pour lof dans une mer
très grosse, perd son ancre à jet, puis remonte vers le nord et sonde 25 puis
45 brasses le 14 -- donc à quelques lieues de la côte. On ne peut pas en tirer
de position ; on peut en tirer une route vraisemblable, et le dire.

Rejouable : un parcours déjà complété ne produit plus aucun ajout.

Usage : python3 scripts/naturaliste_juin_1801.py [--ecrire]
"""
import datetime
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from littoral import Cote, Terre, km, RACINE

GEOJSON = os.path.join(RACINE, 'data', 'baudin_parcours.geojson')
NAVIRE = 'le Naturaliste'

# Le point du 10 juin, tiré des deux relèvements sur le cap Naturaliste.
DEPART = [115.1900, -33.5600]
# La rade de Gage, entre Rottnest et l'embouchure de la rivière des Cygnes.
MOUILLAGE = [115.6600, -32.0200]

DEBUT_ESTIME = datetime.date(1801, 6, 10)
FIN_ESTIME = datetime.date(1801, 6, 14)
DEBUT_MOUILLAGE = datetime.date(1801, 6, 15)
FIN_MOUILLAGE = datetime.date(1801, 6, 27)

TABLE = ("journal anonyme tenu à bord du Naturaliste ; les tables de route de "
         "Freycinet ne reprennent ce bâtiment qu'au 28 juin 1801")

RELEVE = ("position déduite des relèvements du journal : la pointe d'entrée "
          "de la baie du Géographe -- le cap Naturaliste -- au N78°O à dix "
          "milles, puis au N86°O à huit milles")

ESTIME = ("position estimée : les tables ne suivent plus le Naturaliste entre "
          "la séparation du 10 juin et le 28. Le journal du bord le montre "
          "virant lof pour lof dans une mer très grosse, puis remontant vers "
          "le nord et sondant 25 puis 45 brasses le 14 ; la route est tracée "
          "entre le dernier relèvement du 10 juin et le mouillage de la rade "
          "de Gage, sans qu'aucune position intermédiaire soit relevée")

AU_MOUILLAGE = ("position tenue au mouillage : rade de Gage, entre l'île "
                "Rottnest et l'embouchure de la rivière des Cygnes, où Baudin "
                "avait assigné le rendez-vous en cas de séparation. Le journal "
                "y montre treize jours d'immobilité, canots à Rottnest et à la "
                "rivière des Cygnes, chaloupe réparée. Le relèvement du "
                "Géographe « dans le SSO à 24 milles » et le premier relevé de "
                "Freycinet au 28 juin concordent")


def jours(a, b):
    n = (b - a).days
    return [a + datetime.timedelta(days=i) for i in range(n + 1)]


def gabarit(date, coords, alerte, mouillage=False):
    props = {
        'date': date.isoformat(),
        'navire': NAVIRE,
        'table': TABLE,
        'extrapole': True,
        'alerte': alerte,
    }
    if mouillage:
        props['mouillage'] = True
    return {'type': 'Feature',
            'geometry': {'type': 'Point', 'coordinates': [round(c, 4) for c in coords]},
            'properties': props}


def main(ecrire):
    gj = json.load(io.open(GEOJSON, encoding='utf-8'))
    deja = {(f['properties'].get('date'), f['properties'].get('navire'))
            for f in gj['features'] if f['geometry']['type'] == 'Point'}

    nouveaux = []

    # --- La travée estimée, du 10 au 14 juin.
    estimes = jours(DEBUT_ESTIME, FIN_ESTIME)
    for i, date in enumerate(estimes):
        if (date.isoformat(), NAVIRE) in deja:
            continue
        if i == 0:
            nouveaux.append(gabarit(date, DEPART, RELEVE))
            continue
        # Une part égale du chemin chaque jour : le journal ne permet pas mieux.
        t = i / float(len(estimes))
        coords = [DEPART[0] + (MOUILLAGE[0] - DEPART[0]) * t,
                  DEPART[1] + (MOUILLAGE[1] - DEPART[1]) * t]
        nouveaux.append(gabarit(date, coords, ESTIME))

    # --- Le mouillage, du 15 au 27 juin.
    for date in jours(DEBUT_MOUILLAGE, FIN_MOUILLAGE):
        if (date.isoformat(), NAVIRE) in deja:
            continue
        nouveaux.append(gabarit(date, MOUILLAGE, AU_MOUILLAGE, mouillage=True))

    # --- Les garde-fous : aucune position à terre, aucun trait qui la traverse.
    terre = Terre()
    aterre = [f for f in nouveaux if terre.contient(f['geometry']['coordinates'])]
    print('journées ajoutées      : %d' % len(nouveaux))
    print('   dont relevées       : %d' % sum(1 for f in nouveaux
                                              if f['properties']['alerte'] == RELEVE))
    print('   dont estimées       : %d' % sum(1 for f in nouveaux
                                              if f['properties']['alerte'] == ESTIME))
    print('   dont au mouillage   : %d' % sum(1 for f in nouveaux
                                              if f['properties'].get('mouillage')))
    print('positions à terre      : %d' % len(aterre))
    if aterre:
        for f in aterre:
            print('     %s %s' % (f['properties']['date'], f['geometry']['coordinates']))
        print('rien n\'est écrit.')
        return

    cote = Cote()
    # Le trait rejoint le dernier point commun aux deux corvettes, puis suit
    # les journées ajoutées, puis rejoint le premier relevé de Freycinet.
    suite = [[115.1325, -33.4222]] + [f['geometry']['coordinates'] for f in nouveaux] \
            + [[115.5164, -31.8331]]
    coupes = [(suite[i], suite[i + 1]) for i in range(len(suite) - 1)
              if cote.traverse(suite[i], suite[i + 1])]
    print('segments traversant la terre : %d' % len(coupes))
    for a, b in coupes:
        print('     %s -> %s' % (a, b))
    if coupes:
        print('rien n\'est écrit.')
        return

    total = sum(km(suite[i], suite[i + 1]) for i in range(len(suite) - 1))
    print('longueur de la route rendue  : %.0f km en %d jours' % (total, len(suite) - 1))

    if not ecrire:
        print('\n(simulation — relancer avec --ecrire)')
        return
    if nouveaux:
        gj['features'].extend(nouveaux)
        gj['features'].sort(key=lambda f: (f['geometry']['type'] != 'Point',
                                           str(f.get('properties', {}).get('date', ''))))
        json.dump(gj, io.open(GEOJSON, 'w', encoding='utf-8'), ensure_ascii=False)
        print('\n-> %s mis à jour' % os.path.relpath(GEOJSON, RACINE))


if __name__ == '__main__':
    main('--ecrire' in sys.argv)
