/** Gráfico de líneas sencillo en SVG (se dibuja al compilar la web, sin JavaScript). */
export function lineas(series: { nombre: string; puntos: [string, number][]; color: string }[], opts: { ancho?: number; alto?: number; dec?: number; sufijo?: string } = {}) {
  const W = opts.ancho ?? 720, H = opts.alto ?? 260, m = { t: 16, r: 16, b: 28, l: 52 };
  const todos = series.flatMap((s) => s.puntos);
  if (!todos.length) return '';
  const fechas = [...new Set(todos.map((p) => p[0]))].sort();
  const t0 = Date.parse(fechas[0]), t1 = Date.parse(fechas[fechas.length - 1]) || t0 + 1;
  let vmin = Math.min(...todos.map((p) => p[1])), vmax = Math.max(...todos.map((p) => p[1]));
  const pad = (vmax - vmin) * 0.1 || 1; vmin -= pad; vmax += pad;
  const x = (f: string) => m.l + ((Date.parse(f) - t0) / (t1 - t0 || 1)) * (W - m.l - m.r);
  const y = (v: number) => m.t + (1 - (v - vmin) / (vmax - vmin)) * (H - m.t - m.b);
  const dec = opts.dec ?? 2, suf = opts.sufijo ?? '';
  const fmt = (v: number) => v.toLocaleString('es-ES', { minimumFractionDigits: dec, maximumFractionDigits: dec, useGrouping: 'always' } as any) + suf;
  const ticks = Array.from({ length: 5 }, (_, i) => vmin + (i * (vmax - vmin)) / 4);
  const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
  const etqX = [fechas[0], fechas[Math.floor(fechas.length / 2)], fechas[fechas.length - 1]];
  const lab = (f: string) => { const [a, mm] = f.split('-'); return `${MESES[+mm - 1]} ${a.slice(2)}`; };
  let svg = `<svg viewBox="0 0 ${W} ${H}" class="grafico" role="img">`;
  for (const t of ticks) svg += `<line x1="${m.l}" x2="${W - m.r}" y1="${y(t)}" y2="${y(t)}" stroke="var(--rule)"/><text x="${m.l - 6}" y="${y(t) + 4}" text-anchor="end" font-size="11" fill="var(--muted)">${fmt(t)}</text>`;
  for (const f of etqX) svg += `<text x="${x(f)}" y="${H - 8}" text-anchor="middle" font-size="11" fill="var(--muted)">${lab(f)}</text>`;
  for (const s of series) {
    const d = s.puntos.map((p, i) => `${i ? 'L' : 'M'}${x(p[0]).toFixed(1)},${y(p[1]).toFixed(1)}`).join('');
    svg += `<path d="${d}" fill="none" stroke="${s.color}" stroke-width="2"/>`;
  }
  return svg + '</svg>';
}
