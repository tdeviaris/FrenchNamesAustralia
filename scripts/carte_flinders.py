#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Géoréférence la carte générale de Flinders et en découpe des vues.

« General chart of Terra Australis or Australia, showing the parts explored
between 1798 and 1803 », Londres, 1814. L'exemplaire numérisé par la
Bibliothèque nationale d'Australie (nla.obj-232588549) mesure 5000 x 3795
pixels. Flinders y a porté ses routes, jalonnées de dates.

La carte est en projection de Mercator, comme toute carte marine : la longitude
est linéaire en abscisse, la latitude l'est en ordonnée une fois passée par
ln(tan(45° + φ/2)). Les repères ont été mesurés sur la gravure elle-même :

  douze méridiens, de 5 en 5 degrés, espacés de 365,3 px ; le méridien 110° E
  tombe à x = 761, ce que confirment les libellés des marges ;

  cinq parallèles, de 5 en 5 degrés de 15° à 35° Sud, espacés de 388 à 439 px.
  L'ajustement de Mercator y tient à 0,2 % près, et donne 4242 px par unité.

Contrôle : le cap Leeuwin, calculé d'après ses coordonnées modernes, tombe à
quelques pixels du libellé « C. Leeuwin » de la gravure. Un pixel vaut environ
1,2 km.

Usage :
  python3 scripts/carte_flinders.py <carte.jpg> --vers-geo X Y
  python3 scripts/carte_flinders.py <carte.jpg> --vers-pixel LON LAT
  python3 scripts/carte_flinders.py <carte.jpg> --vue LON LAT [--large 700] [--zoom 2]
"""
import math, os, sys

from PIL import Image

# Repères mesurés sur la gravure.
X_110, PX_DEGRE = 761.0, 73.04          # abscisse du méridien 110° E
Y_15S, PX_MERCATOR = 844.0, 4242.0      # ordonnée du parallèle 15° S


def mercator(phi):
    """L'ordonnée de Mercator d'une latitude, en valeur absolue."""
    return math.log(math.tan(math.radians(45 + abs(phi) / 2)))


def vers_geo(x, y):
    """Longitude et latitude d'un pixel."""
    lon = 110.0 + (x - X_110) / PX_DEGRE
    m = mercator(15) + (y - Y_15S) / PX_MERCATOR
    lat = -(2 * math.degrees(math.atan(math.exp(m))) - 90)
    return round(lon, 4), round(lat, 4)


def vers_pixel(lon, lat):
    """Le pixel d'une position."""
    x = X_110 + (lon - 110.0) * PX_DEGRE
    y = Y_15S + (mercator(lat) - mercator(15)) * PX_MERCATOR
    return int(round(x)), int(round(y))


def vue(carte, lon, lat, large=700, haut=None, zoom=2, sortie=None):
    """Découpe la carte autour d'une position, agrandie pour la lecture."""
    haut = haut or round(large * 0.72)
    im = Image.open(carte)
    x, y = vers_pixel(lon, lat)
    boite = (max(0, x - large // 2), max(0, y - haut // 2),
             min(im.width, x + large // 2), min(im.height, y + haut // 2))
    c = im.crop(boite)
    c = c.resize((c.width * zoom, c.height * zoom), Image.LANCZOS)
    chemin = sortie or os.path.join(os.path.dirname(carte),
                                    'vue_%.2f_%.2f.jpg' % (lon, lat))
    c.save(chemin, quality=92)
    return chemin, boite, c.size


def main():
    carte = sys.argv[1]
    if '--vers-geo' in sys.argv:
        i = sys.argv.index('--vers-geo')
        print('%.4f E, %.4f' % vers_geo(float(sys.argv[i+1]), float(sys.argv[i+2])))
    elif '--vers-pixel' in sys.argv:
        i = sys.argv.index('--vers-pixel')
        print('x=%d y=%d' % vers_pixel(float(sys.argv[i+1]), float(sys.argv[i+2])))
    elif '--vue' in sys.argv:
        i = sys.argv.index('--vue')
        lon, lat = float(sys.argv[i+1]), float(sys.argv[i+2])
        large = int(sys.argv[sys.argv.index('--large')+1]) if '--large' in sys.argv else 700
        zoom = int(sys.argv[sys.argv.index('--zoom')+1]) if '--zoom' in sys.argv else 2
        chemin, boite, taille = vue(carte, lon, lat, large, zoom=zoom)
        print('%s\n  origine %s  taille %s' % (chemin, boite[:2], taille))
    else:
        print(__doc__)


if __name__ == '__main__':
    main()


# --- La gravure à sa pleine résolution -------------------------------------
#
# La bibliothèque sert aussi la carte en tuiles DeepZoom, dont le niveau 14 est
# le fichier maître : 11850 x 8992, soit deux fois et demie ce que rend le
# point d'accès ordinaire. À cette échelle un pixel vaut cinq cents mètres, et
# les quantièmes que Flinders a portés le long de ses routes se lisent sans
# hésitation. On ne récupère que les tuiles qui couvrent la vue demandée.

TUILES = 'https://nla.gov.au/nla.obj-232588549/dzi?tile=14/%d_%d.jpg'
TUILE = 256
MAITRE = (11850, 8992)
ORDINAIRE = (5000, 3795)
KX = MAITRE[0] / ORDINAIRE[0]
KY = MAITRE[1] / ORDINAIRE[1]


def vers_maitre(x, y):
    """Du repère de l'image ordinaire à celui de la gravure pleine."""
    return x * KX, y * KY


def vue_maitre(lon, lat, large=560, haut=None, cache=None, sortie=None):
    """Découpe la gravure pleine autour d'une position.

    `large` et `haut` restent exprimés dans le repère de l'image ordinaire,
    pour que les vues se comparent d'une résolution à l'autre.
    """
    import urllib.request
    haut = haut or round(large * 0.72)
    x, y = vers_pixel(lon, lat)
    cx, cy = vers_maitre(x, y)
    demi_l, demi_h = large * KX / 2, haut * KY / 2
    x0, y0 = max(0, int(cx - demi_l)), max(0, int(cy - demi_h))
    x1 = min(MAITRE[0], int(cx + demi_l))
    y1 = min(MAITRE[1], int(cy + demi_h))

    c0, r0 = x0 // TUILE, y0 // TUILE
    c1, r1 = (x1 - 1) // TUILE, (y1 - 1) // TUILE
    planche = Image.new('RGB', ((c1 - c0 + 1) * TUILE, (r1 - r0 + 1) * TUILE), 'white')
    cache = cache or os.path.join(os.path.expanduser('~'), '.cache', 'flinders_tuiles')
    os.makedirs(cache, exist_ok=True)
    for c in range(c0, c1 + 1):
        for r in range(r0, r1 + 1):
            chemin = os.path.join(cache, '14_%d_%d.jpg' % (c, r))
            if not os.path.exists(chemin):
                req = urllib.request.Request(
                    TUILES % (c, r),
                    headers={'User-Agent': 'Mozilla/5.0 (recherche historique)'})
                with urllib.request.urlopen(req, timeout=30) as f:
                    open(chemin, 'wb').write(f.read())
            planche.paste(Image.open(chemin), ((c - c0) * TUILE, (r - r0) * TUILE))
    bout = planche.crop((x0 - c0 * TUILE, y0 - r0 * TUILE,
                         x1 - c0 * TUILE, y1 - r0 * TUILE))
    chemin = sortie or ('vue_maitre_%.2f_%.2f.jpg' % (lon, lat))
    bout.save(chemin, quality=93)
    return chemin, (x0, y0), bout.size


def geo_maitre(xm, ym):
    """Longitude et latitude d'un pixel de la gravure pleine."""
    return vers_geo(xm / KX, ym / KY)
