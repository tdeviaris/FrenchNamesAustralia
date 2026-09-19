#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tire de la nomenclature de Dany Breelle les noms donnés par Flinders.

Source : « Flinders nomenclature.xls », feuille Sheet2, où Dany a rassemblé les
lieux qu'a nommés Matthew Flinders, avec pour chacun le passage du récit publié
qui explique le nom, la catégorie du choix, la journée du voyage, et le
bâtiment qu'il montait alors.

Trois particularités du classeur :

  - Des lignes sans État coupent la liste en sections géographiques (« Western
    Australia », « Spencer Gulf »…) : ce ne sont pas des toponymes.
  - Les coordonnées y sont écrites de sept façons, sexagésimales pour la
    plupart, parfois décimales, avec des degrés ° ou º et des minutes ' ou ′.
  - Le nom porte parfois sa propre glose : « Twin Peaks now North Twin Peak ».
    On sépare alors le nom que Flinders a donné de celui que porte la carte
    d'aujourd'hui.

Tous ces noms sont anglais : ce sont ceux d'un navigateur anglais. La fiche les
annonce donc autrement que les toponymes français des deux autres expéditions.

Usage : python3 scripts/toponymes_flinders.py <classeur.xls> [--ecrire]
"""
import datetime
import io
import json
import os
import re
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SORTIE = os.path.join(RACINE, 'data', 'flinders.json')
# Les citations traduites, une par fichier, nommees comme le code du lieu.
# Sans elles la fiche francaise porte la citation anglaise, introduite en
# francais : lisible, mais en deux langues.
CITATIONS_FR = os.path.join(RACINE, 'data', 'flinders_citations_fr.json')
FEUILLE = 'Sheet2'
PREMIERE = 2                       # les deux premières lignes sont des titres

# Les colonnes, dans l'ordre où le classeur les donne.
NOM, ETAT, NAVIRE, ORIGINE = 0, 1, 2, 3
CATEGORIE, SOUS_CATEGORIE, CLASSE = 4, 5, 6
LAT, LON, COMMENTAIRE, PLANCHE, DATE = 7, 8, 9, 10, 11

# Le classeur abrège, et pas toujours de la même façon : « Norfolk 1798 » et
# « Norfolk1799 » sont le même sloop, deux campagnes. On garde la campagne,
# qui date le nom, mais on écrit la coque en toutes lettres.
# Chaque entrée porte la coque — elle sert à regrouper les noms — puis la
# campagne, en français et en anglais. On dit la campagne et non « à bord de » :
# Flinders ne montait pas la baleinière, que George Bass mena seul, mais les
# deux noms qui en viennent lui sont attribués par la nomenclature.
NAVIRES = {
    'invest': ("l'Investigator",
               "lors de la campagne de levé de l'Investigator (1801-1803)",
               "during the Investigator's survey voyage (1801-1803)"),
    'norfolk 1798': ('le Norfolk',
                     'lors de la circumnavigation de la Terre de Van Diemen, '
                     'sur le sloop Norfolk (1798-1799)',
                     "during the Norfolk's circumnavigation of Van Diemen's "
                     'Land (1798-1799)'),
    'norfolk1799': ('le Norfolk',
                    'lors de la campagne du Norfolk sur la côte du '
                    'Queensland (1799)',
                    "during the Norfolk's voyage along the Queensland "
                    'coast (1799)'),
    'norfolk1800': ('le Norfolk',
                    'lors de la campagne du Norfolk de 1800',
                    "during the Norfolk's voyage of 1800"),
    'francis 1798': ('le Francis',
                     'lors de la campagne du Francis aux îles Furneaux (1798)',
                     "during the Francis's voyage to the Furneaux "
                     'Islands (1798)'),
    'tom thumb 1796': ('le Tom Thumb',
                       'lors des reconnaissances côtières du Tom Thumb, avec '
                       'George Bass (1796)',
                       'during the Tom Thumb coastal surveys with George '
                       'Bass (1796)'),
    "bass'whaleboat 1798": ('la baleinière de Bass',
                            "lors de l'expédition de George Bass en "
                            'baleinière (1798)',
                            "during George Bass's whaleboat expedition (1798)"),
}
NAVIRES['francis1798'] = NAVIRES['francis 1798']
DEFAUT = NAVIRES['invest']

ETATS = {'WA': 'WA', 'SA': 'SA', 'VIC': 'VIC', 'TAS': 'Tas',
         'NSW': 'NSW', 'QLD': 'QLD', 'NT': 'NT'}

MOIS = {m: i + 1 for i, m in enumerate(
    'JANUARY FEBRUARY MARCH APRIL MAY JUNE JULY AUGUST SEPTEMBER OCTOBER '
    'NOVEMBER DECEMBER'.split())}
JOUR_DATE = re.compile(r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})')

# « -34º 22' 36'' S », « 22° 40′ 07″ S », « 135° 55'14" E », « -37°57'S »
SEXA = re.compile(r"""(-?\d{1,3})\s*[°º]\s*
                      (\d{1,2})\s*['′]\s*
                      (?:(\d{1,2}(?:\.\d+)?)\s*(?:''|["″]))?\s*
                      ([NSEWnsew])?""", re.X)
DECIMALE = re.compile(r'Decimal\s*Degrees?\s*(-?\d{1,3}(?:\.\d+)?)', re.I)
# « Twin Peaks now North Twin Peak », « Cape Bauer (now Cape Bauer) »
DEVENU = re.compile(r'\s*\bnow(?:adays)?\b\s*', re.I)


def texte(cellule):
    return re.sub(r'\s+', ' ', str(cellule)).strip()


def coordonnee(brut, axe):
    """Une longitude ou une latitude, quelle que soit la façon de l'écrire.

    `axe` vaut 'lat' ou 'lon' : il donne l'hémisphère quand la cellule ne le
    dit pas. Le classeur est entièrement austral et oriental, mais il note le
    sud tantôt par un signe, tantôt par la lettre S, tantôt par les deux.
    """
    brut = texte(brut)
    if not brut:
        return None
    d = DECIMALE.search(brut)
    if d:
        v = float(d.group(1))
    else:
        m = SEXA.search(brut)
        if not m:
            return None
        deg, mi, sec, lettre = m.group(1), m.group(2), m.group(3), m.group(4)
        v = abs(float(deg)) + float(mi) / 60.0 + float(sec or 0) / 3600.0
        negatif = deg.startswith('-') or (lettre or '').upper() in ('S', 'W')
        v = -v if negatif else v
    # Le classeur ne sort pas d'Australie ni de ses récifs : une latitude y est
    # négative, une longitude positive. Un signe manquant se rattrape ainsi sans
    # risque, et ce qui tombe hors de la fenêtre est une cellule fautive — la
    # longitude de Sleaford Bay, par exemple, recopie sa latitude.
    # La borne orientale laisse passer Wreck Reefs, par 155° 20'.
    if axe == 'lat':
        v = -abs(v)
        return v if -45 <= v <= -8 else None
    v = abs(v)
    return v if 110 <= v <= 160 else None


def date_iso(brut):
    """« MONDAY 7 DECEMBER 1801 » ou « 9 November 1798 » -> 1801-12-07."""
    m = JOUR_DATE.search(texte(brut))
    if not m:
        return ''
    mois = MOIS.get(m.group(2).upper())
    if not mois:
        return ''
    try:
        return datetime.date(int(m.group(3)), mois, int(m.group(1))).isoformat()
    except ValueError:
        return ''


def noms(brut):
    """Le nom donné par Flinders, et celui que porte la carte aujourd'hui.

    La cellule mêle les deux quand ils diffèrent, et laisse parfois un doute
    entre parenthèses : « Point Rapid? (where???) ». On retient la question
    sans la trancher.
    """
    t = texte(brut)
    doute = '?' in t
    t = re.sub(r'\((?:nowadays|where)\?*\)', '', t, flags=re.I)
    parts = DEVENU.split(t, maxsplit=1)
    propre = lambda s: s.strip().strip('()').strip(' .,;?').strip()
    donne = propre(parts[0])
    actuel = propre(parts[1]) if len(parts) > 1 else ''
    return donne, actuel, doute


def fiche(actuel, ligne, nav, date, langue, citation_fr=None):
    """Le texte de la fiche : ce que Flinders en a écrit, et quand."""
    coque, campagne_fr, campagne_en = nav
    citation = texte(ligne[ORIGINE]).strip('"“” ')
    if langue == 'fr' and citation_fr:
        citation = citation_fr
    quand = ''
    if date:
        j = datetime.date.fromisoformat(date)
        if langue == 'fr':
            MOIS_FR = ('janvier février mars avril mai juin juillet août '
                       'septembre octobre novembre décembre').split()
            quand = ' le %d %s %d' % (j.day, MOIS_FR[j.month - 1], j.year)
        else:
            quand = j.strftime(' on %d %B %Y').replace(' 0', ' ')
    if langue == 'fr':
        tete = ('Nom donné par Matthew Flinders%s, %s.'
                % (quand, campagne_fr))
        if actuel:
            tete += ' La carte d’aujourd’hui porte « %s ».' % actuel
        if citation:
            tete += (' Flinders écrit, dans « A Voyage to Terra Australis » '
                     '(Londres, 1814) : « %s »' % citation)
    else:
        tete = 'Named by Matthew Flinders%s, %s.' % (quand, campagne_en)
        if actuel:
            tete += ' Today’s charts give “%s”.' % actuel
        if citation:
            tete += (' Flinders writes, in “A Voyage to Terra Australis” '
                     '(London, 1814): “%s”' % citation)
    return tete


def citations_francaises():
    if not os.path.exists(CITATIONS_FR):
        return {}
    return json.load(io.open(CITATIONS_FR, encoding='utf-8'))


def main():
    import xlrd
    classeur = sys.argv[1]
    s = xlrd.open_workbook(classeur).sheet_by_name(FEUILLE)

    fr = citations_francaises()
    lieux, sections, sans_coord, sans_date, inconnus = [], [], [], [], set()
    section = ''
    for r in range(PREMIERE, s.nrows):
        ligne = [texte(s.cell_value(r, c)) for c in range(13)]
        if not ligne[NOM]:
            continue
        if not ligne[ETAT]:
            section = ligne[NOM]           # intitulé de section, pas un lieu
            sections.append(ligne[NOM])
            continue

        donne, actuel, doute = noms(ligne[NOM])
        cle = ligne[NAVIRE].lower().strip()
        nav = NAVIRES.get(cle, DEFAUT)
        navire, campagne = nav[0], nav[1]
        if cle and cle not in NAVIRES:
            inconnus.add(ligne[NAVIRE])
        lat = coordonnee(ligne[LAT], 'lat')
        lon = coordonnee(ligne[LON], 'lon')
        date = date_iso(ligne[DATE])
        if lat is None or lon is None:
            # La carte exige les deux : une latitude seule ne place rien.
            sans_coord.append('%s (%s)' % (donne, 'longitude' if lon is None
                                           else 'latitude'))
        if not date:
            sans_date.append(donne)

        lieux.append({
            'code': 'Flinders%03d' % (len(lieux) + 1),
            'expedition': 'Flinders',
            'state': ETATS.get(ligne[ETAT].upper(), ligne[ETAT]),
            'frenchName': donne,
            'variantName': '',
            'ausEName': actuel or donne,
            'indigenousName': '',
            'indigenousLanguage': '',
            'lat': lat,
            'lon': lon,
            'characteristic': fiche(actuel, ligne, nav, date, 'en'),
            'characteristic_fr': fiche(actuel, ligne, nav, date, 'fr',
                                       fr.get('Flinders%03d' % (len(lieux) + 1))),
            'history': '',
            'history_fr': '',
            'detailsLink': '',
            'detailsLink_en': '',
            'imgUrl': '',
            'mapUrl': '',
            'mapTitle_fr': '',
            'mapTitle_en': '',
            'origin_fr': '',
            'other_link': '',
            'wiki_fr': '',
            'wiki_en': '',
            # Propres à Flinders : ils servent à relier le nom à la route.
            'navire': navire,
            'campagne': campagne,
            'date': date,
            'secteur': section,
            'categorie': ligne[CATEGORIE],
            'sousCategorie': ligne[SOUS_CATEGORIE],
            'classe': ligne[CLASSE],
            'planche': ligne[PLANCHE],
            'commentaire': ligne[COMMENTAIRE],
            'incertain': doute,
        })

    import collections
    print('citations traduites  : %d / %d'
          % (sum(1 for l in lieux
                 if 'Flinders écrit, dans' in l['characteristic_fr']
                 and fr.get(l['code'])), len(fr)))
    print('sections traversées : %d' % len(sections))
    print('toponymes           : %d' % len(lieux))
    print('  sans coordonnées  : %d  %s'
          % (len(sans_coord), ', '.join(sans_coord[:4]) + ('…' if len(sans_coord) > 4 else '')))
    print('  plaçables         : %d'
          % sum(1 for l in lieux if l['lat'] is not None and l['lon'] is not None))
    print('  sans date         : %d' % len(sans_date))
    print('  nom douteux       : %d' % sum(1 for l in lieux if l['incertain']))
    print('  renommés depuis   : %d'
          % sum(1 for l in lieux if l['ausEName'] != l['frenchName']))
    if inconnus:
        print('  bâtiments non reconnus : %s' % sorted(inconnus))
    print('par bâtiment : %s'
          % dict(collections.Counter(l['navire'] for l in lieux)))
    print('par État     : %s'
          % dict(collections.Counter(l['state'] for l in lieux)))
    dates = sorted(l['date'] for l in lieux if l['date'])
    print('dates        : %s -> %s' % (dates[0], dates[-1]))

    if '--ecrire' in sys.argv:
        json.dump(lieux, io.open(SORTIE, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        print('\n-> %s' % os.path.relpath(SORTIE, RACINE))
    else:
        print('\n(simulation — relancer avec --ecrire)')


if __name__ == '__main__':
    main()
