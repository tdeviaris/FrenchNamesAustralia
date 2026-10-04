# Scripts (maintenance / génération)

Ce répertoire regroupe les scripts utilisés pour générer / nettoyer des contenus du site (HTML, données, navigation) ainsi que la configuration de l’assistant IA.

## Ce qui n'est plus ici

- **Outils communs aux deux sites** (dépôt `toponymes-commun`, sous-module `commun/`), à lancer depuis la
  racine du site : `commun/scripts/` — serveur local (`npm run dev`), trait de côte (`littoral.py`,
  `controle_littoral.py`, `contournements.py`, `renfloue.py`), traduction des journaux (`traduit_journaux.py`),
  images (`generate_avif_previews.sh`, `encode_pngs_to_jpg_mozjpeg.sh`), et le script du classeur Google
  (`Toponyms_update.gs`, à coller dans Apps Script), qui publie dans les deux dépôts.
- **Scripts des données Flinders** (journal, route, calage, carte, visuels) : dans le site Flinders Place Names
  (`../FlindersPlaceNames/scripts/`), propriétaire de ces données.

## Données Flinders

Le serveur MCP, la base de connaissance et l'assistant de ce site lisent aussi les données Flinders, dont ce
dépôt garde une **copie en lecture**. `scripts/synchro_flinders.sh` la met à jour depuis `../FlindersPlaceNames`
(et y renvoie `data/journaux_reperes.json`, calculé ici par `reperes_journaux.py` sur les routes des deux sites).
On ne corrige jamais ces copies ici. `flinders.json` arrive directement du classeur, dans les deux dépôts.

## Assistant IA

La base de connaissance de l’assistant est fabriquée par `rag/` (voir `rag/README.md`). L’ancien `setup-assistant.js` (API Assistants) est archivé hors dépôt, dans `Toponymes/_archives/versions_precedentes_site/`.

## Données / conversions

- `convert_csv_to_json.py` : convertit `data/Toponymes.csv` en JSON exploitable par la carte.
- `convert_docs_to_html.sh` : convertit les documents de `Source_documents/` en pages HTML dans `details/` (LibreOffice requis) + post-traitement.
- `postprocess_html.py` : post-traitement des HTML générés (nettoyage, favicon, etc.).
- `format_html.py` : utilitaire de formatage / normalisation HTML.

## Navigation / pages

- `inject_nav.cjs` : injecte le menu de navigation dans un ensemble de pages HTML.
- `clean_nav_styles.sh` : retire/normalise certains styles de navigation sur des pages ciblées.
- `clean_all_nav_styles.py` : variante Python (traitements en lot).
- `remove_nav_styles.py` : suppression ciblée de styles nav.
- `replace_nav_with_include.py` : remplace la nav inline par un include.
- `add_about_menu.py` : ajoute/ajuste l’entrée “À propos”.
- `remove_duplicate_about.py` : retire des doublons liés au menu “À propos”.
- `merge_resource_pages.py` : tentative/outillage de fusion FR/EN des pages ressources (actuellement surtout diagnostic).

## Divers

- `build_map_wa.sh` : build spécifique pour `mapWA.html`.
- `map_old.html` : ancien fichier de carte (référence).

