#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verse dans le corpus du chatbot tout ce que le site publie.

Quatre gisements, quatre sorties :

  corpus/toponymes/      un fichier par toponyme, tiré de data/{baudin,
                         entrecasteaux,flinders}.json — c'est la maille que
                         l'on veut citer quand on demande « pourquoi ce nom ? »
  corpus/site/           une page du site, un fichier : les pages de la racine
                         et les 483 fiches détaillées de details/
  corpus/donnees/        les autres JSON : chronologies, attributions,
                         citations, relevés, tables de route
  corpus/journaux_site/  le texte des journaux que porte le site, mois par
                         mois — y compris les journées sans coordonnées, que
                         la carte ne montre jamais
  corpus/routes/         les relevés de route des trois expéditions et la
                         table de Freycinet, par expédition et par mois, une
                         section par journée

Usage : python3 rag/extraire_site.py
"""
import json
import os
import re
import unicodedata
from collections import defaultdict

from bs4 import BeautifulSoup

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(RACINE, 'rag', 'corpus')
SITE = 'https://www.frenchplacenames.au'

# Pages de la racine qui ne portent aucun contenu propre.
PAGES_IGNOREES = {'site_map.html', 'sources.html', 'Viewer.html'}

# Géométries pures : des millions de coordonnées, pas un mot de texte.
JSON_IGNORES = {'ne_10m_coastline.geojson', 'ne_10m_land.geojson', 'img_alias.json'}

EXPEDITIONS = {
    'baudin.json': ('Baudin', "expédition Baudin (1800-1804)"),
    'entrecasteaux.json': ('Entrecasteaux', "expédition d'Entrecasteaux (1791-1794)"),
    'flinders.json': ('Flinders', "voyage de Matthew Flinders (1801-1803)"),
}

JOURNAUX_DU_SITE = {
    'journal_baudin_autographe': "Journal de mer autographe de Nicolas Baudin",
    'journal_baudin': "Journal de Nicolas Baudin",
    'journal_anonyme': "Journal anonyme du Naturaliste",
    'journal_breton_geographe': "Journal de Désiré Breton (le Géographe)",
    'journal_breton_naturaliste': "Journal de Désiré Breton (le Naturaliste)",
    'journal_geographe': "Journal de bord du Géographe",
    'journal_flinders': "Récit de Matthew Flinders, A Voyage to Terra Australis",
}

MOIS = ('janvier février mars avril mai juin juillet août septembre '
        'octobre novembre décembre').split()


def ardoise(nom):
    """Un nom de fichier sûr, sans accent ni espace."""
    nom = unicodedata.normalize('NFKD', nom).encode('ascii', 'ignore').decode()
    return re.sub(r'[^A-Za-z0-9._-]+', '_', nom).strip('_')


def entete(titre, source, langue='fr', complements=()):
    lignes = ['---', f'titre: "{titre}"', f'langue: {langue}', f'source: "{source}"']
    for cle, valeur in complements:
        if valeur not in ('', None):
            lignes.append(f'{cle}: "{valeur}"')
    lignes += ['---', '', f'# {titre}', '']
    return '\n'.join(lignes)


def ecrit(sous_dossier, nom, contenu):
    dossier = os.path.join(CORPUS, sous_dossier)
    os.makedirs(dossier, exist_ok=True)
    with open(os.path.join(dossier, nom), 'w', encoding='utf-8') as f:
        f.write(contenu)


def texte_html(chemin):
    """Le texte d'une page, sans les scripts, les styles ni la navigation."""
    with open(chemin, encoding='utf-8', errors='replace') as f:
        soupe = BeautifulSoup(f.read(), 'html.parser')
    titre = soupe.title.get_text(strip=True) if soupe.title else ''
    for balise in soupe(['script', 'style', 'noscript', 'nav', 'footer', 'svg']):
        balise.decompose()
    for classe in ('lang-switcher', 'chatbot-widget', 'back-to-top'):
        for balise in soupe.select(f'.{classe}'):
            balise.decompose()

    morceaux = []
    for balise in soupe.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'li', 'figcaption',
                                 'td', 'th', 'blockquote', 'dt', 'dd']):
        mot = balise.get_text(' ', strip=True)
        if not mot:
            continue
        if balise.name in ('h1', 'h2', 'h3', 'h4'):
            niveau = '#' * (int(balise.name[1]) + 1)
            morceaux.append(f'\n{niveau} {mot}\n')
        elif balise.name == 'li':
            morceaux.append(f'- {mot}')
        else:
            morceaux.append(mot)

    texte = '\n\n'.join(morceaux)
    texte = re.sub(r'\n{3,}', '\n\n', texte)
    return titre, texte.strip()


# --------------------------------------------------------------------------
# 1. Les toponymes, un fichier chacun
# --------------------------------------------------------------------------

def fiche_toponyme(rec, expedition, periode):
    titre = rec.get('frenchName') or rec.get('ausEName') or rec['code']
    actuel = rec.get('ausEName', '')
    lignes = [entete(
        f"{titre} ({actuel})" if actuel and actuel != titre else titre,
        f"{SITE}/map.html — fiche {rec['code']}, {periode}",
        'fr',
        [('code', rec['code']), ('expedition', expedition),
         ('nom_francais', rec.get('frenchName', '')),
         ('nom_australien', actuel),
         ('etat', rec.get('state', '')),
         ('latitude', rec.get('lat', '')), ('longitude', rec.get('lon', ''))],
    )]

    def bloc(entete_, valeur):
        if valeur and str(valeur).strip():
            lignes.append(f'\n## {entete_}\n\n{str(valeur).strip()}')

    bloc("Identité", '\n'.join(filter(None, [
        f"- Nom français : {rec.get('frenchName','')}" if rec.get('frenchName') else '',
        f"- Variante : {rec['variantName']}" if rec.get('variantName') else '',
        f"- Nom australien actuel : {actuel}" if actuel else '',
        f"- Nom autochtone : {rec['indigenousName']}" if rec.get('indigenousName') else '',
        f"- Langue autochtone : {rec['indigenousLanguage']}" if rec.get('indigenousLanguage') else '',
        f"- État : {rec.get('state','')}",
        f"- Coordonnées : {rec.get('lat','')}, {rec.get('lon','')}",
        f"- Expédition : {expedition} — {periode}",
        f"- Navire : {rec['navire']}" if rec.get('navire') else '',
        f"- Date d'attribution : {rec['date']}" if rec.get('date') else '',
        f"- Secteur : {rec['secteur']}" if rec.get('secteur') else '',
        f"- Catégorie : {rec['categorie']}" if rec.get('categorie') else '',
    ])))
    bloc("Origine du nom", rec.get('origin_fr'))
    bloc("Description (français)", rec.get('characteristic_fr'))
    bloc("Description (anglais)", rec.get('characteristic'))
    bloc("Histoire (français)", rec.get('history_fr'))
    bloc("Histoire (anglais)", rec.get('history'))
    bloc("Commentaire", rec.get('commentaire'))
    bloc("Carte", '\n'.join(filter(None, [
        rec.get('mapTitle_fr', ''), rec.get('mapTitle_en', ''),
    ])))
    liens = [f'- {c} : {rec[k]}' for k, c in (
        ('wiki_fr', 'Wikipédia (fr)'), ('wiki_en', 'Wikipédia (en)'),
        ('other_link', 'Autre ressource'),
        ('detailsLink', 'Fiche détaillée (fr)'), ('detailsLink_en', 'Fiche détaillée (en)'),
    ) if rec.get(k)]
    bloc("Liens", '\n'.join(liens))
    return '\n'.join(lignes) + '\n'


def extrait_toponymes():
    print('\n📍 Toponymes')
    total = 0
    for fichier, (expedition, periode) in EXPEDITIONS.items():
        chemin = os.path.join(RACINE, 'data', fichier)
        données = json.load(open(chemin, encoding='utf-8'))
        for rec in données:
            ecrit('toponymes', f"{ardoise(rec['code'])}.md",
                  fiche_toponyme(rec, expedition, periode))
        total += len(données)
        print(f'  ✅ {expedition} : {len(données)} fiches')
    return total


# --------------------------------------------------------------------------
# 2. Les pages du site
# --------------------------------------------------------------------------

def extrait_pages():
    print('\n🌐 Pages du site')
    pages = sorted(f for f in os.listdir(RACINE)
                   if f.endswith('.html') and f not in PAGES_IGNOREES)
    for fichier in pages:
        titre, texte = texte_html(os.path.join(RACINE, fichier))
        if len(texte) < 200:
            continue
        ecrit('site', 'page_' + ardoise(fichier[:-5]) + '.md',
              entete(titre or fichier, f'{SITE}/{fichier}', 'fr',
                     [('type', 'page du site')]) + '\n' + texte + '\n')
    print(f'  ✅ {len(pages)} pages de la racine')

    dossier = os.path.join(RACINE, 'details')
    fiches = sorted(f for f in os.listdir(dossier) if f.endswith('.html'))
    gardees = 0
    for fichier in fiches:
        titre, texte = texte_html(os.path.join(dossier, fichier))
        if len(texte) < 200:
            continue
        code = fichier[:-5]
        langue = 'fr' if code.endswith('F') else 'en'
        ecrit('site', 'fiche_' + ardoise(code) + '.md',
              entete(titre or code, f'{SITE}/details/{fichier}', langue,
                     [('type', 'fiche détaillée'), ('code', code[:-1])]) + '\n' + texte + '\n')
        gardees += 1
    print(f'  ✅ {gardees} fiches détaillées sur {len(fiches)}')
    return len(pages) + gardees


# --------------------------------------------------------------------------
# 3. Les journaux, mois par mois, journées sans position comprises
# --------------------------------------------------------------------------

def libelle_mois(cle):
    annee, mois = cle.split('-')
    return f'{MOIS[int(mois) - 1]} {annee}'


def libelle_jour(date):
    annee, mois, jour = date.split('-')
    quantieme = '1er' if jour == '01' else str(int(jour))
    return f'{quantieme} {MOIS[int(mois) - 1]} {annee}'


def entete_de_journee(date, nom_journal, complement=''):
    """Le titre d'une journée, et une phrase qui se suffit à elle-même.

    Un fichier porte un mois entier, et le découpage en morceaux indexables
    tombe où il veut. Un titre réduit à « ## 1801-07-31 » se retrouvait noyé au
    milieu d'un morceau parlant de Madère, et une question sur le 31 juillet
    ramenait le bon fichier mais le mauvais passage.

    On répète donc la date sous ses deux formes — en toutes lettres et en
    chiffres — et on nomme le journal, dans une phrase qui tient seule. Où que
    la coupe tombe, le morceau dit de quel jour il parle.
    """
    jour = libelle_jour(date)
    titre = f'## {jour} — {date}'
    if complement:
        titre += f' ({complement})'
    return f'\n{titre}\n\nJournée du {jour}. {nom_journal}, {date}.\n\n'


def extrait_journaux():
    print('\n📖 Journaux publiés par le site')
    total = 0
    for fichier, langue in (('baudin_fr.json', 'fr'), ('baudin_en.json', 'en'),
                            ('flinders_fr.json', 'fr'), ('flinders_en.json', 'en')):
        chemin = os.path.join(RACINE, 'data', 'journaux', fichier)
        if not os.path.exists(chemin):
            continue
        données = json.load(open(chemin, encoding='utf-8'))
        campagne = fichier.split('_')[0]

        # Un fichier par journal et par mois : assez gros pour que le contexte
        # tienne, assez fin pour qu'une réponse cite une date juste.
        par_journal = defaultdict(lambda: defaultdict(list))
        for date in sorted(données):
            for champ, texte in (données[date] or {}).items():
                if texte and str(texte).strip():
                    par_journal[champ][date[:7]].append((date, str(texte).strip()))

        for champ, mois_ in par_journal.items():
            nom_journal = JOURNAUX_DU_SITE.get(champ, champ)
            for cle_mois, journees in sorted(mois_.items()):
                corps = []
                for date, texte in journees:
                    corps.append(entete_de_journee(date, nom_journal) + texte + '\n')
                titre = f'{nom_journal} — {libelle_mois(cle_mois)}'
                ecrit('journaux_site',
                      f'{ardoise(campagne)}_{ardoise(champ)}_{cle_mois}_{langue}.md',
                      entete(titre, f'{SITE}/map.html — journaux de bord, {cle_mois}',
                             langue,
                             [('journal', nom_journal), ('mois', cle_mois),
                              ('journees', len(journees))])
                      + ''.join(corps) + '\n')
                total += 1
        print(f'  ✅ {fichier} : {len(données)} journées → {sum(len(m) for m in par_journal.values())} fichiers')

    # data/journal_*.json sont les journaux tels que les scripts d'origine les
    # ont produits ; data/journaux/baudin_fr.json les rassemble ensuite pour la
    # carte. Le rassemblement est fidèle sauf pour Breton, dont 114 journées ne
    # sont reprises ni sous le Géographe ni sous le Naturaliste. Ce sont elles
    # qu'on va chercher ici — sans quoi elles resteraient hors de portée.
    rassemble = json.load(open(os.path.join(RACINE, 'data', 'journaux', 'baudin_fr.json'),
                               encoding='utf-8'))
    chemin = os.path.join(RACINE, 'data', 'journal_breton.json')
    if os.path.exists(chemin):
        breton = json.load(open(chemin, encoding='utf-8'))
        oubliees = {d: t for d, t in breton.items()
                    if t and str(t).strip()
                    and not any((rassemble.get(d) or {}).get(c) for c in
                                ('journal_breton_geographe', 'journal_breton_naturaliste'))}
        par_mois = defaultdict(list)
        for date in sorted(oubliees):
            par_mois[date[:7]].append((date, str(oubliees[date]).strip()))
        for cle_mois, journees in sorted(par_mois.items()):
            corps = ''.join(
                entete_de_journee(date, 'Journal de Désiré Breton') + texte + '\n'
                for date, texte in journees)
            ecrit('journaux_site', f'breton_hors_carte_{cle_mois}_fr.md', entete(
                f"Journal de Désiré Breton — {libelle_mois(cle_mois)} (journées hors carte)",
                f'{SITE}/data/journal_breton.json',
                'fr', [('journal', 'Journal de Désiré Breton'), ('mois', cle_mois),
                       ('note', "journées que le rassemblement des journaux ne reprend pas")],
            ) + corps + '\n')
            total += 1
        print(f'  ✅ journal_breton.json : {len(oubliees)} journées hors carte récupérées')

    # Le journal de Baudin dans l'édition imprimée de la BnF, océrisé.
    chemin = os.path.join(RACINE, 'data', 'journal_baudin_bnf.json')
    if os.path.exists(chemin):
        données = json.load(open(chemin, encoding='utf-8'))
        par_mois = defaultdict(list)
        for date in sorted(données):
            par_mois[date[:7]].append((date, données[date]))
        for cle_mois, journees in sorted(par_mois.items()):
            corps = []
            for date, rec in journees:
                texte = (rec.get('texte') or '').strip()
                if not texte:
                    continue
                tete = rec.get('entete', '')
                rep = rec.get('republicain', '')
                corps.append(entete_de_journee(
                    date, 'Journal de Nicolas Baudin, édition BnF', rep)
                    + (f'*{tete}*\n\n' if tete else '') + texte + '\n')
            if not corps:
                continue
            ecrit('journaux_site', f'baudin_bnf_{cle_mois}_fr.md', entete(
                f"Journal de Nicolas Baudin, édition BnF — {libelle_mois(cle_mois)}",
                "transcription océrisée de l'édition imprimée, Bibliothèque nationale de France",
                'fr', [('journal', 'Journal de Baudin, édition BnF'), ('mois', cle_mois)],
            ) + ''.join(corps) + '\n')
            total += 1
        print(f'  ✅ journal_baudin_bnf.json : {len(données)} journées')
    return total


# --------------------------------------------------------------------------
# 4. Les routes, relevé par relevé
# --------------------------------------------------------------------------

# Un parcours versé d'un bloc faisait un fichier de 200 à 400 Ko, une ligne par
# jour, datée seulement « 1793-01-01 ». Le découpage en morceaux indexables
# ramenait le bon fichier mais un morceau voisin, et le chatbot lisait la ligne
# d'un autre jour. On reprend donc la recette des journaux : un fichier par
# mois, un titre par journée, la date en lettres et en chiffres, et une phrase
# qui nomme l'expédition, le navire et la position sans rien devoir au reste.
ROUTES = {
    # fichier : (clé, nom, navires par défaut, source des relevés)
    'dentrecasteaux_parcours.geojson': (
        'dentrecasteaux', "Expédition d'Entrecasteaux",
        "la Recherche et l'Espérance",
        "tables de route publiées par Rossel, Voyage de Dentrecasteaux (Paris, 1808)"),
    'baudin_parcours.geojson': (
        'baudin', "Expédition Baudin", "le Géographe et le Naturaliste",
        "tables de route publiées par Louis de Freycinet (Paris, 1815)"),
    'flinders_parcours.geojson': (
        'flinders', "Voyage de Flinders", "l'Investigator",
        "Matthew Flinders, A Voyage to Terra Australis et General Chart of Terra Australis (Londres, 1814)"),
}
# Libellés lisibles des champs ; les autres passent sous leur nom d'origine.
CHAMPS_ROUTE = {
    'section': 'Section de la table', 'table': 'Table', 'page': 'Page',
    'page_verso': 'Page (verso)', 'page_recto': 'Page (recto)',
    'date_republicaine': 'Date républicaine',
    'source_latitude': 'Nature de la latitude', 'source_longitude': 'Nature de la longitude',
    'obs_latitude': 'Latitude observée', 'obs_longitude': 'Longitude observée',
    'vents_etat_du_ciel': 'Vents et état du ciel', 'barometre_hpa': 'Baromètre (hPa)',
    'thermometre': 'Thermomètre', 'hygrometre': 'Hygromètre',
    'declinaison_dms': 'Déclinaison de la boussole', 'declinaison_ref': 'Déclinaison vers',
    'declinaison_boussole': 'Déclinaison de la boussole',
    'remarque': 'Remarque', 'remarque_portee': 'Portée de la remarque',
    'mouillage': 'Au mouillage', 'au_mouillage': 'Au mouillage',
    'alerte': 'Avertissement', 'notes': 'Notes',
}
CHAMPS_ROUTE_TUS = {'date', 'navire', 'expedition', 'longitude_brute', 'ajustement_lon',
                    'extrapole'}


def dms(valeur, positif, negatif):
    v = abs(valeur)
    degres = int(v)
    minutes = round((v - degres) * 60)
    if minutes == 60:
        degres, minutes = degres + 1, 0
    return f"{degres}°{minutes:02d}′ {positif if valeur >= 0 else negatif}"


def vrai(valeur):
    return valeur is True or str(valeur).strip().lower() in ('true', 'oui', '1')


def phrase_de_releve(date, expedition, navire, lat, lon, reconstitue):
    jour = libelle_jour(date)
    position = (f"latitude {dms(lat, 'N', 'S')} ({lat:.4f}), "
                f"longitude {dms(lon, 'E', 'O')} de Greenwich ({lon:.4f})")
    nature = ("position reconstituée, non relevée ce jour-là" if reconstitue
              else "position de la table")
    return f"Relevé de route du {jour}. {expedition}, {navire}, {date} : {position} — {nature}."


def extrait_routes():
    print('\n🧭 Routes des trois expéditions')
    dossier = os.path.join(RACINE, 'data')
    sortie = os.path.join(CORPUS, 'routes')
    if os.path.isdir(sortie):
        for vieux in os.listdir(sortie):
            if vieux.endswith('.md'):
                os.remove(os.path.join(sortie, vieux))
    total = 0
    for fichier, (cle, expedition, navires_defaut, source) in ROUTES.items():
        de_qui = {'dentrecasteaux': "de l’expédition d'Entrecasteaux",
                  'baudin': "de l’expédition Baudin",
                  'flinders': "du voyage de Flinders"}[cle]
        chemin = os.path.join(dossier, fichier)
        if not os.path.exists(chemin):
            continue
        traits = json.load(open(chemin, encoding='utf-8')).get('features', [])
        par_mois = defaultdict(lambda: defaultdict(list))
        for t in traits:
            p = t.get('properties', {})
            geo = (t.get('geometry') or {}).get('coordinates') or []
            date = str(p.get('date') or '')
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', date) or len(geo) < 2:
                continue
            par_mois[date[:7]][date].append((p, float(geo[1]), float(geo[0])))
        for cle_mois, jours in sorted(par_mois.items()):
            corps = []
            for date in sorted(jours):
                corps.append(f'\n## {libelle_jour(date)} — {date}\n')
                for p, lat, lon in jours[date]:
                    navire = p.get('navire') or navires_defaut
                    corps.append('\n' + phrase_de_releve(date, expedition, navire, lat, lon,
                                                          vrai(p.get('extrapole'))) + '\n')
                    for k, v in p.items():
                        if k in CHAMPS_ROUTE_TUS or v in ('', None) or v is False:
                            continue
                        v = 'oui' if v is True else v
                        corps.append(f'- {CHAMPS_ROUTE.get(k, k)} : {v}\n')
            nb = sum(len(v) for v in jours.values())
            titre = f'{expedition} — route de {libelle_mois(cle_mois)}'
            ecrit('routes', f'route_{cle}_{cle_mois}.md', entete(
                titre, f'{SITE}/data/{fichier}', 'fr',
                [('type', 'relevés de route'), ('expedition', expedition),
                 ('mois', cle_mois), ('releves', nb), ('source_des_releves', source)],
            ) + f'Relevés de route {de_qui} pour {libelle_mois(cle_mois)}, d’après les {source}. '
              'Latitudes et longitudes ramenées au méridien de Greenwich.\n'
              + ''.join(corps) + '\n')
            total += 1
        print(f'  ✅ {fichier} : {len(traits)} relevés → {len(par_mois)} mois')

    # La table de Freycinet elle-même, qui garde ce que le parcours ne reprend
    # pas : dates républicaines, longitudes comptées depuis Paris, degrés et
    # minutes tels qu'imprimés, points lunaires et solaires.
    import csv
    chemin = os.path.join(dossier, 'baudin_tables_de_route.csv')
    if os.path.exists(chemin):
        lignes = list(csv.DictReader(open(chemin, encoding='utf-8', errors='replace')))
        par_mois = defaultdict(list)
        for r in lignes:
            date = (r.get('date_gregorienne') or r.get('date') or '').strip()
            if re.match(r'^\d{4}-\d{2}-\d{2}$', date):
                par_mois[date[:7]].append((date, r))
        for cle_mois, rangs in sorted(par_mois.items()):
            corps = []
            for date, r in sorted(rangs, key=lambda x: x[0]):
                rep_ = (r.get('date_republicaine') or '').strip()
                navire = (r.get('navire') or '').strip() or 'les corvettes'
                corps.append(f"\n## {libelle_jour(date)} — {date}"
                             + (f" ({rep_})" if rep_ else '') + f" — {navire}\n\n"
                             f"Table de route de Freycinet, {libelle_jour(date)}, {navire}, {date}"
                             + (f", {rep_}" if rep_ else '') + '.\n')
                for k, v in r.items():
                    v = (v or '').strip()
                    if not v or k in ('date', 'date_gregorienne', 'navire', 'date_republicaine'):
                        continue
                    corps.append(f'- {CHAMPS_ROUTE.get(k, k)} : {v}\n')
            ecrit('routes', f'table_freycinet_{cle_mois}.md', entete(
                f"Tables de route de Freycinet (expédition Baudin) — {libelle_mois(cle_mois)}",
                f'{SITE}/data/baudin_tables_de_route.csv', 'fr',
                [('type', 'table de route'), ('mois', cle_mois), ('lignes', len(rangs)),
                 ('note', "longitude_paris : comptée depuis le méridien de Paris ; latitude et longitude : ramenées à Greenwich")],
            ) + ''.join(corps) + '\n')
            total += 1
        print(f'  ✅ baudin_tables_de_route.csv : {len(lignes)} lignes → {len(par_mois)} mois')
    return total


# --------------------------------------------------------------------------
# 5. Les autres JSON
# --------------------------------------------------------------------------

def aplatit(valeur, profondeur=0):
    """Rend un JSON quelconque en listes Markdown, sans accolades ni guillemets."""
    marge = '  ' * profondeur
    if isinstance(valeur, dict):
        lignes = []
        for cle, sous in valeur.items():
            if sous in ('', None, [], {}):
                continue
            if isinstance(sous, (dict, list)):
                lignes.append(f'{marge}- **{cle}** :')
                lignes.append(aplatit(sous, profondeur + 1))
            else:
                lignes.append(f'{marge}- **{cle}** : {sous}')
        return '\n'.join(lignes)
    if isinstance(valeur, list):
        return '\n'.join(aplatit(v, profondeur) for v in valeur)
    return f'{marge}{valeur}'


def extrait_donnees():
    print('\n🗂  Autres données')
    dossier = os.path.join(RACINE, 'data')
    # Les journaux sont déjà versés mois par mois par extrait_journaux(), avec
    # leurs dates en titres de section ; les reverser ici en aplat n'ajouterait
    # qu'un doublon sans repère de date.
    dejà_vus = set(EXPEDITIONS) | {
        'journal_baudin_bnf.json', 'journal_baudin_bnf.txt',
        'journal_anonyme.json', 'journal_baudin.json',
        'journal_breton.json', 'journal_geographe.json',
    }
    fichiers = sorted(f for f in os.listdir(dossier)
                      if f.endswith(('.json', '.geojson'))
                      and f not in JSON_IGNORES and f not in dejà_vus
                      and f not in ROUTES)
    # Les routes ont leur propre gisement (extrait_routes) : on retire l'ancien
    # aplat d'un seul tenant, qui ramenait la ligne d'un autre jour.
    for f in list(ROUTES) + ['baudin_tables_de_route.csv']:
        vieux = os.path.join(CORPUS, 'donnees', ardoise(os.path.splitext(f)[0]) + '.md')
        if os.path.exists(vieux):
            os.remove(vieux)
    for fichier in fichiers:
        chemin = os.path.join(dossier, fichier)
        try:
            données = json.load(open(chemin, encoding='utf-8'))
        except Exception as erreur:
            print(f'  ⚠️  {fichier} : {erreur}')
            continue

        if fichier.endswith('.geojson'):
            traits = données.get('features', [])
            corps = ['Relevés de position, un par journée ou par observation.', '']
            for trait in traits:
                p = trait.get('properties', {})
                geo = (trait.get('geometry') or {}).get('coordinates') or ['', '']
                détail = ' ; '.join(f'{k} : {v}' for k, v in p.items() if v not in ('', None))
                corps.append(f"- {p.get('date', '?')} — {geo[1]}, {geo[0]} — {détail}")
            texte = '\n'.join(corps)
            nature = 'parcours'
        else:
            texte = aplatit(données)
            nature = 'données'

        if len(texte) < 80:
            continue
        ecrit('donnees', ardoise(os.path.splitext(fichier)[0]) + '.md', entete(
            f'Données du site — {fichier}', f'{SITE}/data/{fichier}', 'fr',
            [('type', nature), ('fichier', fichier)],
        ) + '\n' + texte + '\n')
    print(f'  ✅ {len(fichiers)} fichiers de données')

    # Les autres CSV. La table de Freycinet est versée mois par mois par
    # extrait_routes().
    for fichier in sorted(f for f in os.listdir(dossier)
                          if f.endswith('.csv') and f != 'baudin_tables_de_route.csv'):
        with open(os.path.join(dossier, fichier), encoding='utf-8', errors='replace') as f:
            contenu = f.read()
        ecrit('donnees', ardoise(os.path.splitext(fichier)[0]) + '.md', entete(
            f'Table de route — {fichier}', f'{SITE}/data/{fichier}', 'fr',
            [('type', 'table de route'), ('fichier', fichier)],
        ) + '\n```\n' + contenu + '\n```\n')
    return len(fichiers)


def main():
    extrait_toponymes()
    extrait_pages()
    extrait_journaux()
    extrait_routes()
    extrait_donnees()
    print('\n📦 Corpus')
    grand_total = 0
    for sous in sorted(os.listdir(CORPUS)):
        chemin = os.path.join(CORPUS, sous)
        if not os.path.isdir(chemin):
            continue
        fichiers = [f for f in os.listdir(chemin) if f.endswith('.md')]
        poids = sum(os.path.getsize(os.path.join(chemin, f)) for f in fichiers)
        grand_total += len(fichiers)
        print(f'  {sous:<18} {len(fichiers):>5} fichiers  {poids / 1e6:>6.1f} Mo')
    print(f'  {"TOTAL":<18} {grand_total:>5} fichiers')


if __name__ == '__main__':
    main()
