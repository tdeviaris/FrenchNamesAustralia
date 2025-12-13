# Scripts (maintenance / génération)

Ce répertoire regroupe les scripts utilisés pour générer / nettoyer des contenus du site (HTML, données, navigation) ainsi que la configuration de l’assistant IA.

## Assistant IA

- `setup-assistant.js` : crée / met à jour l’assistant OpenAI (upload des fichiers de connaissance, création de l’assistant, sauvegarde de l’ID).
  - Usage : `node scripts/setup-assistant.js`

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
- `Toponyms_update` : notes/outillage divers sur les mises à jour de toponymes.

