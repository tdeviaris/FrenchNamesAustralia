import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../commun/carte/carte.js', import.meta.url), 'utf8');
const functionSource = source.match(
  /const vignetteWikimedia = \(url, largeur\) => \{[\s\S]*?\n        \};/,
)?.[0];

if (!functionSource) throw new Error('Fonction vignetteWikimedia introuvable');

const context = {};
vm.runInNewContext(`${functionSource}\nthis.vignetteWikimedia = vignetteWikimedia;`, context);
const supportsCommonsPages = source.includes('Special:Redirect/file');

test('a Commons File page becomes a directly usable resized image URL', {
  skip: !supportsCommonsPages,
}, () => {
  const actual = context.vignetteWikimedia(
    'https://commons.wikimedia.org/wiki/File:Caroline_Murat_by_Vigee-Lebrun.jpg?utm_source=commons.wikimedia.org',
    330,
  );
  assert.equal(
    actual,
    'https://commons.wikimedia.org/wiki/Special:Redirect/file/Caroline_Murat_by_Vigee-Lebrun.jpg?width=330',
  );
});

test('an upload.wikimedia original still becomes a thumbnail URL', {
  skip: !supportsCommonsPages,
}, () => {
  const actual = context.vignetteWikimedia(
    'https://upload.wikimedia.org/wikipedia/commons/0/0c/Caroline_Murat_by_Vigee-Lebrun.jpg?utm_source=commons.wikimedia.org',
    1280,
  );
  assert.equal(
    actual,
    'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0c/Caroline_Murat_by_Vigee-Lebrun.jpg/1280px-Caroline_Murat_by_Vigee-Lebrun.jpg',
  );
});
