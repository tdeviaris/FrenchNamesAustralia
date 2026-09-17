#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extraction du journal de François-Désiré Breton (baudin.sydney.edu.au).

Deux volumes dans un seul manuscrit :
  vol. 1  16 sept. 1800 -> 29 oct. 1801 : à bord du Géographe
  vol. 2  31 oct.  1801 -> 26 mai  1803 : à bord du Naturaliste

Usage : python3 scripts/journal_breton.py <breton.txt> [--ecrire]
"""
import json, re, sys, unicodedata

MOIS = {'janvier':1,'février':2,'mars':3,'avril':4,'mai':5,'juin':6,
        'juillet':7,'août':8,'septembre':9,'octobre':10,'novembre':11,'décembre':12}

BASCULE_NATURALISTE = '1801-10-31'          # Breton passe sur le Naturaliste

# Coquilles de la transcription : le quantième républicain et la date grégorienne
# donnée entre crochets ne concordent pas. On tranche d'après la suite des
# en-têtes voisins, qui ne laisse pas de doute.
CORRECTIONS = {
    # « Le 5 [brumaire, 26 octobre 1800] » : 5 brumaire an 9 = 27 octobre, et
    # l'en-tête suivant est « Le 6 [brumaire, 28 octobre 1800] ».
    ('Le 5', '1800-10-26'): '1800-10-27',
}

# En-tête couvrant plusieurs journées : « Le 9, 10, 11 & 12 [fructidor, 27, 28,
# 29 et 30 août 1802] ». On rattache le bloc à sa première date.
PREMIER_JOUR = re.compile(
    r'(\d{1,2})(?:\s*(?:,|&|et)\s*\d{1,2})+\s+('
    + '|'.join(MOIS) + r')\s+(\d{4})')
# « an 9 », « an X » : le millésime républicain ne doit pas être pris pour un jour
ANNEE_REP = re.compile(r'\ban\s+[IVXLC\d]+\s*(?:e|er)?\s*,?', re.I)

# en-tête d'entrée en début de ligne, avec sa date grégorienne entre crochets
ENTETE = re.compile(
    r'(?m)^[ \t]*(Le \d{1,2}|Le|Les|Du|Suite du)\b([^\n\[]{0,60})'
    r'\[([^\]]{0,80}?(\d{1,2})\s*(?:er)?\s+('
    + '|'.join(MOIS) + r')\s+(\d{4}))\s*\]')


def nettoie(texte):
    """Retire l'appareil de page : sauts de page, folios, notes marginales."""
    t = texte.replace(' ', ' ')

    # bloc de notes de bas de page : longue suite d'espaces puis « * [En marge…] »
    t = re.sub(r'\n[ \t]{20,}\n(?:[*#][^\n]*\n)+', '\n', t)
    t = re.sub(r'(?m)^[*#]\s*\[En marge[^\]]*\][^\n]*$', '', t)

    # saut de page suivi du numéro de page du PDF, éventuellement du folio [n] :
    # la coupure peut tomber en plein mot, on recolle avec une simple espace
    t = re.sub(r'\x0c\s*\n?\s*\d{1,3}\s*\n(?:\s*\n)?(?:\s*\[\d+\]\s*\n(?:\s*\n)?)?', ' ', t)
    t = re.sub(r'\x0c', ' ', t)

    # folios isolés et numéros de page résiduels en ligne seule
    t = re.sub(r'(?m)^\s*\[\d+\]\s*$', '', t)
    t = re.sub(r'\[{1,2}\d{1,3}\]', ' ', t)
    t = re.sub(r'(?m)^\s*\d{1,3}\s*$', '', t)

    # mentions éditoriales d'état du manuscrit
    t = re.sub(r'\[page (?:de garde|blanche)\]', '', t)
    return t


def decoupe(texte):
    """Rend [(date, corps, position)] en recollant les en-têtes « Suite du »."""
    coupes = list(ENTETE.finditer(texte))
    brut = []
    for i, m in enumerate(coupes):
        fin = coupes[i + 1].start() if i + 1 < len(coupes) else len(texte)
        jour, mois, annee = int(m.group(4)), MOIS[m.group(5)], int(m.group(6))
        liste = PREMIER_JOUR.search(ANNEE_REP.sub(' ', m.group(3)))
        if liste:                            # en-tête couvrant plusieurs jours
            jour, mois, annee = int(liste.group(1)), MOIS[liste.group(2)], int(liste.group(3))
        d = '%04d-%02d-%02d' % (annee, mois, jour)
        d = CORRECTIONS.get((m.group(1).strip(), d), d)
        corps = texte[m.end():fin]
        corps = corps.lstrip(' .:;-–—\t\n')
        brut.append((d, corps, m.start(), m.group(1)))

    fusion = {}
    ordre = []
    for d, corps, pos, mot in brut:
        if d in fusion:                      # « Suite du … » ou journée reprise
            fusion[d] = fusion[d].rstrip() + ' ' + corps.lstrip()
        else:
            fusion[d] = corps
            ordre.append(d)
    return [(d, fusion[d]) for d in ordre]


ANNEXES = (
    re.compile(r'\s*Noms,\s*qualités,\s*Epoques.*$', re.S),
    re.compile(r'\s*Journal\s+de Breton Aspirant.*$', re.S),
)


def detache_annexes(corps):
    """Sépare le corps de journée des annexes de fin de volume."""
    reste = []
    for motif in ANNEXES:
        m = motif.search(corps)
        if m:
            reste.append(corps[m.start():].strip())
            corps = corps[:m.start()]
    return corps, reste


def normalise(corps):
    c = re.sub(r'[ \t]+', ' ', corps)
    c = re.sub(r'\s*\n\s*', ' ', c)
    c = re.sub(r' {2,}', ' ', c)
    return c.strip(' .:;\n')


def navire(date):
    return 'N' if date >= BASCULE_NATURALISTE else 'G'


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    source = sys.argv[1]
    texte = nettoie(open(source, encoding='utf-8').read())

    entrees, annexes = {}, {}
    for d, corps in decoupe(texte):
        corps, reste = detache_annexes(corps)
        if reste:
            annexes[d] = [normalise(x) for x in reste]
        c = normalise(corps)
        if len(c) >= 25:                     # écarte les en-têtes de volume nus
            entrees[d] = c

    print('journées extraites : %d' % len(entrees))
    print('  %s -> %s' % (min(entrees), max(entrees)))
    g = [d for d in entrees if navire(d) == 'G']
    n = [d for d in entrees if navire(d) == 'N']
    print('  Géographe   : %d' % len(g))
    print('  Naturaliste : %d' % len(n))
    print('caractères : %d' % sum(len(v) for v in entrees.values()))
    for d, xs in annexes.items():
        print('annexe détachée au %s : %d bloc(s), %d car.'
              % (d, len(xs), sum(len(x) for x in xs)))

    if '--ecrire' in sys.argv:
        with open('data/journal_breton.json', 'w', encoding='utf-8') as f:
            json.dump(entrees, f, ensure_ascii=False, indent=1, sort_keys=True)
        print('écrit : data/journal_breton.json')
        with open('data/journal_breton_annexes.json', 'w', encoding='utf-8') as f:
            json.dump(annexes, f, ensure_ascii=False, indent=1, sort_keys=True)
        print('écrit : data/journal_breton_annexes.json')


if __name__ == '__main__':
    main()
