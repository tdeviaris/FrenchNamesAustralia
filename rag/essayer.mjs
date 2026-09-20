#!/usr/bin/env node
/**
 * Pose quelques questions au chatbot sur un magasin donné, sans passer par
 * Vercel — de quoi juger un nouvel index avant de basculer la production.
 *
 * Les questions sont choisies pour ne trouver leur réponse que dans ce qui
 * vient d'être ajouté : une journée de journal sans coordonnées, un journal de
 * Sydney, la transcription de Hamelin, le glossaire du site.
 *
 * Usage :
 *   node rag/essayer.mjs                      # sur VECTOR_STORE_ID_V2
 *   node rag/essayer.mjs vs_xxxxxxxx          # sur un magasin nommé
 *   node rag/essayer.mjs vs_xxx "ma question" # une question à soi
 */

import OpenAI from 'openai';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { TOPONYMES_INSTRUCTIONS } from '../responses/instructions.js';

const RACINE = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

const QUESTIONS = [
  "Que raconte le journal de Flinders le 31 juillet 1801 ? Il n'a pas relevé de position ce jour-là.",
  "Que dit Ronsard de la rade de Sainte-Croix de Ténériffe ?",
  "Que sait-on du journal du capitaine Hamelin ? Jusqu'où va sa transcription ?",
  "Qu'est-ce que le Dépôt des cartes et plans de la Marine ?",
  "Pourquoi la baie Paterson porte-t-elle ce nom ?",
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

async function main() {
  chargeEnv();
  const args = process.argv.slice(2);
  const magasin = args[0]?.startsWith('vs_') ? args.shift() : process.env.VECTOR_STORE_ID_V2;
  const questions = args.length ? args : QUESTIONS;

  if (!magasin) {
    console.error('❌ Aucun magasin : ni argument vs_…, ni VECTOR_STORE_ID_V2 dans .env.');
    process.exit(1);
  }

  const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
  console.log(`🔎 Magasin ${magasin}\n`);

  for (const question of questions) {
    console.log('─'.repeat(76));
    console.log(`❓ ${question}\n`);
    const réponse = await openai.responses.create({
      model: 'gpt-4.1',
      instructions: TOPONYMES_INSTRUCTIONS,
      input: '[IMPORTANT: Réponds UNIQUEMENT en français] ' + question,
      temperature: 0.3,
      tools: [{ type: 'file_search', vector_store_ids: [magasin], max_num_results: 20 }],
      include: ['file_search_call.results'],
    });

    console.log(réponse.output_text.trim());

    const citées = new Set();
    for (const sortie of réponse.output || []) {
      for (const r of sortie.results || []) if (r.filename) citées.add(r.filename);
    }
    if (citées.size) console.log(`\n📄 documents consultés : ${[...citées].join(', ')}`);
    console.log();
  }
}

main().catch((e) => { console.error('❌', e?.message || e); process.exit(1); });
