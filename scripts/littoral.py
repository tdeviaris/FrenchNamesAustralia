"""Outils partages pour les controles de trace sur le trait de cote.

Le trait de cote est Natural Earth 10 m (ne_10m_coastline.geojson).
"""
import io, json, math, os
import numpy as np

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAUT_COTE = os.path.join(RACINE, 'data', 'ne_10m_coastline.geojson')
URL_COTE = ('https://raw.githubusercontent.com/nvkelso/natural-earth-vector'
            '/master/geojson/ne_10m_coastline.geojson')
DEFAUT_TERRE = os.path.join(RACINE, 'data', 'ne_10m_land.geojson')
URL_TERRE = ('https://raw.githubusercontent.com/nvkelso/natural-earth-vector'
             '/master/geojson/ne_10m_land.geojson')


def assurer_cote(chemin=DEFAUT_COTE):
    """Telecharge le trait de cote Natural Earth s'il est absent (9,6 Mo)."""
    if os.path.exists(chemin):
        return chemin
    import urllib.request
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    print(f"telechargement du trait de cote -> {chemin}")
    urllib.request.urlretrieve(URL_COTE, chemin)
    return chemin


def km(p, q):
    """Distance approchee en km entre deux couples (lon, lat)."""
    (x1, y1), (x2, y2) = p, q
    return math.hypot((x2 - x1) * math.cos(math.radians((y1 + y2) / 2)), y2 - y1) * 111.32


class Cote:
    """Trait de cote charge en aretes, teste par intersection exacte."""

    def __init__(self, chemin=DEFAUT_COTE):
        data = json.load(io.open(assurer_cote(chemin), encoding='utf-8'))
        ax, ay, bx, by = [], [], [], []
        for f in data['features']:
            c = f['geometry']['coordinates']
            for i in range(1, len(c)):
                ax.append(c[i - 1][0]); ay.append(c[i - 1][1])
                bx.append(c[i][0]);     by.append(c[i][1])
        self.ax, self.ay, self.bx, self.by = map(np.asarray, (ax, ay, bx, by))
        self.minx = np.minimum(self.ax, self.bx); self.maxx = np.maximum(self.ax, self.bx)
        self.miny = np.minimum(self.ay, self.by); self.maxy = np.maximum(self.ay, self.by)

    def __len__(self):
        return len(self.ax)

    @staticmethod
    def _orient(px, py, qx, qy, rx, ry):
        return np.sign((qx - px) * (ry - py) - (qy - py) * (rx - px))

    def croisements(self, p, q):
        """(nombre d'aretes proprement traversees, une arete temoin)."""
        (px, py), (qx, qy) = p, q
        m = ((self.maxx >= min(px, qx)) & (self.minx <= max(px, qx))
             & (self.maxy >= min(py, qy)) & (self.miny <= max(py, qy)))
        if not m.any():
            return 0, None
        ex1, ey1, ex2, ey2 = self.ax[m], self.ay[m], self.bx[m], self.by[m]
        d1 = self._orient(px, py, qx, qy, ex1, ey1)
        d2 = self._orient(px, py, qx, qy, ex2, ey2)
        d3 = self._orient(ex1, ey1, ex2, ey2, px, py)
        d4 = self._orient(ex1, ey1, ex2, ey2, qx, qy)
        hit = (d1 != d2) & (d3 != d4) & (d1 != 0) & (d2 != 0) & (d3 != 0) & (d4 != 0)
        n = int(hit.sum())
        if n == 0:
            return 0, None
        i = int(np.argmax(hit))
        return n, (float(ex1[i]), float(ey1[i]))

    def traverse(self, p, q):
        return self.croisements(p, q)[0] > 0


def points_tries(gj):
    """Points du GeoJSON groupes par navire, tries par date."""
    groupes = {}
    for f in gj['features']:
        if f['geometry']['type'] != 'Point':
            continue
        nav = str(f['properties'].get('navire') or 'la Recherche')
        groupes.setdefault(nav, []).append(f)
    for lst in groupes.values():
        lst.sort(key=lambda f: str(f['properties'].get('date', '')))
    return groupes


class Terre:
    """Polygones terrestres, pour savoir si une position relevee tombe a terre."""

    def __init__(self, chemin=DEFAUT_TERRE):
        if not os.path.exists(chemin):
            import urllib.request
            os.makedirs(os.path.dirname(chemin), exist_ok=True)
            print(f"telechargement des polygones terrestres -> {chemin}")
            urllib.request.urlretrieve(URL_TERRE, chemin)
        data = json.load(io.open(chemin, encoding='utf-8'))
        self.anneaux = []
        for f in data['features']:
            g = f['geometry']
            polys = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
            for poly in polys:
                for ring in poly:
                    a = np.asarray(ring, dtype=float)
                    if len(a) > 3:
                        self.anneaux.append(a)
        self.bbox = np.array([[a[:, 0].min(), a[:, 0].max(), a[:, 1].min(), a[:, 1].max()]
                              for a in self.anneaux])

    def contient(self, point):
        """Vrai si (lon, lat) tombe a l'interieur d'une terre emergee."""
        lon, lat = point[0], point[1]
        cand = np.where((self.bbox[:, 0] <= lon) & (self.bbox[:, 1] >= lon)
                        & (self.bbox[:, 2] <= lat) & (self.bbox[:, 3] >= lat))[0]
        dedans = False
        for i in cand:
            a = self.anneaux[i]
            x1, y1 = a[:, 0], a[:, 1]
            x2, y2 = np.roll(x1, -1), np.roll(y1, -1)
            cond = (y1 > lat) != (y2 > lat)
            with np.errstate(divide='ignore', invalid='ignore'):
                xi = (x2 - x1) * (lat - y1) / (y2 - y1) + x1
            if int(np.sum(cond & (lon < xi))) % 2 == 1:
                dedans = not dedans
        return dedans
