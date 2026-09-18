#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dresse la liste des journées à confronter au manuscrit autographe.

La copie dactylographiée de la BnF se trompe de nom de mois à plusieurs
reprises. Les journées où la date lue contredit la datation calculée sont
signalées « à relire » ; ce sont elles qu'il faut arbitrer sur l'original.

L'original est aux Archives nationales, fonds du Service hydrographique de la
Marine, et se répartit en quatre articles dont les bornes correspondent
exactement à celles du typescript. Chaque journée douteuse est donc rattachée
à sa cote, pour que la consultation se fasse par article et non au hasard.

Usage : python3 scripts/a_verifier_baudin.py <dossier> [--ecrire]
"""
import datetime, importlib.util, json, os, re, sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOURNAL = os.path.join(RACINE, 'data', 'journal_baudin_bnf.json')
GEOJSON = os.path.join(RACINE, 'data', 'baudin_parcours.geojson')

ARK = 'https://gallica.bnf.fr/ark:/12148/btv1b55013925h'

# Les quatre articles du journal de mer autographe de Baudin.
# Archives nationales, MAR/5JJ, inventaire FRAN_IR_054071.
# Journees deja arbitrees, et par quel moyen. Elles restent dans la liste pour
# memoire, mais n'appellent plus de consultation.
REGLEES = {
    96: 'le dactylographe se corrige lui-même : « Floréal (Prairial) »',
    462: 'latitude observée 32°21\'27" S : le Géographe était à 32°22\' S le '
         '5 mai 1802, et à 37°56\' S le 4 avril',
    487: 'latitude observée 41°22\'53" S : le Géographe était à 41°23\' S le '
         '1er juin 1802, et à 32°49\' S le 1er mai',
}

COTES = [
    ('MAR/5JJ/37',   '1801-02-20', '1801-07-22', '1er ventôse - 3 thermidor an IX'),
    ('MAR/5JJ/38',   '1801-07-23', '1802-02-27', '4 thermidor an IX - 8 ventôse an X'),
    ('MAR/5JJ/39',   '1802-02-28', '1803-02-21', '8 ventôse an X - 2 ventôse an XI'),
    ('MAR/5JJ/40/A', '1803-02-22', '1803-08-05', '4 ventôse - 17 thermidor an XI'),
]


def module(nom):
    """Charge un script voisin comme module, pour n'écrire qu'une fois les
    règles de lecture du calendrier républicain et des latitudes."""
    chemin = os.path.join(os.path.dirname(os.path.abspath(__file__)), nom)
    spec = importlib.util.spec_from_file_location(nom[:-3], chemin)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


D = module('dates_baudin_bnf.py')
C = module('controle_baudin_bnf.py')


def date_ecrite(ligne, calculee):
    """La date que porte le typescript, en grégorien.

    On lit le quantième et le nom du mois sur la ligne d'en-tête, et l'on
    retient l'année républicaine qui rapproche le plus cette date de la date
    calculée : c'est le mois qui est en cause, jamais l'année.
    """
    m = D.ENTETE.search(ligne)
    if not m:
        return None
    mois = D.mois_de(ligne, m.end())
    jour = D.chiffre(m.group(2)) if m.group(2) else D.chiffre(m.group(1))
    if mois is None or jour is None or not 1 <= jour <= 30:
        return None
    candidats = []
    for an in D.NOUVEL_AN:
        try:
            candidats.append(D.gregorien(an, mois, jour))
        except (ValueError, OverflowError):
            pass
    if not candidats:
        return None
    return min(candidats, key=lambda d: abs((d - calculee).days))


def positions():
    gj = json.load(open(GEOJSON, encoding='utf-8'))
    ref = {}
    for f in gj['features']:
        if f['geometry']['type'] != 'Point':
            continue
        p = f['properties']
        if p.get('navire') in ('le Géographe', 'les corvettes') and p.get('date'):
            ref.setdefault(p['date'], f['geometry']['coordinates'][1])
    return ref


def arbitre(texte, calculee, ecrite, ref):
    """Laquelle des deux dates la latitude du jour désigne-t-elle ?

    On accepte les confusions de la fonte sur les degrés : une latitude lue
    53° pour 33° ne doit pas faire manquer un arbitrage par ailleurs net.
    """
    if ecrite is None or ecrite == calculee:
        return None
    lats = C.latitudes(texte, tolerant=True)
    a, b = calculee.isoformat(), ecrite.isoformat()
    if not lats or a not in ref or b not in ref:
        return None
    ea = min(abs(l - ref[a]) for l in lats)
    eb = min(abs(l - ref[b]) for l in lats)
    # il faut un écart franc : sinon les deux dates sont également plausibles
    if min(ea, eb) > 1.0 or abs(ea - eb) < 1.0:
        return None
    return ('calcul', ea, eb) if ea < eb else ('typescript', ea, eb)


def cote_de(date):
    for nom, a, b, _ in COTES:
        if a <= date <= b:
            return nom
    return '—'


def main():
    dossier = sys.argv[1].rstrip('/')
    dates = json.load(open(os.path.join(dossier, 'dates.json'), encoding='utf-8'))
    douteuses = [d for d in dates if d['etat'] == 'désaccord']
    douteuses.sort(key=lambda d: d['date'])

    # arbitrage par les positions déjà établies du parcours
    jour = json.load(open(JOURNAL, encoding='utf-8'))
    ref = positions()
    for d in douteuses:
        calculee = datetime.date.fromisoformat(d['date'])
        ecrite = date_ecrite(d['ligne'], calculee)
        d['ecrite'] = ecrite.isoformat() if ecrite else None
        entree = jour.get(d['date'])
        d['verdict'] = (arbitre(entree['texte'], calculee, ecrite, ref)
                        if entree else None)
        # Deux natures de doute, qui n'appellent pas le meme remede.
        # Si le nom du mois est lisible et contredit le calcul, c'est une
        # erreur du dactylographe : seul l'autographe tranche. Sinon le
        # desaccord ne porte que sur un chiffre, que la fonte rend mal, et
        # la loupe sur l'image de Gallica y suffit.
        m = D.ENTETE.search(d['ligne'])
        mois_lu = D.mois_de(d['ligne'], m.end()) if m else None
        mois_calcule = D.republicain(calculee)[1]
        if d['vue'] in REGLEES:
            d['genre'] = 'reglee'
        elif d['verdict']:
            d['genre'] = 'tranche'
        elif mois_lu is not None and mois_lu != mois_calcule:
            d['genre'] = 'mois'
        else:
            d['genre'] = 'chiffre'
    compte = {g: sum(1 for d in douteuses if d['genre'] == g)
              for g in ('reglee', 'tranche', 'mois', 'chiffre')}

    lignes = ["""# Journées à confronter au manuscrit autographe

La copie dactylographiée de la Bibliothèque nationale (SG MS4-33, ark
btv1b55013925h) se trompe de nom de mois à plusieurs reprises : elle écrit
toujours le mois voisin du bon. Le dactylographe s'en est aperçu au moins une
fois et s'est corrigé entre parenthèses — « Du 13 Floréal (Prairial) an 9 ».

Les journées ci-dessous sont celles où la date lue sur le typescript contredit
la datation calculée. Trois d'entre elles ont déjà été arbitrées et ont toutes
donné tort à la lettre du typescript :

- **vue 96** — le dactylographe se corrige lui-même entre parenthèses ;
- **vue 462** — latitude observée 32°21'27" S : le Géographe était à 32°22' S
  le 5 mai 1802, date calculée, et à 37°56' S le 4 avril, date écrite ;
- **vue 487** — latitude observée 41°22'53" S : 41°23' S le 1er juin 1802,
  date calculée, contre 32°49' S le 1er mai, date écrite.

## L'original

Archives nationales, Service hydrographique de la Marine, sous-série MAR/5JJ,
inventaire FRAN_IR_054071. Journal de mer autographe, en quatre articles :

| Cote | Période | Dates grégoriennes |
|---|---|---|
| MAR/5JJ/36 | 2 vendémiaire - 30 pluviôse an IX | 24 sept. 1800 - 19 févr. 1801 |
| MAR/5JJ/37 | 1er ventôse - 3 thermidor an IX | 20 févr. - 22 juill. 1801 |
| MAR/5JJ/38 | 4 thermidor an IX - 8 ventôse an X | 23 juill. 1801 - 27 févr. 1802 |
| MAR/5JJ/39 | 8 ventôse an X - 2 ventôse an XI | 27 févr. 1802 - 21 févr. 1803 |
| MAR/5JJ/40/A | 4 ventôse - 17 thermidor an XI | 23 févr. - 5 août 1803 |

L'article 36 est celui qu'a publié l'université de Sydney. Les quatre suivants
couvrent très exactement ce que couvre le typescript, du 20 février 1801 au
5 août 1803 — les deux bornes concordent au jour près.
"""]

    for nom, a, b, periode in COTES:
        lot = [d for d in douteuses if a <= d['date'] <= b]
        if not lot:
            continue
        lignes.append('\n## %s — %s\n' % (nom, periode))
        lignes.append('%d journée%s à vérifier.\n'
                      % (len(lot), 's' if len(lot) > 1 else ''))
        n_mois = sum(1 for d in lot if d['genre'] == 'mois')
        lignes.append('%d journée%s douteuse%s, dont **%d où le mois est en '
                      'cause** et qui appellent l’autographe.\n'
                      % (len(lot), 's' if len(lot) > 1 else '',
                         's' if len(lot) > 1 else '', n_mois))
        lignes.append('| Date retenue | Républicain | Vue | Ce que porte le '
                      'typescript | Arbitrage |')
        lignes.append('|---|---|---|---|---|')
        for d in lot:
            if d['genre'] == 'reglee':
                note = 'déjà vérifié — %s' % REGLEES[d['vue']]
            elif d['genre'] == 'tranche':
                qui, ea, eb = d['verdict']
                note = ('tranché : la latitude tombe à %.2f° de la date '
                        'calculée et à %.2f° de la date écrite — '
                        '**le %s a raison**' % (ea, eb, qui))
            elif d['genre'] == 'mois':
                note = '**mois en cause — à voir sur l’autographe**'
            else:
                note = 'chiffre mal lu par l’OCR — la loupe sur Gallica suffit'
            lignes.append('| %s | %s | [f%03d](%s/f%d.item) | `%s` | %s |'
                          % (d['date'], d['republicain'], d['vue'], ARK,
                             d['vue'], d['ligne'].replace('|', '¦'), note))

    texte = '\n'.join(lignes) + '\n'
    print('journées douteuses                 : %d' % len(douteuses))
    print('  déjà vérifiées sur l’image       : %d' % compte['reglee'])
    print('  tranchées par les positions      : %d' % compte['tranche'])
    print('  MOIS en cause, voir l’autographe : %d' % compte['mois'])
    print('  simple chiffre mal lu par l’OCR  : %d' % compte['chiffre'])
    for nom, a, b, _ in COTES:
        n = sum(1 for d in douteuses
                if a <= d['date'] <= b and d['genre'] == 'mois')
        print('  %-12s : %2d à voir sur l’autographe' % (nom, n))

    if '--ecrire' in sys.argv:
        chemin = os.path.join(dossier, 'A_VERIFIER.md')
        open(chemin, 'w', encoding='utf-8').write(texte)
        print('\nécrit : %s' % chemin)
        # la même liste, classée, pour les outils qui l'exploitent
        brut = os.path.join(dossier, 'a_verifier.json')
        json.dump([{k: v for k, v in d.items() if k != 'verdict'}
                   for d in douteuses],
                  open(brut, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        print('écrit : %s' % brut)


if __name__ == '__main__':
    main()
