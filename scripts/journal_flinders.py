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
    ('le Cumberland',  '1803-09-21', '1803-12-17'),
]


def navire_du_jour(d):
    """Le bâtiment que Flinders monte ce jour-là, ou None."""
    for nom, du, au in NAVIRES:
        if datetime.date.fromisoformat(du) <= d <= datetime.date.fromisoformat(au):
            return nom
    return None

# Les quatre escales de Port Jackson portent la position de l'ENTREE du port,
# 151° 16' E, et non celle de Sydney Cove ou le navire mouillait reellement :
# le trait de cote employe par la carte, au 1/10 000 000, ne resout pas le
# port, et Sydney Cove y tombe en pleine terre. Toute route partant de la
# traversait alors la presqu'ile. L'ecart est de onze kilometres, et la fiche
# nomme le mouillage.
#
# Au mouillage, Flinders cesse de donner sa position : elle ne change pas. Sans
# ces escales le trace saute d'un bout a l'autre du continent, et il manquait
# tout Port Jackson -- ou l'Investigator passa dix semaines, en meme temps que
# Baudin. Les dates viennent du recit lui-meme.
ESCALES = [
    {'du': '1801-07-18', 'au': '1801-07-18',
     'lon': -1.100, 'lat': 50.750,
     'lieu': "Spithead, appareillage de l'Investigator",
     'appui': "« On July 18 we sailed from Spithead » ; les vivres étaient "
              "venus à bord la veille au matin, « when the ship was "
              "unmoored »"},
    {'du': '1801-12-09', 'au': '1802-01-04',
     'lon': 117.95, 'lat': -35.05,
     'lieu': "King George's Sound",
     'appui': "le 10 décembre « we got the ship under way to beat up to the "
              "entrance » ; le 30, « the ship unmoored » ; le 3 janvier on "
              "prend congé des habitants"},
    {'du': '1802-05-09', 'au': '1802-07-22',
     'lon': 151.286, 'lat': -33.851,
     'lieu': "Port Jackson, mouillage de Sydney Cove",
     'appui': "le 9 mai « the Investigator was anchored in Sydney Cove » ; "
              "le 22 juillet « we sailed out of Port Jackson »"},
    {'du': '1803-06-09', 'au': '1803-06-09',
     'lon': 151.286, 'lat': -33.851,
     'lieu': 'Port Jackson, retour de la circumnavigation',
     'appui': "fin de la campagne de l'Investigator, condamné à son retour"},
    {'du': '1803-08-10', 'au': '1803-08-10',
     'lon': 151.286, 'lat': -33.851,
     'lieu': 'Port Jackson, appareillage du Porpoise',
     'appui': "le 10 août « we sailed out of Port Jackson together, at eleven "
              "o'clock of the same morning, and steered north-eastward for "
              "Torres' Strait »"},
    {'du': '1803-09-21', 'au': '1803-09-21',
     'lon': 151.286, 'lat': -33.851,
     'lieu': 'Port Jackson, appareillage de la Cumberland',
     'appui': "le 21 septembre « I sailed out of the harbour in the Cumberland "
              "at daylight, with the Rolla and Francis in company »"},
    {'du': '1803-12-16', 'au': '1803-12-16',
     'lon': 57.38, 'lat': -20.52,
     'lieu': "Baie du Cap, à l'Île de France",
     'appui': "le 15 décembre la terre est vue au point du jour et la goélette "
              "mouille dans la baie ; le 16, le commandant retient la "
              "Cumberland et Flinders dîne chez le major Dunienville"},
    {'du': '1803-12-17', 'au': '1803-12-17',
     'lon': 57.48, 'lat': -20.15,
     'lieu': 'Port Louis, terme du voyage',
     'appui': "« PORT LOUIS. SATURDAY 17 DECEMBER 1803 » : la Cumberland "
              "mouille dans la rade, et Flinders y sera retenu six ans et "
              "demi. C'est la dernière position de la campagne"},
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
    # --- 20 septembre 2026 : depouillement elargi -------------------------
    # Le motif ANCRE ci-dessus n'accepte qu'une poignee de tournures. Le recit
    # en emploie d'autres, tout aussi fermes : « at noon, the latitude was »,
    # « our observations gave », « the anchor was dropped in latitude ». Une
    # relecture a ramasse TOUTE phrase portant un couple latitude/longitude,
    # ecarte celles qui designent un amer, soumis le reste au trait de cote et
    # a la vitesse, puis relu chaque survivante a la main : le recit n'est pas
    # une table, et aucune regle ne remplace la lecture.
    # Deux dates ont du etre rectifiees -- « until the 23rd » dans le bloc du
    # 15 aout, « at noon next day » dans celui du 7 septembre. Un cas a du etre
    # tranche par le voisinage : le recit donne parfois la longitude sans dire
    # l'hemisphere, et le supposer « est » versait l'Atlantique dans l'ocean
    # Indien.
    # Ecartes a la relecture : les positions d'amers (Bald Head, Duyfhen Point,
    # la tete du Grand Golfe Australien, Cato's Bank), le mouillage de Memory
    # Cove et le releve du 8 janvier 1802, tous deux tombant a terre sur le
    # trait au 1/10 000 000, et le 30 juillet 1801, dont le « 30° 5' north »
    # contredit Porto Santo vu au ouest-nord-ouest le meme apres-midi.
    {'date': '1801-08-23', 'lon': -23.0, 'lat': 11.0, 'volume': '1',
     'appui': "« These variable winds […] continued until the 23rd, in "
               "latitude 11° north and longitude 23° west ». La journée n'a "
               "pas d'en-tête propre dans le récit : la date est celle que la "
               "phrase désigne"},
    {'date': '1801-08-27', 'lon': -17.5, 'lat': 6.0, 'volume': '1',
     'appui': "« On the 27th, in latitude 6° north and longitude 17½° west, a "
               "noddy was caught »"},
    {'date': '1801-09-02', 'lon': -11.25, 'lat': 3.8333, 'volume': '1',
     'appui': "« this could not be done with any advantage until the 2nd of "
               "September, when we were in latitude 3° 50' north, and "
               "longitude 11¼° west »"},
    {'date': '1801-09-08', 'lon': -17.1167, 'lat': -0.2833, 'volume': '1',
     'appui': "« At noon next day, the latitude was 0° 17' south, and "
               "longitude 17° 7' west ; so that the line had been crossed in "
               "nearly 17° ». Passage de l'équateur, vers sept heures du matin"},
    {'date': '1801-09-09', 'lon': -18.5833, 'lat': -0.7167, 'volume': '1',
     'appui': "« On the 9th, the latitude was 0° 43' south, and longitude 18° "
               "35' ». Le récit ne dit pas l'hémisphère de la longitude ; les "
               "positions de la veille et du lendemain, toutes deux à l'ouest, "
               "ne laissent pas de doute"},
    {'date': '1801-09-10', 'lon': -20.0833, 'lat': -0.3667, 'volume': '1',
     'appui': "« Next day at noon, our situation was in 0° 22' south and 20° "
               "5' west ». Flinders abandonne ce jour-là la recherche de l'île "
               "Saint-Paul et fait route vers le cap de Bonne-Espérance"},
    {'date': '1801-09-13', 'lon': -23.2833, 'lat': -4.7333, 'volume': '1',
     'appui': "« On the 13th, in latitude 4° 44' south and longitude 23° 17' "
               "west, a swallow, a gannet, and two sheerwaters were seen »"},
    {'date': '1801-09-30', 'lon': -22.7667, 'lat': -30.6833, 'volume': '1',
     'appui': "« On the following noon, the observed latitude was 30° 41' and "
               "longitude 22° 46' ». Ni l'hémisphère de la latitude ni celui "
               "de la longitude ne sont dits : la recherche du Saxemberg, "
               "entre les positions du 29 septembre et du 1er octobre, les "
               "fixe au sud et à l'ouest"},
    {'date': '1801-10-01', 'lon': -20.4667, 'lat': -30.5667, 'volume': '1',
     'appui': "« Next day, our observations gave 30° 34' south, and 20° 28' "
               "west ». Flinders court à l'est sur le parallèle du Saxemberg, "
               "île portée aux cartes qu'il établit ce jour-là ne pas exister"},
    {'date': '1801-11-12', 'lon': 38.3833, 'lat': -36.6, 'volume': '1',
     'appui': "« The latitude of our situation was 36° 36' south, and "
               "longitude 38° 23' east »"},
    {'date': '1802-03-11', 'lon': 137.8322, 'lat': -32.7447, 'volume': '1',
     'appui': "« The observations taken by lieutenant Flinders fixed the "
               "position of the ship in latitude 32° 44' 41\" south, and "
               "longitude by the time keepers 137° 49' 56\" east ». C'est le "
               "point le plus avancé dans le golfe Spencer"},
    {'date': '1802-10-07', 'lon': 150.8, 'lat': -20.9667, 'volume': '2',
     'appui': "« at noon, when we tacked to the northward in 20° 58' south "
               "and 150° 48' east, there were five others [récifs], distant "
               "from two to five miles ». Navigation dans le labyrinthe de la "
               "Grande Barrière"},
    {'date': '1802-10-10', 'lon': 150.9083, 'lat': -20.9417, 'volume': '2',
     'appui': "« the anchor was dropped in latitude 20° 56½' south and "
               "longitude 150° 54½' east ». Mouillage de nuit, les hauts-fonds "
               "étant indiscernables à marée haute"},
    {'date': '1802-10-23', 'lon': 149.0333, 'lat': -15.2, 'volume': '2',
     'appui': "« Next day at noon, we were in 15° 12' south, and 149° 2' east "
               "; the current had set half a knot to the N. N. W. »"},
    {'date': '1803-03-26', 'lon': 126.5, 'lat': -10.6333, 'volume': '2',
     'appui': "« until the evening of the 26th, in 10° 38' south and 126° 30' "
               "east ; in which situation they were lost » — les sondes, "
               "perdues ce soir-là. Le vent de sud-ouest pousse l'Investigator "
               "vers Timor"},
    {'date': '1803-03-28', 'lon': 125.7833, 'lat': -10.6, 'volume': '2',
     'appui': "« On the 28th, being then in 10° 36' south, and 125° 47' east, "
               "the high land of Timor was seen bearing N. »"},
    {'date': '1803-04-27', 'lon': 104.3333, 'lat': -20.55, 'volume': '2',
     'appui': "« the mean, corrected to the meridian, will be 3° 43' west, in "
               "20° 33' south and 104° 20' east longitude ». Position d'une "
               "observation de variation, sur la traversée de retour"},
    {'date': '1803-05-23', 'lon': 128.9, 'lat': -35.1667, 'volume': '2',
     'appui': "« In the afternoon of the 23rd, being in latitude 35° 10' and "
               "longitude 128° 54', the variation was observed with three "
               "compasses ». Le récit ne dit pas les hémisphères : la côte "
               "méridionale, longée ce mois-là, les fixe au sud et à l'est"},
    {'date': '1803-05-26', 'lon': 135.8, 'lat': -37.8833, 'volume': '2',
     'appui': "« On the 26th, in 37° 53' south and 135° 48' east, with the "
               "head S. E. by E., the variation was 1° 33' west ». Le jour où "
               "meurt James Greenhalgh, sergent des marines"},
    {'date': '1803-10-12', 'lon': 155.0333, 'lat': -20.7667, 'volume': '2',
     'appui': "« and at noon were in 20° 46' south and 155° 2' east ». "
               "Traversée de la Cumberland, après le naufrage de Wreck Reef"},
    {'date': '1801-07-27', 'lon': -14.300, 'lat': 38.0167, 'volume': '1',
     'appui': "comparaison des compas à l'habitacle et sur les bittons : "
              "« The head was south-west by the steering compass, our latitude "
              "was 38° 1' north, longitude 14° 18' west ». Au large du "
              "Portugal, cette position écarte la route de l'Espagne"},
    {'date': '1801-11-10', 'lon': 33.633, 'lat': -36.5, 'volume': '1',
     'appui': "traversée du Cap de Bonne-Espérance vers la Nouvelle-Hollande, "
              "cinq jours après le départ de False Bay : « During our run "
              "across the Agulhas Bank, I did not find any current setting to "
              "the westward; but in the five days taken to reach the latitude "
              "36° 30' and longitude 33° 38', the ship was set 59' to the "
              "north of the reckoning ». L'en-tête TUESDAY 10 NOVEMBER 1801 "
              "est inséré au milieu de cette phrase, après la longitude : le "
              "dépouillement automatique la manquait"},
    {'date': '1803-09-22', 'lon': 152.22, 'lat': -32.73,
     'appui': "« I anchored in a small bight under Point Stephens, in very bad "
              "plight » ; le lendemain la Cumberland rejoint la Rolla et la "
              "Francis dans Port Stephens"},
    {'date': '1803-12-15', 'lon': 57.95, 'lat': -20.55,
     'appui': "atterrage à l'Île de France : « before daylight, the land was "
              "seen » ; la goélette double l'angle sud-est de l'île le long "
              "d'un récif, puis « in steering westward along the shore » "
              "gagne Baie du Cap, où elle mouille le soir"},
    {'date': '1803-10-02', 'lon': 153.867, 'lat': -22.2,
     'appui': "« on the 2nd a.m. our corrected longitude was 153° 52' », par le "
              "travers de Wreck Reef, que la goélette cherche cinq jours durant"},
]

# Entre Point Stephens et Wreck Reef, dix jours sans une seule position : le
# trait direct couperait la Nouvelle-Galles du Sud sur trois cents kilometres.
# Ce point-ci n'est pas releve, il est CALCULE : c'est le plus proche de la
# route directe qui degage le trait de cote des deux cotes. La fiche le dit.
CONTOURNEMENTS = [
    {'date': '1802-03-11', 'lon': 137.786, 'lat': -32.978,
     'raison': "remontée de la tête du golfe Spencer. La ligne droite venue du "
                "9 mars coupait la rive est ; ce point la dégage en "
                "n'allongeant la route que de trois pour cent, quarante-deux "
                "kilomètres au lieu de quarante et un"},
    # Le depart. Les trois premiers points sortent le navire de Spithead : le
    # trait de cote au 1/10 000 000 ne separe pas l'ile de Wight du continent,
    # le Solent n'y figure pas, et la route directe traversait la terre.
    {'date': '1801-07-18', 'lon': -1.050, 'lat': 50.680,
     'raison': "sortie de Spithead par l'est de l'île de Wight. Le trait de "
               "côte employé par la carte, au 1/10 000 000, ne sépare pas "
               "l'île du continent : le Solent n'y figure pas, et toute route "
               "partant du mouillage traversait la terre. Ces deux points la "
               "contournent par où le trait laisse le passage [1/2]"},
    {'date': '1801-07-18', 'lon': -1.300, 'lat': 50.500,
     'raison': "sortie de Spithead par l'est de l'île de Wight. Le trait de "
               "côte employé par la carte, au 1/10 000 000, ne sépare pas "
               "l'île du continent : le Solent n'y figure pas, et toute route "
               "partant du mouillage traversait la terre. Ces deux points la "
               "contournent par où le trait laisse le passage [2/2]"},
    {'date': '1801-07-20', 'lon': -3.5089, 'lat': 49.9592,
     'raison': "au large du Start, d'où Flinders prend son point de départ : "
               "« our departure was taken from the Start, bearing N. 18° W. "
               "five or six leagues ». La position se déduit de ce relèvement "
               "et de cette distance — cinq lieues et demie, soit trente "
               "kilomètres au S 18° E du cap"},
    {'date': '1801-07-21', 'lon': -6.000, 'lat': 48.400,
     'raison': "au large d'Ouessant, où l'Investigator rencontre le "
               "vice-amiral Sir Andrew Mitchell et quatre vaisseaux à trois "
               "ponts de la flotte qui bloque Brest. Flinders ne donne pas sa "
               "position : seule la station de blocus est connue, au large "
               "dans l'ouest. Le point est estimé, et c'est lui qui écarte la "
               "route de la Bretagne"},
    {'date': '1801-08-01', 'lon': -16.278, 'lat': 32.434,
     'raison': "atterrage de Madère, déduit des relèvements de midi : « Porto "
               "Santo bore N. 11° W., and the rocky islands called Dezertas, "
               "from N. 65° to S. 85° W. distant three leagues ». Le point est "
               "le meilleur accord entre les trois relèvements et la "
               "distance ; il place le navire à l'est des Dezertas, d'où la "
               "route gagne Funchal par le sud sans couper Madère"},
    {'date': '1803-05-15', 'lon': 117.0, 'lat': -35.2,
     'raison': "au sud d'Albany, entre les deux relèves de la carte de 1814 — "
               "le 12 mai au sud-ouest du cap Leeuwin, le 16 mai déjà loin sur "
               "la côte méridionale. Le trait direct coupait la pointe "
               "sud-ouest du continent : Flinders doubla le cap, et ce point "
               "est le plus proche de sa route qui dégage la côte des deux "
               "côtés. Il allonge la traversée de vingt et un kilomètres sur "
               "huit cent quarante-quatre"},
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
            # Un mouillage n'est pas une position calculee : le lieu est connu
            # et date. La fiche doit le dire autrement.
            "mouillage": True,
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
                       'volume': e.get('volume', '2'),
                       'navire': navire_du_jour(d), 'dite': e})
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
