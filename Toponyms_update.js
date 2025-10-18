// ----- 1. VOS VARIABLES À CONFIGURER -----
const GITHUB_TOKEN_NAME = 'GITHUB_TOKEN';
const GITHUB_USER = 'tdeviaris'; // Votre nom d'utilisateur GitHub
const GITHUB_REPO = 'FrenchNamesAustralia'; // Le nom de votre dépôt

// NOUVEAU : Définissez les chemins pour les DEUX fichiers JSON de sortie
const ENTRECASTEAUX_PATH = 'data/entrecasteaux.json'; // Chemin pour le fichier d'Entrecasteaux
const BAUDIN_PATH = 'data/baudin.json';             // Chemin pour le fichier Baudin

const SHEET_NAME = 'Source'; // Assurez-vous que c'est le nom exact de votre onglet
// ------------------------------------------


/**
 * MODIFIÉ : Le nom de la fonction principale a changé pour refléter la nouvelle logique.
 * C'est cette fonction qu'il faudra exécuter.
 */
function updateJsonFilesOnGitHub() {
  try {
    // Étape 1 : Lire la feuille et trier les données dans deux objets distincts.
    const datasets = convertSheetToTwoDatasets();
    
    if (!datasets) {
      Logger.log("Conversion annulée : feuille vide ou colonne 'Expedition' manquante.");
      return;
    }

    Logger.log(`Trouvé ${datasets.entrecasteaux.length} entrées pour d'Entrecasteaux.`);
    Logger.log(`Trouvé ${datasets.baudin.length} entrées pour Baudin.`);

    // Étape 2 : Uploader le premier fichier JSON sur GitHub.
    const entrecasteauxJsonString = JSON.stringify(datasets.entrecasteaux, null, 2);
    uploadToGitHub(ENTRECASTEAUX_PATH, entrecasteauxJsonString, "Mise à jour automatique (d'Entrecasteaux)");
    
    // Étape 3 : Uploader le second fichier JSON sur GitHub.
    const baudinJsonString = JSON.stringify(datasets.baudin, null, 2);
    uploadToGitHub(BAUDIN_PATH, baudinJsonString, "Mise à jour automatique (Baudin)");

  } catch (e) {
    Logger.log(`Erreur lors de la mise à jour GitHub : ${e.stack}`);
  }
}

/**
 * NOUVEAU : Cette fonction lit la feuille et la divise en deux listes,
 * en reproduisant la logique du script Python.
 */
function convertSheetToTwoDatasets() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  if (!sheet) {
    Logger.log(`Erreur : L'onglet "${SHEET_NAME}" est introuvable.`);
    return null;
  }
  
  const data = sheet.getDataRange().getValues();
  if (data.length <= 1) {
    Logger.log("Feuille vide ou ne contient que l'en-tête.");
    return null;
  }
  
  const headers = data.shift();
  
  // Trouve l'index de la colonne 'Expedition', qui est cruciale pour le tri.
  const expeditionIndex = headers.indexOf('Expedition');
  if (expeditionIndex === -1) {
      Logger.log("Erreur critique : La colonne 'Expedition' est introuvable dans les en-têtes.");
      return null;
  }
  
  // Crée un mappage des en-têtes vers leur index pour un accès facile.
  const headerMap = {};
  headers.forEach((header, index) => {
    headerMap[header] = index;
  });

  const entrecasteaux_data = [];
  const baudin_data = [];

  data.forEach(row => {
    const expedition_value = (row[expeditionIndex] || '').trim().toLowerCase();
    
    // Fonction pour obtenir une valeur de manière sûre
    const getValue = (headerName) => row[headerMap[headerName]] || '';

    // Conversion des coordonnées en nombres (float)
    const latStr = (getValue('latitude South') || '0').replace(',', '.');
    const lonStr = (getValue('longitude East') || '0').replace(',', '.');
    const lat = parseFloat(latStr) || 0.0;
    const lon = parseFloat(lonStr) || 0.0;

    // Crée l'objet "place" exactement comme dans le script Python
    const place = {
      "code": getValue('Code'),
      "expedition": getValue('Expedition'),
      "state": getValue('State'),
      "frenchName": getValue('French name'),
      "variantName": getValue('Variant and other historical name'),
      "ausEName": getValue('Australian name'),
      "indigenousName": getValue('Aboriginal name'),
      "indigenousLanguage": getValue('Aboriginal language group'),
      "lat": lat,
      "lon": lon,
      "characteristic_fr": getValue('Caracteristiques  (FR)'),
      "characteristic": getValue('Characteristic  (EN)'),
      "history_fr": getValue('Histoire (FR)'),
      "history": getValue('Story (EN)'),
      "wiki_fr": getValue('URL WIKI FR'),
      "wiki_en": getValue('URL WIKi EN'),
      "imgUrl": getValue('URL IMG'),
      "other_link": getValue('URL DIV'),
      "mapUrl": getValue('URL Carte'),
      "mapTitle_fr": getValue('Titre Carte (FR)'),
      "mapTitle_en": getValue('Map title (EN)'),
      "origin_fr": getValue('Origine du nom version initiale'),
      "detailsLink": getValue('fiche detaillee F'),
      "detailsLink_en": getValue('detailed information sheet E')
    };

    // Trie l'objet dans la bonne liste
    if (expedition_value === "d'entrecasteaux" || expedition_value === "entrecasteaux") {
        entrecasteaux_data.push(place);
    } else if (expedition_value === 'baudin') {
        baudin_data.push(place);
    }
  });
  
  return { entrecasteaux: entrecasteaux_data, baudin: baudin_data };
}


/**
 * MODIFIÉ : La fonction d'upload est maintenant plus générique.
 */
function uploadToGitHub(filePath, jsonContent, commitMessage) {
  const token = PropertiesService.getScriptProperties().getProperty(GITHUB_TOKEN_NAME);
  if (!token) {
    throw new Error("Token GitHub non trouvé. Configurez-le via le menu.");
  }

  const apiUrl = `https://api.github.com/repos/${GITHUB_USER}/${GITHUB_REPO}/contents/${filePath}`;
  const headers = {
    'Authorization': `token ${token}`,
    'Accept': 'application/vnd.github.v3+json'
  };

  let currentSha = null;
  try {
    const getResponse = UrlFetchApp.fetch(apiUrl, { method: 'get', headers: headers, muteHttpExceptions: true });
    if (getResponse.getResponseCode() == 200) {
      currentSha = JSON.parse(getResponse.getContentText()).sha;
    }
  } catch (e) { /* Fichier n'existe pas, c'est normal */ }

  const contentBase64 = Utilities.base64Encode(jsonContent, Utilities.Charset.UTF_8);
  const payload = {
    message: commitMessage,
    content: contentBase64,
    branch: 'main'
  };

  if (currentSha) {
    payload.sha = currentSha;
  }

  const putOptions = {
    method: 'put',
    headers: headers,
    contentType: 'application/json',
    payload: JSON.stringify(payload)
  };

  const putResponse = UrlFetchApp.fetch(apiUrl, putOptions);
  if (putResponse.getResponseCode() == 200 || putResponse.getResponseCode() == 201) {
    Logger.log(`Succès ! Fichier ${filePath} mis à jour/créé.`);
  } else {
    Logger.log(`Échec de l'upload pour ${filePath}. Réponse : ${putResponse.getContentText()}`);
  }
}


// ----- FONCTIONS DU MENU (INCHANGÉES) -----
function setGitHubToken() {
  const token = Browser.inputBox('Stocker le Token GitHub', 
                                'Veuillez coller votre Personal Access Token GitHub ici :', 
                                Browser.Buttons.OK_CANCEL);
  if (token && token !== 'cancel') {
    PropertiesService.getScriptProperties().setProperty(GITHUB_TOKEN_NAME, token);
    // LIGNE CORRIGÉE CI-DESSOUS
    Browser.msgBox('Succès', 'Votre Token GitHub a été stocké.', Browser.Buttons.OK);
  }
}

function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('GitHub')
    .addItem('Mettre à jour les JSONs maintenant', 'updateJsonFilesOnGitHub') // MODIFIÉ pour appeler la bonne fonction
    .addSeparator()
    .addItem('Configurer le Token GitHub', 'setGitHubToken')
    .addToUi();
}