import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const posts = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/posts' }),
  schema: z.object({
    title: z.string().max(110),
    description: z.string().max(170), // entradilla y meta description para Google
    date: z.coerce.date(),
    updated: z.coerce.date().optional(),
    category: z.enum(['ahorro', 'fondos', 'bolsa', 'jubilacion', 'impuestos']),
    tags: z.array(z.coerce.string()).default([]),  // una etiqueta como 2027 se lee como número: se convierte a texto
    image: z.string().optional(),
    imageAlt: z.string().optional(),
    imageCredit: z.string().optional(),
    imageCreditUrl: z.string().url().optional(),
    // propuesta o anuncio aún no publicado en el BOE → aviso visible
    pendiente: z.boolean().default(false),
    // guía viva: página de referencia que se mantiene actualizada en la misma dirección
    guia: z.boolean().default(false),
    orden: z.number().default(99),
    sources: z.array(z.object({ name: z.string(), url: z.string().url() })).default([]),
    // correcciones visibles al final del artículo
    correcciones: z.array(z.object({ fecha: z.coerce.date(), texto: z.string() })).default([]),
    draft: z.boolean().default(false),
  }),
});

export const collections = { posts };
