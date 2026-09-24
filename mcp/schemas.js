import { z } from 'zod';

export const LanguageSchema = z
  .enum(['fr', 'en', 'both'])
  .optional()
  .describe(
    "Language of the user's question, 'fr' or 'en': narrative fields are searched and returned in that language only. " +
      "Use 'both' only when the user asks for both languages. When omitted, the server infers it from the query text, falling back to 'fr'.",
  );

export const ExpeditionNameSchema = z.enum(['Baudin', 'Entrecasteaux', 'Flinders']);
export const ExpeditionSchema = ExpeditionNameSchema.optional();
export const ExpeditionsSchema = z.array(ExpeditionNameSchema).max(3).optional();
export const StateSchema = z
  .enum(['NSW', 'NT', 'QLD', 'SA', 'Tas', 'VIC', 'WA'])
  .describe('Australian state or territory; matching ignores case.');
export const StatesSchema = z.array(StateSchema).max(7).optional();

export const IsoDateSchema = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);

export const VesselSchema = z
  .string()
  .max(60)
  .describe("Vessel name as recorded, for example l'Investigator or le Géographe; matching ignores case and accents.");

export const SearchFieldsSchema = z
  .array(
    z.enum([
      'code',
      'names',
      'indigenous',
      'characteristics',
      'history',
      'citations',
      'attributions',
      'classification',
    ]),
  )
  .min(1)
  .max(8)
  .default(['code', 'names', 'indigenous', 'characteristics', 'history']);

export const BoundingBoxSchema = z
  .object({
    south: z.number().min(-90).max(90),
    north: z.number().min(-90).max(90),
    west: z.number().min(-180).max(180),
    east: z.number().min(-180).max(180),
  })
  .refine((box) => box.south <= box.north, {
    message: 'south must be less than or equal to north',
  })
  .refine((box) => box.west <= box.east, {
    message: 'west must be less than or equal to east',
  });

export const CoordinateSchema = z.object({
  latitude: z.number().min(-90).max(90),
  longitude: z.number().min(-180).max(180),
});

export const SearchToponymsSchema = z
  .object({
    query: z.string().max(500).default(''),
    language: LanguageSchema,
    fields: SearchFieldsSchema,
    expedition: ExpeditionSchema,
    expeditions: ExpeditionsSchema,
    states: StatesSchema,
    boundingBox: BoundingBoxSchema.optional(),
    vessel: VesselSchema.optional(),
    categorie: z.string().max(120).optional(),
    secteur: z.string().max(120).optional(),
    uncertain: z.boolean().optional(),
    dateFrom: IsoDateSchema.optional(),
    dateTo: IsoDateSchema.optional(),
    hasCitation: z.boolean().optional(),
    hasAttribution: z.boolean().optional(),
    limit: z.number().int().min(1).max(200).default(10),
    cursor: z.string().max(500).optional(),
  })
  .strict();

export const GetToponymSchema = z
  .object({
    code: z.string().min(1).max(50),
    language: LanguageSchema,
  })
  .strict();

export const NearbyToponymsSchema = z
  .object({
    latitude: z.number().min(-90).max(90),
    longitude: z.number().min(-180).max(180),
    radiusKm: z.number().positive().max(20000).default(100),
    language: LanguageSchema,
    expedition: ExpeditionSchema,
    expeditions: ExpeditionsSchema,
    states: StatesSchema,
    limit: z.number().int().min(1).max(200).default(20),
  })
  .strict();

export const AnalysisGroupSchema = z.enum([
  'expedition',
  'state',
  'navire',
  'secteur',
  'categorie',
  'sousCategorie',
  'classe',
  'planche',
  'year',
  'incertain',
  'hasCitation',
  'hasAttribution',
  'hasCoordinates',
  'hasIndigenousName',
  'hasIndigenousLanguage',
  'hasImage',
  'hasMap',
  'hasWikipedia',
  'hasCharacteristicsFr',
  'hasCharacteristicsEn',
  'hasHistoryFr',
  'hasHistoryEn',
]);

export const DistinctFieldSchema = z.enum([
  'code',
  'expedition',
  'state',
  'navire',
  'secteur',
  'categorie',
  'sousCategorie',
  'classe',
  'frenchName',
  'variantName',
  'ausEName',
  'indigenousName',
  'indigenousLanguage',
]);

export const AnalyzeToponymsSchema = z
  .object({
    query: z.string().max(500).default(''),
    language: LanguageSchema,
    fields: SearchFieldsSchema,
    expedition: ExpeditionSchema,
    expeditions: ExpeditionsSchema,
    states: StatesSchema,
    boundingBox: BoundingBoxSchema.optional(),
    vessel: VesselSchema.optional(),
    categorie: z.string().max(120).optional(),
    secteur: z.string().max(120).optional(),
    uncertain: z.boolean().optional(),
    dateFrom: IsoDateSchema.optional(),
    dateTo: IsoDateSchema.optional(),
    hasCitation: z.boolean().optional(),
    hasAttribution: z.boolean().optional(),
    center: CoordinateSchema.optional(),
    radiusKm: z.number().positive().max(20000).optional(),
    groupBy: z.array(AnalysisGroupSchema).max(3).default([]),
    distinctBy: z.array(DistinctFieldSchema).max(12).default([]),
  })
  .strict()
  .superRefine((value, context) => {
    if ((value.center && value.radiusKm == null) || (!value.center && value.radiusKm != null)) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'center and radiusKm must be provided together',
      });
    }
  });

export const SearchTimelineSchema = z
  .object({
    query: z.string().max(500).default(''),
    language: LanguageSchema,
    vessel: z.enum(['geographe', 'naturaliste', 'casuarina', 'flinders']).optional(),
    dateFrom: IsoDateSchema.optional(),
    dateTo: IsoDateSchema.optional(),
    interpolation: z.boolean().optional(),
    limit: z.number().int().min(1).max(200).default(20),
    cursor: z.string().max(500).optional(),
  })
  .strict()
  .refine((value) => !value.dateFrom || !value.dateTo || value.dateFrom <= value.dateTo, {
    message: 'dateFrom must be before or equal to dateTo',
  });

export const RouteFlagSchema = z.enum([
  'extrapole',
  'mouillage',
  'contournement',
  'renfloue',
  'de_conserve',
  'releve_corrige',
  'releve_carte',
]);

export const SearchRoutePositionsSchema = z
  .object({
    query: z
      .string()
      .max(500)
      .default('')
      .describe('Free text searched in remarks, alerts, sections, route tables, and weather notes.'),
    expedition: ExpeditionSchema,
    expeditions: ExpeditionsSchema,
    vessel: VesselSchema.optional(),
    dateFrom: IsoDateSchema.optional(),
    dateTo: IsoDateSchema.optional(),
    boundingBox: BoundingBoxSchema.optional(),
    center: CoordinateSchema.optional(),
    radiusKm: z.number().positive().max(20000).optional(),
    flags: z
      .record(RouteFlagSchema, z.boolean())
      .optional()
      .describe('Require a route qualifier to be true or false, for example {"mouillage": true}.'),
    withWeather: z
      .boolean()
      .optional()
      .describe('Keep only positions that carry a wind, barometer, or thermometer reading.'),
    includeObservation: z
      .boolean()
      .optional()
      .describe('Add the onboard observation (source latitude and longitude, wind and sky, barometer, thermometer, declination). Implied by withWeather.'),
    order: z.enum(['date', 'distance']).default('date'),
    limit: z.number().int().min(1).max(200).default(20),
    cursor: z.string().max(500).optional(),
  })
  .strict()
  .superRefine((value, context) => {
    if ((value.center && value.radiusKm == null) || (!value.center && value.radiusKm != null)) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'center and radiusKm must be provided together',
      });
    }
    if (value.order === 'distance' && !value.center) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'order "distance" requires center and radiusKm',
      });
    }
    if (value.dateFrom && value.dateTo && value.dateFrom > value.dateTo) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'dateFrom must be before or equal to dateTo',
      });
    }
  });

export const RouteSummarySchema = z
  .object({
    expedition: ExpeditionSchema,
    expeditions: ExpeditionsSchema,
    vessel: VesselSchema.optional(),
    dateFrom: IsoDateSchema.optional(),
    dateTo: IsoDateSchema.optional(),
    groupBy: z
      .array(z.enum(['expedition', 'navire', 'coque', 'navireSource', 'year', 'section', 'table']))
      .max(2)
      .default(['expedition', 'navire'])
      .describe(
        'Group the positions. "navire" uses the reconciled label of the hulls placed by the reading; "coque" reports one row per ship, counting a shared reading for each; "navireSource" keeps the collective label as the published route table wrote it.',
      ),
  })
  .strict();

export const JournalSourceSchema = z.enum([
  'baudin',
  'baudin_autographe',
  'breton',
  'anonyme',
  'geographe',
]);

export const SearchJournalsSchema = z
  .object({
    query: z.string().max(500).default(''),
    sources: z.array(JournalSourceSchema).max(5).optional(),
    language: LanguageSchema,
    dateFrom: IsoDateSchema.optional(),
    dateTo: IsoDateSchema.optional(),
    limit: z.number().int().min(1).max(100).default(20),
    cursor: z.string().max(500).optional(),
    full: z
      .boolean()
      .default(false)
      .describe('Return complete day entries instead of excerpts around the match.'),
  })
  .strict()
  .refine((value) => !value.dateFrom || !value.dateTo || value.dateFrom <= value.dateTo, {
    message: 'dateFrom must be before or equal to dateTo',
  });

export const GetJournalDaySchema = z
  .object({
    date: IsoDateSchema,
    sources: z.array(JournalSourceSchema).max(5).optional(),
    language: LanguageSchema,
  })
  .strict();

export const RemarkableDatesSchema = z
  .object({
    query: z.string().max(500).default(''),
    language: LanguageSchema,
    expedition: ExpeditionSchema,
    expeditions: ExpeditionsSchema,
    vessel: VesselSchema.optional(),
    dateFrom: IsoDateSchema.optional(),
    dateTo: IsoDateSchema.optional(),
    limit: z.number().int().min(1).max(200).default(100),
    cursor: z.string().max(500).optional(),
  })
  .strict()
  .refine((value) => !value.dateFrom || !value.dateTo || value.dateFrom <= value.dateTo, {
    message: 'dateFrom must be before or equal to dateTo',
  });
