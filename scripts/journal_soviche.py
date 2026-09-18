#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Découpe par journée la transcription du journal autographe de Baudin.

Le document est l'œuvre de Marc Soviche, capitaine de la marine marchande,
qui a transcrit le journal de mer autographe de Nicolas Baudin d'après les
originaux des Archives nationales — Marine 5JJ/36 à 5JJ/40, cinq volumes,
du départ du Havre le 26 vendémiaire an 9 au 17 thermidor an 11.

C'est une édition, non une copie : elle porte les renvois de feuillet, restitue
les notes marginales, signale chaque page laissée vierge par Baudin, et donne
la date grégorienne à côté de la républicaine. Ce sont ces dates entre
parenthèses qui permettent de rattacher chaque journée au parcours.

La journée de mer court de midi à midi. Un en-tête « Du 7 au 8 Ventôse
(du 26 au 27 février 1801) » est donc rattaché au 27 février, jour où elle
s'achève — c'est la convention suivie par le reste du projet.

Usage : python3 scripts/journal_soviche.py <fichier.docx> [--ecrire]
"""
import datetime, io, json, os, re, sys, zipfile
from xml.etree import ElementTree as ET

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SORTIE = os.path.join(RACINE, 'data', 'journaux', 'baudin_fr.json')
CHAMP = 'journal_baudin_autographe'
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

MOIS_GREG = {m: i + 1 for i, m in enumerate(
    'janvier février mars avril mai juin juillet août septembre octobre '
    'novembre décembre'.split())}
MOIS_REP = ('vendémiaire|brumaire|frimaire|nivôse|pluviôse|ventôse|germinal|'
            'floréal|prairial|messidor|thermidor|fructidor')

# « (du 26 au 27 février 1801) », « (9 avril 1801) », « (17 novembre 1802) »
DATE_GREG = re.compile(
    r'\(\s*(?:du\s+(\d{1,2})\s+(?:([a-zûéô]+)\s+)?au\s+)?'
    r'(\d{1,2})(?:er)?\s+([a-zûéô]+)\s+(\d{4})\s*\)', re.I)
# une ligne d'en-tête nomme un mois républicain et une année
ENTETE_REP = re.compile(r'\b(' + MOIS_REP + r')\b', re.I)
ANNEE_REP = re.compile(r'\ban\s*(\d{1,2})', re.I)
# apparat de l'éditeur : renvois de feuillet et filets de séparation
FEUILLET = re.compile(r'\[\s*\d+\s*V\s*p\.?\s*[\d,\s àa]*\]\s*')
FILET = re.compile(r'^[_\-–—\s]{8,}$')
# une journée qui ne porte que des notes d'éditeur n'a pas de texte
VIDE = re.compile(r'^\(?\s*(vierge|blanc|table de lock[^)]*|non transcrit[^)]*|'
                  r'tableau vierge|cadre vierge|partie de cadre, vierge)\s*\)?\.?$',
                  re.I)


def paragraphes(chemin):
    """Le texte du .docx, paragraphe par paragraphe."""
    racine = ET.fromstring(zipfile.ZipFile(chemin).read('word/document.xml'))
    for p in racine.iter(W + 'p'):
        bouts = []
        for n in p.iter():
            if n.tag == W + 't':
                bouts.append(n.text or '')
            elif n.tag in (W + 'tab', W + 'br'):
                bouts.append(' ')
        yield re.sub(r'\s+', ' ', ''.join(bouts)).strip()


# Passé mars 1803, l'éditeur cesse de donner la date grégorienne entre
# parenthèses : il faut convertir la date républicaine de l'en-tête. Baudin
# écrit ses quantièmes tantôt en chiffres, tantôt en toutes lettres.
NOUVEL_AN = {9: (1800, 9, 23), 10: (1801, 9, 23),
             11: (1802, 9, 23), 12: (1803, 9, 24)}
ORDRE = ('vendémiaire brumaire frimaire nivôse pluviôse ventôse germinal '
         'floréal prairial messidor thermidor fructidor').split()
UNITES = ['', 'un', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit',
          'neuf', 'dix', 'onze', 'douze', 'treize', 'quatorze', 'quinze',
          'seize', 'dix sept', 'dix huit', 'dix neuf', 'vingt']
EN_LETTRES = {'premier': 1, 'trente': 30}
for _i in range(1, 21):
    EN_LETTRES[UNITES[_i]] = _i
for _i in range(1, 11):
    EN_LETTRES['vingt et un' if _i == 1 else 'vingt ' + UNITES[_i]] = 20 + _i
LETTRES = sorted(EN_LETTRES, key=len, reverse=True)

QUANTIEME = re.compile(
    r'\bd[uo]\s+(.{1,34}?)\s*(?:è|ème|er)?\s*\b(' + MOIS_REP + r')\b', re.I)
# « Du 30 Vendémiaire au Premier Brumaire » : la journée s'achève dans le mois
# suivant. On relève donc tous les couples quantième-mois de l'en-tête et l'on
# retient le dernier, celui où la journée de mer se termine.
COUPLE = re.compile(r'([\wéèêô]+(?:\s+(?:et\s+)?[\wéèêô]+){0,2}?)\s*'
                    r'(?:è|ème|er)?\s*\b(' + MOIS_REP + r')\b', re.I)


def quantieme(brut):
    """Le quantième d'un en-tête, en chiffres ou en toutes lettres."""
    brut = re.sub(r'\s+', ' ', brut.strip().lower())
    # « Du 27 au 28 », « Du Vingt Deux au Vingt Trois » : on garde le second
    if ' au ' in brut:
        brut = brut.split(' au ')[-1]
    brut = re.sub(r'\b(?:è|ème|er|e)\b', '', brut).strip()
    m = re.search(r'\d{1,2}', brut)
    if m:
        return int(m.group(0))
    for mot in LETTRES:
        if re.search(r'\b' + re.escape(mot) + r'\b', brut):
            return EN_LETTRES[mot]
    return None


def date_republicaine(ligne):
    """La date grégorienne déduite de l'en-tête républicain."""
    couples = COUPLE.findall(ligne)
    a = ANNEE_REP.search(ligne)
    if not couples or not a:
        return None
    if len(couples) > 1:
        brut, mois_nom = couples[-1]        # la journée finit dans ce mois-là
    else:
        m = QUANTIEME.search(ligne)
        if not m:
            return None
        brut, mois_nom = m.group(1), m.group(2)
    jour = quantieme(brut)
    an = int(a.group(1))
    if jour is None or not 1 <= jour <= 30 or an not in NOUVEL_AN:
        return None
    mois = ORDRE.index(mois_nom.lower())
    y, mo, d = NOUVEL_AN[an]
    return (datetime.date(y, mo, d)
            + datetime.timedelta(days=mois * 30 + jour - 1))


def date_de(ligne):
    """La date grégorienne que porte un en-tête, si elle y est."""
    m = DATE_GREG.search(ligne)
    if not m:
        return None
    _, _, jour, mois, an = m.groups()
    n = MOIS_GREG.get(mois.lower())
    if not n:
        return None
    try:
        return datetime.date(int(an), n, int(jour))
    except ValueError:
        return None


def est_entete(ligne):
    """Un en-tête de journée : il nomme un mois, ou porte une date en clair."""
    if not ligne or len(ligne) > 220:
        return False
    nu = FEUILLET.sub('', ligne).strip()
    if DATE_GREG.search(nu) and re.match(r'^\W{0,4}(d[uo]|départ|arrivée|second)\b',
                                         nu, re.I):
        return True
    return bool(ENTETE_REP.search(nu) and ANNEE_REP.search(nu)
                and len(nu) < 160)


def journees(chemin):
    """Les blocs de texte, un par en-tête rencontré."""
    lots, courant = [], None
    for ligne in paragraphes(chemin):
        if FILET.match(ligne):
            continue
        if est_entete(ligne):
            if courant:
                lots.append(courant)
            courant = {'entete': FEUILLET.sub('', ligne).strip(), 'corps': []}
        elif courant is not None:
            nu = FEUILLET.sub('', ligne).strip()
            if nu and not VIDE.match(nu):
                courant['corps'].append(nu)
    if courant:
        lots.append(courant)
    return lots


def main():
    chemin = sys.argv[1]
    lots = journees(chemin)
    textes, sans_date, vides = {}, 0, 0
    derniere = None
    for lot in lots:
        d = date_de(lot['entete']) or date_republicaine(lot['entete'])
        if d is None:
            sans_date += 1
            # une journée sans date en clair se rattache à la précédente :
            # l'éditeur poursuit alors le même jour sur un nouveau feuillet
            if derniere is None or not lot['corps']:
                continue
            d = derniere
        if not lot['corps']:
            vides += 1
            continue
        cle = d.isoformat()
        textes[cle] = (textes.get(cle, '') + '\n'.join(lot['corps']) + '\n')
        derniere = d

    js = sorted(textes)
    print('en-têtes repérés          : %d' % len(lots))
    print('  sans date en clair      : %d' % sans_date)
    print('  sans texte (page vierge): %d' % vides)
    print('journées retenues         : %d' % len(textes))
    print('couverture                : %s → %s' % (js[0], js[-1]))
    print('caractères                : %d'
          % sum(len(t) for t in textes.values()))

    if '--ecrire' in sys.argv:
        gros = json.load(io.open(SORTIE, encoding='utf-8'))
        for cle, texte in textes.items():
            gros.setdefault(cle, {})[CHAMP] = texte.strip()
        json.dump(gros, io.open(SORTIE, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1, sort_keys=True)
        print('\n-> %s : %d journées au total'
              % (os.path.relpath(SORTIE, RACINE), len(gros)))
    else:
        print('\n(simulation — relancer avec --ecrire)')


if __name__ == '__main__':
    main()
