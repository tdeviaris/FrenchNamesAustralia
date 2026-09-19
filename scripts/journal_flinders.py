#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tire du récit publié par Flinders le parcours de ses trois bâtiments.

« A Voyage to Terra Australis », Londres, 1814, deux volumes, tels que les
donne Project Gutenberg Australia. Le texte est daté journée par journée, en
capitales : THURSDAY 8 APRIL 1802. Flinders y consigne sa position de midi
quand il fait route, mais pendant les levés côtiers il donne surtout des
relèvements et la position des terres qu'il reconnaît. La trace est donc plus
lâche que celle de Baudin, qui repose sur des tables journalières.

Deux volumes se succèdent sans rien perdre : le premier s'arrête au 9 mai 1802,
le second reprend au 22 juillet. L'intervalle est le carénage de Port Jackson,
où le navire ne bougeait pas — et où Baudin se trouvait aussi.

L'Investigator est condamné à son retour à Port Jackson. Flinders repart le
10 août 1803 sur le Porpoise, qui se perd sept jours plus tard sur Wreck Reef,
puis le 21 septembre sur la goélette Cumberland. Le récit ne s'interrompt pas :
seul change le bâtiment sous ses pieds, et c'est ce que dit NAVIRES.

Les positions sont rapportées à Greenwich, non à Paris : aucune conversion.

ATTENTION : ce script RÉÉCRIT data/flinders_parcours.geojson à partir du seul
récit. Les positions relevées sur la carte générale de 1814 y sont versées
ensuite, par scripts/integre_carte_flinders.py — quarante-deux points, dont
toute la traversée de retour d'avril et mai 1803, que le récit ne donne pas.
Les relancer dans l'ordre, toujours :

    python3 scripts/journal_flinders.py <dossier> --ecrire
    python3 scripts/integre_carte_flinders.py --ecrire

Usage : python3 scripts/journal_flinders.py <dossier des textes> [--ecrire]
"""
import datetime, io, json, os, re, sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SORTIE = os.path.join(RACINE, 'data', 'flinders_parcours.geojson')
JOURNAL = os.path.join(RACINE, 'data', 'journaux', 'flinders_en.json')
# Chaque campagne, du jour de l'appareillage au dernier jour utile. Entre le
# naufrage de Wreck Reef et l'appareillage de la Cumberland, Flinders regagne
# Port Jackson dans un canot puis y attend un bâtiment : ces cinq semaines ne
# sont la route d'aucun navire, et ne portent pas de point.
NAVIRES = [
    ("l'Investigator", '1801-01-01', '1803-06-09'),
    ('le Porpoise',    '1803-08-10', '1803-08-17'),
    ('le Cumberland',  '1803-09-21', '1803-12-16'),
]


def navire_du_jour(d):
    """Le bâtiment que Flinders monte ce jour-là, ou None."""
    for nom, du, au in NAVIRES:
        if datetime.date.fromisoformat(du) <= d <= datetime.date.fromisoformat(au):
            return nom
    return None

# Au mouillage, Flinders cesse de donner sa position : elle ne change pas. Sans
# ces escales le trace saute d'un bout a l'autre du continent, et il manquait
# tout Port Jackson -- ou l'Investigator passa dix semaines, en meme temps que
# Baudin. Les dates viennent du recit lui-meme.
ESCALES = [
    {'du': '1801-12-09', 'au': '1802-01-04',
     'lon': 117.95, 'lat': -35.05,
     'lieu': "King George's Sound",
     'appui': "le 10 décembre « we got the ship under way to beat up to the "
              "entrance » ; le 30, « the ship unmoored » ; le 3 janvier on "
              "prend congé des habitants"},
    {'du': '1802-05-09', 'au': '1802-07-22',
     'lon': 151.1461, 'lat': -33.8667,
     'lieu': 'Port Jackson',
     'appui': "le 9 mai « the Investigator was anchored in Sydney Cove » ; "
              "le 22 juillet « we sailed out of Port Jackson »"},
    {'du': '1803-06-09', 'au': '1803-06-09',
     'lon': 151.1461, 'lat': -33.8667,
     'lieu': 'Port Jackson, retour de la circumnavigation',
     'appui': "fin de la campagne de l'Investigator, condamné à son retour"},
    {'du': '1803-08-10', 'au': '1803-08-10',
     'lon': 151.1461, 'lat': -33.8667,
     'lieu': 'Port Jackson, appareillage du Porpoise',
     'appui': "le 10 août « we sailed out of Port Jackson together, at eleven "
              "o'clock of the same morning, and steered north-eastward for "
              "Torres' Strait »"},
    {'du': '1803-09-21', 'au': '1803-09-21',
     'lon': 151.1461, 'lat': -33.8667,
     'lieu': 'Port Jackson, appareillage de la Cumberland',
     'appui': "le 21 septembre « I sailed out of the harbour in the Cumberland "
              "at daylight, with the Rolla and Francis in company »"},
    {'du': '1803-10-07', 'au': '1803-10-11',
     'lon': 155.293, 'lat': -22.239,
     'lieu': 'Wreck Reef, où la Cumberland recueille les naufragés',
     'appui': "arrivée le 7 octobre ; « on parting from the Rolla, at noon "
              "Oct. 11, off Bird Islet, our course was steered N. N. W. »"},
]

# Flinders a perdu son journal dans le naufrage du Porpoise : la traversee de
# la Cumberland vers Wreck Reef est racontee de memoire, sans les tournures
# habituelles, et le depouillement automatique n'y trouve rien. Ces deux
# positions-la sont pourtant dites en toutes lettres.
POSITIONS_DITES = [
    {'date': '1803-09-22', 'lon': 152.22, 'lat': -32.73,
     'appui': "« I anchored in a small bight under Point Stephens, in very bad "
              "plight » ; le lendemain la Cumberland rejoint la Rolla et la "
              "Francis dans Port Stephens"},
    {'date': '1803-10-02', 'lon': 153.867, 'lat': -22.2,
     'appui': "« on the 2nd a.m. our corrected longitude was 153° 52' », par le "
              "travers de Wreck Reef, que la goélette cherche cinq jours durant"},
]

# Entre Point Stephens et Wreck Reef, dix jours sans une seule position : le
# trait direct couperait la Nouvelle-Galles du Sud sur trois cents kilometres.
# Ce point-ci n'est pas releve, il est CALCULE : c'est le plus proche de la
# route directe qui degage le trait de cote des deux cotes. La fiche le dit.
CONTOURNEMENTS = [
    {'date': '1803-09-24', 'lon': 153.55, 'lat': -31.6,
     'raison': "au large de Smoky Cape, entre le mouillage de Point Stephens du "
               "22 septembre et le travers de Wreck Reef du 2 octobre. Flinders "
               "a perdu son journal dans le naufrage et ne donne aucune position "
               "de cette traversée : seul le passage au large est certain"},
]

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
        # L'en-tête est entre crochets — « [THURSDAY 8 APRIL 1802] » — mais le
        # motif ne prend que la date. Les deux crochets tombaient donc chez le
        # voisin : le fermant en tête du bloc, l'ouvrant du suivant à sa queue.
        bloc = re.sub(r'^\s*\]\s*[.,;:]?\s*', '', texte[m.end():fin])
        bloc = re.sub(r'\s*\[\s*$', '', bloc)
        yield d, bloc


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


# Restes de la mise en page du site qui héberge le texte, et renvois d'atlas :
# rien de cela n'appartient au récit.
PARASITES = re.compile(
    # La parenthèse ouvrante fait partie du renvoi : sans elle, « (Atlas
    # Plate II.) » laissait un « ( » orphelin au milieu du récit.
    r'(?:Go to reference to Table[^.]{0,40}\.?|[(\[]?\s*Atlas[^)\]]{0,40}[)\]]|'
    r'Project Gutenberg[^.]{0,80}\.|CHAPTER [IVXL]+\.)', re.I)


def texte_du_jour(bloc):
    """Le récit de la journée, débarrassé de l'appareil de l'édition."""
    t = PARASITES.sub(' ', bloc)
    # Les filets des tableaux d'appendice sont de la mise en page, non du récit.
    t = re.sub(r'-{3,}', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    # Le bloc court jusqu'à l'en-tête suivant : on s'arrête à la fin de la
    # dernière phrase entière, pour ne pas laisser une amorce en suspens.
    # Une fiche de carte n'est pas une page de livre : on donne la substance de
    # la journée et l'on renvoie au texte complet par le lien de la source.
    if len(t) > 3600:
        coupe = t.rfind('. ', 0, 3600)
        t = (t[:coupe + 1] if coupe > 1200 else t[:3600]) + ' […]'
    return t


def proprietes(p):
    """Ce que porte un point : sa source, et pourquoi il est la."""
    e = p.get('escale')
    if e:
        return {
            "date": p['date'].isoformat(), "navire": p['navire'],
            "expedition": "Flinders",
            "table": "Matthew Flinders, A Voyage to Terra Australis, Londres, 1814",
            "extrapole": True,
            "alerte": "position tenue au mouillage : %s (%s)" % (e['lieu'], e['appui']),
        }
    commun = {
        "date": p['date'].isoformat(), "navire": p['navire'],
        "expedition": "Flinders",
        "table": "Matthew Flinders, A Voyage to Terra Australis, "
                 "Londres, 1814, vol. %s" % p['volume'],
    }
    detour = p.get('detour')
    if detour:
        commun["extrapole"] = True
        commun["alerte"] = ("position calculée, non relevée : %s"
                            % detour['raison'])
        return commun
    dite = p.get('dite')
    if dite:
        commun["alerte"] = ("position donnée en prose dans le récit, et non "
                            "dans une observation de midi : %s" % dite['appui'])
        return commun
    commun["alerte"] = ("position relevée dans le récit publié ; Flinders ne la "
                        "donne pas tous les jours")
    return commun


def main():
    dossier = sys.argv[1].rstrip('/')
    sol = terre()
    points, refuses, aterre, hors = [], 0, 0, 0
    recits = {}
    for fichier in ('volume1.txt', 'volume2.txt'):
        chemin = os.path.join(dossier, fichier)
        if not os.path.exists(chemin):
            sys.exit('introuvable : %s' % chemin)
        texte = io.open(chemin, encoding='utf-8').read().replace('\xad', '')
        for d, bloc in journees(texte):
            navire = navire_du_jour(d)
            if navire is None:
                hors += 1
                continue
            recit = texte_du_jour(bloc)
            if len(recit) > 120:
                recits[d.isoformat()] = recit
            p = position(bloc)
            if not p:
                continue
            # Une position a terre n'est pas celle d'un navire : c'est une
            # longitude discutee, ou un chiffre mal lu.
            if sol.contient(p):
                aterre += 1
                continue
            points.append({'date': d, 'coords': list(p),
                           'volume': fichier[6], 'navire': navire})

    # Les positions que Flinders donne en prose, hors de ses tournures
    # habituelles : elles ne remplacent jamais une position deja trouvee.
    connues = {p['date'] for p in points}
    for e in POSITIONS_DITES:
        d = datetime.date.fromisoformat(e['date'])
        if d in connues:
            continue
        points.append({'date': d, 'coords': [e['lon'], e['lat']],
                       'volume': '2', 'navire': navire_du_jour(d), 'dite': e})
    for e in CONTOURNEMENTS:
        d = datetime.date.fromisoformat(e['date'])
        if d in connues:
            continue
        points.append({'date': d, 'coords': [e['lon'], e['lat']],
                       'volume': '2', 'navire': navire_du_jour(d), 'detour': e})

    # Les escales. On ne pose pas un point par journee du sejour : le navire ne
    # bouge pas, et un marqueur muet n'apprend rien. On retient les journees ou
    # Flinders a ecrit quelque chose, plus le premier et le dernier jour, qui
    # marquent l'arrivee et l'appareillage.
    connues = {p['date'] for p in points}
    for e in ESCALES:
        d = datetime.date.fromisoformat(e['du'])
        fin = datetime.date.fromisoformat(e['au'])
        while d <= fin:
            if d not in connues and (d.isoformat() in recits or d == fin
                                     or d == datetime.date.fromisoformat(e['du'])):
                points.append({'date': d, 'coords': [e['lon'], e['lat']],
                               'volume': '-', 'escale': e,
                               'navire': navire_du_jour(d)})
                connues.add(d)
            d += datetime.timedelta(days=1)

    points.sort(key=lambda x: x['date'])
    # Une position qui demanderait une vitesse impossible n'est pas celle du
    # navire : c'est une terre citée, ou un chiffre mal lu.
    gardes = []
    for p in points:
        if (gardes and not p.get('escale') and not p.get('dite')
                and not p.get('detour')
                and gardes[-1]['navire'] == p['navire']):
            v = km(gardes[-1]['coords'], p['coords'])
            j = max(1, (p['date'] - gardes[-1]['date']).days)
            if v / j > KM_JOUR_MAX:
                refuses += 1
                continue
        gardes.append(p)

    print('positions retenues : %d' % len(gardes))
    print('  écartées, tombant à terre     : %d' % aterre)
    print('  écartées, vitesse impossible  : %d' % refuses)
    print('  journées hors campagne (retour du naufrage) : %d' % hors)
    from collections import Counter
    for nom, n in Counter(p['navire'] for p in gardes).items():
        print('  %-16s : %d' % (nom, n))
    print('récits de journée : %d  (%d caractères)'
          % (len(recits), sum(len(x) for x in recits.values())))
    avec = sum(1 for p in gardes if p['date'].isoformat() in recits)
    print('  positions accompagnées de leur récit : %d / %d' % (avec, len(gardes)))
    if gardes:
        print('  du %s au %s' % (gardes[0]['date'], gardes[-1]['date']))

    if '--ecrire' in sys.argv:
        gj = {"type": "FeatureCollection", "features": [
            {"type": "Feature",
             "geometry": {"type": "Point", "coordinates": p['coords']},
             "properties": proprietes(p)} for p in gardes]}
        json.dump(gj, io.open(SORTIE, 'w', encoding='utf-8'), ensure_ascii=False)
        print('\n-> %s' % os.path.relpath(SORTIE, RACINE))
        os.makedirs(os.path.dirname(JOURNAL), exist_ok=True)
        json.dump({d: {'journal_flinders': t} for d, t in sorted(recits.items())},
                  io.open(JOURNAL, 'w', encoding='utf-8'), ensure_ascii=False)
        print('-> %s' % os.path.relpath(JOURNAL, RACINE))
        print('\nLe parcours ne contient que le récit. Pour y remettre les '
              'quarante-deux\npositions lues sur la carte de 1814, enchaîner '
              'maintenant :\n'
              '    python3 scripts/integre_carte_flinders.py --ecrire')
    else:
        print('\n(simulation — relancer avec --ecrire)')


if __name__ == '__main__':
    main()
