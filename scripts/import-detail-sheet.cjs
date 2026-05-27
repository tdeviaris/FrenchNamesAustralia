#!/usr/bin/env node
/*
 * Import a French or English detailed notice for the map popup.
 *
 * Usage:
 *   node scripts/import-detail-sheet.cjs Baudin001 --fr "C:\path\Baudin001F.rtf"
 *   node scripts/import-detail-sheet.cjs Baudin001 --en "C:\path\Baudin001E.html"
 *   node scripts/import-detail-sheet.cjs Baudin001 --fr "...\fiche.rtf" --en "...\sheet.rtf"
 *
 * The script writes details/Baudin001F.html or details/Baudin001E.html and
 * updates data/baudin.json (or data/entrecasteaux.json for Entre codes).
 */

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const DETAILS_DIR = path.join(ROOT, 'details');
const SOURCE_DIR = path.join(ROOT, 'Source_documents');
const OFFICE_INPUTS = new Set(['.rtf', '.doc', '.docx']);
const SUPPORTED_INPUTS = new Set(['.rtf', '.doc', '.docx', '.html', '.htm', '.txt']);

const cp1252 = {
  0x80: '\u20ac', 0x82: '\u201a', 0x83: '\u0192', 0x84: '\u201e',
  0x85: '\u2026', 0x86: '\u2020', 0x87: '\u2021', 0x88: '\u02c6',
  0x89: '\u2030', 0x8a: '\u0160', 0x8b: '\u2039', 0x8c: '\u0152',
  0x8e: '\u017d', 0x91: '\u2018', 0x92: '\u2019', 0x93: '\u201c',
  0x94: '\u201d', 0x95: '\u2022', 0x96: '\u2013', 0x97: '\u2014',
  0x98: '\u02dc', 0x99: '\u2122', 0x9a: '\u0161', 0x9b: '\u203a',
  0x9c: '\u0153', 0x9e: '\u017e', 0x9f: '\u0178',
};

const destinationsToSkip = new Set([
  'fonttbl', 'colortbl', 'stylesheet', 'info', 'pict', 'object', 'header',
  'footer', 'generator', 'listtable', 'listoverridetable', 'datastore',
  'themedata', 'colorschememapping', 'xmlnstbl', 'latentstyles',
]);

function usage(exitCode = 1) {
  const text = [
    'Usage:',
    '  node scripts/import-detail-sheet.cjs Baudin001 --fr "C:\\path\\fiche.rtf"',
    '  node scripts/import-detail-sheet.cjs Baudin001 --en "C:\\path\\sheet.html"',
    '  node scripts/import-detail-sheet.cjs Entre01 --fr "C:\\path\\fiche.rtf"',
    '',
    'Options:',
    '  --fr <file>     Import a French notice and update detailsLink',
    '  --en <file>     Import an English notice and update detailsLink_en',
    '  --no-source     Do not copy the source document to Source_documents/',
    '  --title <text>  Override the HTML title',
  ].join('\n');
  console.error(text);
  process.exit(exitCode);
}

function parseArgs(argv) {
  if (argv.includes('--help') || argv.includes('-h')) usage(0);
  if (argv.length < 3) usage();
  const code = argv[2];
  const imports = [];
  let copySource = true;
  let titleOverride = '';

  for (let i = 3; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--fr' || arg === '--en') {
      const file = argv[i + 1];
      if (!file) usage();
      imports.push({ lang: arg === '--fr' ? 'fr' : 'en', file });
      i += 1;
    } else if (arg === '--no-source') {
      copySource = false;
    } else if (arg === '--title') {
      titleOverride = argv[i + 1] || '';
      i += 1;
    } else {
      console.error(`Option inconnue : ${arg}`);
      usage();
    }
  }

  if (!/^(?:Baudin\d{3}|Entre\d{2,3})$/i.test(code)) {
    throw new Error(`Code invalide : ${code}. Exemple attendu : Baudin001 ou Entre01.`);
  }
  if (imports.length === 0) {
    throw new Error('Aucun fichier fourni. Utilise --fr <fichier> ou --en <fichier>.');
  }

  return { code: normalizeCode(code), imports, copySource, titleOverride };
}

function normalizeCode(code) {
  const match = code.match(/^(Baudin|Entre)(\d+)$/i);
  const prefix = match[1].toLowerCase() === 'baudin' ? 'Baudin' : 'Entre';
  const width = prefix === 'Baudin' ? 3 : 2;
  return `${prefix}${match[2].padStart(width, '0')}`;
}

function datasetPathForCode(code) {
  return path.join(ROOT, 'data', code.startsWith('Baudin') ? 'baudin.json' : 'entrecasteaux.json');
}

function htmlEscape(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function decodeCp1252Byte(byte) {
  return cp1252[byte] || String.fromCharCode(byte);
}

function rtfToText(buffer) {
  const input = buffer.toString('latin1');
  const out = [];
  const stack = [{ skip: false, uc: 1 }];
  let uc = 1;
  let skipChars = 0;

  const current = () => stack[stack.length - 1];
  const isSkipping = () => current().skip;
  const append = (text) => {
    if (!isSkipping() && skipChars <= 0) out.push(text);
  };

  for (let i = 0; i < input.length; i += 1) {
    const ch = input[i];

    if (skipChars > 0 && ch !== '\\' && ch !== '{' && ch !== '}') {
      skipChars -= 1;
      continue;
    }

    if (ch === '{') {
      stack.push({ skip: current().skip, uc });
      continue;
    }
    if (ch === '}') {
      const popped = stack.pop();
      uc = stack.length ? current().uc : (popped?.uc || 1);
      continue;
    }
    if (ch !== '\\') {
      append(ch);
      continue;
    }

    const next = input[i + 1];
    if (next === '\\' || next === '{' || next === '}') {
      append(next);
      i += 1;
      continue;
    }
    if (next === '~') {
      append('\u00a0');
      i += 1;
      continue;
    }
    if (next === '-') {
      append('\u00ad');
      i += 1;
      continue;
    }
    if (next === '_') {
      append('\u2011');
      i += 1;
      continue;
    }
    if (next === '*') {
      current().skip = true;
      i += 1;
      continue;
    }
    if (next === "'") {
      const hex = input.slice(i + 2, i + 4);
      if (/^[0-9a-f]{2}$/i.test(hex)) {
        append(decodeCp1252Byte(parseInt(hex, 16)));
        i += 3;
        continue;
      }
    }

    const match = input.slice(i + 1).match(/^([a-zA-Z]+)(-?\d+)? ?/);
    if (!match) {
      i += 1;
      continue;
    }

    const word = match[1];
    const param = match[2] === undefined ? null : Number(match[2]);
    i += match[0].length;

    if (destinationsToSkip.has(word)) {
      current().skip = true;
      continue;
    }
    if (word === 'uc' && Number.isFinite(param)) {
      uc = Math.max(0, param);
      current().uc = uc;
      continue;
    }
    if (word === 'u' && Number.isFinite(param)) {
      let codePoint = param;
      if (codePoint < 0) codePoint += 65536;
      append(String.fromCharCode(codePoint));
      skipChars = uc;
      continue;
    }
    if (word === 'par' || word === 'sect') {
      append('\n\n');
      continue;
    }
    if (word === 'line' || word === 'tab') {
      append(word === 'tab' ? '\t' : '\n');
      continue;
    }
    if (word === 'emdash') append('\u2014');
    if (word === 'endash') append('\u2013');
    if (word === 'lquote') append('\u2018');
    if (word === 'rquote') append('\u2019');
    if (word === 'ldblquote') append('\u201c');
    if (word === 'rdblquote') append('\u201d');
  }

  return out.join('')
    .replace(/\r/g, '')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function splitParagraphs(text) {
  return text
    .replace(/\u0000/g, '')
    .split(/\n\s*\n/g)
    .map((paragraph) => paragraph.replace(/\s*\n\s*/g, ' ').trim())
    .filter(Boolean);
}

function linkifyEscaped(text) {
  return htmlEscape(text).replace(
    /(https?:\/\/[^\s<]+)/g,
    (url) => {
      const clean = url.replace(/[.,);]+$/, '');
      const trailing = url.slice(clean.length);
      return `<a href="${clean}" target="_blank" rel="noopener noreferrer">${clean}</a>${trailing}`;
    },
  );
}

function buildHtmlFromText({ code, lang, title, text }) {
  const paragraphs = splitParagraphs(text);
  const refIndex = paragraphs.findIndex((p) => /^(références|references|bibliographie|bibliography)\b/i.test(p));
  const body = refIndex >= 0 ? paragraphs.slice(0, refIndex) : paragraphs;
  const refs = refIndex >= 0 ? paragraphs.slice(refIndex) : [];
  const heading = title || body[0] || code;
  const bodyStart = body.length > 1 && body[0] === heading ? 1 : 0;
  const langAttr = lang === 'fr' ? 'fr-FR' : 'en';
  const refHeading = refs[0] || (lang === 'fr' ? 'Références' : 'References');
  const refItems = refs.slice(1);

  return `<!DOCTYPE html>
<html lang="${langAttr}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${htmlEscape(heading)}</title>
  <link rel="icon" type="image/png" sizes="32x32" href="../img/favicon32.png">
  <link rel="icon" type="image/png" sizes="16x16" href="../img/favicon16.png">
  <style>
    body {
      margin: 0;
      padding: 2em 1.5em;
      color: #222;
      background: #fdfdfd;
      font-family: Aptos, Calibri, "Segoe UI", Arial, sans-serif;
      line-height: 1.6;
      letter-spacing: 0;
    }
    .document-header {
      margin: 0 0 1.8em;
      text-align: center;
    }
    .document-header p {
      margin: 0.15em 0;
    }
    .detail-title,
    .detail-subtitle {
      font-family: "Aptos Display", Aptos, Calibri, "Segoe UI", Arial, sans-serif;
      font-weight: 700;
      line-height: 1.35;
    }
    .main-text {
      margin: 0 auto 2em;
      max-width: 72ch;
      text-align: justify;
      font-family: Aptos, Calibri, "Segoe UI", Arial, sans-serif;
      font-size: 0.96rem;
    }
    .main-text p {
      margin: 0 0 1em;
    }
    .references-section {
      max-width: 72ch;
      margin: 2em auto 0;
      padding-top: 1em;
      border-top: 1px solid #ccc;
      font-family: "Speak Pro", Aptos, Calibri, "Segoe UI", Arial, sans-serif;
      font-size: 0.86rem;
      line-height: 1.45;
    }
    .references-section h2 {
      margin: 0 0 0.5em;
      font-size: 1rem;
    }
    .references-section ul {
      list-style: disc;
      padding-left: 1.5em;
      margin: 0.5em 0 0;
    }
    .references-section li {
      margin: 0.4em 0;
    }
    a {
      color: #0056b3;
      text-decoration: none;
    }
    a:hover {
      text-decoration: underline;
    }
  </style>
</head>
<body>
  <header class="document-header">
    <p class="detail-title">${htmlEscape(heading)}</p>
  </header>
  <main class="main-text">
${body.slice(bodyStart).map((p) => `    <p>${linkifyEscaped(p)}</p>`).join('\n')}
  </main>
${refs.length ? `  <section class="references-section">
    <h2>${htmlEscape(refHeading.replace(/:$/, ''))}</h2>
${refItems.length ? `    <ul>
${refItems.map((item) => `      <li>${linkifyEscaped(item)}</li>`).join('\n')}
    </ul>` : ''}
  </section>
` : ''}</body>
</html>
`;
}

function normalizeExistingHtml(sourceHtml, title) {
  let html = sourceHtml;
  if (!/<meta\s+charset=/i.test(html)) {
    html = html.replace(/<head[^>]*>/i, (match) => `${match}\n  <meta charset="utf-8">`);
  }
  if (!/<meta\s+name=["']viewport["']/i.test(html)) {
    html = html.replace(/<head[^>]*>/i, (match) => `${match}\n  <meta name="viewport" content="width=device-width, initial-scale=1.0">`);
  }
  if (!/<title>.*<\/title>/is.test(html)) {
    html = html.replace(/<head[^>]*>/i, (match) => `${match}\n  <title>${htmlEscape(title)}</title>`);
  }
  if (!/favicon32\.png/i.test(html)) {
    html = html.replace(/<\/head>/i, '  <link rel="icon" type="image/png" sizes="32x32" href="../img/favicon32.png">\n  <link rel="icon" type="image/png" sizes="16x16" href="../img/favicon16.png">\n</head>');
  }
  return html;
}

function findSoffice() {
  const candidates = [
    process.env.SOFFICE,
    'soffice',
    'C:\\Program Files\\LibreOffice\\program\\soffice.exe',
    'C:\\Program Files (x86)\\LibreOffice\\program\\soffice.exe',
  ].filter(Boolean);

  for (const candidate of candidates) {
    if (candidate.includes('\\') || candidate.includes('/')) {
      if (fs.existsSync(candidate)) return candidate;
      continue;
    }
    const probe = process.platform === 'win32'
      ? spawnSync('where.exe', [candidate], { encoding: 'utf8' })
      : spawnSync('sh', ['-c', `command -v ${candidate}`], { encoding: 'utf8' });
    if (probe.status === 0) {
      const found = probe.stdout.split(/\r?\n/).map((line) => line.trim()).find(Boolean);
      return found || candidate;
    }
  }
  return '';
}

function convertWithLibreOffice({ sourcePath, targetBase, title }) {
  const soffice = findSoffice();
  if (!soffice) return '';

  const tempDir = path.join(ROOT, '.tmp', `detail-import-${process.pid}-${Date.now()}`);
  fs.mkdirSync(tempDir, { recursive: true });
  const tempSource = path.join(tempDir, `${targetBase}${path.extname(sourcePath).toLowerCase()}`);
  fs.copyFileSync(sourcePath, tempSource);

  const result = spawnSync(
    soffice,
    ['--headless', '--convert-to', 'html:HTML', '--outdir', tempDir, tempSource],
    { encoding: 'utf8' },
  );

  if (result.status !== 0) {
    fs.rmSync(tempDir, { recursive: true, force: true });
    return '';
  }

  const generatedHtml = path.join(tempDir, `${targetBase}.html`);
  if (!fs.existsSync(generatedHtml)) {
    fs.rmSync(tempDir, { recursive: true, force: true });
    return '';
  }

  for (const entry of fs.readdirSync(tempDir)) {
    const from = path.join(tempDir, entry);
    if (from === generatedHtml || from === tempSource) continue;
    const to = path.join(DETAILS_DIR, entry);
    fs.copyFileSync(from, to);
  }

  const html = normalizeExistingHtml(fs.readFileSync(generatedHtml, 'utf8'), title);
  fs.rmSync(tempDir, { recursive: true, force: true });
  return html;
}

function convertInputToHtml({ sourcePath, code, lang, title, targetBase }) {
  const ext = path.extname(sourcePath).toLowerCase();
  if (!SUPPORTED_INPUTS.has(ext)) {
    throw new Error(`Format non pris en charge sans LibreOffice/Word : ${ext}. Utilise .rtf, .html ou .txt.`);
  }

  if (ext === '.html' || ext === '.htm') {
    return normalizeExistingHtml(fs.readFileSync(sourcePath, 'utf8'), title || code);
  }

  if (OFFICE_INPUTS.has(ext)) {
    const libreOfficeHtml = convertWithLibreOffice({ sourcePath, targetBase, title: title || code });
    if (libreOfficeHtml) return libreOfficeHtml;
    if (ext !== '.rtf') {
      throw new Error(`La conversion ${ext} nécessite LibreOffice/soffice. Convertis le fichier en RTF ou HTML, ou installe LibreOffice.`);
    }
    console.warn('[info] LibreOffice/soffice introuvable ou conversion échouée : conversion RTF en texte HTML simple (les images intégrées ne seront pas extraites).');
  }

  const text = ext === '.rtf'
    ? rtfToText(fs.readFileSync(sourcePath))
    : fs.readFileSync(sourcePath, 'utf8').trim();

  if (!text) {
    throw new Error(`Aucun texte lisible trouvé dans ${sourcePath}`);
  }
  return buildHtmlFromText({ code, lang, title, text });
}

function updateDataset({ code, lang, htmlName }) {
  const datasetPath = datasetPathForCode(code);
  const data = JSON.parse(fs.readFileSync(datasetPath, 'utf8'));
  const matches = data.filter((place) => place.code === code);
  if (!matches.length) {
    throw new Error(`Aucune entrée ${code} trouvée dans ${path.relative(ROOT, datasetPath)}.`);
  }
  const key = lang === 'fr' ? 'detailsLink' : 'detailsLink_en';
  for (const place of matches) {
    place[key] = htmlName;
  }
  fs.writeFileSync(datasetPath, `${JSON.stringify(data, null, 2)}\n`, 'utf8');
  return { datasetPath, count: matches.length, key };
}

function copySourceDocument(sourcePath, targetBase) {
  fs.mkdirSync(SOURCE_DIR, { recursive: true });
  const target = path.join(SOURCE_DIR, `${targetBase}${path.extname(sourcePath).toLowerCase()}`);
  fs.copyFileSync(sourcePath, target);
  return target;
}

function main() {
  const args = parseArgs(process.argv);
  fs.mkdirSync(DETAILS_DIR, { recursive: true });

  const results = [];
  for (const item of args.imports) {
    const sourcePath = path.resolve(item.file);
    if (!fs.existsSync(sourcePath)) {
      throw new Error(`Fichier introuvable : ${sourcePath}`);
    }

    const suffix = item.lang === 'fr' ? 'F' : 'E';
    const targetBase = `${args.code}${suffix}`;
    const htmlName = `${targetBase}.html`;
    const htmlPath = path.join(DETAILS_DIR, htmlName);
    const title = args.titleOverride;
    const html = convertInputToHtml({ sourcePath, code: args.code, lang: item.lang, title, targetBase });
    fs.writeFileSync(htmlPath, html, 'utf8');

    const copiedSource = args.copySource ? copySourceDocument(sourcePath, targetBase) : null;
    const dataset = updateDataset({ code: args.code, lang: item.lang, htmlName });
    results.push({ htmlPath, copiedSource, dataset, lang: item.lang });
  }

  for (const result of results) {
    console.log(`OK ${result.lang.toUpperCase()} -> ${path.relative(ROOT, result.htmlPath)}`);
    if (result.copiedSource) {
      console.log(`Source copiée -> ${path.relative(ROOT, result.copiedSource)}`);
    }
    console.log(`JSON mis à jour -> ${path.relative(ROOT, result.dataset.datasetPath)} (${result.dataset.count} entrée(s), ${result.dataset.key})`);
  }
}

try {
  main();
} catch (error) {
  console.error(`Erreur : ${error.message}`);
  process.exit(1);
}
