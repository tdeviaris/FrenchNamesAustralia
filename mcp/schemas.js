import { z } from 'zod';

export const LanguageSchema = z
  .enum(['fr', 'en', 'both'])
  .default('both')
  .describe('Language of narrative fields to search and return.');

export const ExpeditionSchema = z.enum(['Baudin', 'Entrecasteaux']).optional();
export const StateSchema = z.enum(['NT', 'SA', 'Tas', 'VIC', 'WA']);
export const StatesSchema = z.array(StateSchema).max(5).optional();

export const SearchFieldsSchema = z
  .array(z.enum(['code', 'names', 'indigenous', 'characteristics', 'history']))
  .min(1)
  .max(5)
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
    states: StatesSchema,
    boundingBox: BoundingBoxSchema.optional(),
    limit: z.number().int().min(1).max(200).default(20),
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
    states: StatesSchema,
    limit: z.number().int().min(1).max(200).default(50),
  })
  .strict();

export const AnalysisGroupSchema = z.enum([
  'expedition',
  'state',
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
    states: StatesSchema,
    boundingBox: BoundingBoxSchema.optional(),
    center: CoordinateSchema.optional(),
    radiusKm: z.number().positive().max(20000).optional(),
    groupBy: z.array(AnalysisGroupSchema).max(2).default([]),
    distinctBy: z.array(DistinctFieldSchema).max(8).default([]),
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
    dateFrom: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional(),
    dateTo: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional(),
    interpolation: z.boolean().optional(),
    limit: z.number().int().min(1).max(200).default(20),
    cursor: z.string().max(500).optional(),
  })
  .strict()
  .refine((value) => !value.dateFrom || !value.dateTo || value.dateFrom <= value.dateTo, {
    message: 'dateFrom must be before or equal to dateTo',
  });
