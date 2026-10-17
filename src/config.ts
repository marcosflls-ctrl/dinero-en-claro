// ⚙️ CONFIGURACIÓN GENERAL — cambia aquí el nombre, dominio, AdSense y redes
export const SITE = {
  name: 'Dinero en Claro',
  tagline: 'Ahorro, inversión y mercados explicados sin letra pequeña',
  url: 'https://dineroenclaro.com', // también en astro.config.mjs
  lang: 'es',
  locale: 'es_ES',
  email: 'contacto@dineroenclaro.com',
  author: {
    name: 'Redacción Dinero en Claro',
    slug: 'redaccion',
    bio: 'El equipo de Dinero en Claro explica cómo funcionan los productos de ahorro e inversión, sus costes y sus impuestos, siempre con datos y fuentes oficiales y sin recomendar productos concretos.',
  },
  ownerName: 'Marcos Fernández León',
  ownerNif: '48158108H',
  // AdSense: la misma cuenta que las otras webs. Se activa cuando Google apruebe este sitio.
  adsenseClient: 'ca-pub-2093028838178784',
  cfAnalyticsToken: '',
  social: { telegram: '', whatsapp: '', facebook: '', x: '' },
  // Webs hermanas, para enlazarlas en el pie
  hermanas: [{ nombre: 'Al Final de Mes', url: 'https://alfinaldemes.com/', texto: 'economía de casa: pensiones, paro, Hacienda y luz' }],
};

export const CATEGORIES = {
  ahorro: {
    label: 'Ahorro',
    titulo: 'Ahorro: depósitos, cuentas y Letras del Tesoro',
    desc: 'Depósitos, cuentas remuneradas, Letras del Tesoro y tipos de interés: cuánto rinde de verdad tu dinero y qué riesgos tiene cada opción.',
  },
  fondos: {
    label: 'Fondos y ETF',
    titulo: 'Fondos de inversión y ETF',
    desc: 'Fondos indexados, ETF, comisiones y traspasos: cómo funcionan, cuánto cuestan y qué mirar antes de contratar uno.',
  },
  bolsa: {
    label: 'Bolsa y mercados',
    titulo: 'Bolsa y mercados',
    desc: 'El Ibex 35 y las bolsas, los tipos de interés, la inflación y las noticias de los mercados que afectan a tus ahorros.',
  },
  jubilacion: {
    label: 'Jubilación',
    titulo: 'Planes de pensiones y ahorro para la jubilación',
    desc: 'Planes de pensiones individuales y de empleo, límites de aportación, rescate y ahorro a largo plazo para complementar la pensión pública.',
  },
  impuestos: {
    label: 'Impuestos',
    titulo: 'Impuestos del ahorro y la inversión',
    desc: 'Cómo tributan intereses, dividendos y ganancias, compensación de pérdidas, retenciones y la declaración de la renta del inversor.',
  },
} as const;

export type CategoryKey = keyof typeof CATEGORIES;
