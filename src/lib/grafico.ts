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

/** Gráfico de barras sencillo en SVG para valores positivos y negativos (por ejemplo, rentabilidad de cada año). */
export function barras(datos: [string, number][], opts: { ancho?: number; alto?: number; sufijo?: string } = {}) {
  if (!datos.length) return '';
  const W = opts.ancho ?? 720, H = opts.alto ?? 260, m = { t: 22, r: 12, b: 46, l: 12 };
  const suf = opts.sufijo ?? ' %';
  const vmax = Math.max(0, ...datos.map((d) => d[1])), vmin = Math.min(0, ...datos.map((d) => d[1]));
  const rango = vmax - vmin || 1;
  const y = (v: number) => m.t + ((vmax - v) / rango) * (H - m.t - m.b);
  const paso = (W - m.l - m.r) / datos.length, ancho = Math.min(paso * 0.6, 90), fs = W < 500 ? 13 : 12;
  const fmt = (v: number) => (v > 0 ? '+' : '') + v.toLocaleString('es-ES', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + suf;
  let svg = `<svg viewBox="0 0 ${W} ${H}" class="grafico" role="img">`;
  svg += `<line x1="${m.l}" x2="${W - m.r}" y1="${y(0)}" y2="${y(0)}" stroke="var(--ink)"/>`;
  datos.forEach(([etq, v], i) => {
    const cx = m.l + paso * i + paso / 2, x = cx - ancho / 2;
    const top = Math.min(y(v), y(0)), alto = Math.abs(y(v) - y(0));
    const color = v >= 0 ? 'var(--brand)' : '#b4442c';
    svg += `<rect x="${x.toFixed(1)}" y="${top.toFixed(1)}" width="${ancho.toFixed(1)}" height="${Math.max(alto, 1).toFixed(1)}" fill="${color}"/>`;
    const ty = v >= 0 ? top - 6 : top + alto + 14;
    svg += `<text x="${cx.toFixed(1)}" y="${ty.toFixed(1)}" text-anchor="middle" font-size="${fs}" fill="var(--ink)">${fmt(v)}</text>`;
    svg += `<text x="${cx.toFixed(1)}" y="${H - 6}" text-anchor="middle" font-size="${fs}" fill="var(--muted)">${etq}</text>`;
  });
  return svg + '</svg>';
}
