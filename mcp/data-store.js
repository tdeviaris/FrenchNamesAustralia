import { readFileSync } from 'node:fs';

const DATASET_FILES = {
  Baudin: new URL('../data/baudin.json', import.meta.url),
  Entrecasteaux: new URL('../data/entrecasteaux.json', import.meta.url),
};

const TIMELINE_FILE = new URL('../data/timeline_baudin.json', import.meta.url);

function readJson(url) {
  return JSON.parse(readFileSync(url, 'utf8'));
}

export function normalizeText(value) {
  return String(value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('fr')
    .replace(/[’']/g, ' ')
    .replace(/[^\p{L}\p{N}.-]+/gu, ' ')
    .trim()
    .replace(/\s+/g, ' ');
}

const baudin = readJson(DATASET_FILES.Baudin);
const entrecasteaux = readJson(DATASET_FILES.Entrecasteaux);

export const TOPONYMS = Object.freeze(
  [...baudin, ...entrecasteaux].map((record) =>
    Object.freeze({
      ...record,
      _provenance: Object.freeze({
        dataset:
          record.expedition === 'Entrecasteaux'
            ? 'data/entrecasteaux.json'
            : 'data/baudin.json',
        code: record.code,
      }),
    }),
  ),
);

export const TIMELINE = Object.freeze(
  readJson(TIMELINE_FILE).map((event) =>
    Object.freeze({
      ...event,
      _provenance: Object.freeze({
        dataset: 'data/timeline_baudin.json',
        id: event.id,
      }),
    }),
  ),
);

export const TOPONYM_BY_CODE = new Map(
  TOPONYMS.map((record) => [normalizeText(record.code), record]),
);

export const SEARCH_INDEX = TOPONYMS.map((record) => ({
  record,
  normalized: Object.fromEntries(
    [
      'code',
      'frenchName',
      'variantName',
      'ausEName',
      'indigenousName',
      'indigenousLanguage',
      'characteristic_fr',
      'characteristic',
      'history_fr',
      'history',
      'state',
      'expedition',
    ].map((field) => [field, normalizeText(record[field])]),
  ),
}));

export const DATASET_SUMMARY = Object.freeze({
  toponyms: TOPONYMS.length,
  timelineEvents: TIMELINE.length,
  expeditions: [...new Set(TOPONYMS.map((record) => record.expedition))].sort(),
  states: [...new Set(TOPONYMS.map((record) => record.state))].sort(),
  coordinateBounds: {
    minLatitude: Math.min(...TOPONYMS.map((record) => record.lat)),
    maxLatitude: Math.max(...TOPONYMS.map((record) => record.lat)),
    minLongitude: Math.min(...TOPONYMS.map((record) => record.lon)),
    maxLongitude: Math.max(...TOPONYMS.map((record) => record.lon)),
  },
  primaryFields: [
    'lat',
    'lon',
    'characteristic_fr',
    'characteristic',
    'history_fr',
    'history',
  ],
  sources: ['data/baudin.json', 'data/entrecasteaux.json', 'data/timeline_baudin.json'],
});
