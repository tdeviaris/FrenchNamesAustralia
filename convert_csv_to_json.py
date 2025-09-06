import csv
import json
import os

def convert_csv_to_json():
    """
    Lit le fichier toponymes.csv, incluant la nouvelle colonne 'URL IMG',
    et génère les fichiers entrecasteaux.json et baudin.json.
    """
    # Définit les chemins des fichiers en supposant que le script est à la racine du projet.
    csv_path = os.path.join('data', 'toponymes.csv')
    entrecasteaux_path = os.path.join('data', 'entrecasteaux.json')
    baudin_path = os.path.join('data', 'baudin.json')

    # Vérifie si le fichier CSV source existe.
    if not os.path.exists(csv_path):
        print(f"Erreur : Le fichier source '{csv_path}' est introuvable.")
        print("Veuillez vous assurer que 'toponymes.csv' se trouve bien dans le dossier 'data'.")
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
            if 'Expedition' not in reader.fieldnames:
                print(f"Erreur critique : La colonne 'Expedition' est introuvable dans les en-têtes du fichier CSV.")
                print(f"Les en-têtes détectés sont : {reader.fieldnames}")
                print("Cela est souvent dû à un problème de délimiteur (virgule vs point-virgule).")
                return

            for row in reader:
                # Récupère latitude et longitude, et les convertit en nombres (float).
                try:
                    # Remplace la virgule par un point pour les nombres décimaux si nécessaire
                    lat_str = row.get('latitude', '0.0').replace(',', '.')
                    lon_str = row.get('longitude', '0.0').replace(',', '.')
                    lat = float(lat_str) if lat_str else 0.0
                    lon = float(lon_str) if lon_str else 0.0
                except (ValueError, TypeError):
                    print(f"Avertissement : Coordonnées invalides pour '{row.get('frenchName', 'N/A')}'. Utilisation de 0.0.")
                    lat, lon = 0.0, 0.0

                # Crée le dictionnaire pour l'entrée JSON.
                # .get(key, '') est utilisé pour éviter une erreur si une colonne est manquante.
                place = {
                    "expedition": row.get('Expedition', ''),
                    "frenchName": row.get('French name', ''),
                    "ausEName": row.get('Australian name', ''),
                    "indigenousName": row.get('Aborigines name', ''),
                    "indigenousLanguage": row.get('Aborigines langage', ''),
                    "lat": lat,
                    "lon": lon,
                    "characteristic_fr": row.get('Caracteristiques (FR)', ''),
                    "characteristic": row.get('Characteristic (EN)', ''),
                    "origin_fr": row.get('Origine du nom (FR)', ''),
                    "origin": row.get('Origin of the name (EN)', ''),
                    "wiki_fr": row.get('URL WIKI FR', ''),
                    "wiki_en": row.get('URL WIKi EN', ''),
                    "other_link": row.get('URL DIV', ''),
                    "detailsLink": row.get('détails', ''),
                    "imgUrl": row.get('URL IMG', '')  # Récupère la nouvelle URL de l'image
                }

                # Trie le lieu dans la bonne liste en fonction de l'expédition.
                if place['expedition'].lower() == 'entrecasteaux':
                    entrecasteaux_data.append(place)
                elif place['expedition'].lower() == 'baudin':
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