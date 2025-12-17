#!/usr/bin/env node
/**
 * Script de configuration "Responses API" (file_search via Vector Store).
 *
 * Ce script :
 * 1) Upload les fichiers de la base de connaissance
 * 2) Crée un Vector Store
 * 3) Ajoute les fichiers au Vector Store et attend la fin de l'indexation
 * 4) Sauvegarde VECTOR_STORE_ID dans .env
 *
 * Usage: node responses/setup-vector-store.js
 */

import OpenAI from 'openai';
import fs from 'fs';
import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function main() {
  console.log('🚀 Setup Vector Store (Responses API / file_search)\n');

  if (!process.env.OPENAI_API_KEY) {
    console.error("❌ OPENAI_API_KEY n'est pas définie dans les variables d'environnement");
    process.exit(1);
  }

  const openai = new OpenAI({
    apiKey: process.env.OPENAI_API_KEY,
    dangerouslyAllowBrowser: false,
  });

  const filesToUpload = [
    { path: path.join(__dirname, '../data/baudin.json'), name: 'baudin.json' },
    { path: path.join(__dirname, '../data/entrecasteaux.json'), name: 'entrecasteaux.json' },
    { path: path.join(__dirname, '../assistant/Descriptif_fr.txt'), name: 'Descriptif_fr.txt' },
    { path: path.join(__dirname, '../assistant/Findings.txt'), name: 'Findings.txt' },
    { path: path.join(__dirname, '../assistant/expedition_baudin.pdf'), name: 'expedition_baudin.pdf' },
    { path: path.join(__dirname, '../assistant/expedition_dentrecasteaux.pdf'), name: 'expedition_dentrecasteaux.pdf' },
  ];

  console.log('📤 Upload des fichiers...');
  const uploadedFileIds = [];

  for (const fileInfo of filesToUpload) {
    console.log(`  ⬆️  Uploading ${fileInfo.name}...`);
    const file = await openai.files.create({
      file: fs.createReadStream(fileInfo.path),
      purpose: 'assistants',
    });
    uploadedFileIds.push(file.id);
    console.log(`  ✅ ${fileInfo.name} uploadé (ID: ${file.id})`);
  }

  console.log('\n🧠 Création du Vector Store...');
  const vectorStore = await openai.vectorStores.create({
    name: 'Expert Toponymes (Responses API)',
  });
  console.log(`  ✅ Vector Store créé (ID: ${vectorStore.id})`);

  console.log('\n📚 Indexation (file batch) — attente de traitement...');
  const batch = await openai.vectorStores.fileBatches.createAndPoll(vectorStore.id, {
    file_ids: uploadedFileIds,
  });

  if (batch.file_counts?.failed_count > 0) {
    console.error(`\n❌ Certains fichiers n'ont pas pu être indexés (failed_count=${batch.file_counts.failed_count}).`);
    console.error('   Vérifie le dashboard OpenAI (Vector Stores) pour les détails.');
    process.exit(1);
  }

  console.log('  ✅ Indexation terminée');

  console.log('\n💾 Sauvegarde de VECTOR_STORE_ID dans .env...');
  const envPath = path.join(__dirname, '../.env');
  let envContent = '';

  if (fs.existsSync(envPath)) {
    envContent = fs.readFileSync(envPath, 'utf-8');
  }

  if (envContent.includes('VECTOR_STORE_ID=')) {
    envContent = envContent.replace(/VECTOR_STORE_ID=.*/g, `VECTOR_STORE_ID=${vectorStore.id}`);
  } else {
    envContent += `\nVECTOR_STORE_ID=${vectorStore.id}\n`;
  }

  fs.writeFileSync(envPath, envContent);
  console.log('  ✅ .env mis à jour');

  console.log('\n════════════════════════════════════════════════════════');
  console.log('✅ Setup terminé');
  console.log('════════════════════════════════════════════════════════');
  console.log(`• VECTOR_STORE_ID=${vectorStore.id}`);
  console.log('\n⚠️  Pense aussi à définir VECTOR_STORE_ID sur Vercel (Environment Variables), puis redeployer.');
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((err) => {
    console.error('\n❌ Erreur:', err?.message || err);
    process.exit(1);
  });
}
