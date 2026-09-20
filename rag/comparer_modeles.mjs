#!/usr/bin/env node
/**
 * Compare plusieurs modèles sur le même magasin et les mêmes questions.
 *
 * On mesure ce qui compte pour ce chatbot-là : le temps de réponse — un
 * visiteur attend devant sa page —, le coût, et surtout si le modèle va
 * chercher le bon document et respecte la syntaxe de liens du site.
 *
 * Usage : node rag/comparer_modeles.mjs [vs_xxx] [modele1,modele2,...]
 */

import OpenAI from 'openai';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { TOPONYMES_INSTRUCTIONS } from '../responses/instructions.js';

const RACINE = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

// Trois questions qui éprouvent trois choses différentes : aller chercher une
// journée précise dans un journal, tenir la syntaxe de liens du site, et
// avouer une limite plutôt que de broder.
const QUESTIONS = [
  ["journal daté",
   "Que raconte le journal de Flinders le 31 juillet 1801 ?"],
  ["liens du site",
   "Pourquoi la baie Paterson porte-t-elle ce nom ? Cite le lieu et les personnes."],
  ["aveu d'ignorance",
   "Que dit le journal de Hamelin de l'escale de Port Jackson en juin 1802 ?"],
];

function chargeEnv() {
  for (const nom of ['.env.local', '.env']) {
    const chemin = path.join(RACINE, nom);
    if (!fs.existsSync(chemin)) continue;
    for (const ligne of fs.readFileSync(chemin, 'utf-8').split('\n')) {
      const m = ligne.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
      if (m && !process.env[m[1]]) process.env[m[1]] = m[2].replace(/^["']|["']$/g, '');
    }
  }
}

async function interroge(openai, modele, magasin, question) {
  const debut = Date.now();
  const requete = {
    model: modele,
    instructions: TOPONYMES_INSTRUCTIONS,
    input: '[IMPORTANT: Réponds UNIQUEMENT en français] ' + question,
    tools: [{ type: 'file_search', vector_store_ids: [magasin], max_num_results: 20 }],
    include: ['file_search_call.results'],
  };
  // Les modèles à raisonnement refusent temperature ; gpt-4.1 l'accepte.
  if (/^gpt-4/.test(modele)) requete.temperature = 0.3;

  try {
    const r = await openai.responses.create(requete);
    const documents = new Set();
    for (const sortie of r.output || []) {
      for (const res of sortie.results || []) if (res.filename) documents.add(res.filename);
    }
    return {
      secondes: (Date.now() - debut) / 1000,
      texte: r.output_text.trim(),
      documents: [...documents],
      jetons: r.usage,
    };
  } catch (erreur) {
    return { erreur: erreur?.message || String(erreur), secondes: (Date.now() - debut) / 1000 };
  }
}

async function main() {
  chargeEnv();
  const args = process.argv.slice(2);
  const magasin = args[0]?.startsWith('vs_') ? args.shift() : process.env.VECTOR_STORE_ID_V2;
  const modeles = (args[0] || 'gpt-4.1,gpt-5.4-mini,gpt-5.4,gpt-5.5').split(',');

  const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
  console.log(`🔎 Magasin ${magasin}\n   Modèles : ${modeles.join(', ')}\n`);

  const bilan = {};
  for (const [etiquette, question] of QUESTIONS) {
    console.log('═'.repeat(78));
    console.log(`❓ [${etiquette}] ${question}\n`);
    for (const modele of modeles) {
      const r = await interroge(openai, modele, magasin, question);
      bilan[modele] ??= { secondes: 0, entree: 0, sortie: 0, echecs: 0 };
      if (r.erreur) {
        bilan[modele].echecs++;
        console.log(`── ${modele}  ❌ ${r.erreur}\n`);
        continue;
      }
      bilan[modele].secondes += r.secondes;
      bilan[modele].entree += r.jetons?.input_tokens || 0;
      bilan[modele].sortie += r.jetons?.output_tokens || 0;
      console.log(`── ${modele}  (${r.secondes.toFixed(1)} s, ` +
                  `${r.jetons?.input_tokens} jetons entrée / ${r.jetons?.output_tokens} sortie)`);
      console.log(r.texte.split('\n').map((l) => '   ' + l).join('\n'));
      console.log(`   📄 ${r.documents.slice(0, 6).join(', ')}${r.documents.length > 6 ? ' …' : ''}\n`);
    }
  }

  console.log('═'.repeat(78));
  console.log('BILAN (somme sur les trois questions)\n');
  console.log('modèle'.padEnd(16) + 'temps'.padStart(9) + 'entrée'.padStart(10) +
              'sortie'.padStart(9) + 'échecs'.padStart(8));
  for (const [m, b] of Object.entries(bilan)) {
    console.log(m.padEnd(16) + `${b.secondes.toFixed(1)} s`.padStart(9) +
                String(b.entree).padStart(10) + String(b.sortie).padStart(9) +
                String(b.echecs).padStart(8));
  }
}

main().catch((e) => { console.error('❌', e?.message || e); process.exit(1); });
