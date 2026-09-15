"""Repere les segments de parcours qui traversent un trait de cote.

Usage : python3 scripts/controle_littoral.py [dossier data]

Ne modifie rien. Les segments sont classes par nature de probleme :
  CAP       etape courte coupant un cap  -> scripts/contournements.py sait corriger
  A TERRE   un releve tombe hors de l'eau -> erreur de position d'epoque, non corrigeable
  LACUNE    plus de 3 jours entre deux releves -> trou dans les donnees
  MOUILLAGE moins de 12 km -> baie non resolue par le trait de cote (faux positif)
"""
import datetime, io, json, os, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from littoral import Cote, Terre, km, points_tries, RACINE

ECART_MAX_JOURS = 3
LONGUEUR_MIN_KM = 12
FICHIERS = [('Baudin', 'baudin_parcours.geojson'),
            ("d'Entrecasteaux", 'dentrecasteaux_parcours.geojson')]


def main(data):
    cote, terre = Cote(), Terre()
    print(f"trait de cote : {len(cote):,} aretes\n")
    global_cat = Counter()
    total = 0

    for nom, fichier in FICHIERS:
        chemin = os.path.join(data, fichier)
        if not os.path.exists(chemin):
            continue
        gj = json.load(io.open(chemin, encoding='utf-8'))
        print(f"{'='*78}\n{nom}\n{'='*78}")

        for nav, lst in points_tries(gj).items():
            fautifs = []
            for i in range(1, len(lst)):
                p = lst[i - 1]['geometry']['coordinates']
                q = lst[i]['geometry']['coordinates']
                if abs(q[0] - p[0]) > 180:
                    continue
                if not cote.traverse(p, q):
                    continue
                d1 = str(lst[i - 1]['properties'].get('date') or '')
                d2 = str(lst[i]['properties'].get('date') or '')
                try:
                    ecart = (datetime.date.fromisoformat(d2) - datetime.date.fromisoformat(d1)).days
                except ValueError:
                    ecart = None
                longueur = km(p, q)
                if terre.contient(p) or terre.contient(q):
                    cat = 'A TERRE'
                elif ecart is not None and ecart > ECART_MAX_JOURS:
                    cat = 'LACUNE'
                elif longueur < LONGUEUR_MIN_KM:
                    cat = 'MOUILLAGE'
                else:
                    cat = 'CAP'
                fautifs.append((cat, d1, d2, p, q, longueur, ecart))

            par_cat = Counter(f[0] for f in fautifs)
            global_cat.update(par_cat)
            total += len(fautifs)
            resume = ', '.join(f"{v} {k}" for k, v in sorted(par_cat.items())) or 'aucun'
            print(f"\n  {nav} — {len(lst)} points — {len(fautifs)} segment(s) : {resume}")
            for cat, d1, d2, p, q, longueur, ecart in sorted(fautifs):
                j = f"{ecart}j" if ecart is not None else "?"
                print(f"     [{cat:9}] {d1} -> {d2} ({j:>5}) | {p[1]:>9.4f},{p[0]:<10.4f} ->"
                      f" {q[1]:>9.4f},{q[0]:<10.4f} | {longueur:6.0f} km")

    print(f"\n{'='*78}\nTOTAL : {total} segment(s)")
    for k in sorted(global_cat):
        print(f"   {k:10} : {global_cat[k]}")


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(RACINE, 'data'))
