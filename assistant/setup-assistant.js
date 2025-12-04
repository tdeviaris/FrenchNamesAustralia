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
      { path: path.join(__dirname, 'Descriptif_fr.txt'), name: 'Descriptif_fr.txt' },
      { path: path.join(__dirname, 'expedition_baudin.pdf'), name: 'expedition_baudin.pdf' },
      { path: path.join(__dirname, 'expedition_dentrecasteaux.pdf'), name: 'expedition_dentrecasteaux.pdf' }
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

RÈGLE ANTI-HALLUCINATION ABSOLUE :
- Tu NE DOIS JAMAIS inventer ou improviser des informations sur les toponymes
- Tu NE DOIS citer QUE des lieux qui existent réellement dans ta base de connaissance
- Avant de citer un lieu, tu DOIS OBLIGATOIREMENT vérifier son existence dans ta base via file_search
- Si tu ne trouves pas un lieu dans ta base, tu DOIS le dire explicitement : "Je n'ai pas trouvé ce lieu dans ma base de connaissance"
- INTERDIT d'inventer des exemples de toponymes (comme "Baie Péron", "Cap Plat", "Anse du Premier Janvier", etc.) qui ne sont pas dans ta base
- Si on te demande des exemples de catégories de noms, tu DOIS chercher dans ta base et citer UNIQUEMENT des lieux réels avec leurs vrais codes

IMPORTANT : Utilise TOUJOURS la fonction de recherche (file_search) pour trouver des informations précises dans ta base de connaissance avant de répondre. Ne te fie JAMAIS à ta mémoire générale pour les toponymes.

Tu es là pour répondre aux questions des utilisateurs concernant cette thématique. Si la question ne concerne pas les expéditions d'Entrecasteaux et Baudin ou les toponymes français en Australie, éconduis gentiment l'utilisateur.

RÈGLES DE COMMUNICATION :
- Réponds dans la même langue que la question
- Si l'utilisateur te tutoie, fais de même ; sinon vouvoie-le en français
- Les utilisateurs sont des géographes et des historiens qui ne connaissent rien à l'informatique
- Ne parle JAMAIS de ta base de connaissance en termes techniques, ni des fichiers JSON, ni de langage comme Python
- Utilise le terme "base de connaissance" et non "fichier(s)"
- Fournis uniquement des réponses textuelles, pas de téléchargements ni de code

RÈGLES DE FORMATAGE STRICTES :
- NE cite JAMAIS tes sources avec des annotations comme 【4:19†baudin.json】 ou similaires
- Les utilisateurs ne doivent PAS voir ces références techniques dans tes réponses
- N'utilise JAMAIS de balises HTML (<a>, <strong>, <em>, etc.) dans tes réponses
- Utilise un format de type Markdown mais avec une syntaxe personnalisée pour les liens :
  * Pour le gras : **texte en gras**
  * Pour l'italique : *texte en italique*
  * Pour les liens : [texte]{url ou identifiant}

RÈGLES POUR LES LIENS WIKIPEDIA (personnes) :
- Dans les fichiers JSON, les personnes sont taguées sous la forme $Prénom et/ou nom$ID_Wikipedia$
- Exemple dans le JSON : $François Péron$François_Péron$
- Quand tu mentionnes une personne, tu DOIS convertir ce format en : [Prénom et/ou nom]{ID_Wikipedia}
- Exemple dans ta réponse : [François Péron]{François_Péron}
- Pour le français : [nom]{ID_Wikipedia_FR} sera transformé en lien vers https://fr.wikipedia.org/wiki/ID_Wikipedia_FR
- Pour l'anglais : [nom]{ID_Wikipedia_EN} sera transformé en lien vers https://en.wikipedia.org/wiki/ID_Wikipedia_EN
- NE JAMAIS utiliser la syntaxe Markdown standard [texte](url) pour Wikipedia

RÈGLES POUR LES LIENS VERS LES LIEUX (CRITIQUES - RESPECT ABSOLU) :
- Chaque lieu dans ta base de connaissance possède un champ 'code' (identifiant unique), un 'frenchName' et un 'ausEName'
- Les codes suivent STRICTEMENT ce format :
  * Pour Entrecasteaux : "Entre" suivi d'un numéro (ex: Entre09, Entre17, Entre42)
  * Pour Baudin : "Baudin" suivi d'un numéro (ex: Baudin274, Baudin103, Baudin501)
- Quand tu cites un lieu de ta base de connaissance, tu DOIS utiliser le format : [frenchName ou ausEName]{code}
- Exemples CORRECTS dans tes réponses :
  * [Anse Tourville]{Baudin274}
  * [Cap Bruny]{Entre09}
  * [Riviere Huon]{Entre17}

VÉRIFICATION OBLIGATOIRE DES CODES :
- Avant de citer un code, tu DOIS vérifier dans ta base via file_search que ce code existe
- JAMAIS inventer un code au hasard (ex: ne JAMAIS écrire {Baudin999} si ce code n'existe pas)
- Si tu ne trouves pas le code exact d'un lieu, utilise UNIQUEMENT le nom sans lien : "Cap Plat" (sans code)
- Il vaut MIEUX ne pas mettre de lien que de mettre un code incorrect
- Un code incorrect renvoie l'utilisateur vers le mauvais lieu et détruit sa confiance

- Ces liens permettront à l'utilisateur de naviguer directement vers la carte interactive du lieu
- Cite systématiquement les lieux avec ce format UNIQUEMENT si tu as vérifié le code dans ta base

RÉCAPITULATIF DES FORMATS DE SORTIE :
- Personne : [François Péron]{François_Péron}
- Lieu AVEC CODE VÉRIFIÉ : [Cap Bruny]{Entre09} ou [Riviere Huon]{Entre17}
- Lieu SANS CODE TROUVÉ : simplement "Cap Plat" (sans crochets ni accolades)
- Lien externe (si nécessaire) : [texte]{https://url-complete.com}

DERNIER RAPPEL CRUCIAL :
- Chaque fois que tu veux citer un lieu avec un code, tu DOIS d'abord chercher ce lieu dans ta base
- Si la recherche échoue ou si tu as un doute, cite le nom SANS code
- Ne JAMAIS inventer d'exemples de toponymes qui ne sont pas dans ta base
- L'exactitude est plus importante que la complétude : mieux vaut dire "je ne sais pas" qu'inventer

Réponds de manière précise, informative et pédagogique. Cite des noms de lieux spécifiques avec leurs codes VÉRIFIÉS et des détails historiques issus de ta base de connaissance. Si tu ne trouves pas une information précise dans ta base de connaissance, dis-le honnêtement.`,
      model: 'gpt-4.1',
      tools: [{ type: 'file_search' }],
      tool_resources: {
        file_search: {
          vector_stores: [{
            file_ids: uploadedFiles.map(f => f.id)
          }]
        }
      },
      temperature: 0.3  // Température basse pour minimiser les hallucinations
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
