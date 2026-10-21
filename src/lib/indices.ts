import fs from 'node:fs';

export interface Rent { [periodo: string]: number | null }
export interface Activo {
  nombre: string; moneda: 'USD' | 'EUR'; unidad?: string; proxy?: string; fuente: string;
  fecha: string; cierre: number; anterior: number; var_dia: number; var_anio: number | null; var_12m: number | null;
  max_12m: number; min_12m: number; anual: Rent; por_anio: Record<string, number>;
  historico: [string, number][]; mensual: [string, number][];
  eur?: { cierre: number; var_anio: number | null; var_12m: number | null; anual: Rent; por_anio: Record<string, number>; mensual?: [string, number][] };
}
export interface DatosIndices { actualizado: string; eurusd: { fecha: string; valor: number }; activos: Record<string, Activo> }

/** Datos de scripts/indices.py (null si aún no se han descargado). */
export function datosIndices(): DatosIndices | null {
  try { return JSON.parse(fs.readFileSync('src/data/indices.json', 'utf8')); } catch { return null; }
}
