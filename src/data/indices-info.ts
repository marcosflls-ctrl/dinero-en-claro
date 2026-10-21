// Textos de las páginas «hoy» de cada índice, del oro y del petróleo (src/pages/bolsa/[pagina].astro).
// Los datos los descarga scripts/indices.py en src/data/indices.json.
// «dividendos»: si el dato ya incluye los dividendos reinvertidos (importa para comparar rentabilidades).

export interface InfoActivo {
  id: string;            // clave en indices.json
  slug: string;          // dirección: /bolsa/<slug>/
  h1: string;
  titulo: string;        // <title>
  corto: string;         // nombre en tablas y enlaces
  unidad: string;        // «puntos», «€ por participación», «$ por onza»...
  dec: number;
  dividendos: 'no' | 'si' | 'na';
  fondos?: string;       // clave de índice en fondos.json para enlazar fichas
  guia?: { href: string; texto: string };
  que: string[];         // párrafos de «Qué es»
  claves: string[];      // lista de cosas a saber
  invertir: string[];    // párrafos de «Cómo invertir»
}

export const INFO: InfoActivo[] = [
  {
    id: 'sp500', slug: 'sp-500-hoy', h1: 'S&P 500 hoy', corto: 'S&P 500',
    titulo: 'S&P 500 hoy: cierre, rentabilidad en euros y evolución', unidad: 'puntos', dec: 2, dividendos: 'no', fondos: 'sp-500',
    guia: { href: '/bolsa/msci-world-y-sp-500-que-son/', texto: 'MSCI World y S&P 500: qué son y en qué se diferencian' },
    que: [
      'El S&P 500 reúne a las 500 mayores empresas cotizadas de Estados Unidos y es la referencia de la bolsa mundial. Cada empresa pesa según lo que vale en bolsa, así que las grandes tecnológicas tienen mucho peso.',
      'Lo calcula S&P Dow Jones Indices. Es un índice de precios: no incluye los dividendos, que añaden algo más del 1 % al año a quien invierte en él.',
    ],
    claves: [
      'Cotiza en dólares. Si el dólar baja frente al euro, un inversor español gana menos de lo que dice el índice; si sube, gana más. Por eso damos también la rentabilidad en euros.',
      'Unas pocas empresas muy grandes explican buena parte de lo que sube o baja.',
      'Ha tenido caídas fuertes, como el −19 % de 2022 o casi un −40 % en 2008, y ha tardado años en recuperarse de algunas.',
    ],
    invertir: [
      'La forma más sencilla es un fondo indexado o un ETF que lo replique, con comisiones bajas. Los fondos se pueden traspasar sin pagar impuestos; los ETF no, pero se compran como una acción.',
    ],
  },
  {
    id: 'nasdaq100', slug: 'nasdaq-100-hoy', h1: 'Nasdaq 100 hoy', corto: 'Nasdaq 100',
    titulo: 'Nasdaq 100 hoy: cierre, rentabilidad en euros y evolución', unidad: 'puntos', dec: 2, dividendos: 'no', fondos: 'nasdaq-100',
    que: [
      'El Nasdaq 100 agrupa a las 100 mayores empresas que cotizan en el mercado Nasdaq de Estados Unidos, sin contar los bancos y otras financieras. Está dominado por las grandes tecnológicas.',
      'Es un índice de precios, sin dividendos, y cotiza en dólares.',
    ],
    claves: [
      'Sube más que el S&P 500 en los años buenos y cae más en los malos: en 2022 perdió alrededor de un 33 %.',
      'Está muy concentrado en un solo sector y en unas pocas empresas, así que diversifica menos que un índice mundial.',
      'Como cotiza en dólares, el tipo de cambio también afecta a lo que ganas en euros.',
    ],
    invertir: [
      'Se invierte sobre todo con ETF que lo replican. Por su concentración, suele usarse como complemento de un índice amplio, no como única inversión.',
    ],
  },
  {
    id: 'eurostoxx50', slug: 'euro-stoxx-50-hoy', h1: 'Euro Stoxx 50 hoy', corto: 'Euro Stoxx 50',
    titulo: 'Euro Stoxx 50 hoy: cierre, rentabilidad del año y evolución', unidad: 'puntos', dec: 2, dividendos: 'no',
    que: [
      'El Euro Stoxx 50 reúne a 50 de las mayores empresas de los países del euro. Incluye varias españolas, como Iberdrola, Santander o Inditex, junto a grandes compañías francesas, alemanas, italianas y holandesas.',
      'Es un índice de precios: no incluye los dividendos, que en Europa son altos, en torno al 3 % anual.',
    ],
    claves: [
      'Cotiza en euros, así que no tiene riesgo de divisa para un inversor español.',
      'Está más cargado de bancos, energía e industria que los índices estadounidenses, y menos de tecnología.',
      'No incluye el Reino Unido ni Suiza, que no usan el euro; para toda Europa se usan índices como el MSCI Europe.',
    ],
    invertir: [
      'Hay fondos indexados y ETF que lo replican. Si buscas toda Europa, los fondos que siguen al MSCI Europe incluyen más países y empresas.',
    ],
  },
  {
    id: 'dax', slug: 'dax-hoy', h1: 'DAX hoy', corto: 'DAX 40',
    titulo: 'DAX hoy: cierre de la bolsa alemana y evolución', unidad: 'puntos', dec: 2, dividendos: 'si',
    que: [
      'El DAX es el índice de la bolsa de Fráncfort y reúne a las 40 mayores empresas alemanas, desde fabricantes de coches hasta grandes industriales, químicas y aseguradoras.',
      'A diferencia de casi todos los demás índices, el DAX es un índice de rentabilidad total: sus puntos ya incluyen los dividendos reinvertidos. Por eso no se puede comparar directamente con el Ibex o el Euro Stoxx 50, que no los incluyen.',
    ],
    claves: [
      'Cotiza en euros, sin riesgo de divisa para un inversor español.',
      'Muchas de sus empresas venden sobre todo fuera de Alemania, así que depende mucho de la economía mundial y del comercio.',
    ],
    invertir: [
      'Se invierte sobre todo con ETF que lo replican. Al ser un solo país, suele usarse como complemento.',
    ],
  },
  {
    id: 'msciworld', slug: 'msci-world-hoy', h1: 'MSCI World hoy', corto: 'MSCI World',
    titulo: 'MSCI World hoy: evolución y rentabilidad en euros', unidad: '€ por participación del ETF', dec: 2, dividendos: 'si', fondos: 'msci-world',
    guia: { href: '/bolsa/msci-world-y-sp-500-que-son/', texto: 'MSCI World y S&P 500: qué son y en qué se diferencian' },
    que: [
      'El MSCI World reúne a unas 1.300 empresas grandes y medianas de 23 países desarrollados. Estados Unidos pesa más de dos tercios; detrás van Japón, Reino Unido y los grandes países de Europa. Es el índice que más usan los fondos indexados para invertir «en todo el mundo».',
      'MSCI no publica gratis el valor del índice, así que mostramos el precio en euros del ETF más grande que lo replica, el iShares Core MSCI World. Es un ETF de acumulación: su precio ya incluye los dividendos reinvertidos y descuenta sus gastos (0,20 % al año).',
    ],
    claves: [
      'Al estar en euros, el dato ya recoge el efecto del dólar y las demás monedas: es lo que habría ganado un inversor español.',
      'Diversifica más que el S&P 500, pero sigue muy concentrado en Estados Unidos y en las grandes tecnológicas.',
      'No incluye países emergentes como China, India o Brasil.',
    ],
    invertir: [
      'Hay fondos indexados y ETF de varias gestoras que lo replican con comisiones muy bajas. Es una de las opciones más habituales como base de una cartera a largo plazo.',
    ],
  },
  {
    id: 'emergentes', slug: 'mercados-emergentes-hoy', h1: 'Mercados emergentes hoy', corto: 'Emergentes',
    titulo: 'Mercados emergentes hoy: MSCI Emerging Markets en euros', unidad: '€ por participación del ETF', dec: 2, dividendos: 'si', fondos: 'msci-em',
    que: [
      'Los índices de mercados emergentes reúnen a empresas de países como China, India, Taiwán, Corea del Sur o Brasil. El más usado es el MSCI Emerging Markets.',
      'Como el valor del índice no se publica gratis, mostramos el precio en euros del iShares Core MSCI EM IMI, uno de los ETF más grandes de emergentes, que incluye también empresas pequeñas. Es de acumulación: su precio incluye los dividendos reinvertidos y descuenta sus gastos.',
    ],
    claves: [
      'Suben y bajan más que las bolsas de los países desarrollados, y les afectan mucho la política y las divisas locales.',
      'China, India y Taiwán suman más de la mitad del índice.',
      'En los últimos diez años han ganado bastante menos que el MSCI World, aunque hay periodos en los que lo han hecho mejor.',
    ],
    invertir: [
      'Se suelen usar como complemento de un fondo del MSCI World, con un peso pequeño, para tener todo el mundo. Otra opción son los fondos que siguen índices globales con emergentes, como el FTSE All-World.',
    ],
  },
  {
    id: 'oro', slug: 'precio-oro-hoy', h1: 'Precio del oro hoy', corto: 'Oro',
    titulo: 'Precio del oro hoy: onza en dólares y en euros, y gramo', unidad: '$ por onza', dec: 2, dividendos: 'na',
    que: [
      'El oro se cotiza en dólares por onza troy, que son 31,1 gramos. Mostramos el precio de referencia del contrato de futuros de oro de Nueva York, el más negociado del mundo, y su equivalencia en euros.',
      'El precio que pagas al comprar oro físico, en lingotes o monedas, es algo más alto: las tiendas y los bancos cobran un margen sobre este precio.',
    ],
    claves: [
      'El oro no da intereses ni dividendos: solo ganas si sube su precio.',
      'Suele subir en épocas de crisis o de inflación alta, pero también ha pasado años enteros bajando.',
      'El oro de inversión no paga IVA en España. Lo que ganes al venderlo tributa en la base del ahorro del IRPF, del 19 % al 30 %.',
    ],
    invertir: [
      'Se puede comprar físico, en lingotes o monedas de inversión, o invertir a través de ETC que siguen su precio, que se compran como una acción. Los fondos de empresas mineras de oro no siguen exactamente al metal: se mueven mucho más.',
    ],
  },
  {
    id: 'brent', slug: 'precio-petroleo-brent-hoy', h1: 'Precio del petróleo Brent hoy', corto: 'Petróleo Brent',
    titulo: 'Precio del petróleo Brent hoy: barril en dólares y en euros', unidad: '$ por barril', dec: 2, dividendos: 'na',
    que: [
      'El Brent es el petróleo de referencia en Europa. Se cotiza en dólares por barril, que son 159 litros. Mostramos el precio del contrato de futuros más cercano, el que se usa como referencia diaria.',
    ],
    claves: [
      'Su precio se nota en la gasolina y el diésel con unas semanas de retraso, pero no en la misma proporción: los impuestos y otros costes pesan mucho en el precio del surtidor.',
      'Lo mueven la producción de la OPEP+, la demanda mundial y los conflictos en las zonas productoras.',
      'Como se paga en dólares, un euro fuerte abarata el petróleo para Europa.',
    ],
    invertir: [
      'Invertir en petróleo directamente se hace con productos complejos, como futuros o ETC que se renuevan cada mes y pueden ganar menos que el precio del barril. Para la mayoría de ahorradores no es una inversión adecuada a largo plazo.',
    ],
  },
];
