#!/usr/bin/env node
/**
 * Verse rag/corpus/ dans un Vector Store OpenAI, celui que file_search
 * interroge depuis api/responses-chat.js.
 *
 * Le corpus est produit par les deux scripts Python d'à côté :
 *   python3 rag/extraire_site.py        (le site : pages, fiches, données, journaux)
 *   python3 rag/convertir_sources.py    (les journaux et documents du dehors)
 *
 * L'indexation crée un magasin NEUF et ne touche pas à l'ancien : tant que
 * VECTOR_STORE_ID n'a pas bougé sur Vercel, le chatbot en production continue
 * de répondre sur l'ancienne base. Le nouvel identifiant est écrit dans .env
 * sous VECTOR_STORE_ID_V2, et un journal de bord est laissé dans
 * rag/derniere_indexation.json — c'est lui qui permet de reprendre une
 * indexation interrompue avec --reprendre <vs_...>.
 *
 * Usage :
 *   node rag/indexer.mjs                 # nouveau magasin, corpus entier
 *   node rag/indexer.mjs --reprendre vs_xxx   # complète un magasin existant
 *   node rag/indexer.mjs --essai         # compte les fichiers, n'envoie rien
 */

import OpenAI from 'openai';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const RACINE = path.dirname(__dirname);
const CORPUS = path.join(__dirname, 'corpus');
const JOURNAL = path.join(__dirname, 'derniere_indexation.json');

// OpenAI accepte jusqu'à 500 fichiers par lot ; on reste bien en deçà pour
// qu'un échec ne coûte que quelques dizaines de fichiers à refaire.
const TAILLE_LOT = 80;

function listeDuCorpus() {
  const fichiers = [];
  for (const sous of fs.readdirSync(CORPUS).sort()) {
    const dossier = path.join(CORPUS, sous);
    if (!fs.statSync(dossier).isDirectory()) continue;
    for (const nom of fs.readdirSync(dossier).sort()) {
      if (nom.endsWith('.md')) fichiers.push(path.join(dossier, nom));
    }
  }
  return fichiers;
}

function chargeEnv() {
  // Vercel n'est pas là quand on lance le script à la main : on lit .env
  // nous-mêmes plutôt que d'ajouter une dépendance.
  for (const nom of ['.env.local', '.env']) {
    const chemin = path.join(RACINE, nom);
    if (!fs.existsSync(chemin)) continue;
    for (const ligne of fs.readFileSync(chemin, 'utf-8').split('\n')) {
      const m = ligne.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
      if (m && !process.env[m[1]]) process.env[m[1]] = m[2].replace(/^["']|["']$/g, '');
    }
  }
}

function inscritDansEnv(cle, valeur) {
  const chemin = path.join(RACINE, '.env');
  let contenu = fs.existsSync(chemin) ? fs.readFileSync(chemin, 'utf-8') : '';
  if (new RegExp(`^${cle}=`, 'm').test(contenu)) {
    contenu = contenu.replace(new RegExp(`^${cle}=.*$`, 'm'), `${cle}=${valeur}`);
  } else {
    contenu += `${contenu.endsWith('\n') ? '' : '\n'}${cle}=${valeur}\n`;
  }
  fs.writeFileSync(chemin, contenu);
}

async function main() {
  chargeEnv();

  const fichiers = listeDuCorpus();
  const poids = fichiers.reduce((t, f) => t + fs.statSync(f).size, 0);
  const parDossier = {};
  for (const f of fichiers) {
    const sous = path.basename(path.dirname(f));
    parDossier[sous] = (parDossier[sous] || 0) + 1;
  }

  console.log('📚 Corpus à indexer');
  for (const [sous, n] of Object.entries(parDossier).sort()) {
    console.log(`   ${sous.padEnd(18)} ${String(n).padStart(5)} fichiers`);
  }
  console.log(`   ${'TOTAL'.padEnd(18)} ${String(fichiers.length).padStart(5)} fichiers, ${(poids / 1e6).toFixed(1)} Mo\n`);

  if (process.argv.includes('--essai')) {
    console.log('🧪 --essai : rien n’a été envoyé.');
    return;
  }
  if (!fichiers.length) {
    console.error('❌ Corpus vide. Lance d’abord extraire_site.py et convertir_sources.py.');
    process.exit(1);
  }
  if (!process.env.OPENAI_API_KEY) {
    console.error('❌ OPENAI_API_KEY absente (ni dans l’environnement, ni dans .env).');
    process.exit(1);
  }

  const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

  const iReprise = process.argv.indexOf('--reprendre');
  let magasinId;
  if (iReprise !== -1) {
    magasinId = process.argv[iReprise + 1];
    console.log(`♻️  Reprise sur le magasin ${magasinId}`);
  } else {
    const nom = `Toponymes — corpus complet (${new Date().toISOString().slice(0, 10)})`;
    const magasin = await openai.vectorStores.create({ name: nom });
    magasinId = magasin.id;
    console.log(`🧠 Magasin créé : ${magasinId}\n   « ${nom} »`);
  }

  // Ce qui est déjà en place, pour ne pas le renvoyer lors d'une reprise.
  // Le magasin ne garde que des identifiants OpenAI, qui ne disent rien du
  // chemin local : c'est notre propre journal de bord qui fait le lien.
  const journal = { magasin: magasinId, debut: new Date().toISOString(), envoyes: [], echecs: [] };
  let déjàLà = new Set();
  if (iReprise !== -1) {
    if (fs.existsSync(JOURNAL)) {
      const ancien = JSON.parse(fs.readFileSync(JOURNAL, 'utf-8'));
      if (ancien.magasin === magasinId) {
        déjàLà = new Set(ancien.envoyes);
        journal.envoyes = [...ancien.envoyes];
      } else {
        console.log(`   ⚠️  le journal de bord vise ${ancien.magasin}, pas ${magasinId} :`);
        console.log('      tout le corpus sera renvoyé, et les doublons se cumuleront.');
      }
    }
    const distants = await openai.vectorStores.retrieve(magasinId);
    console.log(`   ${déjàLà.size} fichiers connus du journal de bord, ` +
                `${distants.file_counts?.total ?? '?'} présents dans le magasin`);
  }

  const àEnvoyer = fichiers.filter((f) => !déjàLà.has(path.relative(CORPUS, f)));
  if (àEnvoyer.length !== fichiers.length) {
    console.log(`   ${fichiers.length - àEnvoyer.length} fichiers passés, ${àEnvoyer.length} à envoyer`);
  }

  let faits = 0;

  for (let i = 0; i < àEnvoyer.length; i += TAILLE_LOT) {
    const lot = àEnvoyer.slice(i, i + TAILLE_LOT);
    const numero = Math.floor(i / TAILLE_LOT) + 1;
    const total = Math.ceil(àEnvoyer.length / TAILLE_LOT);
    process.stdout.write(`   lot ${numero}/${total} (${lot.length} fichiers)… `);

    try {
      const flux = lot.map((f) => fs.createReadStream(f));
      const résultat = await openai.vectorStores.fileBatches.uploadAndPoll(magasinId, { files: flux });
      faits += lot.length;
      journal.envoyes.push(...lot.map((f) => path.relative(CORPUS, f)));
      const ratés = résultat.file_counts?.failed || 0;
      console.log(`✅ ${faits}/${àEnvoyer.length}${ratés ? `  (${ratés} en échec)` : ''}`);
    } catch (erreur) {
      console.log(`❌ ${erreur?.message || erreur}`);
      journal.echecs.push({ lot: numero, fichiers: lot.map((f) => path.relative(CORPUS, f)), erreur: String(erreur?.message || erreur) });
    }
    fs.writeFileSync(JOURNAL, JSON.stringify(journal, null, 2));
  }

  journal.fin = new Date().toISOString();
  fs.writeFileSync(JOURNAL, JSON.stringify(journal, null, 2));

  const final = await openai.vectorStores.retrieve(magasinId);
  console.log('\n════════════════════════════════════════════════════════');
  console.log(`✅ Indexation terminée — ${JSON.stringify(final.file_counts)}`);
  console.log('════════════════════════════════════════════════════════');

  inscritDansEnv('VECTOR_STORE_ID_V2', magasinId);
  console.log(`\n💾 .env : VECTOR_STORE_ID_V2=${magasinId}`);
  console.log('   L’ancien VECTOR_STORE_ID est intact ; le site répond encore dessus.');
  console.log('\n👉 Pour basculer : mettre VECTOR_STORE_ID à cette valeur dans les');
  console.log('   variables d’environnement Vercel, puis redéployer.');
  if (journal.echecs.length) {
    console.log(`\n⚠️  ${journal.echecs.length} lot(s) en échec — voir rag/derniere_indexation.json`);
    console.log(`   Reprendre avec : node rag/indexer.mjs --reprendre ${magasinId}`);
  }
}

main().catch((erreur) => {
  console.error('\n❌ Erreur :', erreur?.message || erreur);
  process.exit(1);
});
