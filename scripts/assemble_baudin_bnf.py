#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assemble l'OCR de la copie dactylographiée du journal de Baudin (BnF).

Produit deux fichiers :
  data/journal_baudin_bnf.txt    le journal suivi, vue par vue, daté
  data/journal_baudin_bnf.json   le même texte découpé par journée

La datation vient de scripts/dates_baudin_bnf.py, qui écrit dates.json dans le
dossier de travail. Il faut donc l'avoir lancé d'abord.

Usage : python3 scripts/assemble_baudin_bnf.py <dossier> [--ecrire]
"""
import json, os, re, sys

# Les premières vues sont des plats de reliure et des feuillets blancs : la
# reconnaissance y produit du bruit, qu'il ne faut pas faire passer pour du
# texte. On mesure la densité des mots les plus courants de la langue : la
# prose de Baudin en compte une bonne dizaine pour cent, le bruit, presque
# aucun.
COURANTS = set('le la les de du des et est en un une nous il ils on que qui '
               'dans pour sur par au aux ce cette se sa son ses ne pas plus '
               'nous vents temps jour nuit mer bord'.split())
MOTS = re.compile(r"[A-Za-zÀ-ÿ']+")


def densite(texte):
    mots = [m.lower() for m in MOTS.findall(texte)]
    if len(mots) < 20:
        return 0.0
    return sum(m in COURANTS for m in mots) / float(len(mots))


SEUIL = 0.20

ARK = 'https://gallica.bnf.fr/ark:/12148/btv1b55013925h'

AVERTISSEMENT = """\
==============================================================================
JOURNAL DE BORD DU COMMANDANT NICOLAS BAUDIN
Copie dactylographiée — 20 février 1801 au 5 août 1803
Bibliothèque nationale de France, département Société de Géographie,
SG MS4-33 (1149) — ark:/12148/btv1b55013925h, 737 vues.
==============================================================================

CE QUE CONTIENT CE FICHIER

Le texte de la reconnaissance optique (Tesseract 5, français) faite sur les
images de Gallica, vue par vue, dans l'ordre des feuillets. Il n'a pas été relu
intégralement. Chaque page porte son numéro de vue et son adresse sur Gallica,
pour qu'on puisse revenir à l'image.

Ce volume prend la suite du volume 1 conservé à l'université de Sydney, qui
s'arrête au 19 février 1801. Le raccord est exact : la première journée du
typescript est celle du 19 au 20 février 1801. Il n'y a ni lacune ni
recouvrement entre les deux.

TROIS RÉSERVES, PAR ORDRE DE GRAVITÉ

1. LES CHIFFRES NE SONT PAS FIABLES. La machine à écrire du dactylographe n'a
   pas de touche « 1 » : il frappe un I majuscule, que la reconnaissance rend
   tantôt « I », tantôt « T ». La fonte lui fait par ailleurs confondre 3 et 5,
   0 et 6. Les latitudes, longitudes, sondes et distances sont donc à relire
   sur l'image avant tout usage.

2. LE DACTYLOGRAPHE SE TROMPE DE MOIS. À plusieurs reprises il écrit le mois
   voisin du bon — « Germinal » pour Floréal, « Floréal » pour Prairial,
   « Pluviôse » pour Ventôse. Il s'en est aperçu au moins une fois et s'est
   corrigé entre parenthèses : « Du 13 Floréal (Prairial) an 9 ». Les dates
   portées ci-dessous ne sont donc PAS celles que donne la lettre du
   typescript, mais celles qu'établit le raisonnement décrit plus bas.

3. LA PROSE EST LISIBLE MAIS FAUTIVE. Noms propres écorchés, lettres
   substituées (« 11 » pour « il », « ê » pour « è »). Le sens se suit sans
   peine, la citation exacte demande un retour à l'image.

COMMENT LES JOURNÉES ONT ÉTÉ DATÉES

Le journal est continu : chaque en-tête « - Du N au N+1 <mois> - » ferme une
journée de mer, de midi à midi, et deux en-têtes qui se suivent sont presque
toujours à un jour l'un de l'autre. Plutôt que de lire chaque date — ce que la
fonte interdit — on cherche la suite de dates qui explique le mieux l'ensemble
de ce qui a été lu : le quantième, le nom du mois, le quantième répété en
toutes lettres au début du récit (« Le treize au point du jour… »), et le
nombre de vues qui sépare deux en-têtes. La suite retenue est celle de moindre
coût, ancrée sur la première journée.

Trois vérifications ont été faites sur l'image et sur les positions déjà
établies du parcours :
  - vue 96  : « Du 13 Floréal (Prairial) an 9 », correction du dactylographe
              lui-même, conforme au calcul ;
  - vue 462 : latitude observée 32°21'27" S — le Géographe était à 32°22' S le
              5 mai 1802 (15 floréal), et à 37°56' S le 4 avril (15 germinal,
              ce qu'écrit le typescript) ;
  - vue 487 : latitude observée 41°22'53" S — le Géographe était à 41°23' S le
              1er juin 1802 (12 prairial), et à 32°49' S le 1er mai (12 floréal,
              ce qu'écrit le typescript).

Les journées marquées [à relire] sont celles où la date lue ne s'accorde pas
avec le calcul. Elles méritent un coup d'œil sur l'image ; les trois cas
vérifiés ci-dessus ont tous donné raison au calcul contre la lettre du
typescript.

==============================================================================

"""


def main():
    dossier = sys.argv[1].rstrip('/')
    ocr = os.path.join(dossier, 'ocr')
    chemin_dates = os.path.join(dossier, 'dates.json')
    if not os.path.exists(chemin_dates):
        sys.exit('lancer d’abord : python3 scripts/dates_baudin_bnf.py %s'
                 % dossier)
    dates = json.load(open(chemin_dates, encoding='utf-8'))

    # les en-têtes datés, groupés par vue et dans l'ordre où ils y figurent
    par_vue = {}
    for d in dates:
        par_vue.setdefault(d['vue'], []).append(d)

    vues = sorted(f for f in os.listdir(ocr) if f.endswith('.txt'))
    morceaux, journees, illisibles = [], [], []
    courante, jour = [], None
    for nom in vues:
        vue = int(nom[1:-4])
        texte = open(os.path.join(ocr, nom), encoding='utf-8').read().strip()
        if not texte:
            continue
        # le texte est conservé tel quel, mais signalé : rien n'est retranché
        muette = densite(texte) < SEUIL
        if muette:
            illisibles.append(vue)
        titres = par_vue.get(vue, [])
        if titres:
            resume = ' ; '.join(
                '%s = %s%s' % (t['date'], t['republicain'],
                               ' [à relire]' if t['etat'] == 'désaccord' else '')
                for t in titres)
        else:
            resume = 'suite de la journée précédente'
        if muette:
            resume = ('AUCUN TEXTE SUIVI — plat de reliure, feuillet blanc ou '
                      'page trop dégradée ; ce qui suit est du bruit')
        morceaux.append('\n\n%s\nVue %d — %s\n%s/f%d.item\n%s\n\n%s'
                        % ('-' * 78, vue, resume, ARK, vue, '-' * 78, texte))

        # découpage par journée : le texte court d'un en-tête au suivant
        restants = [] if muette else list(titres)
        for ligne in texte.split('\n'):
            if restants and ligne.strip() == restants[0]['ligne']:
                if jour and courante:
                    journees.append((jour, '\n'.join(courante)))
                jour, courante = restants.pop(0), []
            else:
                courante.append(ligne)
    if jour and courante:
        journees.append((jour, '\n'.join(courante)))

    par_date = {}
    for t, bout in journees:
        par_date.setdefault(t['date'], {
            'republicain': t['republicain'], 'vue': t['vue'],
            'etat': t['etat'], 'entete': t['ligne'], 'texte': ''})
        par_date[t['date']]['texte'] += bout.strip() + '\n'

    print('vues assemblées   : %d' % len(vues))
    print('  sans texte suivi : %d  %s' % (len(illisibles), illisibles[:12]))
    print('journées datées   : %d' % len(par_date))
    print('  à relire        : %d'
          % sum(1 for v in par_date.values() if v['etat'] == 'désaccord'))
    print('caractères        : %d' % sum(len(m) for m in morceaux))

    if '--ecrire' in sys.argv:
        with open('data/journal_baudin_bnf.txt', 'w', encoding='utf-8') as f:
            f.write(AVERTISSEMENT)
            f.write(''.join(morceaux))
        print('écrit : data/journal_baudin_bnf.txt')
        with open('data/journal_baudin_bnf.json', 'w', encoding='utf-8') as f:
            json.dump(par_date, f, ensure_ascii=False, indent=1, sort_keys=True)
        print('écrit : data/journal_baudin_bnf.json')
    else:
        print('\n(simulation — relancer avec --ecrire)')


if __name__ == '__main__':
    main()
