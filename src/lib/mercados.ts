import fs from 'node:fs';

export interface Letra { fecha: string; tipo: number; anterior: { fecha: string; tipo: number } | null; historico: { fecha: string; tipo: number }[] }
export interface Indice { fecha: string; cierre: number; anterior: number; var_dia: number; var_anio: number | null; var_12m: number | null; max_12m: number; min_12m: number; historico: [string, number][] }
export interface Mercados {
  actualizado: string;
  bce: Record<'deposito' | 'principal' | 'marginal', { valor: number; desde: string; cambios: { fecha: string; valor: number }[] }>;
  letras: Record<'3' | '6' | '9' | '12', Letra>;
  secundario: Record<'letra_1a' | 'bono_3a' | 'bono_5a' | 'bono_10a', { fecha: string; valor: number; historico: [string, number][] }>;
  bolsa: Record<'ibex' | 'igbm', Indice>;
}

/** Datos de scripts/mercados.py (null si aún no se han descargado). */
export function datosMercados(): Mercados | null {
  try { return JSON.parse(fs.readFileSync('src/data/mercados.json', 'utf8')); } catch { return null; }
}

const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
export const fecha = (iso: string, anio = true) => {
  const [a, m, d] = iso.split('-').map(Number);
  return `${d} de ${MESES[m - 1]}${anio ? ` de ${a}` : ''}`;
};
export const num = (n: number, dec = 2) => n.toLocaleString('es-ES', { minimumFractionDigits: dec, maximumFractionDigits: dec, useGrouping: 'always' } as any);
export const pct = (n: number, dec = 2) => `${num(n, dec)} %`;
export const signo = (n: number, dec = 2) => `${n > 0 ? '+' : n < 0 ? '−' : ''}${num(Math.abs(n), dec)}`;

/** Precio de una Letra de 1.000 € y lo que se gana, a partir del tipo de interés (base actual/360). */
export function letra(tipo: number, dias: number, nominal = 1000) {
  const precio = nominal / (1 + (tipo / 100) * dias / 360);
  return { precio, ganancia: nominal - precio };
}
export const DIAS_PLAZO: Record<string, number> = { '3': 91, '6': 182, '9': 273, '12': 364 };
