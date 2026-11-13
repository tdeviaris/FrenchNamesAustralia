import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const readJson = async (path) => JSON.parse(await readFile(path, 'utf8'));

test('popup italics match the current Baudin and d\'Entrecasteaux narratives', async () => {
  const [metadata, baudin, entrecasteaux] = await Promise.all([
    readJson('data/popup_italics.json'),
    readJson('data/baudin.json'),
    readJson('data/entrecasteaux.json'),
  ]);
  const placesByCode = new Map(
    [...baudin, ...entrecasteaux].map((place) => [place.code, place]),
  );

  for (const [code, fields] of Object.entries(metadata)) {
    if (code === '_meta') continue;
    const place = placesByCode.get(code);
    assert.ok(place, `Unknown popup italics code: ${code}`);

    for (const [field, terms] of Object.entries(fields)) {
      assert.ok(
        ['characteristic_fr', 'characteristic', 'history_fr', 'history'].includes(field),
        `Unsupported popup italics field: ${code}.${field}`,
      );
      assert.ok(Array.isArray(terms) && terms.length > 0, `Empty italics list: ${code}.${field}`);
      for (const term of terms) {
        assert.ok(
          String(place[field] || '').includes(term),
          `Italic text is absent from ${code}.${field}: ${term}`,
        );
      }
    }
  }

  assert.ok(
    metadata.Baudin065.characteristic_fr.includes('La Princesse de Clèves'),
    'The literary-title regression example must remain covered',
  );
});
