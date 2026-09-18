# Conventions de transcription — journal de mer de Baudin (BnF, SG MS4-33)

On transcrit une **copie dactylographiée** du début du XXe siècle, faite d'après
le manuscrit de Nicolas Baudin. Le but est un texte fidèle, propre et
directement affichable dans les fiches de la carte.

## Ce qu'on rétablit

**Le chiffre 1.** La machine du dactylographe n'a pas de touche « 1 » : il
frappe un I majuscule. Partout où un I tient la place d'un chiffre, on écrit 1.

    lu    « Du I5 Messidor »   « 4I°20'I0" »   « N°3I »   « I7 5/IO »
    écrit « Du 15 Messidor »   « 41°20'10" »   « N°31 »   « 17 5/10 »

Attention : le I reste un I quand c'est une lettre — « Ile de France »,
« II » chiffre romain dans « an XI ». Le contexte tranche toujours.

**Les mots coupés en fin de ligne.** On les rejoint, sans laisser de tiret.

    lu    « la bor- / dée que nous courions »
    écrit « la bordée que nous courions »

**Les corrections portées à la main.** Le relecteur du typescript a parfois
ajouté une lettre ou un chiffre à l'encre. On les intègre au texte, sans les
signaler : le « e » inséré dans `isls` donne `isles`, le « 27 » ajouté dans
l'en-tête donne `- Du 26 au 27 Floréal -`.

**Rien d'autre.** Ni l'orthographe, ni la ponctuation, ni la syntaxe.

## Ce qu'on ne touche pas

- **L'orthographe d'époque et les graphies de Baudin** : « bay », « attérage »,
  « lock » pour loch, « Ile de France », « Ténériffe », « naturels ». On copie.
- **Les fautes de frappe du dactylographe**, y compris ses erreurs de mois
  (« Du 13 Floréal (Prairial) an 9 »). Elles font partie du document.
- **La ponctuation serrée** : le dactylographe ne met pas d'espace après la
  virgule ou le point (« la mer.Cet aspirant »). On conserve.
- **Les majuscules** telles qu'elles sont frappées.

### Les accents : ni les ajouter, ni les enlever

C'est ici qu'une transcription se trahit, et dans les deux sens.

Le dactylographe est **inconstant**. Il écrit « nous eûmes » sur un feuillet et
« nous eumes » sur un autre ; « Cette ance » quinze lignes avant « cette anse ».
Ce n'est pas une inadvertance à corriger, et ce n'est pas non plus une règle à
généraliser : **chaque accent se lit sur l'image, un par un.**

Les deux fautes possibles, toutes deux constatées :

- **rétablir un accent qui n'y est pas** — écrire « nous eûmes » là où la page
  porte « nous eumes ». C'est le réflexe du français moderne.
- **retirer un accent qui y est** — écrire « nous eumes » là où la page porte
  « nous eûmes ». C'est le réflexe de qui a retenu l'exemple précédent et en a
  fait une règle.

Les formes en *-ûmes*, *-îmes*, *-âmes* sont les plus exposées : eûmes, fûmes,
vîmes, prîmes, mîmes, restâmes, continuâmes. Regarde la voyelle avant d'écrire.
Si l'accent est trop pâle pour trancher, transcris sans accent et ajoute `[?]`.

Le reste s'applique de la même façon, et toujours par l'observation : les
graphies de Baudin (« bay », « attérage », « lock », « constemment »), les
coquilles du dactylographe, ses « Baromêtre » et « Thermomêtre » à l'accent
retourné, et l'espace après le point qu'il met tantôt et tantôt non
(« longtemps. Cependant » mais « la mer.Cet aspirant »).

## Ce qu'on signale

| Cas | Notation | Exemple |
|---|---|---|
| Lecture douteuse | `[?]` après le mot | `Bonnefoi[?]` |
| Mot illisible | `[illisible]` | |
| Passage manquant (déchirure, page coupée) | `[lacune]` | |
| Numéro de feuillet à la main en marge | ligne `Folio : 94` en tête | |
| Filet de séparation tapé à la machine | `----------` sur sa propre ligne | |
| Blanc laissé par le dactylographe | `……` tel quel | `observée ……` |

## Structure d'un fichier

Un fichier par vue, nommé `f096.txt`, encodé en UTF-8 :

```
Vue : 96
Folio : 94
Date : 1802-06-02
En-tête : - Du 13 Floréal (Prairial) an 9 -

[texte de la page, paragraphes conservés]
```

- `Folio` : seulement si un numéro est porté à la main ; sinon, omettre la ligne.
- `Date` : reprise de `dates.json`, fournie dans la consigne ; si la page ne
  porte aucun en-tête, écrire `Date : suite`.
- `En-tête` : la ligne d'en-tête telle qu'elle est frappée, chiffres rétablis ;
  omettre la ligne si la page n'en porte pas.
- Les **tableaux de sondes** se transcrivent en conservant l'alignement en
  colonnes, séparées par deux espaces au moins.
- Les **titres centrés** (« Relèvement des terres à 5 heures du soir ») gardent
  leur ligne propre.
- Les **alinéas** de Baudin sont marqués par un retrait dans le typescript : on
  les rend par un simple retour à la ligne, sans espace insécable ni retrait.

## Trois règles de prudence

1. **Ne jamais moderniser.** À chaque mot qui « sonne faux », le réflexe doit
   être de le recopier tel quel, pas de le réparer. Voir le tableau des accents
   ci-dessus : c'est la faute la plus fréquente et la plus sournoise, parce
   qu'elle produit un texte plausible.
2. **Ne jamais deviner un chiffre.** Une latitude, une longitude, une sonde, un
   relèvement : si le chiffre n'est pas net, `[?]`. C'est la donnée la plus
   précieuse du journal et la plus facile à corrompre.
3. **Ne jamais compléter une phrase.** Si la bande s'arrête au milieu d'un mot,
   on transcrit ce qu'on voit ; le recouvrement entre les deux bandes permet de
   raccorder, et c'est au raccord que le mot se reconstitue.

## Les deux bandes d'une page

Chaque vue est fournie en deux images, `f096a.jpg` (haut) et `f096b.jpg` (bas),
qui **se recouvrent de trois à quatre lignes**. On transcrit la page entière en
une fois, sans répéter les lignes communes aux deux bandes.
