"""Rattache un journal de bord anonyme aux points du parcours Baudin.

Deux journaux sont traités, chacun dans sa propre propriété :
  journal_anonyme    Archives nationales, Marine 5JJ53 — à bord du Naturaliste
  journal_geographe  Muséum, ms 1686 — à bord du Géographe

L'auteur — vraisemblablement Charles Moreau, aspirant — navigue sur le
Naturaliste. Deux precautions en decoulent :

  * au-dela du 20 novembre 1802 le journal suit le Naturaliste qui rentre en
    France, alors que nos donnees suivent le Geographe et le Casuarina le long
    des cotes australiennes : ces entrees sont ecartees ;
  * avant cette date, une entree se rattache au navire ou se trouvait l'auteur,
    jamais a un autre batiment de la meme date.

Usage : python3 scripts/journal_anonyme.py <textes.json> <propriete> [--ecrire]
"""
import datetime, io, json, os, sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEOJSON = os.path.join(RACINE, 'data', 'baudin_parcours.geojson')
LIMITE = '1802-11-20'          # depart du Naturaliste pour la France

# Navires auxquels rattacher, par ordre de preference, selon la periode.
PERIODES = [
    ('1800-10-19', '1801-06-11', ['les corvettes', 'le Géographe']),  # de conserve
    ('1801-06-12', '1801-11-12', ['le Naturaliste']),
    ('1801-11-13', '1802-03-08', ['les corvettes']),
    ('1802-03-09', LIMITE,       ['le Naturaliste']),
]
PORT_JACKSON = [151.1461, -33.8667]
DEBUT_ESCALE_PJ = '1802-04-21'

# Dates ou l'interpolation lineaire donnerait une position fausse.
POSITIONS_IMPOSEES = {
    # Appareillage de Sainte-Croix de Tenerife : le navire est encore sur rade,
    # alors qu'interpoler jusqu'au releve du 14 le placerait deja au large.
    '1800-11-13': ([-16.2569, 28.4769], 'rade de Sainte-Croix de Ténériffe'),
}


def navires_pour(date):
    for a, b, navs in PERIODES:
        if a <= date <= b:
            return navs
    return []


def interpole(serie, date):
    """Position estimee a une date, entre les deux releves qui l'encadrent."""
    avant = [p for p in serie if p[0] < date]
    apres = [p for p in serie if p[0] > date]
    if not avant:
        return None
    if not apres:
        return None
    a, b = avant[-1], apres[0]
    ta = datetime.date.fromisoformat(a[0]).toordinal()
    tb = datetime.date.fromisoformat(b[0]).toordinal()
    t = datetime.date.fromisoformat(date).toordinal()
    f = (t - ta) / (tb - ta) if tb > ta else 0
    return [round(a[1][0] + (b[1][0] - a[1][0]) * f, 5),
            round(a[1][1] + (b[1][1] - a[1][1]) * f, 5)]


def main(chemin_textes, propriete, ecrire):
    textes = json.load(io.open(chemin_textes, encoding='utf-8'))
    gj = json.load(io.open(GEOJSON, encoding='utf-8'))
    fs = gj['features']

    par_nav, series = {}, {}
    for f in fs:
        if f['geometry']['type'] != 'Point':
            continue
        p = f['properties']
        nav, d = p.get('navire'), p.get('date')
        if not nav or not d:
            continue
        par_nav.setdefault(nav, {})[d] = f
        if not p.get('extrapole'):
            series.setdefault(nav, []).append((d, f['geometry']['coordinates']))
    for s in series.values():
        s.sort()

    rattaches = crees = ecartes = perdus = 0
    nouveaux = []
    for date in sorted(textes):
        texte = textes[date]
        if date > LIMITE:
            ecartes += 1
            continue
        navs = navires_pour(date)
        if not navs:
            ecartes += 1
            continue
        cible = next((par_nav[n][date] for n in navs
                      if date in par_nav.get(n, {})), None)
        if cible is not None:
            cible['properties'][propriete] = texte
            rattaches += 1
            continue
        # Aucun releve ce jour-la : on cree un point, sans position observee.
        nav = navs[0]
        if date in POSITIONS_IMPOSEES:
            coords, motif = POSITIONS_IMPOSEES[date]
            coords = list(coords)
        elif date >= DEBUT_ESCALE_PJ and nav == 'le Naturaliste':
            coords = list(PORT_JACKSON)          # l'escale de Port Jackson
            motif = "escale de Port Jackson"
        else:
            coords = interpole(series.get(nav, []), date)
            motif = "interpolée entre les deux relevés encadrants"
        if coords is None:
            perdus += 1
            continue
        modele = series[nav][0]
        gabarit = par_nav[nav][modele[0]]['properties']
        props = {k: "" for k in gabarit}
        props.update({
            'date': date, 'navire': nav,
            'alerte': f"point ajouté pour une entrée de journal ; position {motif}",
            'extrapole': True,
            propriete: texte,
        })
        nouveaux.append({"type": "Feature",
                         "geometry": {"type": "Point", "coordinates": coords},
                         "properties": props})
        crees += 1

    print(f"entrées du journal        : {len(textes)}")
    print(f"  rattachées à un relevé  : {rattaches}")
    print(f"  points créés            : {crees}")
    print(f"  écartées (après {LIMITE}) : {ecartes}")
    print(f"  sans position calculable: {perdus}")

    if ecrire:
        fs.extend(nouveaux)
        fs.sort(key=lambda f: (f['geometry']['type'] != 'Point',
                               str(f.get('properties', {}).get('date', ''))))
        json.dump(gj, io.open(GEOJSON, 'w', encoding='utf-8'), ensure_ascii=False)
        print(f"\n-> {os.path.basename(GEOJSON)} mis à jour "
              f"({sum(1 for f in fs if f['geometry']['type']=='Point')} points)")
    else:
        print("\n(simulation — relancer avec --ecrire)")


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], '--ecrire' in sys.argv)
