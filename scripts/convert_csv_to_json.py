import csv
import json
import os

def convert_csv_to_json():
    """
    Lit le fichier Toponymes1.csv, incluant la nouvelle colonne 'URL IMG',
    et génère les fichiers entrecasteaux.json et baudin.json.
    """
    # Définit les chemins des fichiers en supposant que le script est à la racine du projet.
    csv_path = os.path.join('data', 'Toponymes1.csv')
    entrecasteaux_path = os.path.join('data', 'entrecasteaux.json')
    baudin_path = os.path.join('data', 'baudin.json')

    # Vérifie si le fichier CSV source existe.
    if not os.path.exists(csv_path):
        print(f"Erreur : Le fichier source '{csv_path}' est introuvable.")
        print("Veuillez vous assurer que 'Toponymes1.csv' se trouve bien dans le dossier 'data'.")
        return

    entrecasteaux_data = []
    baudin_data = []

    try:
        with open(csv_path, mode='r', encoding='utf-8') as infile:
            # Détecte automatiquement le délimiteur (virgule ou point-virgule).
            # C'est plus robuste si le fichier CSV est édité avec différents logiciels (ex: Excel).
            try:
                dialect = csv.Sniffer().sniff(infile.read(2048))
                infile.seek(0)  # Retourne au début du fichier après la détection.
            except csv.Error:
                # Si la détection échoue, on utilise la virgule par défaut.
                dialect = 'excel'
                infile.seek(0)

            reader = csv.DictReader(infile, dialect=dialect)

            # Vérifie que la colonne essentielle 'expedition' est bien présente.
            normalized_headers = [h.strip() if h else '' for h in reader.fieldnames]
            if 'Expedition' not in normalized_headers:
                print("Erreur critique : La colonne 'Expedition' est introuvable dans les en-têtes du fichier CSV.")
                print(f"Les en-têtes détectés sont : {normalized_headers}")
                print("Cela est souvent dû à un problème de délimiteur (virgule vs point-virgule).")
                return

            for row in reader:
                # Normalise les clés pour éviter les problèmes d'espaces ou de casse.
                normalized_row = { (key.strip() if key else ''): (value.strip() if isinstance(value, str) else value)
                                   for key, value in row.items() }

                # Récupère latitude et longitude, et les convertit en nombres (float).
                try:
                    lat_str = (normalized_row.get('latitude South') or '').replace(',', '.')
                    lon_str = (normalized_row.get('longitude East') or '').replace(',', '.')
                    lat = float(lat_str) if lat_str else 0.0
                    lon = float(lon_str) if lon_str else 0.0
                except (ValueError, TypeError):
                    print(f"Avertissement : Coordonnées invalides pour '{normalized_row.get('French name', 'N/A')}'. Utilisation de 0.0.")
                    lat, lon = 0.0, 0.0

                # Crée le dictionnaire pour l'entrée JSON.
                # .get(key, '') est utilisé pour éviter une erreur si une colonne est manquante.
                expedition_value = (normalized_row.get('Expedition') or '').strip()

                place = {
                    "code": normalized_row.get('Code', ''),
                    "expedition": expedition_value,
                    "state": normalized_row.get('State', ''),
                    "frenchName": normalized_row.get('French name', ''),
                    "variantName": normalized_row.get('Variant and other historical name', ''),
                    "ausEName": normalized_row.get('Australian name', ''),
                    "indigenousName": normalized_row.get('Aboriginal name', ''),
                    "indigenousLanguage": normalized_row.get('Aboriginal language group', ''),
                    "lat": lat,
                    "lon": lon,
                    "characteristic_fr": normalized_row.get('Caracteristiques  (FR)', ''),
                    "characteristic": normalized_row.get('Characteristic  (EN)', ''),
                    "history_fr": normalized_row.get('Histoire (FR)', ''),
                    "history": normalized_row.get('Story (EN)', ''),
                    "wiki_fr": normalized_row.get('URL WIKI FR', ''),
                    "wiki_en": normalized_row.get('URL WIKi EN', ''),
                    "imgUrl": normalized_row.get('URL IMG', ''),
                    "other_link": normalized_row.get('URL DIV', ''),
                    "mapUrl": normalized_row.get('URL Carte', ''),
                    "mapTitle_fr": normalized_row.get('Titre Carte (FR)', ''),
                    "mapTitle_en": normalized_row.get('Map title (EN)', ''),
                    "origin_fr": normalized_row.get('Origine du nom version initiale', ''),
                    "detailsLink": normalized_row.get('fiche detaillee F', ''),
                    "detailsLink_en": normalized_row.get('detailed information sheet E', '')
                }

                # Trie le lieu dans la bonne liste en fonction de l'expédition.
                expedition_lower = expedition_value.lower()
                if expedition_lower in {"d'entrecasteaux", "entrecasteaux"}:
                    entrecasteaux_data.append(place)
                elif expedition_lower == 'baudin':
                    baudin_data.append(place)

    except Exception as e:
        print(f"Une erreur est survenue lors de la lecture du fichier CSV : {e}")
        return

    # Écrit le fichier JSON pour d'Entrecasteaux.
    with open(entrecasteaux_path, 'w', encoding='utf-8') as outfile:
        json.dump(entrecasteaux_data, outfile, indent=4, ensure_ascii=False)

    # Écrit le fichier JSON pour Baudin.
    with open(baudin_path, 'w', encoding='utf-8') as outfile:
        json.dump(baudin_data, outfile, indent=4, ensure_ascii=False)

    print(f"Succès : {entrecasteaux_path} généré avec {len(entrecasteaux_data)} entrées.")
    print(f"Succès : {baudin_path} généré avec {len(baudin_data)} entrées.")

# Exécute la fonction de conversion si le script est lancé directement.
if __name__ == '__main__':
    convert_csv_to_json()
