#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vérifie la datation du typescript de la BnF par les latitudes qu'il porte.

Chaque journée de mer donne, sous son en-tête, la latitude Sud estimée puis
observée. Le parcours du projet, établi de son côté sur les tables de route
publiées, donne une position par navire et par jour. Si la datation est juste,
les deux doivent coïncider ; si elle glisse d'un mois, l'écart saute aux yeux.

Le contrôle porte sur l'écart médian : les chiffres du typescript sont lus par
une reconnaissance optique qui confond 3 et 5, quelques latitudes sont donc
aberrantes sans que la date soit en cause.

Usage : python3 scripts/controle_baudin_bnf.py [--detail]
"""
import json, os, re, statistics, sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOURNAL = os.path.join(RACINE, 'data', 'journal_baudin_bnf.json')
GEOJSON = os.path.join(RACINE, 'data', 'baudin_parcours.geojson')

# Le relevé de navigation donne la latitude estimée puis la latitude observée.
# Ces deux mots-là sont le seul point d'accroche sûr : l'OCR écorche tout le
# reste. Il perd les signes de degré — « 4102253 » pour 41°22'53" —, lit le
# tiret de césure comme un point — « La.titude » —, et brise les nombres
# n'importe où. On récupère donc le premier amas de chiffres qui suit le mot,
# et on le découpe en degrés et minutes selon sa longueur.
ANCRE = re.compile(r"(?:estim|observ)[a-zéèê]{0,4}"
                   r"[^0-9\n]{0,10}([0-9][0-9°'\"»,.:;%*\s-]{2,18})", re.I)
BLANCS = re.compile(r'[ \t]+')
# « La- / titude », « La. / titude » : le dactylographe coupe, l'OCR se trompe
# de signe. On recolle avant de chercher.
COUPURE = re.compile(r"[-.,]\s*\n\s*")


def degres_minutes(amas):
    """Degrés et minutes tirés d'un amas de chiffres plus ou moins abîmé."""
    groupes = [g for g in re.findall(r'\d+', amas) if g]
    if not groupes:
        return None
    tete = groupes[0]
    if len(tete) >= 4:
        # les séparateurs ont disparu : « 4102253 » vaut 41°22'53"
        return int(tete[:2]), int(tete[2:4]) % 60
    if len(tete) == 3:
        # « 419 » : le degré a mangé le signe, on ne garde que les degrés
        return int(tete[:2]), 0
    if len(groupes) > 1 and len(groupes[1]) <= 2:
        return int(tete), int(groupes[1]) % 60
    return int(tete), 0


def variantes_degre(d):
    """Le même nombre de degrés, sous les lectures que la fonte autorise."""
    formes = {str(d)}
    for _ in range(2):
        for f in list(formes):
            for a, b in (('3', '5'), ('0', '6'), ('1', '7')):
                formes.add(f.replace(a, b))
                formes.add(f.replace(b, a))
    return {int(f) for f in formes if f.isdigit() and 0 < int(f) <= 55}


def latitudes(texte, tolerant=False):
    """Les latitudes Sud lues dans le relevé de navigation d'une journée."""
    texte = BLANCS.sub(' ', COUPURE.sub('', texte))
    vues = []
    # la ligne de route ouvre la journee, mais Baudin redonne souvent la
    # latitude au fil du recit : on lit toute la journee
    for m in ANCRE.finditer(texte[:2500]):
        dm = degres_minutes(m.group(1))
        if not dm or not 8 <= dm[0] <= 55:
            continue
        d, mi = dm
        for dd in (variantes_degre(d) if tolerant else {d}):
            vues.append(-(dd + mi / 60.0))
    return vues


def main():
    jour = json.load(open(JOURNAL, encoding='utf-8'))
    gj = json.load(open(GEOJSON, encoding='utf-8'))
    # Baudin est sur le Géographe ; avant la séparation les deux naviguent
    # de conserve et le parcours les porte sous « les corvettes »
    ref = {}
    for f in gj['features']:
        if f['geometry']['type'] != 'Point':
            continue
        p = f['properties']
        if p.get('navire') in ('le Géographe', 'les corvettes') and p.get('date'):
            ref.setdefault(p['date'], f['geometry']['coordinates'][1])

    ecarts, tolerants, sans_ref, sans_lat, pires = [], [], 0, 0, []
    for date in sorted(jour):
        if date not in ref:
            sans_ref += 1
            continue
        lats = latitudes(jour[date]['texte'])
        if not lats:
            sans_lat += 1
            continue
        # la plus proche des latitudes lues : l'estimée et l'observée diffèrent
        e = min(abs(l - ref[date]) for l in lats)
        ecarts.append(e)
        tol = latitudes(jour[date]['texte'], tolerant=True)
        tolerants.append(min(abs(l - ref[date]) for l in tol))
        pires.append((e, date, lats[0], ref[date]))

    print('journées du typescript      : %d' % len(jour))
    print('  hors du parcours connu    : %d' % sans_ref)
    print('  sans latitude lisible     : %d' % sans_lat)
    print('  comparées                 : %d' % len(ecarts))
    if not ecarts:
        return
    ecarts.sort()
    print('\nécart à la position du parcours, en degrés de latitude :')
    print('  médiane                   : %.3f°  (%.0f milles)'
          % (statistics.median(ecarts), statistics.median(ecarts) * 60))
    for seuil in (0.25, 0.5, 1.0, 2.0, 5.0):
        n = sum(1 for e in ecarts if e <= seuil)
        print('  à moins de %4.2f°          : %3d  (%.0f %%)'
              % (seuil, n, 100.0 * n / len(ecarts)))
    tolerants.sort()
    print('\nen admettant les confusions de la fonte sur les degrés '
          '(3 pour 5, 0 pour 6, 1 pour 7) :')
    print('  médiane                   : %.3f°  (%.0f milles)'
          % (statistics.median(tolerants), statistics.median(tolerants) * 60))
    for seuil in (0.25, 0.5, 1.0, 2.0):
        n = sum(1 for e in tolerants if e <= seuil)
        print('  à moins de %4.2f°          : %3d  (%.0f %%)'
              % (seuil, n, 100.0 * n / len(tolerants)))

    if '--detail' in sys.argv:
        pires.sort(reverse=True)
        print('\nles vingt plus grands écarts :')
        for e, d, lu, att in pires[:20]:
            print('  %s  lu %7.3f  parcours %7.3f  écart %5.2f°'
                  % (d, lu, att, e))


if __name__ == '__main__':
    main()
