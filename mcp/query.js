import {
  DATASET_SUMMARY,
  hasCoordinates,
  JOURNAL_ENTRIES,
  JOURNAL_INDEX,
  normalizeState,
  normalizeText,
  REMARKABLE_DATES,
  ROUTE_POSITIONS,
  ROUTE_TRAJECTORIES,
  SEARCH_INDEX,
  TIMELINE,
  TOPONYM_BY_CODE,
  TOPONYMS,
} from './data-store.js';

const SEARCH_FIELDS = {
  code: ['code'],
  names: ['frenchName', 'variantName', 'ausEName'],
  indigenous: ['indigenousName', 'indigenousLanguage'],
  characteristics: ['characteristic_fr', 'characteristic'],
  history: ['history_fr', 'history'],
  citations: ['citation_fr'],
  attributions: ['attribution'],
  classification: ['navire', 'campagne', 'secteur', 'categorie', 'sousCategorie', 'classe', 'planche', 'commentaire'],
};

const FIELD_WEIGHTS = {
  code: 100,
  frenchName: 40,
  variantName: 30,
  ausEName: 30,
  indigenousName: 30,
  indigenousLanguage: 10,
  characteristic_fr: 8,
  characteristic: 8,
  history_fr: 7,
  history: 7,
  citation_fr: 7,
  attribution: 9,
  navire: 12,
  campagne: 6,
  secteur: 12,
  categorie: 10,
  sousCategorie: 10,
  classe: 10,
  planche: 6,
  commentaire: 5,
};

const COVERAGE_FIELDS = [
  'characteristic_fr',
  'characteristic',
  'history_fr',
  'history',
  'indigenousName',
  'indigenousLanguage',
  'imgUrl',
  'mapUrl',
  'wiki_fr',
  'wiki_en',
  'citation_fr',
  'attribution',
];

// Les champs wiki_fr / wiki_en ne portent pas toujours un lien : le classeur
// d'origine y a laisse des tirets la ou personne n'avait trouve d'article, et
// une fois le code du toponyme lui-meme. Les compter comme des liens faisait
// remonter des fiches sans rien a montrer.
function hasUsableWikiLink(value) {
  if (!value || typeof value !== 'string') return false;
  const v = value.trim();
  if (!v) return false;
  if (/^[-–—.\s_]*$/.test(v)) return false;
  if (/^(n\/?a|na|nc|none|null|aucun|sans|\?+)$/i.test(v)) return false;
  if (/^(Baudin|Entre|Flinders)\d+$/i.test(v)) return false;
  return true;
}

function round(value, digits = 6) {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function encodeCursor(offset) {
  return Buffer.from(JSON.stringify({ offset }), 'utf8').toString('base64url');
}

function decodeCursor(cursor) {
  if (!cursor) return 0;
  try {
    const parsed = JSON.parse(Buffer.from(cursor, 'base64url').toString('utf8'));
    if (!Number.isInteger(parsed.offset) || parsed.offset < 0) throw new Error('Invalid offset');
    return parsed.offset;
  } catch {
    throw new Error('Invalid pagination cursor');
  }
}

function paginate(items, limit, cursor) {
  const offset = decodeCursor(cursor);
  const page = items.slice(offset, offset + limit);
  const nextOffset = offset + page.length;
  return {
    items: page,
    total: items.length,
    returned: page.length,
    limit,
    offset,
    truncated: nextOffset < items.length,
    nextCursor: nextOffset < items.length ? encodeCursor(nextOffset) : null,
  };
}

function fieldsForSearch(groups = Object.keys(SEARCH_FIELDS), language = 'both') {
  const fields = [...new Set(groups.flatMap((group) => SEARCH_FIELDS[group] ?? []))];
  if (language === 'fr') {
    return fields.filter((field) => !['characteristic', 'history'].includes(field));
  }
  if (language === 'en') {
    return fields.filter(
      (field) => !['characteristic_fr', 'history_fr', 'citation_fr'].includes(field),
    );
  }
  return fields;
}

function looseMatch(value, wanted) {
  if (!wanted) return true;
  return normalizeText(value).includes(normalizeText(wanted));
}

function inBoundingBox(item, boundingBox) {
  if (!hasCoordinates(item)) return false;
  return (
    item.lat >= boundingBox.south &&
    item.lat <= boundingBox.north &&
    item.lon >= boundingBox.west &&
    item.lon <= boundingBox.east
  );
}

function matchesCommonFilters(record, options = {}) {
  const {
    expedition,
    expeditions,
    states,
    boundingBox,
    vessel,
    categorie,
    secteur,
    uncertain,
    dateFrom,
    dateTo,
    hasCitation,
    hasAttribution,
  } = options;
  if (expedition && record.expedition !== expedition) return false;
  if (expeditions?.length && !expeditions.includes(record.expedition)) return false;
  if (states?.length) {
    const wanted = states.map(normalizeState);
    if (!wanted.includes(normalizeState(record.state))) return false;
  }
  if (boundingBox && !inBoundingBox(record, boundingBox)) return false;
  if (vessel && !looseMatch(record.navire, vessel)) return false;
  if (categorie && !looseMatch(record.categorie, categorie)) return false;
  if (secteur && !looseMatch(record.secteur, secteur)) return false;
  if (uncertain != null && Boolean(record.incertain) !== uncertain) return false;
  if (hasCitation != null && Boolean(record.citation_fr) !== hasCitation) return false;
  if (hasAttribution != null && Boolean(record.attribution) !== hasAttribution) return false;
  if (dateFrom && (!record.date || record.date < dateFrom)) return false;
  if (dateTo && (!record.date || record.date > dateTo)) return false;
  return true;
}

function scoreIndexedRecord(indexed, normalizedQuery, fields) {
  if (!normalizedQuery) return 0;
  const tokens = normalizedQuery.split(' ').filter(Boolean);
  let score = 0;

  for (const field of fields) {
    const value = indexed.normalized[field];
    if (!value) continue;
    const weight = FIELD_WEIGHTS[field] ?? 1;
    if (value === normalizedQuery) score += weight * 8;
    else if (value.startsWith(normalizedQuery)) score += weight * 5;
    else if (value.includes(normalizedQuery)) score += weight * 3;
    else {
      const matchedTokens = tokens.filter((token) => value.includes(token)).length;
      score += weight * (matchedTokens / Math.max(tokens.length, 1));
    }
  }
  return round(score, 3);
}

function excerpt(value, query, maxLength = 360) {
  const text = String(value ?? '').trim();
  if (!text || text.length <= maxLength) return text;
  const normalized = normalizeText(text);
  const normalizedQuery = normalizeText(query);
  const matchIndex = normalizedQuery ? normalized.indexOf(normalizedQuery) : -1;
  const approximateStart = matchIndex >= 0 ? Math.max(0, matchIndex - Math.floor(maxLength / 3)) : 0;
  let start = approximateStart;
  if (start > 0) {
    const nextSpace = text.indexOf(' ', start);
    if (nextSpace >= 0) start = nextSpace + 1;
  }
  const end = Math.min(text.length, start + maxLength);
  return `${start > 0 ? '…' : ''}${text.slice(start, end).trim()}${end < text.length ? '…' : ''}`;
}

function narrativeSummary(record, language, query = '') {
  const result = {};
  if (language !== 'en') {
    result.characteristic_fr = excerpt(record.characteristic_fr, query);
    result.history_fr = excerpt(record.history_fr, query);
  }
  if (language !== 'fr') {
    result.characteristic = excerpt(record.characteristic, query);
    result.history = excerpt(record.history, query);
  }
  return result;
}

function recordSummary(record, language = 'both', query = '') {
  return {
    code: record.code,
    expedition: record.expedition,
    state: record.state,
    frenchName: record.frenchName,
    variantName: record.variantName,
    ausEName: record.ausEName,
    indigenousName: record.indigenousName,
    indigenousLanguage: record.indigenousLanguage,
    lat: record.lat,
    lon: record.lon,
    located: hasCoordinates(record),
    ...narrativeSummary(record, language, query),
    ...(record.expedition === 'Flinders'
      ? {
          navire: record.navire,
          date: record.date,
          secteur: record.secteur,
          categorie: record.categorie,
          sousCategorie: record.sousCategorie,
          classe: record.classe,
          incertain: Boolean(record.incertain),
        }
      : {}),
    ...(record.citation_fr && language !== 'en'
      ? { citation_fr: excerpt(record.citation_fr, query) }
      : {}),
    ...(record.attribution ? { attribution: record.attribution } : {}),
    detailsLink: record.detailsLink,
    detailsLink_en: record.detailsLink_en,
    provenance: record._provenance,
  };
}

function localizedFullRecord(record, language = 'both') {
  const result = { ...record, provenance: record._provenance };
  delete result._provenance;
  result.located = hasCoordinates(record);
  // Un tiret n'est pas un lien : on le remplace par du vide plutot que de le
  // laisser filer vers un client qui en ferait une adresse.
  for (const cle of ['wiki_fr', 'wiki_en']) {
    if (cle in result && !hasUsableWikiLink(result[cle])) result[cle] = '';
  }
  if (language === 'fr') {
    delete result.characteristic;
    delete result.history;
    delete result.detailsLink_en;
    delete result.mapTitle_en;
    delete result.wiki_en;
  } else if (language === 'en') {
    delete result.characteristic_fr;
    delete result.history_fr;
    delete result.origin_fr;
    delete result.detailsLink;
    delete result.mapTitle_fr;
    delete result.wiki_fr;
    delete result.citation_fr;
  }
  return result;
}

function recordMatchesText(indexed, query, fields, language) {
  const normalizedQuery = normalizeText(query);
  if (!normalizedQuery) return true;
  return scoreIndexedRecord(indexed, normalizedQuery, fieldsForSearch(fields, language)) > 0;
}

export function searchToponyms(options = {}) {
  const {
    query = '',
    language = 'both',
    fields = Object.keys(SEARCH_FIELDS),
    limit = 20,
    cursor,
    ...filters
  } = options;
  const normalizedQuery = normalizeText(query);
  const selectedFields = fieldsForSearch(fields, language);

  const matches = SEARCH_INDEX.filter(({ record }) => matchesCommonFilters(record, filters))
    .map((indexed) => ({
      record: indexed.record,
      score: normalizedQuery ? scoreIndexedRecord(indexed, normalizedQuery, selectedFields) : 0,
    }))
    .filter(({ score }) => !normalizedQuery || score > 0)
    .sort((a, b) => b.score - a.score || a.record.code.localeCompare(b.record.code));

  const page = paginate(matches, limit, cursor);
  return {
    recordsScanned: TOPONYMS.length,
    query,
    language,
    fields,
    filters,
    ...page,
    items: page.items.map(({ record, score }) => ({
      relevanceScore: score,
      ...recordSummary(record, language, query),
    })),
  };
}

export function getToponym(code, language = 'both') {
  const record = TOPONYM_BY_CODE.get(normalizeText(code));
  return record ? localizedFullRecord(record, language) : null;
}

export function haversineDistanceKm(lat1, lon1, lat2, lon2) {
  const toRadians = (degrees) => (degrees * Math.PI) / 180;
  const earthRadiusKm = 6371.0088;
  const dLat = toRadians(lat2 - lat1);
  const dLon = toRadians(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRadians(lat1)) *
      Math.cos(toRadians(lat2)) *
      Math.sin(dLon / 2) ** 2;
  return earthRadiusKm * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

export function findNearbyToponyms(options) {
  const {
    latitude,
    longitude,
    radiusKm = 100,
    language = 'both',
    expedition,
    expeditions,
    states,
    limit = 50,
  } = options;

  const matches = TOPONYMS.filter(
    (record) => hasCoordinates(record) && matchesCommonFilters(record, { expedition, expeditions, states }),
  )
    .map((record) => ({
      record,
      distanceKm: haversineDistanceKm(latitude, longitude, record.lat, record.lon),
    }))
    .filter(({ distanceKm }) => distanceKm <= radiusKm)
    .sort((a, b) => a.distanceKm - b.distanceKm || a.record.code.localeCompare(b.record.code));

  return {
    recordsScanned: TOPONYMS.length,
    center: { latitude, longitude },
    radiusKm,
    totalMatches: matches.length,
    returned: Math.min(matches.length, limit),
    truncated: matches.length > limit,
    items: matches.slice(0, limit).map(({ record, distanceKm }) => ({
      distanceKm: round(distanceKm, 3),
      ...recordSummary(record, language),
    })),
  };
}

function groupValue(record, field) {
  switch (field) {
    case 'hasIndigenousName':
      return Boolean(record.indigenousName);
    case 'hasIndigenousLanguage':
      return Boolean(record.indigenousLanguage);
    case 'hasImage':
      return Boolean(record.imgUrl);
    case 'hasMap':
      return Boolean(record.mapUrl);
    case 'hasWikipedia':
      return hasUsableWikiLink(record.wiki_fr) || hasUsableWikiLink(record.wiki_en);
    case 'hasCharacteristicsFr':
      return Boolean(record.characteristic_fr);
    case 'hasCharacteristicsEn':
      return Boolean(record.characteristic);
    case 'hasHistoryFr':
      return Boolean(record.history_fr);
    case 'hasHistoryEn':
      return Boolean(record.history);
    case 'hasCitation':
      return Boolean(record.citation_fr);
    case 'hasAttribution':
      return Boolean(record.attribution);
    case 'hasCoordinates':
      return hasCoordinates(record);
    case 'incertain':
      return Boolean(record.incertain);
    case 'year':
      return record.date ? record.date.slice(0, 4) : '(sans date)';
    case 'state':
      return normalizeState(record.state) || '(empty)';
    default:
      return record[field] || '(empty)';
  }
}

function geographicSummary(allRecords) {
  const records = allRecords.filter(hasCoordinates);
  if (!records.length) return null;
  const latitudes = records.map((record) => record.lat);
  const longitudes = records.map((record) => record.lon);
  return {
    locatedRecords: records.length,
    unlocatedRecords: allRecords.length - records.length,
    bounds: {
      south: Math.min(...latitudes),
      north: Math.max(...latitudes),
      west: Math.min(...longitudes),
      east: Math.max(...longitudes),
    },
    meanCoordinate: {
      latitude: round(latitudes.reduce((sum, value) => sum + value, 0) / records.length),
      longitude: round(longitudes.reduce((sum, value) => sum + value, 0) / records.length),
    },
  };
}

function fieldCoverage(records) {
  return Object.fromEntries(
    COVERAGE_FIELDS.map((field) => {
      const present = records.filter((record) => String(record[field] ?? '').trim()).length;
      return [
        field,
        {
          present,
          missing: records.length - present,
          percentPresent: records.length ? round((present / records.length) * 100, 2) : 0,
        },
      ];
    }),
  );
}

export function analyzeToponyms(options = {}) {
  const {
    query = '',
    language = 'both',
    fields = ['names', 'indigenous', 'characteristics', 'history'],
    center,
    radiusKm,
    groupBy = [],
    distinctBy = [],
    ...filters
  } = options;

  const records = SEARCH_INDEX.filter((indexed) => {
    if (!matchesCommonFilters(indexed.record, filters)) return false;
    if (center && radiusKm != null) {
      if (!hasCoordinates(indexed.record)) return false;
      const distance = haversineDistanceKm(
        center.latitude,
        center.longitude,
        indexed.record.lat,
        indexed.record.lon,
      );
      if (distance > radiusKm) return false;
    }
    return recordMatchesText(indexed, query, fields, language);
  }).map(({ record }) => record);

  const grouped = new Map();
  if (groupBy.length) {
    for (const record of records) {
      const dimensions = Object.fromEntries(groupBy.map((field) => [field, groupValue(record, field)]));
      const key = JSON.stringify(dimensions);
      const current = grouped.get(key) ?? { dimensions, count: 0 };
      current.count += 1;
      grouped.set(key, current);
    }
  }

  const groups = [...grouped.values()]
    .map((group) => ({
      ...group,
      percentOfAnalyzed: records.length ? round((group.count / records.length) * 100, 2) : 0,
    }))
    .sort(
      (a, b) =>
        b.count - a.count || JSON.stringify(a.dimensions).localeCompare(JSON.stringify(b.dimensions)),
    );

  return {
    recordsScanned: TOPONYMS.length,
    recordsAnalyzed: records.length,
    filters: { query, language, fields, ...filters, center, radiusKm },
    groupBy,
    groups,
    distinctCounts: Object.fromEntries(
      distinctBy.map((field) => [
        field,
        new Set(
          records
            .map((record) => (field === 'state' ? normalizeState(record.state) : record[field]))
            .filter((value) => String(value ?? '').trim() !== ''),
        ).size,
      ]),
    ),
    geographicSummary: geographicSummary(records),
    fieldCoverage: fieldCoverage(records),
    truncated: false,
  };
}

export function searchTimeline(options = {}) {
  const {
    query = '',
    language = 'both',
    vessel,
    dateFrom,
    dateTo,
    interpolation,
    limit = 20,
    cursor,
  } = options;
  const normalizedQuery = normalizeText(query);

  const matches = TIMELINE.filter((event) => {
    if (dateFrom && event.dateISO < dateFrom) return false;
    if (dateTo && event.dateISO > dateTo) return false;
    if (vessel && !event[vessel]) return false;
    if (interpolation != null && Boolean(event.interpolation) !== interpolation) return false;
    if (!normalizedQuery) return true;
    const texts = language === 'fr' ? [event.histoire] : language === 'en' ? [event.story] : [event.histoire, event.story];
    return texts.some((text) => normalizeText(text).includes(normalizedQuery));
  }).sort((a, b) => a.dateISO.localeCompare(b.dateISO) || a.id - b.id);

  const page = paginate(matches, limit, cursor);
  return {
    recordsScanned: TIMELINE.length,
    query,
    language,
    ...page,
    items: page.items.map((event) => {
      const item = {
        id: event.id,
        dateISO: event.dateISO,
        lat: event.lat,
        lon: event.lon,
        geographe: event.geographe,
        naturaliste: event.naturaliste,
        casuarina: event.casuarina,
        flinders: event.flinders,
        interpolation: event.interpolation,
        provenance: event._provenance,
      };
      if (language !== 'en') item.histoire = event.histoire;
      if (language !== 'fr') item.story = event.story;
      return item;
    }),
  };
}

export function getDatasetSummary() {
  return {
    ...DATASET_SUMMARY,
    fieldCoverage: fieldCoverage(TOPONYMS),
    invariants: {
      uniqueCodes: new Set(TOPONYMS.map((record) => record.code)).size,
      missingCodes: TOPONYMS.filter((record) => !record.code).length,
      invalidCoordinates: TOPONYMS.filter(
        (record) => !Number.isFinite(record.lat) || !Number.isFinite(record.lon),
      ).length,
      unlocatedRecords: TOPONYMS.filter((record) => !hasCoordinates(record)).length,
      unlocatedCodes: TOPONYMS.filter((record) => !hasCoordinates(record)).map(
        (record) => record.code,
      ),
      routePositionsWithoutDate: ROUTE_POSITIONS.filter((position) => !position.date).length,
      journalEntriesWithoutText: JOURNAL_ENTRIES.filter((entry) => !entry.texte.trim()).length,
    },
    routeTrajectories: ROUTE_TRAJECTORIES,
  };
}

const ROUTE_TEXT_FIELDS = [
  'remarque',
  'alerte',
  'section',
  'table',
  'vents_etat_du_ciel',
  'date_republicaine',
  'navire',
  'sourceLatitude',
  'sourceLongitude',
];

function routeMatchesFilters(position, options) {
  const {
    expedition,
    expeditions,
    vessel,
    dateFrom,
    dateTo,
    boundingBox,
    flags,
    withWeather,
  } = options;
  if (expedition && position.expedition !== expedition) return false;
  if (expeditions?.length && !expeditions.includes(position.expedition)) return false;
  // Le filtre porte sur les coques réellement placées par le relevé, et non sur
  // le libellé collectif ; celui-ci reste interrogeable pour la traçabilité.
  if (
    vessel &&
    !position.navires.some((name) => looseMatch(name, vessel)) &&
    !looseMatch(position.navireSource, vessel)
  ) {
    return false;
  }
  if (dateFrom && (!position.date || position.date < dateFrom)) return false;
  if (dateTo && (!position.date || position.date > dateTo)) return false;
  if (boundingBox && !inBoundingBox(position, boundingBox)) return false;
  if (flags) {
    for (const [flag, expected] of Object.entries(flags)) {
      if (position.flags[flag] !== expected) return false;
    }
  }
  if (withWeather != null) {
    const observed = Boolean(
      String(position.vents_etat_du_ciel).trim() ||
        position.barometre_hpa != null ||
        String(position.thermometre).trim(),
    );
    if (observed !== withWeather) return false;
  }
  return true;
}

function routeItem(position, query = '', distanceKm = null) {
  return {
    id: position.id,
    expedition: position.expedition,
    navire: position.navire,
    navires: position.navires,
    navireSource: position.navireSource,
    navireCollectif: position.navireCollectif,
    date: position.date,
    date_republicaine: position.date_republicaine,
    lat: position.lat,
    lon: position.lon,
    ...(distanceKm != null ? { distanceKm: round(distanceKm, 3) } : {}),
    section: position.section,
    table: position.table,
    page: position.page,
    remarque: excerpt(position.remarque, query),
    alerte: excerpt(position.alerte, query),
    observation: {
      latitude: position.sourceLatitude,
      longitude: position.sourceLongitude,
      vents_etat_du_ciel: position.vents_etat_du_ciel,
      barometre_hpa: position.barometre_hpa,
      thermometre: position.thermometre,
      declinaison_dms: position.declinaison_dms,
      declinaison_ref: position.declinaison_ref,
    },
    flags: position.flags,
    provenance: position._provenance,
  };
}

export function searchRoutePositions(options = {}) {
  const {
    query = '',
    center,
    radiusKm,
    order = 'date',
    limit = 50,
    cursor,
    ...filters
  } = options;
  const normalizedQuery = normalizeText(query);

  const matches = ROUTE_POSITIONS.filter((position) => {
    if (!routeMatchesFilters(position, filters)) return false;
    if (center && radiusKm != null) {
      if (!hasCoordinates(position)) return false;
      const distance = haversineDistanceKm(
        center.latitude,
        center.longitude,
        position.lat,
        position.lon,
      );
      if (distance > radiusKm) return false;
    }
    if (!normalizedQuery) return true;
    return ROUTE_TEXT_FIELDS.some((field) =>
      normalizeText(position[field]).includes(normalizedQuery),
    );
  }).map((position) => ({
    position,
    distanceKm: center
      ? haversineDistanceKm(center.latitude, center.longitude, position.lat, position.lon)
      : null,
  }));

  matches.sort((a, b) =>
    order === 'distance'
      ? a.distanceKm - b.distanceKm || a.position.date.localeCompare(b.position.date)
      : a.position.date.localeCompare(b.position.date) ||
        a.position.expedition.localeCompare(b.position.expedition) ||
        a.position.navire.localeCompare(b.position.navire),
  );

  const page = paginate(matches, limit, cursor);
  return {
    recordsScanned: ROUTE_POSITIONS.length,
    query,
    filters: { ...filters, center, radiusKm, order },
    ...page,
    items: page.items.map(({ position, distanceKm }) => routeItem(position, query, distanceKm)),
  };
}

function routeGroupValue(position, field) {
  switch (field) {
    case 'navireSource':
      return position.navireSource || '(sans libellé)';
    case 'year':
      return position.date ? position.date.slice(0, 4) : '(sans date)';
    case 'section':
      return position.section || '(sans section)';
    case 'table':
      return position.table || '(sans table)';
    default:
      return position[field] || '(empty)';
  }
}

export function getRouteSummary(options = {}) {
  const { groupBy = ['expedition', 'navire'], ...filters } = options;
  const positions = ROUTE_POSITIONS.filter((position) => routeMatchesFilters(position, filters));

  // L'axe « coque » déplie les positions partagées : un relevé tenu de conserve
  // compte pour chacun des bâtiments qu'il place.
  const perHull = groupBy.includes('coque');
  const rows = perHull
    ? positions.flatMap((position) =>
        position.navires.map((hull) => ({ position, coque: hull })),
      )
    : positions.map((position) => ({ position, coque: null }));

  const grouped = new Map();
  for (const { position, coque } of rows) {
    const dimensions = Object.fromEntries(
      groupBy.map((field) => [field, field === 'coque' ? coque : routeGroupValue(position, field)]),
    );
    const key = JSON.stringify(dimensions);
    const current = grouped.get(key) ?? {
      dimensions,
      count: 0,
      dates: [],
      flagCounts: Object.fromEntries(Object.keys(position.flags).map((flag) => [flag, 0])),
      withWeather: 0,
      records: [],
    };
    current.count += 1;
    if (position.date) current.dates.push(position.date);
    for (const [flag, value] of Object.entries(position.flags)) {
      if (value) current.flagCounts[flag] += 1;
    }
    if (
      String(position.vents_etat_du_ciel).trim() ||
      position.barometre_hpa != null ||
      String(position.thermometre).trim()
    ) {
      current.withWeather += 1;
    }
    current.records.push(position);
    grouped.set(key, current);
  }

  const groups = [...grouped.values()]
    .map(({ records, dates, ...group }) => {
      const sorted = [...dates].sort();
      return {
        ...group,
        dateRange: sorted.length ? { from: sorted[0], to: sorted[sorted.length - 1] } : null,
        distinctDates: new Set(sorted).size,
        geographicSummary: geographicSummary(records),
      };
    })
    .sort((a, b) => b.count - a.count || JSON.stringify(a.dimensions).localeCompare(JSON.stringify(b.dimensions)));

  return {
    recordsScanned: ROUTE_POSITIONS.length,
    positionsAnalyzed: positions.length,
    filters,
    groupBy,
    perHull,
    groups,
    trajectories: ROUTE_TRAJECTORIES.filter(
      (trajectory) =>
        (!filters.expedition || trajectory.expedition === filters.expedition) &&
        (!filters.expeditions?.length || filters.expeditions.includes(trajectory.expedition)) &&
        (!filters.vessel ||
          trajectory.navires.some((name) => looseMatch(name, filters.vessel)) ||
          looseMatch(trajectory.navireSource, filters.vessel)),
    ),
    truncated: false,
  };
}

export function searchJournals(options = {}) {
  const {
    query = '',
    sources,
    dateFrom,
    dateTo,
    limit = 20,
    cursor,
    full = false,
  } = options;
  const normalizedQuery = normalizeText(query);

  const matches = JOURNAL_INDEX.filter(({ entry, normalized }) => {
    if (sources?.length && !sources.includes(entry.source)) return false;
    if (dateFrom && entry.date < dateFrom) return false;
    if (dateTo && entry.date > dateTo) return false;
    if (!normalizedQuery) return true;
    return normalized.includes(normalizedQuery);
  }).map(({ entry }) => entry);

  const page = paginate(matches, limit, cursor);
  return {
    recordsScanned: JOURNAL_ENTRIES.length,
    query,
    sources: sources ?? null,
    ...page,
    items: page.items.map((entry) => ({
      source: entry.source,
      sourceTitle: entry.sourceTitle,
      date: entry.date,
      republicain: entry.republicain,
      entete: entry.entete,
      etat: entry.etat,
      characters: entry.texte.length,
      texte: full ? entry.texte : excerpt(entry.texte, query, 700),
      provenance: entry._provenance,
    })),
  };
}

export function getJournalDay(options = {}) {
  const { date, sources } = options;
  const entries = JOURNAL_ENTRIES.filter(
    (entry) => entry.date === date && (!sources?.length || sources.includes(entry.source)),
  );
  return {
    date,
    sourcesAvailable: entries.map((entry) => entry.source),
    routePositions: ROUTE_POSITIONS.filter((position) => position.date === date).map((position) =>
      routeItem(position),
    ),
    remarkableDates: REMARKABLE_DATES.filter((entry) => entry.date === date).map(
      ({ _provenance, ...entry }) => ({ ...entry, provenance: _provenance }),
    ),
    timelineEvents: TIMELINE.filter((event) => event.dateISO === date).map((event) => ({
      id: event.id,
      dateISO: event.dateISO,
      histoire: event.histoire,
      story: event.story,
      provenance: event._provenance,
    })),
    entries: entries.map((entry) => ({
      source: entry.source,
      sourceTitle: entry.sourceTitle,
      republicain: entry.republicain,
      entete: entry.entete,
      etat: entry.etat,
      texte: entry.texte,
      provenance: entry._provenance,
    })),
    truncated: false,
  };
}

export function searchRemarkableDates(options = {}) {
  const {
    query = '',
    language = 'both',
    expedition,
    expeditions,
    vessel,
    dateFrom,
    dateTo,
    limit = 100,
    cursor,
  } = options;
  const normalizedQuery = normalizeText(query);

  const matches = REMARKABLE_DATES.filter((entry) => {
    if (expedition && entry.expedition !== expedition) return false;
    if (expeditions?.length && !expeditions.includes(entry.expedition)) return false;
    if (vessel && !looseMatch(entry.navire, vessel)) return false;
    if (dateFrom && entry.date < dateFrom) return false;
    if (dateTo && entry.date > dateTo) return false;
    if (!normalizedQuery) return true;
    const texts =
      language === 'fr'
        ? [entry.libelle_fr]
        : language === 'en'
          ? [entry.libelle_en]
          : [entry.libelle_fr, entry.libelle_en];
    return texts.some((text) => normalizeText(text).includes(normalizedQuery));
  });

  const page = paginate(matches, limit, cursor);
  return {
    recordsScanned: REMARKABLE_DATES.length,
    query,
    language,
    ...page,
    items: page.items.map((entry) => {
      const item = {
        id: entry.id,
        date: entry.date,
        expedition: entry.expedition,
        navire: entry.navire,
        provenance: entry._provenance,
      };
      if (language !== 'en') item.libelle_fr = entry.libelle_fr;
      if (language !== 'fr') item.libelle_en = entry.libelle_en;
      return item;
    }),
  };
}
