import fs from 'node:fs';

export interface DatosEuribor {
  fuente: string; actualizado: string; fecha: string; valor: number;
  mes: string; media_mes: number; dias_mes: number;
  mes_anterior: { mes: string; media: number };
  hace_un_anio: { mes: string; media: number | null };
  medias_mensuales: Record<string, number>;
  diarios: Record<string, number>;
}

/** Datos guardados por scripts/euribor.py (null si aún no se han descargado). */
export function datosEuribor(): DatosEuribor | null {
  try { return JSON.parse(fs.readFileSync('src/data/euribor.json', 'utf8')); } catch { return null; }
}

export const pct = (v?: number | null, d = 3) => (v == null ? '—' : v.toLocaleString('es-ES', { minimumFractionDigits: d, maximumFractionDigits: d }));

const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
/** "2026-10" -> "octubre de 2026" */
export const nombreMes = (m: string, conAnio = true) => `${MESES[parseInt(m.slice(5, 7), 10) - 1]}${conAnio ? ` de ${m.slice(0, 4)}` : ''}`;
/** "2026-10-15" -> "15 de octubre" */
export const diaMes = (d: string) => `${parseInt(d.slice(8, 10), 10)} de ${MESES[parseInt(d.slice(5, 7), 10) - 1]}`;

/** Cuota mensual de un préstamo francés. */
export function cuota(capital: number, tipoAnual: number, meses: number): number {
  const i = tipoAnual / 100 / 12;
  if (meses <= 0) return 0;
  if (Math.abs(i) < 1e-9) return capital / meses;
  return (capital * i) / (1 - Math.pow(1 + i, -meses));
}
