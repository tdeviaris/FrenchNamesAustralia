#!/usr/bin/env node
/**
 * Mesure le temps jusqu'au premier jeton — ce que le visiteur ressent.
 *
 * Le chatbot diffuse sa réponse au fil de l'eau (api/responses-chat.js). Ce qui
 * compte pour lui n'est donc pas la durée totale mais le silence initial :
 * combien de temps la page reste vide avant que le texte ne commence.
 *
 * Trois choses pèsent sur ce silence :
 *   — la recherche dans le magasin ;
 *   — le préchargement des extraits retrouvés (max_num_results) ;
 *   — pour les modèles à raisonnement, la réflexion qui précède l'émission.
 *
 * Le banc croise donc modèles, nombre d'extraits et effort de raisonnement.
 *
 * Usage : node rag/mesurer_latence.mjs [vs_xxx]
 */

import OpenAI from 'openai';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { TOPONYMES_INSTRUCTIONS } from '../responses/instructions.js';

const RACINE = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

const QUESTIONS = [
  "Que raconte le journal de Flinders le 31 juillet 1801 ?",
  "Pourquoi la baie Paterson porte-t-elle ce nom ?",
];

// Le TTFT varie d'un appel à l'autre — file d'attente du modèle, réseau. Deux
// mesures ne disent rien ; on répète et on retient la médiane, que quelques
// appels lents ne déplacent pas.
const REPETITIONS = Number(process.env.REPETITIONS || 4);

function mediane(valeurs) {
  const t = [...valeurs].sort((a, b) => a - b);
  const m = Math.floor(t.length / 2);
  return t.length % 2 ? t[m] : (t[m - 1] + t[m]) / 2;
}

// modèle, effort de raisonnement (null = modèle sans raisonnement)
const MODELES = [
  ['gpt-4.1', null],
  ['gpt-5.4-mini', 'low'],
  ['gpt-5.6-terra', 'low'],
  ['gpt-5.6-terra', 'medium'],
];

const EXTRAITS = [10, 15, 20];

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

async function chronometre(openai, modele, effort, extraits, magasin, question) {
  const requete = {
    model: modele,
    instructions: TOPONYMES_INSTRUCTIONS,
    input: '[IMPORTANT: Réponds UNIQUEMENT en français] ' + question,
    tools: [{ type: 'file_search', vector_store_ids: [magasin], max_num_results: extraits }],
  };
  if (effort) requete.reasoning = { effort };
  else requete.temperature = 0.3;

  const debut = Date.now();
  let premier = null;
  let entree = 0, sortie = 0;

  try {
    const flux = openai.responses.stream(requete);
    flux.on('response.output_text.delta', () => {
      premier ??= Date.now() - debut;
    });
    const fin = await flux.finalResponse();
    entree = fin.usage?.input_tokens || 0;
    sortie = fin.usage?.output_tokens || 0;
    return { ttft: premier, total: Date.now() - debut, entree, sortie };
  } catch (erreur) {
    return { erreur: erreur?.message || String(erreur) };
  }
}

async function main() {
  chargeEnv();
  const magasin = process.argv[2]?.startsWith('vs_') ? process.argv[2] : process.env.VECTOR_STORE_ID_V2;
  const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

  console.log(`⏱  Temps jusqu'au premier jeton — magasin ${magasin}`);
  console.log(`   ${QUESTIONS.length} questions × ${REPETITIONS} répétitions par réglage, médiane affichée\n`);
  console.log('modèle'.padEnd(16) + 'effort'.padEnd(9) + 'extraits'.padStart(9) +
              'TTFT méd.'.padStart(9) + 'min-max'.padStart(11) +
              'total'.padStart(9) + 'entrée'.padStart(9));
  console.log('─'.repeat(72));

  for (const [modele, effort] of MODELES) {
    for (const extraits of EXTRAITS) {
      const mesures = [];
      const tirages = [];
      for (let i = 0; i < REPETITIONS; i++) for (const q of QUESTIONS) tirages.push(q);
      for (const question of tirages) {
        const r = await chronometre(openai, modele, effort, extraits, magasin, question);
        if (r.erreur) {
          console.log(`${modele.padEnd(16)}${(effort || '—').padEnd(9)}${String(extraits).padStart(9)}` +
                      `   ❌ ${r.erreur.slice(0, 60)}`);
          mesures.length = 0;
          break;
        }
        mesures.push(r);
      }
      if (!mesures.length) continue;
      const med = (cle) => mediane(mesures.map((m) => m[cle] ?? 0));
      const ttft = mesures.map((m) => m.ttft);
      console.log(modele.padEnd(16) + (effort || '—').padEnd(9) + String(extraits).padStart(9) +
                  `${(med('ttft') / 1000).toFixed(1)}s`.padStart(9) +
                  `${(Math.min(...ttft) / 1000).toFixed(1)}-${(Math.max(...ttft) / 1000).toFixed(1)}`.padStart(11) +
                  `${(med('total') / 1000).toFixed(1)}s`.padStart(9) +
                  Math.round(med('entree')).toString().padStart(9));
    }
  }
}

main().catch((e) => { console.error('❌', e?.message || e); process.exit(1); });
