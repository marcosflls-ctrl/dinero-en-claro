/**
 * Fiscalidad de 2026 para las calculadoras (territorio común).
 * - Base del ahorro (intereses, dividendos, ganancias): escala estatal + autonómica, igual en todas las comunidades
 *   (art. 66 y 76 de la Ley del IRPF, con el tramo del 30 % por encima de 300.000 € de la Ley 7/2024).
 * - Base general: escala combinada de referencia (la que usa Hacienda para las retenciones); la parte autonómica
 *   cambia algo en cada comunidad, así que el resultado es aproximado.
 */
export const ESCALA_AHORRO: [number, number][] = [[6000, 19], [50000, 21], [200000, 23], [300000, 27], [Infinity, 30]];
export const ESCALA_GENERAL: [number, number][] = [[12450, 19], [20200, 24], [35200, 30], [60000, 37], [300000, 45], [Infinity, 47]];
export const RETENCION_AHORRO = 19;
export const LIMITE_PLAN_INDIVIDUAL = 1500;
export const LIMITE_PLAN_EMPLEO = 8500; // aportaciones a planes de empleo de empresa, además de las 1.500 individuales (máximo 10.000 €)
export const LIMITE_PLAN_AUTONOMO = 4250; // autónomos en planes de empleo simplificados, además de las 1.500 (máximo 5.750 €)

export function cuota(base: number, escala: [number, number][]) {
  let resto = Math.max(0, base), desde = 0, total = 0;
  const tramos: { desde: number; hasta: number; tipo: number; base: number; cuota: number }[] = [];
  for (const [hasta, tipo] of escala) {
    if (resto <= 0) break;
    const b = Math.min(resto, hasta - desde);
    tramos.push({ desde, hasta, tipo, base: b, cuota: b * tipo / 100 });
    total += b * tipo / 100;
    resto -= b;
    desde = hasta;
  }
  return { total, tramos, medio: base > 0 ? total / base * 100 : 0 };
}

export function marginal(base: number, escala: [number, number][]) {
  for (const [hasta, tipo] of escala) if (base <= hasta) return tipo;
  return escala[escala.length - 1][1];
}
