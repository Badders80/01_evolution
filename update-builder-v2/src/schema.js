import { z } from 'zod';

export const updateSchema = z.object({
  preheader: z.string().min(1, 'Preheader is required'),
  slug: z.string()
    .min(1, 'Slug is required')
    .regex(/^[a-z0-9-]+$/, 'Slug must be lowercase letters, numbers, and hyphens only'),
  heading: z.string().min(1, 'Heading is required').max(100, 'Heading must be under 100 characters'),
  subheaderLabel: z.string().min(1, 'Subheader label is required'),
  subheaderBullets: z.array(z.string())
    .min(2, 'At least 2 bullets required')
    .max(5, 'Maximum 5 bullets'),
  bodyParagraphs: z.array(z.string())
    .min(1, 'At least 1 paragraph required')
    .max(3, 'Maximum 3 paragraphs'),
  quoteText: z.string().min(1, 'Quote text is required'),
  quoteAttribution: z.string().min(1, 'Quote attribution is required'),
  linkLabel: z.string().optional(),
  linkUrl: z.string().url('Must be a valid URL').optional().or(z.literal('')),
  heroImageUrl: z.string().url('Must be a valid URL').optional().or(z.literal('')),
  heroImageCaption: z.string().optional(),
  signOffName: z.string().min(1, 'Sign-off name is required'),
  signOffTitle: z.string().min(1, 'Sign-off title is required'),
});
