import { readFileSync } from 'node:fs';

const DATASET_FILES = {
  Baudin: new URL('../data/baudin.json', import.meta.url),
  Entrecasteaux: new URL('../data/entrecasteaux.json', import.meta.url),
  Flinders: new URL('../data/flinders.json', import.meta.url),
};

const DATASET_PATHS = {
  Baudin: 'data/baudin.json',
  Entrecasteaux: 'data/entrecasteaux.json',
  Flinders: 'data/flinders.json',
};

const TIMELINE_FILE = new URL('../data/timeline_baudin.json', import.meta.url);
const REMARKABLE_DATES_FILE = new URL('../data/dates_remarquables.json', import.meta.url);
const CITATIONS_FILE = new URL('../data/flinders_citations_fr.json', import.meta.url);
const ATTRIBUTIONS_FILE = new URL('../data/attributions_hakluyt.json', import.meta.url);

// Les tables de route publiées consignent parfois une position sous un libellé
// collectif, qui ne désigne pas la même paire de coques d'un bout à l'autre du
// voyage. « Les corvettes » vaut le Géographe et le Naturaliste jusqu'au départ
// du Naturaliste pour la France, le 18 novembre 1802, puis le Géographe et le
// Casuarina acheté à Port Jackson. La Recherche et l'Espérance, elles, ont
// navigué de conserve d'un bout à l'autre : les tables ne relèvent qu'une
// position pour les deux.
//
// Ces règles reprennent celles que map.html applique au tracé des parcours.
const COLLECTIVE_LABELS = {
  Baudin: {
    'les corvettes': [
      { until: '1802-11-18', navires: ['le Géographe', 'le Naturaliste'] },
      { navires: ['le Géographe', 'le Casuarina'] },
    ],
  },
  Entrecasteaux: {
    'la Recherche': [{ navires: ['la Recherche', "l'Espérance"] }],
  },
};

function collectiveRules(expedition, label) {
  return COLLECTIVE_LABELS[expedition]?.[label];
}

// Un libellé collectif se résout en une ou deux coques. Quand un compagnon tient
// sa propre table le même jour, c'est qu'il était relevé à part : la position
// collective n'est plus que celle du bâtiment amiral.
function resolveVessels(expedition, label, date, namedByDate) {
  const rules = collectiveRules(expedition, label);
  if (!rules) return label ? [label] : [];

  let pair = rules[rules.length - 1].navires;
  for (const rule of rules) {
    if (!rule.until || String(date) < rule.until) {
      pair = rule.navires;
      break;
    }
  }
  const apart = namedByDate.get(String(date));
  const together = pair.filter((vessel) => !apart || !apart.has(vessel));
  return together.length ? together : [pair[0]];
}

function vesselLabel(vessels) {
  return vessels.join(' et ');
}

const ROUTE_FILES = [
  { expedition: 'Baudin', path: 'data/baudin_parcours.geojson' },
  { expedition: 'Entrecasteaux', path: 'data/dentrecasteaux_parcours.geojson' },
  { expedition: 'Flinders', path: 'data/flinders_parcours.geojson' },
];

const JOURNAL_FILES = [
  { source: 'baudin', path: 'data/journal_baudin.json', title: 'Journal de Nicolas Baudin' },
  {
    source: 'baudin_bnf',
    path: 'data/journal_baudin_bnf.json',
    title: 'Journal de Baudin, transcription du manuscrit de la BnF',
  },
  { source: 'breton', path: 'data/journal_breton.json', title: 'Journal de Pierre-Guillaume Gicquel Breton' },
  { source: 'anonyme', path: 'data/journal_anonyme.json', title: 'Journal anonyme du Naturaliste' },
  { source: 'geographe', path: 'data/journal_geographe.json', title: 'Journal tenu à bord du Géographe' },
];

function readJson(url) {
  return JSON.parse(readFileSync(url, 'utf8'));
}

function readDataFile(path) {
  return readJson(new URL(`../${path}`, import.meta.url));
}

export function normalizeText(value) {
  return String(value ?? '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLocaleLowerCase('fr')
    .replace(/[’']/g, ' ')
    .replace(/[^\p{L}\p{N}.-]+/gu, ' ')
    .trim()
    .replace(/\s+/g, ' ');
}

export function normalizeState(value) {
  return String(value ?? '').trim().toLocaleUpperCase('en');
}

const citations = readJson(CITATIONS_FILE);
const attributions = readJson(ATTRIBUTIONS_FILE);

function annotate(record, datasetPath) {
  const citation = citations[record.code];
  const attribution = attributions[record.code];
  return Object.freeze({
    ...record,
    ...(citation ? { citation_fr: citation } : {}),
    ...(attribution ? { attribution: Object.freeze({ ...attribution }) } : {}),
    _provenance: Object.freeze({
      dataset: datasetPath,
      code: record.code,
      ...(citation ? { citation: 'data/flinders_citations_fr.json' } : {}),
      ...(attribution ? { attribution: 'data/attributions_hakluyt.json' } : {}),
    }),
  });
}

export const TOPONYMS = Object.freeze(
  Object.entries(DATASET_FILES).flatMap(([expedition, url]) =>
    readJson(url).map((record) => annotate(record, DATASET_PATHS[expedition])),
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

const EXPEDITION_BY_LETTER = { B: 'Baudin', E: 'Entrecasteaux', F: 'Flinders' };

export const REMARKABLE_DATES = Object.freeze(
  readJson(REMARKABLE_DATES_FILE)
    .map((entry, index) =>
      Object.freeze({
        id: index + 1,
        date: entry.date,
        expedition: EXPEDITION_BY_LETTER[entry.expedition] ?? entry.expedition,
        navire: entry.navire ?? '',
        libelle_fr: entry.libelle?.fr ?? '',
        libelle_en: entry.libelle?.en ?? '',
        _provenance: Object.freeze({ dataset: 'data/dates_remarquables.json', date: entry.date }),
      }),
    )
    .sort((a, b) => a.date.localeCompare(b.date) || a.id - b.id),
);

const ROUTE_FLAG_FIELDS = [
  'extrapole',
  'mouillage',
  'contournement',
  'renfloue',
  'de_conserve',
  'releve_corrige',
  'releve_carte',
];

function routePosition(feature, expedition, datasetPath, index, fallbackVessel, namedByDate) {
  const properties = feature.properties ?? {};
  const [lon, lat] = feature.geometry.coordinates;
  const resolvedExpedition = properties.expedition || expedition;
  const sourceLabel = properties.navire ?? '';
  const recordedLabel = sourceLabel || fallbackVessel;
  const navires = resolveVessels(
    resolvedExpedition,
    recordedLabel,
    properties.date ?? '',
    namedByDate,
  );
  return Object.freeze({
    id: `${expedition}-${index + 1}`,
    expedition: resolvedExpedition,
    navire: vesselLabel(navires),
    navires: Object.freeze(navires),
    navireSource: recordedLabel,
    navireCollectif: Boolean(collectiveRules(resolvedExpedition, recordedLabel)),
    date: properties.date ?? '',
    lat,
    lon,
    section: properties.section ?? '',
    table: properties.table ?? '',
    page: properties.page ?? properties.page_recto ?? '',
    date_republicaine: properties.date_republicaine ?? '',
    remarque: properties.remarque ?? '',
    alerte: properties.alerte ?? '',
    sourceLatitude: properties.source_latitude ?? properties.obs_latitude ?? '',
    sourceLongitude: properties.source_longitude ?? properties.obs_longitude ?? '',
    vents_etat_du_ciel: properties.vents_etat_du_ciel ?? '',
    barometre_hpa: properties.barometre_hpa ?? null,
    thermometre: properties.thermometre ?? '',
    declinaison_dms: properties.declinaison_dms ?? '',
    declinaison_ref: properties.declinaison_ref ?? '',
    flags: Object.freeze(
      Object.fromEntries(ROUTE_FLAG_FIELDS.map((field) => [field, Boolean(properties[field])])),
    ),
    _provenance: Object.freeze({ dataset: datasetPath, featureIndex: index }),
  });
}

const routeTrajectories = [];

export const ROUTE_POSITIONS = Object.freeze(
  ROUTE_FILES.flatMap(({ expedition, path }) => {
    const collection = readDataFile(path);
    const trajectoryVessels = new Set(
      collection.features
        .filter((feature) => feature.geometry?.type === 'LineString')
        .map((feature) => feature.properties?.navire)
        .filter(Boolean),
    );
    const fallbackVessel = trajectoryVessels.size === 1 ? [...trajectoryVessels][0] : '';

    // Les coques nommément relevées chaque jour, libellés collectifs exclus.
    const namedByDate = new Map();
    for (const feature of collection.features) {
      if (feature.geometry?.type !== 'Point') continue;
      const label = String(feature.properties?.navire ?? '').trim();
      const date = String(feature.properties?.date ?? '');
      if (!label || !date || collectiveRules(expedition, label)) continue;
      if (!namedByDate.has(date)) namedByDate.set(date, new Set());
      namedByDate.get(date).add(label);
    }

    const positions = [];
    collection.features.forEach((feature, index) => {
      if (feature.geometry?.type === 'LineString') {
        const trajectoryLabel = feature.properties?.navire ?? '';
        const trajectoryVessels = collectiveRules(expedition, trajectoryLabel)
          ? [...new Set(collectiveRules(expedition, trajectoryLabel).flatMap((rule) => rule.navires))]
          : trajectoryLabel
            ? [trajectoryLabel]
            : [];
        routeTrajectories.push(
          Object.freeze({
            expedition,
            navire: vesselLabel(trajectoryVessels),
            navires: Object.freeze(trajectoryVessels),
            navireSource: trajectoryLabel,
            type: feature.properties?.type ?? 'trajectoire',
            vertexCount: feature.geometry.coordinates.length,
            _provenance: Object.freeze({ dataset: path, featureIndex: index }),
          }),
        );
        return;
      }
      if (feature.geometry?.type !== 'Point') return;
      positions.push(
        routePosition(feature, expedition, path, index, fallbackVessel, namedByDate),
      );
    });
    return positions;
  }).sort(
    (a, b) =>
      a.date.localeCompare(b.date) ||
      a.expedition.localeCompare(b.expedition) ||
      a.navire.localeCompare(b.navire),
  ),
);

export const ROUTE_TRAJECTORIES = Object.freeze(routeTrajectories);

export const JOURNAL_ENTRIES = Object.freeze(
  JOURNAL_FILES.flatMap(({ source, path, title }) => {
    const raw = readDataFile(path);
    return Object.entries(raw)
      .filter(([date]) => /^\d{4}-\d{2}-\d{2}$/.test(date))
      .map(([date, value]) => {
        const payload = Array.isArray(value) ? { texte: value.join('\n\n') } : value;
        const body = typeof payload === 'string' ? { texte: payload } : payload;
        return Object.freeze({
          source,
          sourceTitle: title,
          date,
          texte: String(body.texte ?? ''),
          entete: body.entete ?? '',
          republicain: body.republicain ?? '',
          etat: body.etat ?? '',
          _provenance: Object.freeze({ dataset: path, date }),
        });
      });
  }).sort((a, b) => a.date.localeCompare(b.date) || a.source.localeCompare(b.source)),
);

export const TOPONYM_BY_CODE = new Map(
  TOPONYMS.map((record) => [normalizeText(record.code), record]),
);

const INDEXED_FIELDS = [
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
  'navire',
  'campagne',
  'secteur',
  'categorie',
  'sousCategorie',
  'classe',
  'planche',
  'commentaire',
  'citation_fr',
];

export const SEARCH_INDEX = TOPONYMS.map((record) => ({
  record,
  normalized: Object.fromEntries([
    ...INDEXED_FIELDS.map((field) => [field, normalizeText(record[field])]),
    ['attribution', normalizeText(
      [record.attribution?.sujet, record.attribution?.type, record.attribution?.note]
        .filter(Boolean)
        .join(' '),
    )],
  ]),
}));

export const JOURNAL_INDEX = JOURNAL_ENTRIES.map((entry) => ({
  entry,
  normalized: normalizeText(entry.texte),
}));

export function hasCoordinates(item) {
  return (
    Number.isFinite(item?.lat) &&
    Number.isFinite(item?.lon) &&
    !(item.lat === 0 && item.lon === 0)
  );
}

function bounds(items) {
  const located = items.filter(hasCoordinates);
  if (!located.length) return null;
  const latitudes = located.map((item) => item.lat);
  const longitudes = located.map((item) => item.lon);
  return {
    minLatitude: Math.min(...latitudes),
    maxLatitude: Math.max(...latitudes),
    minLongitude: Math.min(...longitudes),
    maxLongitude: Math.max(...longitudes),
  };
}

const routeDates = ROUTE_POSITIONS.map((position) => position.date).filter(Boolean).sort();
const journalDates = JOURNAL_ENTRIES.map((entry) => entry.date).sort();

export const DATASET_SUMMARY = Object.freeze({
  toponyms: TOPONYMS.length,
  timelineEvents: TIMELINE.length,
  remarkableDates: REMARKABLE_DATES.length,
  routePositions: ROUTE_POSITIONS.length,
  routeTrajectories: ROUTE_TRAJECTORIES.length,
  journalEntries: JOURNAL_ENTRIES.length,
  expeditions: [...new Set(TOPONYMS.map((record) => record.expedition))].sort(),
  states: [...new Set(TOPONYMS.map((record) => normalizeState(record.state)))].sort(),
  vessels: [
    ...new Set(ROUTE_POSITIONS.flatMap((position) => position.navires).filter(Boolean)),
  ].sort(),
  routeVesselLabels: [
    ...new Set(ROUTE_POSITIONS.map((position) => position.navire).filter(Boolean)),
  ].sort(),
  journalSources: JOURNAL_FILES.map(({ source, title, path }) => ({
    source,
    title,
    entries: JOURNAL_ENTRIES.filter((entry) => entry.source === source).length,
    dataset: path,
  })),
  coordinateBounds: bounds(TOPONYMS),
  routeBounds: bounds(ROUTE_POSITIONS),
  routeDateRange: routeDates.length
    ? { from: routeDates[0], to: routeDates[routeDates.length - 1] }
    : null,
  journalDateRange: journalDates.length
    ? { from: journalDates[0], to: journalDates[journalDates.length - 1] }
    : null,
  toponymsWithCitation: TOPONYMS.filter((record) => record.citation_fr).length,
  toponymsWithAttribution: TOPONYMS.filter((record) => record.attribution).length,
  primaryFields: [
    'lat',
    'lon',
    'characteristic_fr',
    'characteristic',
    'history_fr',
    'history',
  ],
  sources: [
    ...Object.values(DATASET_PATHS),
    'data/timeline_baudin.json',
    'data/dates_remarquables.json',
    'data/flinders_citations_fr.json',
    'data/attributions_hakluyt.json',
    ...ROUTE_FILES.map(({ path }) => path),
    ...JOURNAL_FILES.map(({ path }) => path),
  ],
});
