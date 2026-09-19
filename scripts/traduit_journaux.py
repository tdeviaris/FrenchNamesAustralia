#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Découpe, vérifie et rassemble la traduction des journaux de bord.

La traduction elle-même est faite ailleurs, journée par journée. Ce script
tient les trois bouts autour :

  prepare   écrit les lots de travail dans un dossier, et le texte source de
            chaque journée à côté ;
  verifie   compare ce qui est revenu au texte d'origine — longueur, et
            surtout les chiffres, qui sont ce qu'un journal de mer a de plus
            précieux et ce qu'une traduction perd le plus aisément ;
  fusionne  verse les journées traduites dans le fichier de la langue cible.

Une journée par fichier : un lot interrompu garde ce qu'il a déjà fait, et la
vérification porte sur chaque journée séparément.

Usage :
  python3 scripts/traduit_journaux.py prepare <chantier>
  python3 scripts/traduit_journaux.py verifie <chantier> [--detail]
  python3 scripts/traduit_journaux.py lots <chantier>
  python3 scripts/traduit_journaux.py fusionne <chantier> [--ecrire]
"""
import io
import json
import os
import re
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOURNAUX = os.path.join(RACINE, 'data', 'journaux')

# Les trois chantiers : d'où vient le texte, où il va, et dans quelle langue.
TRAVAUX = [
    {'nom': 'baudin_en',
     'source': os.path.join(JOURNAUX, 'baudin_fr.json'),
     'cible': os.path.join(JOURNAUX, 'baudin_en.json'),
     'champ': 'journal_baudin_autographe',
     'de': 'français', 'vers': 'anglais',
     'quoi': "le journal de mer de Nicolas Baudin, dans la transcription de "
             "Marc Soviche"},
    {'nom': 'flinders_fr',
     'source': os.path.join(JOURNAUX, 'flinders_en.json'),
     'cible': os.path.join(JOURNAUX, 'flinders_fr.json'),
     'champ': 'journal_flinders',
     'de': 'anglais', 'vers': 'français',
     'quoi': "le récit publié par Matthew Flinders, « A Voyage to Terra "
             "Australis », Londres, 1814"},
]

CARACTERES_PAR_LOT = 45000


def charge(chemin):
    if not os.path.exists(chemin):
        return {}
    return json.load(io.open(chemin, encoding='utf-8'))


def lots(jours, taille=CARACTERES_PAR_LOT):
    """Groupe les journées en lots d'à peu près la même longueur."""
    out, courant, n = [], [], 0
    for jour, texte in jours:
        courant.append(jour)
        n += len(texte)
        if n >= taille:
            out.append(courant)
            courant, n = [], 0
    if courant:
        out.append(courant)
    return out


def prepare(chantier):
    total_jours = total_car = 0
    for t in TRAVAUX:
        src = charge(t['source'])
        deja = charge(t['cible'])
        restants = []
        for jour in sorted(src):
            texte = src[jour].get(t['champ'])
            if not texte:
                continue
            if deja.get(jour, {}).get(t['champ']):
                continue                      # déjà traduit
            restants.append((jour, texte))
        dossier = os.path.join(chantier, t['nom'])
        os.makedirs(os.path.join(dossier, 'source'), exist_ok=True)
        os.makedirs(os.path.join(dossier, 'traduit'), exist_ok=True)
        for jour, texte in restants:
            io.open(os.path.join(dossier, 'source', jour + '.txt'),
                    'w', encoding='utf-8').write(texte)
        paquets = lots(restants)
        json.dump({'travail': t['nom'], 'de': t['de'], 'vers': t['vers'],
                   'quoi': t['quoi'], 'champ': t['champ'],
                   'lots': paquets},
                  io.open(os.path.join(dossier, 'lots.json'), 'w',
                          encoding='utf-8'), ensure_ascii=False, indent=1)
        car = sum(len(x[1]) for x in restants)
        total_jours += len(restants)
        total_car += car
        print('%-12s %4d journées à traduire, %9d caractères, %3d lots'
              % (t['nom'], len(restants), car, len(paquets)))
    print('total        %4d journées, %9d caractères' % (total_jours, total_car))


# Un chiffre isolé se perd sans dommage dans une tournure ; une latitude, non.
# On compare donc les nombres de deux caractères et plus, qui sont les degrés,
# les minutes, les brasses et les quantièmes.
NOMBRE = re.compile(r'\d{2,}')

# Un nombre rendu en toutes lettres n'est pas un nombre perdu : « dans les
# 24 heures » devient « in twenty-four hours », et c'est le bon anglais.
LETTRES = {
    '10': ('ten', 'dix'), '11': ('eleven', 'onze'), '12': ('twelve', 'douze'),
    '13': ('thirteen', 'treize'), '14': ('fourteen', 'quatorze'),
    '15': ('fifteen', 'quinze'), '16': ('sixteen', 'seize'),
    '17': ('seventeen', 'dix-sept'), '18': ('eighteen', 'dix-huit'),
    '19': ('nineteen', 'dix-neuf'), '20': ('twenty', 'vingt'),
    '21': ('twenty-one', 'vingt et un'), '22': ('twenty-two', 'vingt-deux'),
    '23': ('twenty-three', 'vingt-trois'), '24': ('twenty-four', 'vingt-quatre'),
    '25': ('twenty-five', 'vingt-cinq'), '26': ('twenty-six', 'vingt-six'),
    '27': ('twenty-seven', 'vingt-sept'), '28': ('twenty-eight', 'vingt-huit'),
    '29': ('twenty-nine', 'vingt-neuf'), '30': ('thirty', 'trente'),
    '31': ('thirty-one', 'trente et un'), '40': ('forty', 'quarante'),
    '50': ('fifty', 'cinquante'), '60': ('sixty', 'soixante'),
    '100': ('hundred', 'cent'),
}
# Les quantièmes se disent en ordinaux : « du 21 au 22 » devient « from the
# twenty-first to the twenty-second ». Sans cela le contrôle crie à tort.
ORDINAUX = {
    '10': 'tenth', '11': 'eleventh', '12': 'twelfth', '13': 'thirteenth',
    '14': 'fourteenth', '15': 'fifteenth', '16': 'sixteenth',
    '17': 'seventeenth', '18': 'eighteenth', '19': 'nineteenth',
    '20': 'twentieth', '21': 'twenty-first', '22': 'twenty-second',
    '23': 'twenty-third', '24': 'twenty-fourth', '25': 'twenty-fifth',
    '26': 'twenty-sixth', '27': 'twenty-seventh', '28': 'twenty-eighth',
    '29': 'twenty-ninth', '30': 'thirtieth', '31': 'thirty-first',
}
for _n, _o in ORDINAUX.items():
    LETTRES[_n] = LETTRES.get(_n, ()) + (_o,)


def ecarts(source, traduit):
    """Ce qui sépare une journée de sa traduction."""
    e = []
    if not traduit.strip():
        return ['vide']
    r = len(traduit) / float(len(source)) if source else 0
    if not 0.55 <= r <= 1.75:
        e.append('longueur %.2f' % r)
    a = sorted(NOMBRE.findall(source))
    b = sorted(NOMBRE.findall(traduit))
    if a != b:
        bas = traduit.lower()
        manquants = [x for x in a if b.count(x) < a.count(x)
                     and not any(m in bas for m in LETTRES.get(x, ()))]
        ajoutes = [x for x in b if a.count(x) < b.count(x)]
        if manquants:
            e.append('chiffres perdus : %s' % ' '.join(manquants[:6]))
        if ajoutes:
            e.append('chiffres apparus : %s' % ' '.join(ajoutes[:6]))
    return e


def par_lot(chantier):
    """L'avancement lot par lot : c'est la maille du travail."""
    for t in TRAVAUX:
        dossier = os.path.join(chantier, t['nom'])
        chemin = os.path.join(dossier, 'lots.json')
        if not os.path.exists(chemin):
            continue
        lots_ = json.load(io.open(chemin, encoding='utf-8'))['lots']
        trad = os.path.join(dossier, 'traduit')
        faits = {f[:-4] for f in os.listdir(trad) if f.endswith('.txt')}
        incomplets = []
        for i, jours in enumerate(lots_):
            n = sum(1 for j in jours if j in faits)
            if n < len(jours):
                incomplets.append((i, n, len(jours)))
        print('%-12s %d lots, %d complets, %d à reprendre'
              % (t['nom'], len(lots_), len(lots_) - len(incomplets),
                 len(incomplets)))
        if incomplets:
            print('   ' + '  '.join('n°%d : %d/%d' % x for x in incomplets[:14]))


def verifie(chantier, detail=False):
    for t in TRAVAUX:
        dossier = os.path.join(chantier, t['nom'])
        src_dir = os.path.join(dossier, 'source')
        trad_dir = os.path.join(dossier, 'traduit')
        if not os.path.isdir(src_dir):
            continue
        attendus = sorted(f[:-4] for f in os.listdir(src_dir) if f.endswith('.txt'))
        faits, manque, suspects = [], [], []
        for jour in attendus:
            chemin = os.path.join(trad_dir, jour + '.txt')
            if not os.path.exists(chemin):
                manque.append(jour)
                continue
            source = io.open(os.path.join(src_dir, jour + '.txt'),
                             encoding='utf-8').read()
            traduit = io.open(chemin, encoding='utf-8').read()
            e = ecarts(source, traduit)
            faits.append(jour)
            if e:
                suspects.append((jour, e))
        print('%-12s %d/%d journées rendues, %d à revoir'
              % (t['nom'], len(faits), len(attendus), len(suspects)))
        if manque:
            print('   manquent : %s%s' % (' '.join(manque[:8]),
                                          '…' if len(manque) > 8 else ''))
        if detail:
            for jour, e in suspects:
                print('   %s : %s' % (jour, ' ; '.join(e)))
        elif suspects:
            print('   à revoir : %s%s' % (' '.join(j for j, _ in suspects[:8]),
                                          '…' if len(suspects) > 8 else ''))


def fusionne(chantier, ecrire=False):
    for t in TRAVAUX:
        trad_dir = os.path.join(chantier, t['nom'], 'traduit')
        if not os.path.isdir(trad_dir):
            continue
        cible = charge(t['cible'])
        n = 0
        for f in sorted(os.listdir(trad_dir)):
            if not f.endswith('.txt'):
                continue
            jour = f[:-4]
            texte = io.open(os.path.join(trad_dir, f), encoding='utf-8').read().strip()
            if not texte:
                continue
            cible.setdefault(jour, {})[t['champ']] = texte
            n += 1
        print('%-12s %d journées versées, %d journées au total'
              % (t['nom'], n, len(cible)))
        if ecrire:
            json.dump(cible, io.open(t['cible'], 'w', encoding='utf-8'),
                      ensure_ascii=False, sort_keys=True)
            print('   -> %s' % os.path.relpath(t['cible'], RACINE))
    if not ecrire:
        print('\n(simulation — relancer avec --ecrire)')


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    action, chantier = sys.argv[1], sys.argv[2]
    if action == 'prepare':
        prepare(chantier)
    elif action == 'verifie':
        verifie(chantier, '--detail' in sys.argv)
    elif action == 'lots':
        par_lot(chantier)
    elif action == 'fusionne':
        fusionne(chantier, '--ecrire' in sys.argv)
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
