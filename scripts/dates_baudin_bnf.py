#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Date chaque vue de la copie dactylographiée du journal de Baudin (BnF).

L'OCR lit la prose de ce typescript, mais pas ses chiffres. La machine à écrire
n'a pas de touche « 1 » : le dactylographe frappe un I majuscule, que Tesseract
rend tantôt « I », tantôt « T ». La fonte lui fait par ailleurs confondre 3 et
5, 0 et 6. Les dates lues ligne à ligne sont donc fausses une fois sur trois,
et le mot « au » de l'en-tête devient « eu », « ou » ou « AU ».

Le journal étant continu, on n'a pas besoin de lire chaque date : il suffit de
les ordonner. Chaque en-tête « - Du N au N+1 <mois> - » ferme une journée de
mer (midi à midi) ; deux en-têtes qui se suivent sont presque toujours à un
jour l'un de l'autre. On cherche donc la suite de dates qui explique le mieux
ce qui a été lu, par programmation dynamique :

  - passer d'un en-tête au suivant coûte d'autant plus cher qu'on saute de
    jours — un saut signifie un en-tête que l'OCR n'a pas vu ;
  - lire une date qui ne correspond pas à la date proposée coûte cher, sauf si
    l'écart s'explique par une confusion connue de la fonte (3/5, 0/6, 1/7).

La suite de moindre coût est la datation retenue. Là où la date lue s'accorde
avec elle, la journée est établie deux fois ; là où elle s'en écarte, la vue
est signalée pour relecture à l'œil sur l'image.

Usage : python3 scripts/dates_baudin_bnf.py <dossier> [--large N]
"""
import datetime, difflib, json, os, re, sys, unicodedata

import numpy as np

MOIS = ['vendemiaire', 'brumaire', 'frimaire', 'nivose', 'pluviose', 'ventose',
        'germinal', 'floreal', 'prairial', 'messidor', 'thermidor', 'fructidor']
# les mêmes, tels qu'on les écrit — la liste ci-dessus sert à la comparaison
MOIS_ECRITS = ['vendémiaire', 'brumaire', 'frimaire', 'nivôse', 'pluviôse',
               'ventôse', 'germinal', 'floréal', 'prairial', 'messidor',
               'thermidor', 'fructidor']
# 1er vendémiaire de chaque année républicaine, en calendrier grégorien
NOUVEL_AN = {9: (1800, 9, 23), 10: (1801, 9, 23),
             11: (1802, 9, 23), 12: (1803, 9, 24)}

# Ancre : la première journée du typescript, « Du 30 [pluviôse] au I de Ventose
# an 9 », soit le 19-20 février 1801. Le volume 1 de Sydney s'arrête au 19 :
# le raccord est exact, sans lacune ni recouvrement.
ANCRE = datetime.date(1801, 2, 20)
FIN_PLAUSIBLE = datetime.date(1803, 9, 30)

LIGNE_COURTE = 62
# un en-tête est centré, précédé d'un ornement typographique court ; la prose
# qui parle elle aussi d'une « nuit du 7 au 8 » commence par des mots
ORNEMENT = re.compile(r'^[\s\W_]{0,6}[dbp]u\s', re.I)
AU = r'(?:au|eu|ou|nu|su|ay|a|8u|4u)'
JETON = r"[IiTtLl|OoQDSsBG0-9]{1,3}"
NB = r'(?:' + JETON + r'|premier|six)'
# Trois formes se rencontrent :
#   « - Du 21 au 22 Floréal - »   la journée de mer, de midi à midi
#   « - Du 10 Germinal - »        une journée d'escale, sans route à porter
#   « - Du 7 Germinal au 9 »      plusieurs jours d'escale réunis
ENTETE = re.compile(r'\b[dbp]u\s+(' + NB + r')\s*(?:' + AU + r'\s*(' + NB
                    + r'))?', re.I)
MOT_MOIS = re.compile(r'[A-Za-zéèêîôûÎÔÛÉÈ]{5,12}')

# Sous l'en-tête, le récit reprend par « Le vingt et un, … ». Ce quantième-là
# est écrit en toutes lettres : c'est un mot, et l'OCR lit les mots.
UNITES = ['', 'un', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit',
          'neuf', 'dix', 'onze', 'douze', 'treize', 'quatorze', 'quinze',
          'seize', 'dix sept', 'dix huit', 'dix neuf', 'vingt']
EN_LETTRES = {}
for _i in range(1, 21):
    EN_LETTRES[UNITES[_i]] = _i
EN_LETTRES['premier'] = 1
for _i in range(1, 11):
    EN_LETTRES['vingt et un' if _i == 1 else 'vingt ' + UNITES[_i]] = 20 + _i
EN_LETTRES['trente'] = 30
REPRISE = re.compile(r'^[\W_]{0,4}le\s+([a-zéèêA-Z]+(?:\s+[a-zéèêA-Z]+){0,2})',
                     re.I)


def quantieme_ecrit(lignes):
    """Le quantième en toutes lettres qui ouvre le récit, s'il est lisible."""
    for ligne in lignes:
        m = REPRISE.match(ligne.strip())
        if not m:
            continue
        mots = sans_accent(m.group(1)).split()
        for n in (3, 2, 1):
            if len(mots) >= n:
                p = difflib.get_close_matches(' '.join(mots[:n]),
                                              list(EN_LETTRES), 1, 0.78)
                if p:
                    return EN_LETTRES[p[0]]
        return None
    return None

# ce que la fonte fait confondre à Tesseract, dans les deux sens
CONFUSIONS = [('3', '5'), ('0', '6'), ('1', '7'), ('8', '6'), ('4', '1')]


def sans_accent(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower())
                   if unicodedata.category(c) != 'Mn')


# mots du relevé de navigation qui ressemblent de trop près à un nom de mois
INTRUS = ('thermometre', 'barometre', 'thermomtre', 'baromtre',
          'thermometr', 'thermomtr')


def mois_de(ligne, apres):
    """Le nom de mois qui suit le second nombre, s'il est reconnaissable."""
    for mot in MOT_MOIS.findall(ligne[apres:]):
        net = sans_accent(mot)
        if any(net.startswith(i[:7]) for i in INTRUS):
            continue
        p = difflib.get_close_matches(net, MOIS, 1, 0.68)
        # « thermomêtre » n'est pas « thermidor » : la longueur doit suivre
        if p and abs(len(net) - len(p[0])) <= 3:
            return MOIS.index(p[0])
    return None


def chiffre(s):
    """Lit un nombre tapé sur une machine sans touche « 1 »."""
    s = s.lower()
    if s == 'six':
        return 6
    if s == 'premier':
        return 1
    s = (s.replace('i', '1').replace('t', '1').replace('l', '1')
          .replace('|', '1').replace('o', '0').replace('q', '0')
          .replace('d', '0').replace('s', '5').replace('b', '8')
          .replace('g', '6'))
    return int(s) if s.isdigit() and 0 < int(s) < 100 else None


def variantes(n):
    """Toutes les lectures d'un nombre compatibles avec les confusions."""
    vues = {str(n)}
    for _ in range(2):
        for s in list(vues):
            for a, b in CONFUSIONS:
                vues.add(s.replace(a, b))
                vues.add(s.replace(b, a))
    return {int(s) for s in vues if s.isdigit()}


def gregorien(an, mois, jour):
    a, m, j = NOUVEL_AN[an]
    return datetime.date(a, m, j) + datetime.timedelta(days=mois * 30 + jour - 1)


def republicain(d):
    for an in sorted(NOUVEL_AN, reverse=True):
        a, m, j = NOUVEL_AN[an]
        debut = datetime.date(a, m, j)
        if d >= debut:
            n = (d - debut).days
            if n // 30 < 12:
                return an, n // 30, n % 30 + 1
            return an, 12, n - 360 + 1          # jours complémentaires
    return None


def entetes(dossier):
    """Les repères de journée, dans l'ordre des feuillets.

    Deux sortes. L'en-tête proprement dit, « - Du 21 au 22 Floréal - ». Et,
    quand la reconnaissance l'a manqué, la reprise du récit — « Le vingt deux
    au matin… » — qui donne le quantième en toutes lettres, donc sous une forme
    que l'OCR lit bien. Une reprise n'est retenue que si aucun en-tête ne la
    précède de peu : sinon elle redirait la journée qui vient d'être ouverte.
    """
    ocr = os.path.join(dossier, 'ocr')
    trouves = []
    for nom in sorted(os.listdir(ocr)):
        if not nom.endswith('.txt'):
            continue
        vue = int(nom[1:-4])
        lignes = open(os.path.join(ocr, nom), encoding='utf-8').read().split('\n')
        pris = []
        for i, ligne in enumerate(lignes):
            ligne = ligne.strip()
            # un en-tête est court et compte peu de mots ; la prose, qui parle
            # elle aussi d'une « nuit du 7 au 8 », en compte davantage
            if (len(ligne) > LIGNE_COURTE or len(ligne.split()) > 9
                    or not ORNEMENT.match(ligne)):
                continue
            m = ENTETE.search(ligne)
            if not m:
                continue
            mois = mois_de(ligne, m.end())
            # sans nom de mois lisible, il faut au moins les deux quantièmes
            if mois is None and (m.group(2) is None
                                 or chiffre(m.group(1)) is None):
                continue
            a = chiffre(m.group(1))
            b = chiffre(m.group(2)) if m.group(2) else None
            if b is None:
                a, b = None, a  # en-tête d'escale : un seul quantième, le bon
            pris.append(i)
            trouves.append({'vue': vue, 'rang': i, 'ligne': ligne, 'a': a,
                            'b': b, 'mois': mois, 'entete': True,
                            'ecrit': quantieme_ecrit(lignes[i + 1:i + 4])})
        for i, ligne in enumerate(lignes):
            n = quantieme_ecrit([ligne])
            if n is None or any(0 <= i - j <= 6 for j in pris):
                continue
            pris.append(i)
            trouves.append({'vue': vue, 'rang': i, 'ligne': ligne.strip(),
                            'a': None, 'b': None, 'mois': None,
                            'entete': False, 'ecrit': n})
    trouves.sort(key=lambda t: (t['vue'], t['rang']))
    return trouves

def cout_lecture(t, d):
    """Ce qu'il en coûte de dater du jour d un en-tête lu comme il l'a été."""
    an, mo, jo = republicain(d)
    c = 0.0
    if not t['entete']:
        # une reprise de récit ne porte rien d'autre que son quantième
        return 0.0 if t['ecrit'] == jo else 6.0
    if t['b'] is None:
        c += 2                      # second nombre illisible
    elif t['b'] == jo:
        pass
    elif t['b'] in variantes(jo):
        c += 2                      # écart explicable par la fonte
    else:
        c += 7
    # le premier nombre est la veille : même mois, ou dernier jour du précédent
    if t['a'] is not None:
        veille = republicain(d - datetime.timedelta(days=1))[2]
        if t['a'] != veille:
            c += 1 if t['a'] in variantes(veille) else 3
    # le nom du mois est le signal le plus sûr : un mot s'océrise bien mieux
    # qu'un chiffre dans cette fonte
    if t['mois'] is None:
        c += 1
    elif mo >= 12:
        c += 2                      # jours complémentaires : pas de nom de mois
    elif t['mois'] != mo:
        c += 9
    # le quantième en toutes lettres : un mot, donc un témoignage sûr
    if t['ecrit'] is not None:
        c += 0 if t['ecrit'] == jo else 6
    return c


# Un saut de plus d'un jour signifie un ou plusieurs en-têtes que l'OCR n'a pas
# vus. Le nombre de vues franchies dit lequel est vraisemblable : le typescript
# tient environ une journée par feuillet, donc dix vues entre deux en-têtes
# annoncent une lacune de dix journées, non une journée de dix pages. On punit
# donc l'écart entre le saut proposé et le nombre de vues franchies, assez
# doucement pour que le mois lu et le quantième écrit gardent le dernier mot.
SAUT_MAX = 200
FORFAIT = 1.5           # tout saut qui n'est pas celui qu'annoncent les vues
PAR_JOUR = 0.6          # et ce qu'il en coûte par journée d'écart
MEME_JOUR = 4.0         # deux en-têtes pour une seule journée : peu probable


def penalites(vues_franchies):
    """Le coût d'un saut de k jours, sachant le nombre de vues franchies."""
    attendu = max(1, vues_franchies)
    p = np.empty(SAUT_MAX + 1)
    for k in range(SAUT_MAX + 1):
        p[k] = 0.0 if k == attendu else FORFAIT + PAR_JOUR * abs(k - attendu)
    p[0] += MEME_JOUR
    return p


def resout(tr):
    """La suite de dates de moindre coût, ancrée sur la première journée."""
    jours = [ANCRE + datetime.timedelta(days=i)
             for i in range((FIN_PLAUSIBLE - ANCRE).days + 1)]
    D, n = len(jours), len(tr)

    base = np.array([[cout_lecture(t, d) for d in jours] for t in tr])
    cout = np.full(D, np.inf)
    cout[0] = base[0][0]            # ancre imposée : la première journée
    parents = np.zeros((n, D), dtype=np.int32)

    for i in range(1, n):
        pen = penalites(tr[i]['vue'] - tr[i - 1]['vue'])
        best = np.full(D, np.inf)
        bestk = np.zeros(D, dtype=np.int32)
        for k in range(SAUT_MAX + 1):
            cand = np.full(D, np.inf)
            if k:
                cand[k:] = cout[:D - k] + pen[k]
            else:
                cand[:] = cout + pen[0]
            m = cand < best
            best[m], bestk[m] = cand[m], k
        cout = base[i] + best
        parents[i] = np.arange(D) - bestk

    d = int(np.argmin(cout))
    suite = [d]
    for i in range(n - 1, 0, -1):
        d = int(parents[i][d])
        suite.append(d)
    return [jours[i] for i in reversed(suite)]


def main():
    dossier = sys.argv[1].rstrip('/')
    tr = entetes(dossier)
    if not tr:
        sys.exit('aucun en-tête trouvé dans %s/ocr' % dossier)
    suite = resout(tr)

    accords = ecarts = sauts = 0
    precedent = None
    for t, d in zip(tr, suite):
        an, mo, jo = republicain(d)
        t['date'], t['rep'] = d, (an, mo, jo)
        t['saut'] = (d - precedent).days if precedent else 1
        precedent = d
        if t['saut'] > 1:
            sauts += t['saut'] - 1
        lu_ok = t['b'] is not None and t['b'] in variantes(jo)
        mois_ok = t['mois'] is None or mo >= 12 or t['mois'] == mo
        ecrit_ok = t['ecrit'] is None or t['ecrit'] == jo
        # le quantième en toutes lettres suffit à établir la journée
        t['etat'] = ('accord' if ((lu_ok or t['ecrit'] == jo) and mois_ok
                                  and ecrit_ok) else 'désaccord')
        accords += t['etat'] == 'accord'
        ecarts += t['etat'] == 'désaccord'

    vues = sorted({t['vue'] for t in tr})
    print('en-têtes repérés         : %d   (vues %d à %d, %d vues)'
          % (len(tr), vues[0], vues[-1], len(vues)))
    print('  date lue conforme      : %d  (%.0f %%)'
          % (accords, 100.0 * accords / len(tr)))
    print('  DÉSACCORD à relire     : %d' % ecarts)
    print('  journées sans en-tête lu : %d  (sauts dans la suite)' % sauts)
    print('couverture               : %s → %s  (%d jours)'
          % (suite[0], suite[-1], (suite[-1] - suite[0]).days + 1))

    if ecarts:
        print('\nvues à relire sur l’image (%d) :' % ecarts)
        for t in tr:
            if t['etat'] == 'désaccord':
                an, mo, jo = t['rep']
                print('  f%03d  %s = %2d %-11s an %-2d | OCR : %s'
                      % (t['vue'], t['date'], jo,
                         MOIS_ECRITS[mo] if mo < 12 else 'complém.', an,
                         t['ligne'][:46]))

    sortie = os.path.join(dossier, 'dates.json')
    json.dump([{'vue': t['vue'], 'date': t['date'].isoformat(),
                'republicain': '%d %s an %d'
                % (t['rep'][2],
                   MOIS_ECRITS[t['rep'][1]] if t['rep'][1] < 12 else 'complém.',
                   t['rep'][0]),
                'etat': t['etat'], 'saut': t['saut'], 'ligne': t['ligne']}
               for t in tr],
              open(sortie, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('\nécrit : %s' % sortie)


if __name__ == '__main__':
    main()
