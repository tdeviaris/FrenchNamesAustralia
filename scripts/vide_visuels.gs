/**
 * Vide les quatre cellules d'image des toponymes dont l'attribution etait
 * fausse, pour que l'import puisse les remplir a nouveau.
 *
 * importeVisuels() respecte toute cellule deja remplie : « le choix de Dany
 * fait foi ». C'est la bonne regle, mais elle bloque aussi la correction
 * d'une erreur venue du depot. Cette fonction ouvre la porte, une fois, sur
 * les seules lignes concernees.
 *
 * Les quinze codes ci-dessous portaient un portrait dementi par l'article
 * de Dany Breelle (Journal of the Hakluyt Society, 2013) : le quatrieme
 * comte Spencer pour le deuxieme, un general de l'armee de terre pour le
 * quartier-maitre Draper, le batteur des Beatles pour l'editeur Nicol.
 *
 * A coller dans l'editeur de scripts du classeur, puis executer une fois.
 * Ensuite : menu GitHub > Mettre a jour les JSONs.
 */
function videLesVisuelsFautifs() {
  const CODES = [
    'Flinders018',   // Draper Island    -> John Draper, quartier-maitre : sans article
    'Flinders033',   // Sinclair Rocks   -> Kennet Sinclair, matelot : sans article
    'Flinders039',   // Lacy Island      -> Denis Lacy, petty officer : sans article
    'Flinders056',   // Pearson Island   -> beau-frere de Flinders : sans article
    'Flinders058',   // Flinders Island  -> Samuel Flinders, son frere : sans article
    'Flinders119',   // Mount Young      -> William Young, et non George
    'Flinders126',   // Hardwicke Bay    -> Charles Philip Yorke
    'Flinders127',   // Spencer Gulf     -> George Spencer, 2e comte
    'Flinders128',   // Cape Spencer     -> George Spencer, 2e comte
    'Flinders151',   // Cape Willoughby  -> Nesbit Willoughby
    'Flinders176',   // Waterhouse Island-> Henry Waterhouse : sans portrait
    'Flinders177',   // Waterhouse Point -> Henry Waterhouse : sans portrait
    'Flinders221',   // De Witt Range    -> Gerrit de Witt : sans article
    'Flinders278',   // Bentinck Island  -> Lord William Bentinck
    'Flinders307'    // Nicol Island     -> George Nicol, libraire
  ];
  const COLONNES = ['URL IMG', 'Credit image', 'Source image', 'Sujet image'];

  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(FLINDERS_SHEET);
  if (!sheet) throw new Error("Onglet « " + FLINDERS_SHEET + " » introuvable.");

  const data = sheet.getDataRange().getValues();
  const entetes = data[0].map(function (h) { return h.toString().trim(); });
  const rangCode = entetes.indexOf('Code');
  if (rangCode === -1) throw new Error("Colonne « Code » introuvable.");

  const rangs = COLONNES.map(function (nom) {
    const i = entetes.indexOf(nom);
    if (i === -1) throw new Error("Colonne « " + nom + " » introuvable.");
    return i;
  });

  const ligneDe = {};
  for (let i = 1; i < data.length; i++) {
    const code = (data[i][rangCode] || '').toString().trim();
    if (code) ligneDe[code] = i;
  }

  const vides = [];
  const absents = [];
  CODES.forEach(function (code) {
    const i = ligneDe[code];
    if (i === undefined) { absents.push(code); return; }
    let touche = false;
    rangs.forEach(function (r) {
      if ((data[i][r] || '').toString().trim()) touche = true;
      sheet.getRange(i + 1, r + 1).clearContent();
    });
    if (touche) vides.push(code);
  });

  SpreadsheetApp.flush();
  const message = vides.length + ' fiche(s) remise(s) à blanc : ' + vides.join(', ')
    + (absents.length ? '\n\nCode(s) absent(s) de l’onglet : ' + absents.join(', ') : '')
    + '\n\nLancer ensuite : menu GitHub > Mettre à jour les JSONs.';
  Logger.log(message);
  Browser.msgBox('Visuels remis à blanc', message, Browser.Buttons.OK);
}
