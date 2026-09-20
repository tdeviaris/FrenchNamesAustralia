#!/usr/bin/env node
/**
 * Départage deux modèles sur ce qui casse vraiment, plutôt que sur l'allure.
 *
 * Deux choses se vérifient à la machine :
 *
 *   — les liens. Le site transforme [texte]{place:X} et [texte]{person:Y} en
 *     liens réels. Si X n'est pas un nom de la base ou Y un identifiant
 *     Wikipédia effectivement balisé dans les données, le visiteur clique dans
 *     le vide. On confronte donc chaque cible à l'index des toponymes et aux
 *     balises $Nom$ID$ des fiches.
 *   — la syntaxe. Aucune balise HTML, aucun lien Markdown standard : les
 *     instructions l'interdisent, et le front ne les rend pas.
 *
 * Le reste — l'honnêteté sur les sources, la façon de traiter des témoins qui
 * se contredisent — se lit. Le script imprime les réponses en regard.
 *
 * Usage : node rag/departager.mjs [vs_xxx] [modeleA] [modeleB]
 */

import OpenAI from 'openai';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { TOPONYMES_INSTRUCTIONS } from '../responses/instructions.js';

const RACINE = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

// Chaque question vise un travers précis.
const EPREUVES = [
  ['attribution',
   "Que dit le journal de Hamelin de l'escale de Port Jackson en juin 1802 ?",
   "la transcription s'arrête en août 1801 : le modèle doit le dire, et ne pas prendre l'étude de Dany Bréelle pour le journal"],
  ['témoins en désaccord',
   "Le Naturaliste fait demi-tour vers Port Jackson en juin 1802. Les témoins s'accordent-ils sur qui a pris la décision ?",
   "Hamelin la présente comme sienne, Heirisson décrit une délibération : le modèle doit rapporter les deux"],
  ['liens',
   "Pourquoi la baie Paterson porte-t-elle ce nom ? Cite les personnes impliquées.",
   "les cibles {place:} et {person:} doivent exister dans la base"],
  ['toponyme inexistant',
   "Parle-moi de la baie de l'Espérance Perdue, nommée par Baudin en 1802.",
   "ce lieu n'existe pas : le modèle doit le dire au lieu de broder"],
  ['journée sans position',
   "Que raconte le journal de Flinders le 31 juillet 1801 ?",
   "journée sans coordonnées, présente seulement dans le texte des journaux"],
  ['en anglais',
   "Which French place names along the South Australian coast honour naturalists of the expedition?",
   "doit répondre en anglais et ne citer que des lieux réels"],
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

/** L'index des cibles légitimes, tel que le backend le résoudra. */
function indexDuSite() {
  const lieux = new Set();
  const personnes = new Set();
  for (const fichier of ['baudin.json', 'entrecasteaux.json', 'flinders.json']) {
    const données = JSON.parse(fs.readFileSync(path.join(RACINE, 'data', fichier), 'utf-8'));
    for (const rec of données) {
      for (const cle of ['frenchName', 'ausEName', 'variantName', 'code']) {
        if (rec[cle]) lieux.add(String(rec[cle]).trim().toLowerCase());
      }
      // Les personnes sont balisées $Nom affiché$ID_Wikipedia$ dans les textes.
      for (const valeur of Object.values(rec)) {
        if (typeof valeur !== 'string') continue;
        for (const m of valeur.matchAll(/\$([^$]{1,60})\$([^$]{1,60})\$/g)) {
          personnes.add(m[2].trim());
        }
      }
    }
  }
  return { lieux, personnes };
}

function controle(texte, index) {
  const griefs = [];
  for (const m of texte.matchAll(/\[[^\]]*\]\{place:([^}]+)\}/g)) {
    if (!index.lieux.has(m[1].trim().toLowerCase())) griefs.push(`lieu inconnu : {place:${m[1]}}`);
  }
  for (const m of texte.matchAll(/\[[^\]]*\]\{person:([^}]+)\}/g)) {
    if (!index.personnes.has(m[1].trim())) griefs.push(`personne non balisée : {person:${m[1]}}`);
  }
  for (const m of texte.matchAll(/\[[^\]]+\]\((https?:[^)]+)\)/g)) {
    griefs.push(`lien Markdown standard : ${m[1].slice(0, 40)}`);
  }
  if (/<(a|strong|em|br|p|div)\b/i.test(texte)) griefs.push('balise HTML');
  return griefs;
}

async function interroge(openai, modele, magasin, question) {
  const debut = Date.now();
  let premier = null;
  // On accumule les deltas nous-mêmes : sur un flux, output_text peut revenir
  // vide selon la façon dont la réponse s'est terminée.
  let accumule = '';
  const flux = openai.responses.stream({
    model: modele,
    instructions: TOPONYMES_INSTRUCTIONS,
    input: question,
    reasoning: { effort: 'low' },
    tools: [{ type: 'file_search', vector_store_ids: [magasin], max_num_results: 20 }],
  });
  flux.on('response.output_text.delta', (e) => {
    premier ??= Date.now() - debut;
    accumule += e?.delta || '';
  });
  const fin = await flux.finalResponse();
  const texte = (fin?.output_text || accumule || '').trim();
  return { texte, ttft: premier ?? (Date.now() - debut), total: Date.now() - debut };
}

async function main() {
  chargeEnv();
  const args = process.argv.slice(2);
  const magasin = args[0]?.startsWith('vs_') ? args.shift() : process.env.VECTOR_STORE_ID_V2;
  const modeles = args.length ? args : ['gpt-5.4-mini', 'gpt-5.6-terra'];

  const index = indexDuSite();
  console.log(`⚖️  ${modeles.join('  contre  ')}   (effort low, 20 extraits)`);
  console.log(`   index de contrôle : ${index.lieux.size} noms de lieux, ${index.personnes.size} personnes balisées\n`);

  const bilan = Object.fromEntries(modeles.map((m) => [m, { griefs: 0, ttft: [], total: [] }]));

  const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
  for (const [etiquette, question, attendu] of EPREUVES) {
    console.log('═'.repeat(78));
    console.log(`🎯 ${etiquette.toUpperCase()} — ${question}`);
    console.log(`   attendu : ${attendu}\n`);
    for (const modele of modeles) {
      const r = await interroge(openai, modele, magasin, question);
      const griefs = controle(r.texte, index);
      bilan[modele].griefs += griefs.length;
      bilan[modele].ttft.push(r.ttft);
      bilan[modele].total.push(r.total);
      console.log(`── ${modele}  (premier jeton ${(r.ttft / 1000).toFixed(1)} s, total ${(r.total / 1000).toFixed(1)} s)`);
      console.log(r.texte.split('\n').map((l) => '   ' + l).join('\n'));
      console.log(griefs.length ? `   ⚠️  ${griefs.join(' | ')}\n` : '   ✅ liens et syntaxe conformes\n');
    }
  }

  console.log('═'.repeat(78));
  console.log('BILAN\n');
  for (const [m, b] of Object.entries(bilan)) {
    const med = (t) => [...t].sort((a, c) => a - c)[Math.floor(t.length / 2)] / 1000;
    console.log(`${m.padEnd(16)} liens fautifs : ${String(b.griefs).padStart(2)}   ` +
                `premier jeton méd. ${med(b.ttft).toFixed(1)} s   total méd. ${med(b.total).toFixed(1)} s`);
  }
}

main().catch((e) => { console.error('❌', e?.message || e); process.exit(1); });
