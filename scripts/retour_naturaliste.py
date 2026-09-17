#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reconstruit la route du Naturaliste entre Port Jackson et la Manche.

Les tables de Freycinet s'arrêtent au 20 novembre 1802 ; le parcours n'a donc
aucune position pour le retour. Les deux journaux du bord, eux, donnent la
latitude et la longitude presque chaque jour.

Difficulté : ni l'hémisphère ni le sens de la longitude ne sont écrits, et les
longitudes sont comptées du méridien de Paris. Un choix glouton, au plus près
du point précédent, échoue au passage de la Ligne : rester dans l'hémisphère
sud est toujours localement plus court que de le franchir. On résout donc les
signes globalement, par programmation dynamique entre deux points d'ancrage
connus — Port Jackson au départ, les approches de la Manche à l'arrivée — en
minimisant la longueur totale de la route.

Usage : python3 scripts/retour_naturaliste.py [--ecrire]
"""
import datetime, json, math, re, sys

PARIS = 2.3372                 # longitude du méridien de Paris
DEPART = '1802-11-20'
PORT_JACKSON = (151.1461, -33.8667)
KM_JOUR_MAX = 420.0            # au-delà, la route journalière est invraisemblable

# Entre le 31 janvier et le 11 février le journal ne donne aucune position :
# c'est la relâche à l'île de France. Le trait droit couperait l'île de France
# puis l'île Bourbon. Le relevé du 11 février précise « nous avons contourné
# lisle Bourbon par le nord qui nous à occasionné du calme » : on pose donc
# deux points de contournement par le nord, seuls conformes à la source.
CONTOURNEMENTS = [
    {'date': '1803-02-04', 'lon': 57.55, 'lat': -19.92, 'source': 'anonyme',
     'extrapole': True, 'motif': 'relâche à l’île de France, contournement par le nord'},
    {'date': '1803-02-09', 'lon': 55.40, 'lat': -20.55, 'source': 'anonyme',
     'extrapole': True, 'motif': 'contournement de l’île Bourbon par le nord, '
                                 'indiqué par le journal au 11 février 1803'},
]

D = r'(\d{1,3})\s*[º°]\s*(\d{1,2})?\s*[\'’]?\s*(\d{1,2})?\s*["”]?'
BIFFE = r'(?:\[[^\]]{0,15}\]\s*)?'
LAT = re.compile(r'Lat[e]?\.?\s*(?:obs\w*|est\w*|id)?\.?\s*' + BIFFE + D, re.I)
LON = re.compile(r'Long[e]?\.?\s*(?:obs\w*|est[ée]?\w*|id)?\.?\s*' + BIFFE + D, re.I)
# Tournures isolées : « Longe et late daprès le relevement. 21º 8 longe. 52º 35' »
LAT_LARGE = re.compile(r'\blat[e]?\b[^0-9]{0,40}' + D, re.I)
LON_LARGE = re.compile(r'\blong[e]?\b[^0-9]{0,40}' + D, re.I)
# Breton écrit « par 24°44'4'' latitude observée / et par 109°26'8'' long N 27 »
LAT_B = re.compile(r'par\s+' + D + r'\s*(?:de\s+)?lat', re.I)
LON_B = re.compile(r'par\s+' + D + r'[^.]{0,14}?long', re.I)


def sexa(m):
    return int(m.group(1)) + int(m.group(2) or 0) / 60 + int(m.group(3) or 0) / 3600


def lit(texte, principal, secours):
    m = principal.search(texte) or secours.search(texte)
    return sexa(m) if m else None


def km(a, b):
    """Distance approchée entre deux (lon, lat) en degrés."""
    dy = (b[1] - a[1]) * 111.2
    dx = (b[0] - a[0]) * 111.2 * math.cos(math.radians((a[1] + b[1]) / 2))
    return math.hypot(dx, dy)


def positions():
    """Rend {date: {source: (|lat|, |long depuis Paris|)}}."""
    brut = {}
    for nom, fichier, pl, pg in (
            ('anonyme', 'data/journal_anonyme.json', LAT, LON),
            ('breton',  'data/journal_breton.json',  LAT_B, LAT)):
        src = json.load(open(fichier, encoding='utf-8'))
        for d, t in src.items():
            if d <= DEPART:
                continue
            if nom == 'anonyme':
                la, lo = lit(t, LAT, LAT_LARGE), lit(t, LON, LON_LARGE)
            else:
                la, lo = lit(t, LAT_B, LAT_B), lit(t, LON_B, LON_B)
            if la is not None and lo is not None and la <= 90 and lo <= 180:
                brut.setdefault(d, {})[nom] = (la, lo)
    return brut


def ecart_jours(a, b):
    fmt = '%Y-%m-%d'
    return (datetime.datetime.strptime(b, fmt) - datetime.datetime.strptime(a, fmt)).days


def resout(brut):
    """Résout les signes par programmation dynamique entre deux ancrages."""
    jours = sorted(brut)
    # le journal donne toujours la position la plus complète : anonyme d'abord
    mesure = {d: (brut[d].get('anonyme') or brut[d]['breton']) for d in jours}
    source = {d: ('anonyme' if 'anonyme' in brut[d] else 'breton') for d in jours}

    def etats(d):
        la, lo = mesure[d]
        return [(slon * lo + PARIS, slat * la) for slat in (-1, 1) for slon in (-1, 1)]

    # dernier relevé : approches de la Manche, donc nord et ouest de Paris
    fin = jours[-1]
    la, lo = mesure[fin]
    ancre_fin = (-lo + PARIS, la)

    cout = {p: km(PORT_JACKSON, p) for p in etats(jours[0])}
    chemin = {p: [p] for p in etats(jours[0])}
    for i in range(1, len(jours)):
        d, prec = jours[i], jours[i - 1]
        neuf_cout, neuf_chemin = {}, {}
        for p in etats(d):
            if d == fin and p != ancre_fin:
                continue
            best = min(((cout[q] + km(q, p), q) for q in cout), key=lambda x: x[0])
            neuf_cout[p] = best[0]
            neuf_chemin[p] = chemin[best[1]] + [p]
        cout, chemin = neuf_cout, neuf_chemin
    final = min(cout, key=cout.get)
    suite = chemin[final]

    trace, rapides, rejets = [], [], []
    precedent, date_prec = PORT_JACKSON, DEPART
    for d, p in zip(jours, suite):
        n = max(1, ecart_jours(date_prec, d))
        vitesse = km(precedent, p) / n
        entree = {'date': d, 'lon': round(p[0], 4), 'lat': round(p[1], 4),
                  'source': source[d], 'km_j': round(vitesse)}
        if vitesse > 3 * KM_JOUR_MAX:
            rejets.append((d, round(vitesse), n))
            continue
        if vitesse > KM_JOUR_MAX:
            entree['invraisemblable'] = True
            rapides.append((d, round(vitesse), n))
        trace.append(entree)
        precedent, date_prec = p, d
    trace.extend(dict(c, km_j=0) for c in CONTOURNEMENTS)
    trace.sort(key=lambda x: x['date'])
    return trace, rapides, rejets


def main():
    brut = positions()
    trace, rapides, rejets = resout(brut)
    print('journées avec latitude ET longitude : %d' % len(brut))
    print('  points construits : %d' % len(trace))
    par_source = {}
    for t in trace:
        par_source[t['source']] = par_source.get(t['source'], 0) + 1
    print('  par source : %s' % par_source)
    if trace:
        print('  %s (%.2f, %.2f) -> %s (%.2f, %.2f)'
              % (trace[0]['date'], trace[0]['lon'], trace[0]['lat'],
                 trace[-1]['date'], trace[-1]['lon'], trace[-1]['lat']))
    print('  routes journalières invraisemblables (> %d km/j) : %d'
          % (KM_JOUR_MAX, len(rapides)))
    for d, v, n in rapides:
        print('     %s : %d km/j sur %d j' % (d, v, n))
    if rejets:
        print('  écartées (lecture erronée, > %d km/j) : %d' % (3 * KM_JOUR_MAX, len(rejets)))
        for d, v, n in rejets:
            print('     %s : %d km/j sur %d j' % (d, v, n))

    # concordance des deux journaux sur les journées communes
    dlat, dlon = [], []
    for d, m in brut.items():
        if len(m) == 2:
            (la1, lo1), (la2, lo2) = m['anonyme'], m['breton']
            dlat.append(abs(la1 - la2))
            dlon.append(abs(lo1 - lo2))
    if dlat:
        med = lambda v: sorted(v)[len(v) // 2]
        print('concordance des deux journaux sur %d journées communes : '
              'écart médian %.3f° en latitude, %.3f° en longitude'
              % (len(dlat), med(dlat), med(dlon)))

    if '--ecrire' in sys.argv:
        json.dump(trace, open('data/retour_naturaliste.json', 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        print('écrit : data/retour_naturaliste.json')


if __name__ == '__main__':
    main()
