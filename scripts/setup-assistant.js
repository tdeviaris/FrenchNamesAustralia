#!/usr/bin/env node
/**
 * Script de configuration de l'Assistant OpenAI avec RAG
 *
 * Ce script :
 * 1. Upload les fichiers de la base de connaissance vers OpenAI
 * 2. Crée un Vector Store avec ces fichiers
 * 3. Crée un Assistant configuré avec file_search
 * 4. Sauvegarde l'Assistant ID dans un fichier .env
 *
 * Usage: node scripts/setup-assistant.js
 */

import OpenAI from 'openai';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Initialiser le client OpenAI
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
  dangerouslyAllowBrowser: false
});

async function main() {
  console.log('🚀 Début de la configuration de l\'Assistant Toponymes...\n');

  try {
    // Vérifier que la clé API existe
    if (!process.env.OPENAI_API_KEY) {
      throw new Error('❌ OPENAI_API_KEY n\'est pas définie dans les variables d\'environnement');
    }

    // 1. Upload des fichiers
    console.log('📤 Upload des fichiers de la base de connaissance...');

    const filesToUpload = [
      { path: path.join(__dirname, '../data/baudin.json'), name: 'baudin.json' },
      { path: path.join(__dirname, '../data/entrecasteaux.json'), name: 'entrecasteaux.json' },
      { path: path.join(__dirname, '../Descriptif_fr.txt'), name: 'Descriptif_fr.txt' }
    ];

    const uploadedFiles = [];

    for (const fileInfo of filesToUpload) {
      console.log(`  ⬆️  Uploading ${fileInfo.name}...`);

      const file = await openai.files.create({
        file: fs.createReadStream(fileInfo.path),
        purpose: 'assistants'
      });

      uploadedFiles.push(file);
      console.log(`  ✅ ${fileInfo.name} uploadé (ID: ${file.id})`);
    }

    console.log(`\n✅ ${uploadedFiles.length} fichiers uploadés avec succès\n`);

    // 2. Créer l'Assistant avec les fichiers
    console.log('🤖 Création de l\'Assistant...');

    const assistant = await openai.beta.assistants.create({
      name: 'Expert Toponymes',
      instructions: `Tu es un expert des expéditions d'Entrecasteaux (1791-1794) et Baudin (1800-1804).

Dans ta base de connaissance figurent une multitude de données sur les lieux auxquels ont été attribués des toponymes français donnés à l'occasion de ces deux expéditions napoléoniennes. Elle contient 670 toponymes documentés dans les atlas officiels : 68 pour l'expédition d'Entrecasteaux et 602 pour l'expédition Baudin.

Les données sont structurées par lieu, avec :
- Les coordonnées GPS
- Les noms français donnés lors des expéditions
- Les noms actuels utilisés en anglais
- De nombreuses informations historiques dans les rubriques Caractéristiques et Histoire, en français et en anglais

NB : Les versions françaises et anglaises ne sont pas de simples traductions, les informations diffèrent légèrement.

Au sein de ces informations, figurent des identifiants Wikipedia concernant les personnes nommées. Elles sont taguées sous la forme $Prénom et/ou nom$ID Wikipedia$.
- Dans la version française, pour consulter la fiche Wikipédia, le lien à utiliser est https://fr.wikipedia.org/wiki/'ID WIKI FR'
- En anglais : https://en.wikipedia.org/wiki/'ID WIKI EN'

IMPORTANT : Utilise TOUJOURS la fonction de recherche (file_search) pour trouver des informations précises dans ta base de connaissance avant de répondre. Ne te fie pas uniquement à ta mémoire générale.

Tu es là pour répondre aux questions des utilisateurs concernant cette thématique. Si la question ne concerne pas les expéditions d'Entrecasteaux et Baudin ou les toponymes français en Australie, éconduis gentiment l'utilisateur.

RÈGLES DE COMMUNICATION :
- Réponds dans la même langue que la question
- Si l'utilisateur te tutoie, fais de même ; sinon vouvoie-le en français
- Les utilisateurs sont des géographes et des historiens qui ne connaissent rien à l'informatique
- Ne parle JAMAIS de ta base de connaissance en termes techniques, ni des fichiers JSON, ni de langage comme Python
- Utilise le terme "base de connaissance" et non "fichier(s)"
- Fournis uniquement des réponses textuelles, pas de téléchargements ni de code

RÈGLES DE FORMATAGE :
- NE cite JAMAIS tes sources avec des annotations comme 【4:19†baudin.json】 ou similaires
- Les utilisateurs ne doivent PAS voir ces références techniques dans tes réponses
- Quand tu mentionnes une personne avec un lien Wikipedia, formate-le comme un lien Markdown cliquable
- Exemple : [François Péron](https://fr.wikipedia.org/wiki/François_Péron) au lieu de https://fr.wikipedia.org/wiki/Fran%C3%A7ois_P%C3%A9ron
- Utilise toujours des URLs décodées et lisibles dans le texte du lien

Réponds de manière précise, informative et pédagogique. Cite des noms de lieux spécifiques et des détails historiques issus de ta base de connaissance quand c'est pertinent. Si tu ne trouves pas une information précise dans ta base de connaissance, dis-le honnêtement.`,
      model: 'gpt-4o',
      tools: [{ type: 'file_search' }],
      tool_resources: {
        file_search: {
          vector_stores: [{
            file_ids: uploadedFiles.map(f => f.id)
          }]
        }
      },
      temperature: 0.7
    });

    console.log(`✅ Assistant créé (ID: ${assistant.id})\n`);

    // 4. Sauvegarder l'Assistant ID
    console.log('💾 Sauvegarde de la configuration...');

    const envPath = path.join(__dirname, '../.env');
    let envContent = '';

    // Lire le fichier .env existant s'il existe
    if (fs.existsSync(envPath)) {
      envContent = fs.readFileSync(envPath, 'utf-8');
    }

    // Ajouter ou mettre à jour ASSISTANT_ID
    if (envContent.includes('ASSISTANT_ID=')) {
      envContent = envContent.replace(/ASSISTANT_ID=.*/g, `ASSISTANT_ID=${assistant.id}`);
    } else {
      envContent += `\nASSISTANT_ID=${assistant.id}\n`;
    }

    fs.writeFileSync(envPath, envContent);
    console.log(`✅ Configuration sauvegardée dans .env\n`);

    // Afficher le résumé
    console.log('════════════════════════════════════════════════════════');
    console.log('✅ Configuration terminée avec succès !');
    console.log('════════════════════════════════════════════════════════');
    console.log(`\n📋 Résumé :`);
    console.log(`  • Fichiers uploadés : ${uploadedFiles.length}`);
    console.log(`  • Assistant ID : ${assistant.id}`);
    console.log(`\n🔑 L'Assistant ID a été sauvegardé dans .env`);
    console.log(`\n⚠️  N'oubliez pas de déployer sur Vercel pour que les changements soient pris en compte :`);
    console.log(`   vercel --prod\n`);

  } catch (error) {
    console.error('\n❌ Erreur lors de la configuration :', error.message);
    process.exit(1);
  }
}

main();
