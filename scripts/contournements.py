"""Insere les points de contournement manquants quand une etape courte coupe une cote.

Pour chaque segment fautif, cherche au large le point le plus proche qui degage
les deux demi-segments, puis l'insere dans le GeoJSON (points et LineString).

Le point insere porte `extrapole: true` : sa position est CALCULEE, non relevee.
La carte l'indique dans la fiche par la mention "Position extrapolee".

Rejouable : un parcours deja corrige ne produit plus aucun ajout.
Usage : python3 scripts/contournements.py [--ecrire]
"""
import datetime, io, json, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from littoral import Cote, Terre, km, points_tries, RACINE

DATA = os.path.join(RACINE, 'data')
# Chaque parcours porte son propre ecart maximal, parce que les sources ne se
# valent pas : Baudin tient des tables journalieres, ou trois jours de silence
# signalent une lacune, tandis que Flinders ne donne sa position que de loin en
# loin et qu'une semaine sans releve y est ordinaire.
FICHIERS = [('Baudin', 'baudin_parcours.geojson', 3),
            ("d'Entrecasteaux", 'dentrecasteaux_parcours.geojson', 3),
            ('Flinders', 'flinders_parcours.geojson', 12)]

ECART_MAX_JOURS = 3      # au-dela : lacune de releve, pas un cap mal contourne
LONGUEUR_MIN_KM = 12     # en deca : mouillage, le trait de cote ne resout pas la baie
OFFSETS_KM = [5, 8, 12, 18, 25, 35, 50, 70, 95, 125, 160, 200, 250, 300]

# Detours poses a la main, pour les caps que la recherche ne trouve pas. Elle
# n'essaie que des points perpendiculaires au segment : une pointe etroite dont
# il faut faire le tour par l'exterieur demande un trace qu'elle ne rencontre
# jamais. Chaque entree porte le chemin retenu et ce qui l'a dicte.
DETOURS_MANUELS = {
    ("l'Investigator", '1801-12-07', '1801-12-09'): {
        'points': [(116.75, -35.35), (118.05, -35.10)],
        'raison': "entrée de King George's Sound. La ligne droite coupait la "
                  "côte méridionale : le navire longe d'abord le rivage au "
                  "large, puis remonte dans le détroit par le sud-est, en "
                  "doublant Bald Head — le cap que Flinders nomma lui-même. "
                  "278 km au lieu de 231, soit un cinquième de plus",
    },
    ('les corvettes', '1802-01-13', '1802-01-14'): {
        'points': [(146.98, -43.62), (147.14, -43.30)],
        'raison': "doublement du cap Sud-Est de la Terre de Van Diemen et "
                  "entrée dans le canal d'Entrecasteaux ; la ligne droite "
                  "coupait la pointe, ces deux points la longent "
                  "(62 km au lieu de 45)",
    },
    ('le Casuarina', '1802-12-12', '1802-12-13'): {
        'points': [(144.72, -40.58), (144.56, -40.98)],
        'raison': "passage à l'ouest des îlots Hunter, au nord-ouest de la "
                  "Terre de Van Diemen ; la ligne droite les traversait "
                  "(114 km au lieu de 85)",
    },
    ('la Recherche', '1793-09-23', '1793-09-24'): {
        'points': [(122.87, -4.495)],
        'raison': "contournement de la pointe méridionale de Bouton, aux "
                  "Célèbes ; le point se pose sur la route directe, qu'il "
                  "n'allonge pas",
    },
    ('les corvettes', '1803-01-03', '1803-01-04'): {
        'points': [(136.63, -36.06), (136.49, -35.85)],
        'raison': "contournement de la pointe occidentale de l'île Decrès "
                  "(Kangaroo Island) par le cap du Couedic ; la ligne droite "
                  "coupait l'île, ces deux points la longent au plus près "
                  "(131 km dans la journée, soit 2,9 nœuds de moyenne)",
    },
}
FRACTIONS = [0.5, 0.35, 0.65, 0.2, 0.8]   # points d'appui le long du segment


def candidat(p, q, fraction, offset_km, signe):
    """Point decale perpendiculairement au segment, a `fraction` de son parcours."""
    (px, py), (qx, qy) = p, q
    lat = (py + qy) / 2
    coslat = max(math.cos(math.radians(lat)), 1e-6)
    dx = (qx - px) * coslat
    dy = qy - py
    norme = math.hypot(dx, dy)
    if norme == 0:
        return None
    px_, py_ = -dy / norme, dx / norme          # perpendiculaire unitaire
    base_x = px + (qx - px) * fraction
    base_y = py + (qy - py) * fraction
    d = offset_km / 111.32
    return (base_x + signe * px_ * d / coslat, base_y + signe * py_ * d)


def contourner(cote, p, q):
    """Plus petit detour degageant p->m et m->q, ou None."""
    for offset in OFFSETS_KM:
        for fraction in FRACTIONS:
            for signe in (1, -1):
                m = candidat(p, q, fraction, offset, signe)
                if m is None or not (-90 < m[1] < 90):
                    continue
                if not cote.traverse(p, m) and not cote.traverse(m, q):
                    return [m], offset
    return None, None


def contourner_double(cote, p, q):
    """Detour en deux points, pour les caps que un seul ne suffit pas a degager."""
    for offset in OFFSETS_KM:
        for signe in (1, -1):
            for f1, f2 in ((0.25, 0.75), (0.2, 0.6), (0.4, 0.8), (0.33, 0.67), (0.15, 0.85)):
                m1 = candidat(p, q, f1, offset, signe)
                m2 = candidat(p, q, f2, offset, signe)
                if m1 is None or m2 is None:
                    continue
                if not (-90 < m1[1] < 90 and -90 < m2[1] < 90):
                    continue
                if (not cote.traverse(p, m1) and not cote.traverse(m1, m2)
                        and not cote.traverse(m2, q)):
                    return [m1, m2], offset
    return None, None


def gabarit(modele, coords, date, raison):
    props = {k: "" for k in modele['properties']}
    props.update({
        'date': date,
        'section': modele['properties'].get('section', ''),
        'navire': modele['properties'].get('navire', ''),
        'alerte': raison,
        'extrapole': True,
        # Un point de contournement porte la meme date que son voisin : la
        # carte doit savoir lequel des deux ouvrir quand on demande ce jour-la.
        'contournement': True,
    })
    if not props.get('navire'):
        props.pop('navire', None)
    return {"type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(coords[0], 5), round(coords[1], 5)]},
            "properties": props}


def main(ecrire):
    cote = Cote()
    terre = Terre()
    print(f"trait de cote : {len(cote):,} aretes | polygones terrestres : {len(terre.anneaux):,} anneaux\n")
    total_ajouts = total_echecs = total_aterre = 0

    for nom, fichier, ecart_max in FICHIERS:
        chemin = os.path.join(DATA, fichier)
        if not os.path.exists(chemin):
            continue
        gj = json.load(io.open(chemin, encoding='utf-8'))
        ajouts = []          # (feature a inserer, feature devant laquelle inserer)
        echecs = []
        aterre = []

        for nav, lst in points_tries(gj).items():
            for i in range(1, len(lst)):
                p = lst[i - 1]['geometry']['coordinates']
                q = lst[i]['geometry']['coordinates']
                if abs(q[0] - p[0]) > 180:
                    continue
                d1 = str(lst[i - 1]['properties'].get('date') or '')
                d2 = str(lst[i]['properties'].get('date') or '')
                try:
                    ecart = (datetime.date.fromisoformat(d2) - datetime.date.fromisoformat(d1)).days
                except ValueError:
                    continue
                longueur = km(p, q)
                if ecart > ecart_max or longueur < LONGUEUR_MIN_KM:
                    continue                      # lacune ou mouillage : hors perimetre
                if not cote.traverse(p, q):
                    continue
                # Une extremite a terre = releve errone : aucun detour ne repare cela.
                aterre_p, aterre_q = terre.contient(p), terre.contient(q)
                if aterre_p or aterre_q:
                    lequel = 'départ' if aterre_p and not aterre_q else (
                             'arrivée' if aterre_q and not aterre_p else 'les deux')
                    aterre.append((nav, d1, d2, round(longueur), lequel))
                    continue
                manuel = DETOURS_MANUELS.get((nav, d1, d2))
                if manuel:
                    ms, offset = [tuple(m) for m in manuel['points']], None
                else:
                    ms, offset = contourner(cote, p, q)
                    if ms is None:
                        ms, offset = contourner_double(cote, p, q)
                if ms is None:
                    echecs.append((nav, d1, d2, round(longueur)))
                    continue
                for rang, m in enumerate(ms):
                    suffixe = f" [{rang + 1}/{len(ms)}]" if len(ms) > 1 else ""
                    if manuel:
                        raison = (f"position extrapolée : {manuel['raison']}"
                                  f"{suffixe}")
                    else:
                        raison = (f"position extrapolée : contournement de côte entre "
                                  f"le {d1} et le {d2} (détour de {offset} km){suffixe}")
                    ajouts.append((gabarit(lst[i], m, d2, raison), lst[i], p, q, rang))

        print(f"{nom} : {len(ajouts)} point(s) de contournement, "
              f"{len(aterre)} releve(s) a terre, {len(echecs)} echec(s)")
        for nav, d1, d2, l, lequel in aterre:
            print(f"    A TERRE {nav} {d1} -> {d2} ({l} km) : {lequel} hors de l'eau")
        for nav, d1, d2, l in echecs:
            print(f"    ECHEC   {nav} {d1} -> {d2} ({l} km) : aucun detour trouve")
        total_ajouts += len(ajouts); total_echecs += len(echecs); total_aterre += len(aterre)

        if ecrire and ajouts:
            fs = gj['features']
            for nouveau, apres, p, q, rang in ajouts:
                # Les points d'un meme detour se suivent dans l'ordre de parcours.
                fs.insert(fs.index(apres), nouveau)
                c_new = nouveau['geometry']['coordinates']
                for f in fs:
                    if f['geometry']['type'] != 'LineString':
                        continue
                    coords = f['geometry']['coordinates']
                    for j in range(1, len(coords)):
                        if (abs(coords[j - 1][1] - p[1]) < 1e-6 and abs(coords[j][1] - q[1]) < 1e-6
                                and abs(coords[j - 1][0] - p[0]) < 1e-6
                                and abs(coords[j][0] - q[0]) < 1e-6):
                            coords.insert(j, list(c_new))
                            break
            json.dump(gj, io.open(chemin, 'w', encoding='utf-8'), ensure_ascii=False)
            print(f"    -> {fichier} mis a jour")

    print(f"\nTOTAL : {total_ajouts} point(s) de contournement inseres, "
          f"{total_aterre} releve(s) a terre (non corrigeables), {total_echecs} echec(s)")
    if not ecrire:
        print("(simulation — relancer avec --ecrire pour appliquer)")


if __name__ == '__main__':
    main('--ecrire' in sys.argv)
