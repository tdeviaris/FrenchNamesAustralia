#!/usr/bin/env python3
"""Porte le glossaire nautique du Markdown dans la page.

La source est `docs/glossaire-nautique.md` ; sa traduction, quand elle
existe, `docs/glossaire-nautique.en.md`. Le script en tire le sommaire et les
notices de chacun des trois volets, et les pose dans `glossary.html` entre
les reperes que la page porte a cet effet. Tant que la traduction manque, le
cote anglais recoit le texte francais : mieux vaut un glossaire lisible dans
une seule langue qu'une page vide.

    python3 scripts/glossaire_nautique.py

Le HTML est ecrit dans la page, pas charge a cote : le moteur de
questions-reponses lit le texte des pages, et ne verrait pas un JSON.
"""
import os
import re
import sys
import unicodedata

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(RACINE, 'glossary.html')
SOURCES = {
    'fr': os.path.join(RACINE, 'docs', 'glossaire-nautique.md'),
    'en': os.path.join(RACINE, 'docs', 'glossaire-nautique.en.md'),
}

# Ordre des volets dans le fichier source, et prefixe de leurs ancres. Le
# prefixe evite que « Mouillage », present dans deux volets, ne serve deux
# fois la meme ancre.
VOLETS = [('manoeuvre', 'man'), ('hydrographie', 'hyd'), ('vie-bord', 'vie')]

HAUT = {'fr': 'Retour en haut', 'en': 'Back to top'}


def slug(texte):
    """Une ancre stable : sans accent, sans ponctuation, en minuscules."""
    plat = unicodedata.normalize('NFD', texte)
    plat = ''.join(c for c in plat if unicodedata.category(c) != 'Mn')
    plat = plat.replace('œ', 'oe').replace('æ', 'ae')
    plat = re.sub(r'[^a-zA-Z0-9]+', '-', plat).strip('-').lower()
    return plat


def echappe(texte):
    return (texte.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def lit_source(chemin):
    """Les trois volets du fichier : titre, intro, sous-sections et termes.

    Le format est celui que produit la relecture : `## volet`, `### section`,
    puis chaque terme en gras sur sa ligne et sa definition au-dessous.
    """
    with open(chemin, encoding='utf-8') as f:
        texte = f.read()

    volets = []
    for bloc in re.split(r'^## ', texte, flags=re.M)[1:]:
        lignes = bloc.split('\n')
        volet = {'titre': lignes[0].strip(), 'intro': '', 'contenu': []}
        courant = None
        for ligne in lignes[1:]:
            brut = ligne.strip()
            if not brut:
                continue
            if brut.startswith('### '):
                volet['contenu'].append(('section', brut[4:].strip()))
                courant = None
            elif brut.startswith('> '):
                # Une remarque de fin de section : elle porte sur l'ensemble
                # des termes qui precedent, non sur le dernier d'entre eux.
                volet['contenu'].append(('note', brut[2:].strip()))
                courant = None
            elif brut.startswith('**') and brut.endswith('**'):
                courant = [brut.strip('*').strip(), []]
                volet['contenu'].append(('terme', courant))
            elif courant is not None:
                courant[1].append(brut)
            elif not volet['contenu']:
                # Avant le premier titre ou terme : c'est l'intro du volet.
                volet['intro'] += (' ' if volet['intro'] else '') + brut
        volets.append(volet)

    if len(volets) != len(VOLETS):
        sys.exit(f'{chemin} : {len(volets)} volets au lieu de {len(VOLETS)}.')
    return volets


def rend_volet(volet, prefixe, langue):
    """Le sommaire du volet, puis ses notices.

    Les deux langues tiennent le meme terme -- « Abattre » reste « Abattre »
    meme une fois sa definition traduite. L'ancre anglaise porte donc sa
    langue en suffixe, sans quoi les deux moities de la page se disputeraient
    le meme identifiant et le lien tomberait toujours sur la premiere.
    """
    suffixe = '' if langue == 'fr' else f'-{langue}'
    lignes = []

    # Deux termes de meme nom -- « Tournevire » parait sous les ancres et sous
    # les palans -- se disputeraient la meme ancre. Le second prend un rang.
    # On les arrete une bonne fois ici : le sommaire et les notices tirent
    # ensuite de la meme liste, et ne peuvent plus se desaccorder.
    vus = {}
    ancres = []
    termes = []
    for genre, valeur in volet['contenu']:
        if genre != 'terme':
            continue
        terme = valeur[0]
        base = f'{prefixe}-{slug(terme)}'
        vus[base] = vus.get(base, 0) + 1
        rang = '' if vus[base] == 1 else f'-{vus[base]}'
        ancres.append(f'{base}{rang}{suffixe}')
        termes.append(terme)

    if volet['intro']:
        lignes.append(f'            <p class="part-intro">{echappe(volet["intro"])}</p>')

    lignes.append('            <ul class="toc">')
    for terme, ancre in zip(termes, ancres):
        lignes.append(f'                <li><a href="#{ancre}">{echappe(terme)}</a></li>')
    lignes.append('            </ul>')

    suivante = iter(ancres)
    for genre, valeur in volet['contenu']:
        if genre == 'section':
            lignes.append(f'\n            <h3 class="part-section">{echappe(valeur)}</h3>')
            continue
        if genre == 'note':
            lignes.append(f'\n            <p class="part-note">{echappe(valeur)}</p>')
            continue
        terme, paragraphes = valeur
        ancre = next(suivante)
        corps = '\n                '.join(
            f'<p>{echappe(p)}</p>' for p in paragraphes) or '<p></p>'
        lignes.append(f'''
            <section class="entry">
                <h4 id="{ancre}" class="entry-title is-term">
                    <span>{echappe(terme)}</span>
                    <a class="backtop" href="#top" title="{HAUT[langue]}">
                        <img src="img/up-arrow.svg" alt="{HAUT[langue]}">
                    </a>
                </h4>
                {corps}
            </section>''')

    return '\n'.join(lignes)


def pose(html, langue, cle, contenu):
    """Remplace ce qui se trouve entre les deux reperes du volet."""
    debut = f'<!-- nautique:{langue}:{cle}:debut -->'
    fin = f'<!-- nautique:{langue}:{cle}:fin -->'
    if debut not in html or fin not in html:
        sys.exit(f'Reperes introuvables pour {langue}/{cle} dans la page.')
    avant, reste = html.split(debut, 1)
    _, apres = reste.split(fin, 1)
    return f'{avant}{debut}\n{contenu}\n            {fin}{apres}'


def main():
    with open(PAGE, encoding='utf-8') as f:
        html = f.read()

    for langue in ('fr', 'en'):
        chemin = SOURCES[langue]
        repli = ''
        if not os.path.exists(chemin):
            chemin = SOURCES['fr']
            repli = ' (texte français, traduction à venir)'
        volets = lit_source(chemin)
        for volet, (cle, prefixe) in zip(volets, VOLETS):
            html = pose(html, langue, cle, rend_volet(volet, prefixe, langue))
        termes = sum(1 for v in volets for c in v['contenu'] if c[0] == 'terme')
        print(f'{langue} : {termes} termes posés{repli}')

    with open(PAGE, 'w', encoding='utf-8') as f:
        f.write(html)


if __name__ == '__main__':
    main()
