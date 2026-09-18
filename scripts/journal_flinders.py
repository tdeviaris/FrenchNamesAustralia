#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tire le parcours de l'Investigator du récit publié par Flinders.

« A Voyage to Terra Australis », Londres, 1814, deux volumes, tels que les
donne Project Gutenberg Australia. Le texte est daté journée par journée, en
capitales : THURSDAY 8 APRIL 1802. Flinders y consigne sa position de midi
quand il fait route, mais pendant les levés côtiers il donne surtout des
relèvements et la position des terres qu'il reconnaît. La trace est donc plus
lâche que celle de Baudin, qui repose sur des tables journalières.

Deux volumes se succèdent sans rien perdre : le premier s'arrête au 9 mai 1802,
le second reprend au 22 juillet. L'intervalle est le carénage de Port Jackson,
où le navire ne bougeait pas — et où Baudin se trouvait aussi.

Les positions sont rapportées à Greenwich, non à Paris : aucune conversion.

Usage : python3 scripts/journal_flinders.py <dossier des textes> [--ecrire]
"""
import datetime, io, json, os, re, sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SORTIE = os.path.join(RACINE, 'data', 'flinders_parcours.geojson')
NAVIRE = "l'Investigator"

MOIS = {m: i + 1 for i, m in enumerate(
    'JANUARY FEBRUARY MARCH APRIL MAY JUNE JULY AUGUST SEPTEMBER OCTOBER '
    'NOVEMBER DECEMBER'.split())}
JOURS = (r'(?:MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY)')
ENTETE = re.compile(JOURS + r'\s+(\d{1,2})\s+(' + '|'.join(MOIS) + r')\s+(\d{4})')

# Les tournures qui annoncent la position du navire, et non celle d'une terre
# qu'il relève. « its latitude is », « lies in latitude » désignent un amer :
# elles sont écartées.
# « in latitude » seul ne vaut rien : Flinders s'en sert aussi pour discuter
# la position que d'autres navigateurs assignent a un rocher. On exige une
# tournure qui rapporte la position au navire.
ANCRE = (r'(?:latitude[, ]{0,2}observ\w*|latitude at noon|our latitude|'
         r'we were in latitude|situation was as under)')
FRACTIONS = {'¼': .25, '½': .5, '¾': .75, '⅓': 1 / 3, '⅔': 2 / 3}
# « 9° 42' south », « 30° 58¼' », « 22° 20' 42" »
SEXA = r'(\d{1,3})\s*°\s*(\d{1,2}[¼½¾⅓⅔]?)?\s*\'?\s*(?:(\d{1,2})\s*")?'
LAT = re.compile(ANCRE + r'[^0-9]{0,60}' + SEXA + r'\s*(south|north|[SN])?', re.I)
# Le degré manque parfois à la longitude des tableaux : « 153 6½ »
LON = re.compile(r'longitude[^0-9]{0,70}(\d{1,3})\s*°?\s*(\d{1,2}[¼½¾]?)?\s*\'?'
                 r'\s*(?:(\d{1,2})\s*")?\s*(east|west|[EW])?', re.I)

# Un bâtiment de 1801 ne franchit pas cela en une journée : au-delà, la lecture
# est fautive ou la position désigne autre chose que le navire.
KM_JOUR_MAX = 420.0

# L'Investigator est condamné à Port Jackson au retour de sa circumnavigation.
# Flinders repart ensuite sur le Porpoise, qui fait naufrage, puis sur le
# Cumberland : le récit continue, mais ce n'est plus le même bâtiment.
FIN_INVESTIGATOR = datetime.date(1803, 6, 9)


def nombre(s):
    """Un nombre qui peut porter une fraction d'époque : 58¼, 36½."""
    if s is None:
        return 0.0
    f = 0.0
    for c, v in FRACTIONS.items():
        if c in s:
            f, s = v, s.replace(c, '')
    s = s.strip(" '\"")
    return (float(s) + f) if re.fullmatch(r'\d+', s) else None


def degres(d, m, s):
    a, b, c = nombre(d), nombre(m), nombre(s)
    if a is None or b is None or c is None:
        return None
    return a + b / 60.0 + c / 3600.0


def km(p, q):
    import math
    lat = math.radians((p[1] + q[1]) / 2)
    return math.hypot((q[0] - p[0]) * math.cos(lat), q[1] - p[1]) * 111.32


def journees(texte):
    """Les blocs de texte, un par en-tête de date."""
    ent = list(ENTETE.finditer(texte))
    for i, m in enumerate(ent):
        fin = ent[i + 1].start() if i + 1 < len(ent) else min(len(texte), m.end() + 4000)
        try:
            d = datetime.date(int(m.group(3)), MOIS[m.group(2)], int(m.group(1)))
        except (ValueError, KeyError):
            continue
        yield d, texte[m.end():fin]


def position(bloc):
    """Latitude et longitude du navire, si le bloc les donne toutes deux."""
    ml = LAT.search(bloc)
    if not ml:
        return None
    lat = degres(ml.group(1), ml.group(2), ml.group(3))
    if lat is None or lat > 60:
        return None
    if (ml.group(4) or 's').lower().startswith('s'):
        lat = -lat
    # la longitude doit suivre de près : au-delà, elle parle d'autre chose
    mo = LON.search(bloc[ml.end():ml.end() + 260])
    if not mo:
        return None
    lon = degres(mo.group(1), mo.group(2), mo.group(3))
    if lon is None or lon > 180:
        return None
    if (mo.group(4) or 'e').lower().startswith('w'):
        lon = -lon
    return round(lon, 5), round(lat, 5)


def terre():
    """Les polygones terrestres, pour refuser une position tombee a terre."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from littoral import Terre
    return Terre()


def main():
    dossier = sys.argv[1].rstrip('/')
    sol = terre()
    points, refuses, aterre, hors = [], 0, 0, 0
    for fichier in ('volume1.txt', 'volume2.txt'):
        chemin = os.path.join(dossier, fichier)
        if not os.path.exists(chemin):
            sys.exit('introuvable : %s' % chemin)
        texte = io.open(chemin, encoding='utf-8').read().replace('\xad', '')
        for d, bloc in journees(texte):
            if d > FIN_INVESTIGATOR:
                hors += 1
                continue
            p = position(bloc)
            if not p:
                continue
            # Une position a terre n'est pas celle d'un navire : c'est une
            # longitude discutee, ou un chiffre mal lu.
            if sol.contient(p):
                aterre += 1
                continue
            points.append({'date': d, 'coords': list(p), 'volume': fichier[6]})

    points.sort(key=lambda x: x['date'])
    # Une position qui demanderait une vitesse impossible n'est pas celle du
    # navire : c'est une terre citée, ou un chiffre mal lu.
    gardes = []
    for p in points:
        if gardes:
            v = km(gardes[-1]['coords'], p['coords'])
            j = max(1, (p['date'] - gardes[-1]['date']).days)
            if v / j > KM_JOUR_MAX:
                refuses += 1
                continue
        gardes.append(p)

    print('positions retenues : %d' % len(gardes))
    print('  écartées, tombant à terre     : %d' % aterre)
    print('  écartées, vitesse impossible  : %d' % refuses)
    print('  journées postérieures à l’Investigator : %d' % hors)
    if gardes:
        print('  du %s au %s' % (gardes[0]['date'], gardes[-1]['date']))

    if '--ecrire' in sys.argv:
        gj = {"type": "FeatureCollection", "features": [
            {"type": "Feature",
             "geometry": {"type": "Point", "coordinates": p['coords']},
             "properties": {
                 "date": p['date'].isoformat(),
                 "navire": NAVIRE,
                 "expedition": "Flinders",
                 "table": "Matthew Flinders, A Voyage to Terra Australis, "
                          "Londres, 1814, vol. %s" % p['volume'],
                 "alerte": "position tirée du récit publié ; Flinders ne la "
                           "donne pas tous les jours",
             }} for p in gardes]}
        json.dump(gj, io.open(SORTIE, 'w', encoding='utf-8'), ensure_ascii=False)
        print('\n-> %s' % os.path.relpath(SORTIE, RACINE))
    else:
        print('\n(simulation — relancer avec --ecrire)')


if __name__ == '__main__':
    main()
