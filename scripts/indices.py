"""
Cierres diarios de los grandes índices del mundo, el oro y el petróleo para Dinero en Claro
(src/data/indices.json). El Ibex 35 sigue en mercados.py, con el dato oficial del Banco de España.

Fuente: la API pública de gráficos de Yahoo Finance (Stooq, que se probó primero, no responde desde GitHub).
Se descarta el cierre del día en curso hasta las 22:00 de Madrid, porque antes sería un precio a mitad de sesión.
El cambio euro-dólar sale del BCE, para dar también la rentabilidad en euros de lo que cotiza en dólares.

Para cada activo guarda: último cierre, variación del día, del año y de 12 meses, máximo y mínimo de
12 meses, rentabilidad anualizada a 3, 5 y 10 años (en su moneda y en euros), la rentabilidad de cada
año natural, la serie diaria del último año y la serie mensual de 10 años para los gráficos.

Uso: python scripts/indices.py            (descarga y guarda)
     python scripts/indices.py --probar   (solo prueba las fuentes y no guarda nada)
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "src" / "data" / "indices.json"
MADRID = ZoneInfo("Europe/Madrid")
UA = "Mozilla/5.0 (compatible; DineroEnClaro/1.0; +https://dineroenclaro.com)"
ECB_USD = "https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?startPeriod=2010-01-01&format=csvdata"

# moneda: la de la cotización. «yahoo»: símbolos en Yahoo Finance (se prueban en este orden).
ACTIVOS = [
    # El Ibex 35 tiene su página con el dato del Banco de España; aquí solo para el comparador (historia larga)
    {"id": "ibex", "nombre": "Ibex 35", "moneda": "EUR", "yahoo": ["^IBEX"]},
    {"id": "sp500", "nombre": "S&P 500", "moneda": "USD", "yahoo": ["^GSPC"]},
    {"id": "nasdaq100", "nombre": "Nasdaq 100", "moneda": "USD", "yahoo": ["^NDX"]},
    {"id": "eurostoxx50", "nombre": "Euro Stoxx 50", "moneda": "EUR", "yahoo": ["^STOXX50E"]},
    {"id": "dax", "nombre": "DAX 40", "moneda": "EUR", "yahoo": ["^GDAXI"]},
    # MSCI World y emergentes: el índice no se publica gratis; usamos el ETF más grande que lo replica, en euros
    {"id": "msciworld", "nombre": "MSCI World", "moneda": "EUR", "proxy": "iShares Core MSCI World UCITS ETF (EUNL, Xetra)", "yahoo": ["EUNL.DE"]},
    {"id": "emergentes", "nombre": "MSCI Emerging Markets", "moneda": "EUR", "proxy": "iShares Core MSCI EM IMI UCITS ETF (IS3N, Xetra)", "yahoo": ["IS3N.DE"]},
    {"id": "oro", "nombre": "Oro", "moneda": "USD", "unidad": "onza", "yahoo": ["GC=F"]},
    {"id": "brent", "nombre": "Petróleo Brent", "moneda": "USD", "unidad": "barril", "yahoo": ["BZ=F"]},
]


def aviso(tipo: str, texto: str) -> None:
    print(texto)
    if os.environ.get("GITHUB_ACTIONS"):
        print(f"::{tipo} title=Índices::{texto}")


def de_yahoo(simbolo: str) -> list[tuple[str, float]]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{requests.utils.quote(simbolo)}"
    for intento in range(3):
        r = requests.get(url, params={"range": "15y", "interval": "1d"}, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
        if r.status_code in (429, 500, 502, 503) and intento < 2:
            time.sleep(20)
            continue
        break
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    tz = res["meta"].get("exchangeTimezoneName") or "UTC"
    cierres = res["indicators"]["quote"][0]["close"]
    serie = []
    for t, c in zip(res["timestamp"], cierres):
        if c is not None:
            serie.append((datetime.fromtimestamp(t, ZoneInfo(tz)).date().isoformat(), float(c)))
    if len(serie) < 300:
        raise ValueError(f"solo {len(serie)} filas")
    return serie


def descargar(a: dict) -> tuple[list[tuple[str, float]], str]:
    errores = []
    hoy = datetime.now(MADRID)
    for fuente, func in (("Yahoo Finance", de_yahoo),):
        for s in a.get(fuente.split()[0].lower(), []):
            try:
                serie = func(s)
                if hoy.hour < 22:
                    serie = [x for x in serie if x[0] < hoy.date().isoformat()]
                # quita días repetidos (se queda con el último) y ordena
                return sorted(dict(serie).items()), f"{fuente} ({s})"
            except Exception as e:  # noqa: BLE001
                errores.append(f"{fuente} {s}: {type(e).__name__} {str(e)[:120]}")
            time.sleep(5)
    raise RuntimeError(" · ".join(errores))


def eurusd() -> dict[str, float]:
    r = requests.get(ECB_USD, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    return {f["TIME_PERIOD"]: float(f["OBS_VALUE"]) for f in csv.DictReader(io.StringIO(r.text)) if f.get("OBS_VALUE")}


def valor_en(serie: list[tuple[str, float]], dia: str) -> float | None:
    """Último cierre en o antes de un día (None si la serie no llega tan atrás)."""
    v = None
    for f, x in serie:
        if f > dia:
            break
        v = x
    return v


def en_euros(serie: list[tuple[str, float]], cambio: dict[str, float]) -> list[tuple[str, float]]:
    fechas = sorted(cambio)
    out, j, ultimo = [], 0, None
    for f, x in serie:
        while j < len(fechas) and fechas[j] <= f:
            ultimo = cambio[fechas[j]]
            j += 1
        if ultimo:
            out.append((f, x / ultimo))
    return out


def anualizada(serie: list[tuple[str, float]], anios: int) -> float | None:
    if not serie:
        return None
    d, v = serie[-1]
    antes = date.fromisoformat(d) - timedelta(days=round(365.25 * anios))
    if serie[0][0] > antes.isoformat():
        return None
    v0 = valor_en(serie, antes.isoformat())
    return round(((v / v0) ** (1 / anios) - 1) * 100, 2) if v0 else None


def por_anio(serie: list[tuple[str, float]]) -> dict[str, float]:
    out = {}
    if not serie:
        return out
    ultimo = int(serie[-1][0][:4])
    for a in range(int(serie[0][0][:4]) + 1, ultimo):
        v0, v1 = valor_en(serie, f"{a - 1}-12-31"), valor_en(serie, f"{a}-12-31")
        if v0 and v1:
            out[str(a)] = round((v1 / v0 - 1) * 100, 2)
    return out


def mensual(serie: list[tuple[str, float]], anios: int = 10) -> list[list]:
    desde = (date.fromisoformat(serie[-1][0]) - timedelta(days=365 * anios)).isoformat()
    meses: dict[str, tuple[str, float]] = {}
    for f, x in serie:
        if f >= desde:
            meses[f[:7]] = (f, x)
    return [[f, round(x, 2)] for f, x in meses.values()]


def resumen(serie: list[tuple[str, float]], serie_eur: list[tuple[str, float]] | None) -> dict:
    d, v = serie[-1]
    anio = int(d[:4])
    ultimo_anio = [x for f, x in serie if f > f"{anio - 1}{d[4:]}"]
    v_ini = valor_en(serie, f"{anio - 1}-12-31")
    v_12m = valor_en(serie, f"{anio - 1}{d[4:]}")
    out = {
        "fecha": d, "cierre": round(v, 2), "anterior": round(serie[-2][1], 2),
        "var_dia": round((v / serie[-2][1] - 1) * 100, 2),
        "var_anio": round((v / v_ini - 1) * 100, 2) if v_ini else None,
        "var_12m": round((v / v_12m - 1) * 100, 2) if v_12m else None,
        "max_12m": round(max(ultimo_anio), 2), "min_12m": round(min(ultimo_anio), 2),
        "anual": {str(n): anualizada(serie, n) for n in (3, 5, 10)},
        "por_anio": por_anio(serie),
        "historico": [[f, round(x, 2)] for f, x in serie if f > f"{anio - 1}{d[4:]}"],
        "mensual": mensual(serie),
    }
    if serie_eur:
        de, ve = serie_eur[-1]
        ve_ini = valor_en(serie_eur, f"{anio - 1}-12-31")
        ve_12m = valor_en(serie_eur, f"{anio - 1}{de[4:]}")
        out["eur"] = {
            "cierre": round(ve, 2),
            "var_anio": round((ve / ve_ini - 1) * 100, 2) if ve_ini else None,
            "var_12m": round((ve / ve_12m - 1) * 100, 2) if ve_12m else None,
            "anual": {str(n): anualizada(serie_eur, n) for n in (3, 5, 10)},
            "por_anio": por_anio(serie_eur),
        }
    return out


def main() -> int:
    probar = "--probar" in sys.argv
    try:
        cambio = eurusd()
        print(f"✓ BCE euro-dólar: {len(cambio)} días, último {max(cambio)}")
    except Exception as e:  # noqa: BLE001
        aviso("error", f"BCE euro-dólar: {type(e).__name__} {str(e)[:200]}")
        return 1

    anterior = {}
    if OUT.exists():
        try:
            anterior = json.loads(OUT.read_text(encoding="utf-8")).get("activos", {})
        except ValueError:
            pass

    activos, fallos = {}, []
    for a in ACTIVOS:
        try:
            serie, fuente = descargar(a)
        except Exception as e:  # noqa: BLE001
            fallos.append(a["nombre"])
            aviso("warning", f"{a['nombre']}: sin datos. {e}")
            if a["id"] in anterior:
                activos[a["id"]] = anterior[a["id"]]  # se mantiene el último dato bueno
            continue
        serie_eur = en_euros(serie, cambio) if a["moneda"] == "USD" else None
        r = resumen(serie, serie_eur)
        r.update({k: a[k] for k in ("nombre", "moneda", "unidad", "proxy") if k in a})
        r["fuente"] = fuente
        activos[a["id"]] = r
        linea = f"✓ {a['nombre']}: {r['cierre']} ({r['fecha']}) · {fuente} · desde {serie[0][0]} · 10 años: {r['anual']['10']} %"
        if probar:
            aviso("notice", linea)
        else:
            print(linea)
        time.sleep(1)

    if probar:
        print(f"Prueba terminada: {len(activos) - len(fallos)} de {len(ACTIVOS)} activos con datos")
        return 1 if len(fallos) == len(ACTIVOS) else 0
    if not activos:
        aviso("error", "Ninguna fuente ha respondido")
        return 1
    salida = {
        "actualizado": datetime.now(MADRID).replace(microsecond=0).isoformat(),
        "eurusd": {"fecha": max(cambio), "valor": cambio[max(cambio)]},
        "activos": activos,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(salida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    aviso("notice", f"{len(activos)} activos guardados" + (f"; sin datos nuevos: {', '.join(fallos)}" if fallos else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
