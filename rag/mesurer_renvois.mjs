#!/usr/bin/env node
/**
 * Compte les renvois vers les journées de journal que le modèle produit.
 *
 * Le renvoi n'est utile que s'il est constant : une réponse qui cite six
 * journées et n'en lie que deux laisse le lecteur devant quatre impasses
 * apparentes. On mesure donc, sur des questions qui appellent plusieurs
 * journées datées, combien de dates citées portent effectivement un renvoi.
 *
 * Usage : node rag/mesurer_renvois.mjs [tirages]
 */

import OpenAI from 'openai';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { TOPONYMES_INSTRUCTIONS } from '../responses/instructions.js';

const RACINE = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

const QUESTIONS = [
  "ou est il mention du poussepied",
  "Que raconte le journal de Breton en février 1802 ?",
  "Quelles journées de journal parlent de la pêche aux îles Furneaux ?",
];

// Les mois en toutes lettres, pour repérer les dates dans une réponse française.
const MOIS = ('janvier|février|mars|avril|mai|juin|juillet|août|septembre'
              + '|octobre|novembre|décembre');
const DATE_EN_TOUTES_LETTRES = new RegExp(`\\b\\d{1,2}(?:er)?\\s+(?:${MOIS})\\s+180\\d\\b`, 'gi');

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
  const tirages = Number(process.argv[2] || 2);
  const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
  const magasin = process.env.VECTOR_STORE_ID_V2;
  const reperes = JSON.parse(
    fs.readFileSync(path.join(RACINE, 'data', 'journaux_reperes.json'), 'utf-8'));

  const existe = (valeur) => {
    const m = valeur.match(/^(\d{4}-\d{2}-\d{2})\s*@\s*(.+)$/);
    if (!m) return false;
    return (reperes[m[1]] || []).some((c) => c.toLowerCase() === m[2].trim().toLowerCase());
  };

  console.log(`🔗 Renvois vers les journées — ${tirages} tirage(s) par question\n`);
  let datesTotal = 0, renvoisTotal = 0, valides = 0;

  for (const question of QUESTIONS) {
    console.log(`« ${question} »`);
    for (let i = 0; i < tirages; i++) {
      const r = await openai.responses.create({
        model: 'gpt-5.6-terra',
        instructions: TOPONYMES_INSTRUCTIONS,
        // Le prefixe que pose api/responses-chat.js en production.
        input: '[IMPORTANT: Réponds UNIQUEMENT en français] ' + question,
        reasoning: { effort: 'low' },
        tools: [{ type: 'file_search', vector_store_ids: [magasin], max_num_results: 20 }],
      });
      const texte = r.output_text;
      const renvois = [...texte.matchAll(/\{journal:([^}]+)\}/g)].map((m) => m[1]);
      // Les dates deja liees ne doivent pas etre comptees deux fois.
      const horsRenvois = texte.replace(/\[[^\]]*\]\{journal:[^}]+\}/g, '');
      const dates = horsRenvois.match(DATE_EN_TOUTES_LETTRES) || [];
      const bons = renvois.filter(existe).length;
      datesTotal += dates.length + renvois.length;
      renvoisTotal += renvois.length;
      valides += bons;
      console.log(`   tirage ${i + 1} : ${renvois.length} renvoi(s) dont ${bons} valide(s), `
                  + `${dates.length} date(s) citée(s) sans renvoi`);
    }
  }

  console.log('\n────────────────────────────────────────');
  console.log(`dates datées rencontrées : ${datesTotal}`);
  console.log(`dont porteuses d'un renvoi : ${renvoisTotal}`
              + ` (${datesTotal ? Math.round(100 * renvoisTotal / datesTotal) : 0} %)`);
  console.log(`renvois pointant sur un relevé réel : ${valides}/${renvoisTotal}`);
}

main().catch((e) => { console.error('❌', e?.message || e); process.exit(1); });
