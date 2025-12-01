#!/usr/bin/env node
/**
 * Injecte le contenu de partials/nav.html dans chaque page listée,
 * en remplaçant le placeholder <div data-include-nav></div>.
 * Permet de servir les pages sans fetch async (pas de flash).
 */

const fs = require('fs');
const path = require('path');

const FILES = [
  'index.html',
  'expert.html',
  'resources.html',
  'glossaryF.html',
  'glossaryE.html',
  'acteursF.html',
  'acteursE.html',
  'cartesF.html',
  'cartesE.html',
  'SourcesF.html',
  'SourcesE.html',
  'map_baudin.html',
  'map_dentrecasteaux.html'
];

const NAV_PARTIAL = path.join(__dirname, '..', 'partials', 'nav.html');

function injectNav(filePath, navHtml) {
  const fullPath = path.join(__dirname, '..', filePath);
  if (!fs.existsSync(fullPath)) {
    console.warn(`⚠️  Fichier introuvable: ${filePath}`);
    return false;
  }

  const content = fs.readFileSync(fullPath, 'utf8');
  const replaced = content.replace(
    /<div\s+data-include-nav[^>]*>\s*<\/div>/i,
    navHtml
  );

  if (replaced !== content) {
    fs.writeFileSync(fullPath, replaced, 'utf8');
    console.log(`✅ Injecté: ${filePath}`);
    return true;
  }

  console.log(`ℹ️  Aucun placeholder à remplacer dans ${filePath}`);
  return false;
}

function run() {
  if (!fs.existsSync(NAV_PARTIAL)) {
    console.error(`❌ Partial de nav introuvable: ${NAV_PARTIAL}`);
    process.exit(1);
  }

  const navHtml = fs.readFileSync(NAV_PARTIAL, 'utf8').trim();
  let changed = 0;
  FILES.forEach((file) => {
    if (injectNav(file, navHtml)) {
      changed += 1;
    }
  });
  console.log(`\n✨ Injection terminée. Fichiers modifiés: ${changed}`);
}

run();
