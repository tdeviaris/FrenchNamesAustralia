#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Donne un point à chaque journée du journal de Flinders, puis les cale un à un.

Deux tiers des journées du récit de Flinders n'avaient pas de position : la
carte ne les montrait pas, et leur texte n'était lisible que par le Q&R. Ce
script leur donne un point, en deux temps.

1. `ajouter` — chaque journée de journal sans point en reçoit un, estimé par
   interpolation. L'estimation suit le tracé existant (y compris les détours de
   contournement de côte) au prorata des jours écoulés, et reste fixe quand le
   navire est au mouillage. Le point est marqué `interpole` : la fiche le dit, et
   la carte le dessine creux.

2. `serveur` — sert le site en local (port 8765 par défaut) et reçoit les
   calages faits à la main dans `map.html?calage=flinders` : un clic droit sur le
   point de midi gravé par Flinders fixe la position du jour. Après chaque
   calage, les journées encore estimées sont ré-interpolées entre les points
   sûrs, pour que la route suive au plus près la carte. Chaque geste est consigné
   dans data/flinders_calage_manuel.json, qui permet de l'annuler.

Le parcours n'est jamais régénéré : on ajoute des points et on retouche ceux
qu'on a ajoutés, sans toucher aux autres (voir la mémoire du projet).

Usage :
  python3 scripts/calage_flinders.py ajouter [--ecrire]
  python3 scripts/calage_flinders.py serveur [--port 8765]
"""
import datetime as dt
import http.server
import json
import math
import os
import shutil
import sys
import threading
import urllib.parse

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARCOURS = os.path.join(RACINE, 'data', 'flinders_parcours.geojson')
JOURNAL_FR = os.path.join(RACINE, 'data', 'journaux', 'flinders_fr.json')
JOURNAL_EN = os.path.join(RACINE, 'data', 'journaux', 'flinders_en.json')
CONSIGNE = os.path.join(RACINE, 'data', 'flinders_calage_manuel.json')

# En deçà, les deux relevés qui encadrent un silence sont le même mouillage.
MOUILLAGE_KM = 3.0
CARTE = "Matthew Flinders, General chart of Terra Australis or Australia, Londres, 1814"

verrou = threading.Lock()


# --------------------------------------------------------------------------
# Lecture et écriture, au format d'origine du fichier
# --------------------------------------------------------------------------

def lire():
    with open(PARCOURS, encoding='utf-8') as f:
        return json.load(f)


def ecrire(donnees):
    # Même forme que les scripts d'origine : une ligne, accents en clair.
    texte = json.dumps(donnees, ensure_ascii=False)
    temporaire = PARCOURS + '.tmp'
    with open(temporaire, 'w', encoding='utf-8') as f:
        f.write(texte)
    os.replace(temporaire, PARCOURS)


def journees_du_journal():
    jours = set()
    for chemin in (JOURNAL_FR, JOURNAL_EN):
        if os.path.exists(chemin):
            for date, champs in json.load(open(chemin, encoding='utf-8')).items():
                if champs and any(str(t).strip() for t in champs.values()):
                    jours.add(date)
    return jours


# --------------------------------------------------------------------------
# Géométrie
# --------------------------------------------------------------------------

def km(a, b):
    """Distance approchée entre deux [lon, lat], en kilomètres."""
    lat = math.radians((a[1] + b[1]) / 2)
    dx = (b[0] - a[0]) * 111.32 * math.cos(lat)
    dy = (b[1] - a[1]) * 110.57
    return math.hypot(dx, dy)


def le_long(sommets, part):
    """Le point situé à la fraction `part` de la ligne brisée `sommets`,
    et sa distance depuis le premier sommet."""
    longueurs = [km(a, b) for a, b in zip(sommets, sommets[1:])]
    total = sum(longueurs)
    if total == 0:
        return list(sommets[0]), 0.0
    cible = part * total
    parcouru = 0.0
    for (a, b), l in zip(zip(sommets, sommets[1:]), longueurs):
        if parcouru + l >= cible and l > 0:
            f = (cible - parcouru) / l
            return [a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1])], cible
        parcouru += l
    return list(sommets[-1]), total


def jour(date):
    return dt.date.fromisoformat(date)


# --------------------------------------------------------------------------
# Interpolation
# --------------------------------------------------------------------------

def est_estime(props):
    """Un point que ce script a posé et que personne n'a encore calé."""
    return bool(props.get('interpole')) and not props.get('cale')


def proprietes_estimees(date, navire, d_avant, d_apres, mouillage):
    props = {'date': date, 'navire': navire, 'expedition': 'Flinders', 'table': '',
             'extrapole': True, 'interpole': True}
    if mouillage:
        props['mouillage'] = True
        props['alerte'] = (f"position tenue au mouillage : le navire n'a pas bougé entre "
                           f"le relevé du {d_avant} et celui du {d_apres}")
    else:
        props['alerte'] = (f"position estimée par interpolation entre les relevés du "
                           f"{d_avant} et du {d_apres}, au prorata des jours écoulés et "
                           f"le long de la route ; elle reste à caler sur la carte de Flinders")
    return props


def interpoler(features, jours_voulus):
    """Rend la liste des features où chaque journée voulue a un point.

    Les points estimés existants sont recalculés ; les autres (relevés, points
    calés, détours de contournement) servent d'appuis et ne bougent pas.
    Les journées nouvelles sont insérées à leur place dans la suite du fichier,
    dans l'ordre où elles tombent le long de la route."""
    appuis = [f for f in features if not est_estime(f['properties'])]
    # Garde les propriétés des points déjà estimés (calage « sans point », etc.)
    anciens = {(f['properties']['date'], f['properties']['navire']): f
               for f in features if est_estime(f['properties'])}

    # Le navire du moment : celui du dernier appui daté.
    datés = sorted(((f['properties']['date'], i, f['properties']['navire'])
                    for i, f in enumerate(appuis) if not f['properties'].get('contournement')))

    def navire_du(date):
        n = None
        for d, _, nav in datés:
            if d <= date:
                n = nav
            else:
                break
        return n

    # Un détour de contournement porte la date d'une journée voisine sans en
    # être le point : il ne compte pas.
    deja = {(f['properties']['date'], f['properties']['navire']) for f in appuis
            if not f['properties'].get('contournement')}
    trous = {}      # (ia, ib) -> [(date, navire)]
    orphelines = []
    for date in sorted(jours_voulus):
        navire = navire_du(date)
        if not navire or (date, navire) in deja:
            continue
        # A : dernier appui sûr de ce navire avant la journée ; B : premier après.
        ia = ib = None
        for i, f in enumerate(appuis):
            p = f['properties']
            if p['navire'] != navire or p.get('contournement'):
                continue
            if p['date'] < date:
                ia = i
            elif p['date'] > date and ib is None:
                ib = i
        if ia is None or ib is None:
            orphelines.append(date)
            continue
        trous.setdefault((ia, ib), []).append((date, navire))

    # Pour chaque trou : la route de A à B (détours compris), les journées
    # posées le long d'elle, et les détours rangés entre elles.
    suites = {}      # ia -> suite à émettre juste après A
    consommes = set()
    for (ia, ib), journees in trous.items():
        a, b = appuis[ia], appuis[ib]
        navire = journees[0][1]
        d_a, d_b = a['properties']['date'], b['properties']['date']
        detours = [j for j in range(ia + 1, ib)
                   if appuis[j]['properties']['navire'] == navire
                   and appuis[j]['properties'].get('contournement')]
        sommets = [a['geometry']['coordinates']] + \
                  [appuis[j]['geometry']['coordinates'] for j in detours] + \
                  [b['geometry']['coordinates']]
        mouillage = km(sommets[0], sommets[-1]) < MOUILLAGE_KM
        elements = []
        cumul = 0.0
        for j, (u, v) in zip(detours, zip(sommets, sommets[1:])):
            cumul += km(u, v)
            elements.append((cumul, 1, j))
        for date, _ in journees:
            if mouillage:
                pos, s = list(sommets[0]), 0.0
            else:
                part = (jour(date) - jour(d_a)).days / (jour(d_b) - jour(d_a)).days
                pos, s = le_long(sommets, part)
            props = proprietes_estimees(date, navire, d_a, d_b, mouillage)
            ancien = anciens.get((date, navire))
            if ancien and ancien['properties'].get('sans_point_carte'):
                props['sans_point_carte'] = True
            elements.append((s, 0, {'type': 'Feature',
                                    'geometry': {'type': 'Point',
                                                 'coordinates': [round(pos[0], 5), round(pos[1], 5)]},
                                    'properties': props}))
        suite = []
        date_courante = d_a
        for _, genre, objet in sorted(elements, key=lambda e: (e[0], e[1])):
            if genre == 1:
                # Un détour prend la date du point qui le précède sur la route :
                # la carte trie par date, et il doit rester à sa place.
                appuis[objet]['properties']['date'] = date_courante
                consommes.add(objet)
                suite.append(appuis[objet])
            else:
                date_courante = objet['properties']['date']
                suite.append(objet)
        suites[ia] = suite

    sortie = []
    for i, f in enumerate(appuis):
        if i in consommes:
            continue
        sortie.append(f)
        sortie.extend(suites.get(i, []))
    return sortie, orphelines


def rattache_a_flinders(features):
    """Les points de contournement de Flinders n'avaient pas d'expédition : la
    fiche leur prêtait alors les journaux de Baudin."""
    n = 0
    for f in features:
        p = f['properties']
        if not str(p.get('expedition') or '').strip():
            p['expedition'] = 'Flinders'
            n += 1
    return n


# --------------------------------------------------------------------------
# Commande « ajouter »
# --------------------------------------------------------------------------

def commande_ajouter(ecrire_fichier):
    donnees = lire()
    avant = len(donnees['features'])
    rattaches = rattache_a_flinders(donnees['features'])
    features, orphelines = interpoler(donnees['features'], journees_du_journal())
    nouveaux = [f for f in features if est_estime(f['properties'])]
    au_mouillage = sum(1 for f in nouveaux if f['properties'].get('mouillage'))
    print(f'{avant} points → {len(features)} ({len(nouveaux)} journées estimées, '
          f'dont {au_mouillage} au mouillage)')
    print(f'{rattaches} points sans expédition rattachés à Flinders')
    if orphelines:
        print(f'{len(orphelines)} journées sans relevé encadrant : {", ".join(orphelines)}')
    dates = [f['properties']['date'] for f in features]
    print('ordre chronologique respecté :', dates == sorted(dates))
    if not ecrire_fichier:
        print('\nEssai à blanc. Relancer avec --ecrire.')
        return
    copie = PARCOURS + '.avant_calage'
    if not os.path.exists(copie):
        shutil.copy2(PARCOURS, copie)
        print(f'copie de sûreté : {os.path.relpath(copie, RACINE)}')
    donnees['features'] = features
    ecrire(donnees)
    print('✅ écrit')


# --------------------------------------------------------------------------
# Calage manuel
# --------------------------------------------------------------------------

def consigne(entree):
    journal = []
    if os.path.exists(CONSIGNE):
        journal = json.load(open(CONSIGNE, encoding='utf-8'))
    entree['le'] = dt.datetime.now().isoformat(timespec='seconds')
    journal.append(entree)
    with open(CONSIGNE, 'w', encoding='utf-8') as f:
        json.dump(journal, f, ensure_ascii=False, indent=1)


def trouve(features, date, navire, rang=0):
    """Le point du jour pour ce navire ; `rang` départage les rares journées
    qui en comptent plusieurs (sortie de Spithead, King George's Sound…)."""
    n = 0
    for f in features:
        p = f['properties']
        if f['geometry']['type'] != 'Point' or p.get('contournement'):
            continue
        if p['date'] == date and p['navire'] == navire:
            if n == rang:
                return f
            n += 1
    return None


def points_de_calage(features):
    """Ce que la page affiche et met à jour : tous les points du parcours,
    relevés compris, sauf les détours de contournement."""
    rangs = {}
    sortie = []
    for f in features:
        p = f['properties']
        if f['geometry']['type'] != 'Point' or p.get('contournement'):
            continue
        cle = (p['date'], p['navire'])
        rang = rangs.get(cle, 0)
        rangs[cle] = rang + 1
        sortie.append({'date': p['date'], 'navire': p['navire'], 'rang': rang,
                       'lon': f['geometry']['coordinates'][0], 'lat': f['geometry']['coordinates'][1],
                       'cale': bool(p.get('cale')),
                       'estime': est_estime(p),
                       'releve': not p.get('interpole'),
                       'mouillage': bool(p.get('mouillage')),
                       'sans_point_carte': bool(p.get('sans_point_carte')),
                       'props': p})
    return sortie


def origine_du(date, navire, rang):
    """L'état d'un point de la source avant son premier calage, tel que le
    journal des gestes l'a gardé."""
    if not os.path.exists(CONSIGNE):
        return None
    for e in json.load(open(CONSIGNE, encoding='utf-8')):
        if (e.get('action') == 'caler' and e.get('origine') and e['date'] == date
                and e['navire'] == navire and e.get('rang', 0) == rang):
            return e['origine']
    return None


def action(donnees_requete):
    quoi = donnees_requete.get('action')
    date = donnees_requete.get('date')
    navire = donnees_requete.get('navire')
    rang = int(donnees_requete.get('rang') or 0)
    with verrou:
        donnees = lire()
        features = donnees['features']
        f = trouve(features, date, navire, rang)
        if quoi != 'etat' and not f:
            return 404, {'erreur': f'aucun point le {date} pour {navire}'}
        if quoi == 'caler':
            lon, lat = float(donnees_requete['lon']), float(donnees_requete['lat'])
            avant = list(f['geometry']['coordinates'])
            p = f['properties']
            entree = {'action': 'caler', 'date': date, 'navire': navire, 'rang': rang,
                      'lon': lon, 'lat': lat, 'avant': avant}
            estime = bool(p.get('interpole'))
            if not estime and not p.get('cale'):
                # Un point de la source : on garde de quoi le rétablir, et le
                # point dit d'où venait sa position.
                entree['origine'] = {'coordinates': avant, 'properties': dict(p)}
                p['position_d_origine'] = (
                    f"{avant[1]:.4f}, {avant[0]:.4f} — {p.get('table') or 'source'}"
                    + (f" ({p['alerte']})" if p.get('alerte') else ''))
            f['geometry']['coordinates'] = [round(lon, 5), round(lat, 5)]
            for cle in ('extrapole', 'interpole', 'mouillage', 'alerte', 'sans_point_carte'):
                p.pop(cle, None)
            p.update({'table': CARTE, 'cale': True,
                      'releve_carte': ("position relevée sur la carte générale que Flinders a "
                                       "dressée en 1814, au point de midi qui correspond "
                                       "à cette journée dans la suite des repères de la route")})
            if estime or p.get('interpole'):
                p['interpole'] = True
            consigne(entree)
        elif quoi == 'annuler':
            origine = origine_du(date, navire, rang) if 'position_d_origine' in f['properties'] else None
            if not origine and not f['properties'].get('interpole'):
                return 400, {'erreur': 'ce point de la source n’a pas été calé : rien à annuler'}
            if origine:
                # Un point de la source retrouve sa position et ses propriétés.
                f['geometry']['coordinates'] = origine['coordinates']
                f['properties'] = dict(origine['properties'])
            else:
                p = f['properties']
                for cle in ('cale', 'releve_carte', 'sans_point_carte'):
                    p.pop(cle, None)
                p['interpole'] = True
                p['extrapole'] = True
            consigne({'action': 'annuler', 'date': date, 'navire': navire, 'rang': rang,
                      'avant': list(f['geometry']['coordinates'])})
        elif quoi == 'sans_point':
            f['properties']['sans_point_carte'] = not f['properties'].get('sans_point_carte')
            consigne({'action': 'sans_point', 'date': date, 'navire': navire, 'rang': rang,
                      'valeur': f['properties']['sans_point_carte']})
        elif quoi != 'etat':
            return 400, {'erreur': f'action inconnue : {quoi}'}
        if quoi != 'etat':
            donnees['features'], _ = interpoler(features, journees_du_journal())
            ecrire(donnees)
        return 200, {'points': points_de_calage(donnees['features'])}


class Gestionnaire(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=RACINE, **k)

    def end_headers(self):
        # Rien en cache : la page doit relire le parcours tel qu'on vient de le caler.
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def log_message(self, fmt, *args):
        if '/api/' in (self.path or ''):
            super().log_message(fmt, *args)

    def repond(self, code, corps):
        texte = json.dumps(corps, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(texte)))
        self.end_headers()
        self.wfile.write(texte)

    def do_GET(self):
        if urllib.parse.urlparse(self.path).path == '/api/calage':
            code, corps = action({'action': 'etat'})
            return self.repond(code, corps)
        return super().do_GET()

    def do_POST(self):
        if urllib.parse.urlparse(self.path).path != '/api/calage':
            return self.repond(404, {'erreur': 'inconnu'})
        longueur = int(self.headers.get('Content-Length') or 0)
        try:
            requete = json.loads(self.rfile.read(longueur) or b'{}')
            code, corps = action(requete)
        except Exception as erreur:  # le calage ne doit jamais tuer le serveur
            code, corps = 500, {'erreur': str(erreur)}
        return self.repond(code, corps)


def commande_serveur(port):
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    serveur = http.server.ThreadingHTTPServer(('127.0.0.1', port), Gestionnaire)
    print(f'Site : http://localhost:{port}/map.html')
    print(f'Calage : http://localhost:{port}/map.html?calage=flinders')
    serveur.serve_forever()


if __name__ == '__main__':
    commande = sys.argv[1] if len(sys.argv) > 1 else ''
    if commande == 'ajouter':
        commande_ajouter('--ecrire' in sys.argv)
    elif commande == 'serveur':
        port = int(sys.argv[sys.argv.index('--port') + 1]) if '--port' in sys.argv else 8765
        commande_serveur(port)
    else:
        print(__doc__)
