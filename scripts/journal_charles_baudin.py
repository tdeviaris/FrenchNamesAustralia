#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Souvenirs de jeunesse de l'amiral Charles Baudin, découpés par journée.

Charles Baudin (1784-1854), aspirant de 2e classe sur le Géographe, a dicté
ses souvenirs bien des années après le voyage : ce n'est pas un journal tenu
au jour le jour mais un récit, qui ne date que les grandes étapes. Source :
Service historique de la Défense, Vincennes, 1 GG2, carton 11 ; transcription
et traduction anglaise de Malcolm Leader, validées par Jean Fornasiero
(baudin.sydney.edu.au, 2019). PDF dans 01_Sources/Journaux_de_bord/Charles_Baudin.

Chaque passage est rattaché à la date du parcours la plus cohérente (table
COUPES) ; le texte d'avant le départ va au 19 octobre 1800, et tout ce qui
suit l'arrivée à l'île de France (7 août 1803, dernier point du parcours du
Géographe) va à cette dernière date. Les coupures tombent aux mêmes endroits
dans les deux langues.

Le script n'écrit que le champ journal_charles_baudin de
data/journaux/baudin_{fr,en}.json.

Usage : python3 scripts/journal_charles_baudin.py [--ecrire]
"""
import json, os, re, sys
import pymupdf

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = os.path.join(os.path.dirname(RACINE), '01_Sources', 'Journaux_de_bord',
                       'Charles_Baudin')
PDF = {'fr': 'charlesbaudinsouvenirsFr.pdf', 'en': 'charlesbaudinsouvenirsenglish.pdf'}
CIBLE = {l: os.path.join(RACINE, 'data', 'journaux', 'baudin_%s.json' % l) for l in PDF}
PARCOURS = os.path.join(RACINE, 'data', 'baudin_parcours.geojson')
CHAMP = 'journal_charles_baudin'

# Le récit commence après le titre (p. 44 du manuscrit) ; son premier mot :
DEBUT = {'fr': 'Nous restions, ma mère et moi', 'en': 'My mother and I were left'}

# (date, début du passage en français, en anglais). Un passage court jusqu'au
# début du suivant ; le premier part de DEBUT.
COUPES = [
    ('1800-10-19', None, None),                        # souvenirs d'avant le départ, départ du Havre
    ('1800-11-02', 'Santa-Cruz, où nous abordâmes', 'Santa Cruz, where we landed'),
    ('1800-11-13', 'Nous quittâmes Ténériffe', 'We left Tenerife after'),
    ('1801-03-16', "Nous arrivâmes à l'île de France", 'We reached Mauritius'),
    ('1801-04-25', "Les équipages, aussi", "The ships’ companies had also"),
    ('1801-05-27', 'Le 27 mai 1801', 'On the 27 May 1801'),
    ('1801-06-09', "Cette baie n'offrait", 'This bay provided no shelter'),
    ('1801-06-27', "N'y ayant pas trouvé le Naturaliste", 'Since we did not find the Naturaliste'),
    ('1801-07-12', 'Le 12 juillet', 'On 12 July'),
    ('1801-08-21', 'Parvenus vers le méridien', 'Having reached the meridian'),
    # Le Géographe n'a pas de point entre le 23 août et le 13 novembre 1801 :
    # l'arrivée du Naturaliste à Coupang (21 septembre) va au départ de Timor.
    ('1801-11-13', 'Cependant, nos réparations', 'However, our repairs were finished'),
    ('1802-01-13', 'Enfin, nous découvrîmes', 'Finally, on 13'),
    ('1802-02-17', 'Le 17 février', 'On the 17 February'),
    # la chaloupe de Freycinet part le 21 février (journal de Baudin), jour de la mort de Maugé
    ('1802-02-21', 'Je fus expédié dans la chaloupe', 'I was sent in the longboat'),
    # le grand canot de Boullanger et Maurouard est expédié le 6 mars
    ('1802-03-06', "En quittant l'île Maria", 'Leaving Maria Island'),
    # coup de vent de l'équinoxe, reçu dans le détroit de Bass
    ('1802-03-21', 'Nous courumes de grands dangers', 'We ran into great dangers'),
    ('1802-06-20', 'Enfin, lorsque les souffrances', 'Finally, when the suffering'),
    # dernier point au Port Jackson avant le départ du 18 novembre
    ('1802-06-22', 'Peu de jours après notre arrivée', 'A few days after our arrival'),
    ('1802-11-18', 'Enfin, vint le moment', 'Finally, the moment came'),
    # le Naturaliste quitte l'île King le 9 décembre ; premier point du Géographe après
    ('1802-12-13', 'Après quelques jours de navigation', 'After several days navigation'),
    ('1803-05-07', 'La reconnaissance de la côte sud achevée', 'Having finished the survey'),
    ('1803-06-03', 'Arrivés le 7 mai 1803', 'Having arrived on 7 May 1803'),
    ('1803-07-07', 'Il était alors mal portant', 'He was then ill'),
    ('1803-08-07', 'Le 7 août', 'On the following 7 August'),   # et toute la fin
]

# Appels de note : la note est rendue entre crochets à la place de l'appel.
NOTES = {
    'fr': [
        ('80 000 fcs 1 ', '80 000 fcs [note de transcription : ce chiffre pourrait se lire '
                          '80 000 ou 20 000 ; la version publiée donne 20 000] '),
        ('[blanc]1 par Lewin', '[blanc ; la version publiée donne 1622] par Lewin'),
        ('séparâmes1 ', 'séparâmes (en marge : 9 juin 1801) '),
        ('mouiller1 ', 'mouiller (en marge : 21 août 1801) '),
        ('3 juin [blanc]1 ', '3 juin [blanc : 1803] '),
        ('le 2l septembre', 'le 21 septembre'),
    ],
    'en': [
        ('[19 October 1800].1 ', '[19 October 1800] [the Republican date was erroneously given '
                                 'in the original as 25 vendémiaire, instead of the 27th, which is '
                                 'the correct date for the expedition’s departure]. '),
        ('[blank] by Leeuwin.1 ', '[blank; 1622 in the published edition] by Leeuwin. '),
        ('Asit happened', 'As it happened'),
        ('great deal of of sincere', 'great deal of sincere'),
    ],
}


def paragraphes(langue):
    """Texte du PDF en paragraphes, sans folios, numéros de page ni notes."""
    doc = pymupdf.open(os.path.join(SOURCES, PDF[langue]))
    paras, courant = [], []
    for page in doc:
        for bloc in page.get_text('dict')['blocks']:
            for ligne in bloc.get('lines', []):
                spans = [s for s in ligne['spans'] if s['text'].strip()]
                if not spans:
                    continue
                texte = ''.join(s['text'] for s in ligne['spans'])
                x, y = ligne['bbox'][0], ligne['bbox'][1]
                if spans[0]['size'] < 10.5:            # texte des notes de bas de page
                    continue
                if y > 770 or re.fullmatch(r'\s*[\(\[]\d+[\)\]]\s*', texte):
                    continue                           # numéro de page du PDF, folio du manuscrit
                if x > 100 and courant:                # alinéa : nouveau paragraphe
                    paras.append(' '.join(courant))
                    courant = []
                courant.append(texte.strip())
    if courant:
        paras.append(' '.join(courant))
    paras = [re.sub(r'\s+', ' ', p).strip() for p in paras]
    # coupure de mot en fin de ligne (« Nouvelle- Hollande », « fort- instruits ») : on garde le trait
    paras = [re.sub(r'(\w)- (\w)', r'\1-\2', p) for p in paras]
    texte = '\n\n'.join(paras)
    texte = texte[texte.index(DEBUT[langue]):]
    texte = texte.split('……')[0].strip() + ' […]'  # le PDF s'arrête en pleine phrase
    return texte


def decoupe(langue):
    texte = paragraphes(langue)
    for avant, apres in NOTES[langue]:
        assert avant in texte, (langue, avant)
        texte = texte.replace(avant, apres)
    positions = [0]
    for date, fr, en in COUPES[1:]:
        ancre = (fr if langue == 'fr' else en).replace(' \n', ' ')
        i = texte.find(ancre, positions[-1])
        assert i > 0, (langue, date, ancre)
        positions.append(i)
    positions.append(len(texte))
    return {COUPES[k][0]: texte[positions[k]:positions[k + 1]].strip()
            for k in range(len(COUPES))}


def main():
    geo = json.load(open(PARCOURS, encoding='utf-8'))
    dates = {f['properties']['date'] for f in geo['features']
             if f['geometry']['type'] == 'Point'
             and f['properties'].get('navire') in ('les corvettes', 'le Géographe')}
    for langue in PDF:
        passages = decoupe(langue)
        absentes = [d for d in passages if d not in dates]
        assert not absentes, absentes
        print('%s : %d passages, %d caractères'
              % (langue, len(passages), sum(len(t) for t in passages.values())))
        for d, t in passages.items():
            print('  %s %5d  %s …' % (d, len(t), t[:60].replace('\n', ' ')))
        if '--ecrire' in sys.argv:
            cible = json.load(open(CIBLE[langue], encoding='utf-8'))
            for v in cible.values():
                v.pop(CHAMP, None)
            for d, t in passages.items():
                cible.setdefault(d, {})[CHAMP] = t
            # chaque fichier garde sa mise en forme : indentée pour le français,
            # sur une seule ligne pour l'anglais (sortie de traduit_journaux.py)
            indent = 1 if langue == 'fr' else None
            with open(CIBLE[langue], 'w', encoding='utf-8') as f:
                json.dump(cible, f, ensure_ascii=False, indent=indent, sort_keys=True)
            print('écrit : %s' % CIBLE[langue])


if __name__ == '__main__':
    main()
