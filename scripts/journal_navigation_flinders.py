#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verse dans les fiches parcours le journal de navigation de Flinders.

Ce n'est pas le recit publie en 1814 (champ journal_flinders), mais le
journal tenu au jour le jour sur l'Investigator, conserve a la Mitchell
Library (State Library of New South Wales, Safe 1/24 et Safe 1/25) et
transcrit par ses benevoles. Les deux volumes, exportes en PDF depuis le
site de la bibliotheque, sont dans
Toponymes/01_Sources/Journaux_de_bord/Flinders :

    vol. 1 : 19 janvier 1801 - juillet 1802 (Port Jackson)
    vol. 2 : 22 juillet 1802 - 10 juin 1803

Les positions n'y sont pas transcrites (« [Navigational data not
transcribed] ») : ce journal enrichit les fiches, il ne touche pas au trace.

Le journal compte presque tous les jours, le parcours non. Une journee sans
point va au point suivant de l'Investigator : le jour nautique de Flinders
court de midi a midi, et s'acheve a la position de midi qui porte sa date.
Les en-tetes de journee du journal restent dans le texte et separent les
jours reunis sur une meme fiche. Les notes anterieures au 17 juillet 1801
(armement a Sheerness et Spithead) n'ont pas de fiche ou s'afficher.

Ce script n'ecrit QUE le champ journal_flinders_navigation des fichiers
data/journaux/flinders_en.json et flinders_fr.json : ni le GeoJSON du
parcours, ni le champ journal_flinders n'y sont touches.

    python3 scripts/journal_navigation_flinders.py extraire
        -> Toponymes/01_Sources/Numerisations/flinders_navigation/en/AAAA-MM-JJ.txt, une
           journee par fichier, sources de la traduction
    python3 scripts/journal_navigation_flinders.py ratures [--ecrire]
        -> marque entre ⟦ et ⟧, dans les fichiers en/ deja extraits, les
           passages barres du PDF (vol. 2 seulement : le vol. 1 ne transcrit
           pas ses ratures). Le texte hors marques ne change pas.
    python3 scripts/journal_navigation_flinders.py integrer [--ecrire]
        -> anglais depuis en/, francais depuis fr/ (les journees non encore
           traduites restent absentes du francais : la fiche montre alors
           l'anglais, signale comme non traduit)
"""
import datetime as dt, glob, json, os, re, sys
from collections import OrderedDict

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOPONYMES = os.path.dirname(RACINE)
DOCS = os.path.join(TOPONYMES, '01_Sources', 'Journaux_de_bord', 'Flinders')
VOLUMES = [
    ("Matthew Flinders journal on HMS 'Investigator', vol. 1, 1801-1802.pdf",
     dt.date(1801, 7, 17), '[Page 58]'),
    ("Matthew Flinders journal on the Investigator, vol. 2, 24 July 1802-10 June 1803.pdf",
     dt.date(1802, 7, 22), None),
]
SOURCES = os.path.join(TOPONYMES, '01_Sources', 'Numerisations', 'flinders_navigation')
PARCOURS = os.path.join(RACINE, 'data', 'flinders_parcours.geojson')
JOURNAUX = {l: os.path.join(RACINE, 'data', 'journaux', f'flinders_{l}.json') for l in ('en', 'fr')}
CHAMP = 'journal_flinders_navigation'

MOIS = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6, 'jul': 7,
        'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
JOURS = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}

M = r'(?:Jan|Feb|Mar|Apr|May|June?|July?|Aug|Sept?|Oct|Nov|Dec)[a-z]*\.?:?,?'
W = r'(?:Sun|Mon|Tue|Wed|Thu|Fri|Sat)[a-z]*\.?'
ENTETE = re.compile(
    r'^\s*\[?\s*(?:Continuation of\s+)?(?P<y1>18\d\d)?\s*(?:' + M + r'\s+(?=' + M + r'))?(?P<m1>' + M + r')?\s*(?P<y3>18\d\d)?\.?\s*'
    r'\[?\s*(?P<w>' + W + r')?\s*\]?\s*[-–]?\s*(?P<m2>' + M + r')?\s*'
    r'(?P<d>\d{1,3})(?:st|nd|rd|th|d)?\b\s*\.?\s*(?:[.,]?\s*(?P<y2>18\d\d))?')
JOUR_SEUL = re.compile(r'^\s*(' + W + r')\s*$')
NOMBRE_SEUL = re.compile(r'^\s*(\d{1,2})\s*$')
EDITORIAL = re.compile(r'^\s*\[\s*(\[|18\d\d|' + M + r'|Continuation)')


def est_entete(l):
    me = ENTETE.match(re.sub(r'\s+', ' ', l.strip())[:90])
    return bool(me and (me.group('w') or me.group('m1') or me.group('m2')))


PAGE = re.compile(r'^\s*\[Page \d+\]\s*$')


def mois(s):
    return MOIS[s.strip('.:, ').lower()[:3]] if s else None


def resout(g, cour):
    """Date proposée par un en-tête, ou None si elle ne cadre pas."""
    m = mois(g['m1'] or g['m2'])
    y = int(g['y1'] or g['y2'] or g.get('y3') or 0) or None
    w = JOURS[g['w'][:3].lower()] if g['w'] else None
    if m is None and w is None:
        return None, 'ni mois ni jour'
    brut = g['d']
    jours = [int(brut)] + ([int(brut[-2:]), int(brut[-1:])] if len(brut) > 2 else [])
    cands = []
    annees = [y or cour.year] + ([cour.year] if y and y != cour.year else [])
    for d in jours:
        couples = ([(a, m) for a in annees] if m else
                   [(cour.year, cour.month),
                    ((cour.replace(day=1) + dt.timedelta(days=32)).year,
                     (cour.replace(day=1) + dt.timedelta(days=32)).month),
                    ((cour.replace(day=1) - dt.timedelta(days=1)).year,
                     (cour.replace(day=1) - dt.timedelta(days=1)).month)])
        for (yy, mm) in couples:
            if m and not y and cour and mm < cour.month - 6:
                yy += 1
            if m and not y and cour and mm > cour.month + 6:
                yy -= 1
            try:
                c = dt.date(yy, mm, d)
            except ValueError:
                continue
            cands.append(c)
    # En avant, jusqu'a 25 jours ; en arriere (journal de mouillage qui
    # reprend les jours passes), seulement si le jour de semaine confirme.
    avec_jour = [c for c in cands if 0 <= (c - cour).days <= 25
                 and (w is None or c.weekday() == w)]
    if avec_jour:
        return avec_jour[0], None
    arriere = [c for c in cands if -15 <= (c - cour).days < 0
               and w is not None and c.weekday() == w]
    if arriere:
        return arriere[0], 'retour en arriere'
    # Remarques rejetees en fin de volume : « May 9. 1802 continued. Additional remarks ».
    if m and y and g.get('suite'):
        loin = [c for c in cands if (c - cour).days < 0 and c.year == y]
        if loin:
            return loin[0], 'remarques reportees'
    # Le jour qui suit, meme si Flinders s'est trompe de jour de semaine.
    suivant = [c for c in cands if 0 <= (c - cour).days <= 2]
    if suivant:
        return suivant[0], 'jour de semaine discordant'
    bons = [c for c in cands if 0 <= (c - cour).days <= 25]
    if bons and m:
        return bons[0], 'jour de semaine discordant'
    return None, 'hors fenêtre %s' % cands[:2]


def decoupe(lignes, debut, alertes, nom):
    jours = OrderedDict()
    cour = debut - dt.timedelta(days=1)
    actif = False
    apres_page = False
    sauter_suivante = False
    i = 0
    while i < len(lignes):
        l = lignes[i]
        if PAGE.match(l):
            apres_page = True
            i += 1
            continue
        if l.strip() == '':
            i += 1
            continue
        if sauter_suivante:
            sauter_suivante = False
            if EDITORIAL.match(l) and est_entete(l):
                i += 1
                continue
        # Double page : le titre que le transcripteur restitue en tete de la
        # page de droite cede la place au vrai titre du jour qui le suit.
        suivante = lignes[i + 1] if i + 1 < len(lignes) else ''
        if apres_page and EDITORIAL.match(l) and est_entete(l) \
                and est_entete(suivante) and not EDITORIAL.match(suivante):
            i += 1
            continue
        # Page de gauche : son vrai titre, puis celui de la page de droite
        # restitue entre crochets, qu'on ignore.
        if apres_page and est_entete(l) and not EDITORIAL.match(l):
            sauter_suivante = True
        date, reste = None, None
        mj = JOUR_SEUL.match(l.strip()[:20])
        if mj and i + 1 < len(lignes) and NOMBRE_SEUL.match(lignes[i + 1]):
            g = {'y1': None, 'y2': None, 'm1': None, 'm2': None, 'w': mj.group(1),
                 'd': NOMBRE_SEUL.match(lignes[i + 1]).group(1)}
            date, err = resout(g, cour)
            if date:
                i += 1
                reste = ''
        else:
            me = ENTETE.match(re.sub(r'\s+', ' ', l.strip())[:90])
            if me and (me.group('w') or me.group('m1') or me.group('m2')):
                gd = dict(me.groupdict(), suite=bool(re.search(r'continued|remarks', l)))
                date, err = resout(gd, cour)
                if not date and err != 'ni mois ni jour':
                    alertes.append(f'{nom}:{i+1} rejeté ({err}) : {l[:90]}')
                elif err:
                    alertes.append(f'{nom}:{i+1} {err} {date} : {l[:90]}')
                reste = l
        if date and reste:
            # Titre courant de page suivi du jour qui commence :
            # « [1803 Feb: [Thursday] -17th. Investigator] [Friday] -18th ... »
            m2 = re.search(r'\]\s*(\[\s*' + W + r'\s*\]\s*[-–]?\s*(?:' + M + r')?\s*\d{1,2}.*)$', reste)
            if m2:
                me2 = ENTETE.match(m2.group(1)[:90])
                if me2:
                    d2, _ = resout(me2.groupdict(), date)
                    if d2 and 0 < (d2 - date).days <= 3:
                        date, reste, l = d2, m2.group(1), m2.group(1)
        if date:
            if date < debut and not actif:
                cour = date
                i += 1
                continue
            actif = True
            editorial = l.lstrip().startswith('[') and apres_page and date == cour
            cour = date
            cle = date.isoformat()
            jours.setdefault(cle, [])
            if reste is not None and not editorial:
                jours[cle].append(reste)
            elif reste == '' :
                pass
        elif actif:
            jours[cour.isoformat()].append(l)
        apres_page = False
        i += 1
    return jours


def paragraphes(lignes):
    """Recolle les lignes coupées par la largeur de page."""
    out = []
    for l in lignes:
        s = l.rstrip()
        if not s.strip():
            continue
        neuf = (not out or s.startswith((' ', '\t')) or s.lstrip().startswith('[')
                or out[-1].lstrip().startswith('[') and out[-1].rstrip().endswith(']')
                or len(lignes_brutes_derniere(out)) < 95)
        if neuf:
            out.append(s.strip())
        else:
            prec = out[-1]
            out[-1] = prec + ('' if prec.endswith('-') and not prec.endswith(' -') else ' ') + s.strip()
        dernieres[0] = s
    return out


dernieres = ['']


def lignes_brutes_derniere(out):
    return dernieres[0]


def texte_pdf(nom):
    import pymupdf
    with pymupdf.open(os.path.join(DOCS, nom)) as doc:
        return ''.join(p.get_text() for p in doc)


def nettoie(par):
    # Le signe du degre sort parfois du PDF en parenthese : « N.74(W ».
    par = re.sub(r"(?<=\d)\((?=[\s.'\"NSEW\d,]|$)", '°', par)
    return par


def extraire():
    alertes = []
    tout = OrderedDict()
    for nom, debut, depart in VOLUMES:
        lignes = texte_pdf(nom).split('\n')
        if depart:
            # Avant la page 58, les tableaux de Sheerness et de Spithead
            # n'ont pas de mois : on commence au 17 juillet 1801.
            k = lignes.index(depart)
            lignes = [''] * k + lignes[k:]
        for cle, v in decoupe(lignes, debut, alertes, nom[:40]).items():
            dernieres[0] = ''
            pars = [nettoie(p) for p in paragraphes(v)
                    if not p.startswith('[Transcribed by')]
            tout.setdefault(cle, []).extend(pars)
    os.makedirs(os.path.join(SOURCES, 'en'), exist_ok=True)
    for cle, pars in tout.items():
        if pars:
            with open(os.path.join(SOURCES, 'en', cle + '.txt'), 'w') as f:
                f.write('\n'.join(pars) + '\n')
    with open(os.path.join(SOURCES, 'alertes_decoupage.txt'), 'w') as f:
        f.write('\n'.join(alertes) + '\n')
    print(f'{len(tout)} journees ecrites dans {SOURCES}/en ; {len(alertes)} alertes')


OUVRE, FERME = '⟦', '⟧'


def page_marquee(page):
    """Texte de la page comme get_text(), les caracteres barres entre ⟦ ⟧.

    Une rature est un trait plein de moins de 1,2 pt d'epaisseur qui passe a
    mi-hauteur des lettres ; plus bas, c'est un soulignement, et les traits
    sans lettre sont les bordures des tableaux."""
    traits = [d['rect'] for d in page.get_drawings()
              if d['rect'].height <= 1.2 and d['rect'].width > 2]
    out = []
    for b in page.get_text('rawdict')['blocks']:
        if b['type'] != 0:
            continue
        for l in b['lines']:
            ligne, dedans = '', False
            for c in (c for s in l['spans'] for c in s['chars']):
                x0, y0, x1, y1 = c['bbox']
                cx, h = (x0 + x1) / 2, y1 - y0
                if not c['c'].strip():
                    ligne += c['c']
                    continue
                barre = any(r.x0 - .5 <= cx <= r.x1 + .5 and y0 + .3 * h <= r.y0 <= y0 + .7 * h
                            for r in traits)
                if barre and not dedans:
                    ligne, dedans = ligne + OUVRE, True
                elif not barre and dedans:
                    k = len(ligne.rstrip(' '))
                    ligne, dedans = ligne[:k] + FERME + ligne[k:], False
                ligne += c['c']
            if dedans:
                k = len(ligne.rstrip(' '))
                ligne = ligne[:k] + FERME + ligne[k:]
            out.append(ligne + '\n')
    return ''.join(out)


def souple(s):
    """Motif qui retrouve s quels que soient les blancs (lignes recollees)."""
    return r'\s*'.join(re.escape(c) for c in s if not c.isspace())


def ratures(ecrire):
    """Reporte les ratures sur les fichiers en/ existants, sans redecouper.

    Le decoupage est refait sur le texte marque, mais seulement pour situer
    chaque rature par ses 40 caracteres de contexte dans le fichier en/ du
    meme jour (a defaut, d'un autre jour) : les marques allongent les lignes
    et changeraient sinon le recollage des paragraphes de 8 journees."""
    import pymupdf
    global texte_pdf
    brut = texte_pdf

    def marque(nom):
        with pymupdf.open(os.path.join(DOCS, nom)) as doc:
            return ''.join(page_marquee(p) for p in doc)
    texte_pdf = marque
    alertes, marques = [], OrderedDict()
    try:
        for nom, debut, depart in VOLUMES:
            lignes = texte_pdf(nom).split('\n')
            if depart:
                k = lignes.index(depart)
                lignes = [''] * k + lignes[k:]
            for cle, v in decoupe(lignes, debut, alertes, nom[:40]).items():
                dernieres[0] = ''
                marques.setdefault(cle, []).extend(paragraphes(v))
    finally:
        texte_pdf = brut
    dossier = os.path.join(SOURCES, 'en')
    textes = {f[:-4]: open(os.path.join(dossier, f)).read()
              for f in os.listdir(dossier) if f.endswith('.txt')}
    textes = {k: v.replace(OUVRE, '').replace(FERME, '') for k, v in textes.items()}
    poses, echecs = {k: set() for k in textes}, []
    for cle, pars in marques.items():
        src = '\n'.join(pars)
        for m in re.finditer(OUVRE + '(.*?)' + FERME, src, re.S):
            g = re.sub('[⟦⟧]', '', src[:m.start()])[-40:]
            d = re.sub('[⟦⟧]', '', src[m.end():])[:40]
            trouve = None
            for jours, n in (([cle], 40), ([cle], 15), (sorted(textes), 25)):
                motif = souple(g[-n:]) + r'\s*(' + souple(m.group(1)) + r')\s*' + souple(d[:n])
                hits = [(j, h.span(1)) for j in jours if j in textes
                        for h in re.finditer(motif, textes[j])]
                if len(hits) == 1:
                    trouve = hits[0]
                    break
            if trouve:
                poses[trouve[0]].add(trouve[1])
            else:
                echecs.append(f'{cle} : {m.group(1)}')
    n = 0
    for cle, spans in poses.items():
        t = textes[cle]
        for a, b in sorted(spans, reverse=True):
            t = t[:a] + OUVRE + t[a:b] + FERME + t[b:]
        n += len(spans)
        if ecrire:
            with open(os.path.join(dossier, cle + '.txt'), 'w') as f:
                f.write(t)
    print(f'{n} ratures sur {sum(1 for s in poses.values() if s)} journees ;'
          f' non reportees (titres de page ecartes) : {echecs}')


def points_investigator():
    with open(PARCOURS) as f:
        g = json.load(f)
    return sorted({p['properties']['date'] for p in g['features']
                   if p['properties'].get('navire') == "l'Investigator"})


def cible(date, points):
    """Le point qui recoit la journee : le sien, sinon le suivant."""
    for p in points:
        if p >= date:
            return p
    return points[-1]


# Un en-tete de journee reste parfois colle a la phrase qu'une fin de page
# interrompait : « ... parmi lesquelles 1802 avril [vendredi] - 9, suite. »
MOIS_EN = r'(?:Jan|Feb|Mar|Apr|May|June?|July?|Aug|Sept?|Oct|Nov|Dec)[a-z]*[.:]?'
MOIS_FR = (r'(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|'
           r'octobre|novembre|décembre)\.?')
ENTETE_COLLE = {l: re.compile(r'(?<=[^\s\n]) (?=\[?18\d\d ' + m + r' ?\[)')
                for l, m in (('en', MOIS_EN), ('fr', MOIS_FR))}


def integrer(ecrire):
    points = points_investigator()
    for langue in ('en', 'fr'):
        fichiers = sorted(glob.glob(os.path.join(SOURCES, langue, '*.txt')))
        par_point = OrderedDict()
        for chemin in fichiers:
            date = os.path.basename(chemin)[:-4]
            with open(chemin) as f:
                texte = f.read().strip()
            texte = ENTETE_COLLE[langue].sub('\n', texte)
            if texte:
                par_point.setdefault(cible(date, points), []).append(texte)
        with open(JOURNAUX[langue]) as f:
            journal = json.load(f)
        for jour in journal.values():
            jour.pop(CHAMP, None)
        for p, textes in par_point.items():
            journal.setdefault(p, {})[CHAMP] = '\n\n'.join(textes)
        journal = OrderedDict(sorted(journal.items()))
        print(f'{langue} : {len(fichiers)} journees sur {len(par_point)} fiches')
        if ecrire:
            with open(JOURNAUX[langue], 'w') as f:
                json.dump(journal, f, ensure_ascii=False)


if __name__ == '__main__':
    if sys.argv[1:2] == ['extraire']:
        extraire()
    elif sys.argv[1:2] == ['ratures']:
        ratures('--ecrire' in sys.argv)
    elif sys.argv[1:2] == ['integrer']:
        integrer('--ecrire' in sys.argv)
    else:
        print(__doc__)
