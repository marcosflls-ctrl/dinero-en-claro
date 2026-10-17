"""
Datos de mercado oficiales para Dinero en Claro (src/data/mercados.json):

- Tipos del BCE: facilidad de depósito, operaciones principales y facilidad marginal (API del BCE).
- Letras del Tesoro: tipo marginal de cada subasta a 3, 6, 9 y 12 meses (Banco de España, tabla ti_1_4).
- Deuda en el mercado secundario: Letras a 1 año y bonos a 3, 5 y 10 años (Banco de España, ti_1_3).
- Bolsa: Ibex 35 e Índice General de la Bolsa de Madrid, cierre diario (Banco de España, ti_1_6).

Uso: python scripts/mercados.py
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "src" / "data" / "mercados.json"
MADRID = ZoneInfo("Europe/Madrid")
UA = "Mozilla/5.0 (compatible; DineroEnClaro/1.0; +https://dineroenclaro.com)"
BDE = "https://www.bde.es/webbe/es/estadisticas/compartido/datos/csv/{}.csv"
ECB = "https://data-api.ecb.europa.eu/service/data/FM/D.U2.EUR.4F.KR.{}.LEV?startPeriod=2019-01-01&format=csvdata"
MESES = {"ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6, "JUL": 7, "AGO": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DIC": 12}

LETRAS = {"3": "D_DTED0C0G", "6": "D_DTED0E0G", "9": "D_DTED0I0G", "12": "D_DTED0G0G"}
SECUNDARIO = {"letra_1a": "D_DTES00U7", "bono_3a": "D_G0B1F0ZN", "bono_5a": "D_G0B1F0ZO", "bono_10a": "D_G0B1F0ZP"}
BOLSA = {"ibex": "DBLEESI100000000IBDI.B", "igbm": "DBLEESI500000000IBDI.B"}
BCE = {"deposito": "DFR", "principal": "MRR_FR", "marginal": "MLFR"}


def fecha_bde(t: str) -> date | None:
    try:
        d, m, a = t.strip().split()
        return date(int(a), MESES[m.upper()[:3]], int(d))
    except Exception:  # noqa: BLE001
        return None


def tabla_bde(nombre: str, codigos: dict[str, str]) -> dict[str, list[tuple[str, float]]]:
    r = requests.get(BDE.format(nombre), headers={"User-Agent": UA}, timeout=90)
    r.raise_for_status()
    r.encoding = "latin-1"
    filas = list(csv.reader(io.StringIO(r.text)))
    cab = filas[0]
    salida = {}
    for clave, cod in codigos.items():
        j = cab.index(cod)
        serie = []
        for f in filas:
            d = fecha_bde(f[0]) if f else None
            if d and j < len(f) and f[j] not in ("", "_"):
                try:
                    serie.append((d.isoformat(), float(f[j])))
                except ValueError:
                    pass
        salida[clave] = serie
    return salida


def serie_bce(clave: str) -> list[tuple[str, float]]:
    r = requests.get(ECB.format(clave), headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    filas = list(csv.DictReader(io.StringIO(r.text)))
    return [(f["TIME_PERIOD"], float(f["OBS_VALUE"])) for f in filas if f.get("OBS_VALUE")]


def cambios(serie: list[tuple[str, float]]) -> list[dict]:
    """Fechas en que cambia el tipo (el BCE publica el valor todos los días)."""
    out, prev = [], None
    for d, v in serie:
        if v != prev:
            out.append({"fecha": d, "valor": v})
            prev = v
    return out


def valor_en(serie: list[tuple[str, float]], dia: str) -> float | None:
    """Último valor en o antes de una fecha."""
    previos = [v for d, v in serie if d <= dia]
    return previos[-1] if previos else None


def main() -> int:
    try:
        letras = tabla_bde("ti_1_4", LETRAS)
        secundario = tabla_bde("ti_1_3", SECUNDARIO)
        bolsa = tabla_bde("ti_1_6", BOLSA)
        bce = {k: serie_bce(v) for k, v in BCE.items()}
    except Exception as e:  # noqa: BLE001
        aviso = f"{type(e).__name__}: {str(e)[:300]}"
        print(f"! {aviso}")
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"::error title=Mercados::{aviso}")
        return 1

    salida: dict = {"fuente": "Banco Central Europeo y Banco de España", "actualizado": datetime.now(MADRID).replace(microsecond=0).isoformat()}

    salida["bce"] = {k: {"valor": s[-1][1], "desde": cambios(s)[-1]["fecha"], "cambios": cambios(s)[-12:]} for k, s in bce.items() if s}

    salida["letras"] = {}
    for plazo, s in letras.items():
        if not s:
            continue
        salida["letras"][plazo] = {
            "fecha": s[-1][0], "tipo": s[-1][1],
            "anterior": {"fecha": s[-2][0], "tipo": s[-2][1]} if len(s) > 1 else None,
            "historico": [{"fecha": d, "tipo": v} for d, v in s[-24:]],
        }

    salida["secundario"] = {k: {"fecha": s[-1][0], "valor": s[-1][1], "historico": [[d, v] for d, v in s[-300:]]} for k, s in secundario.items() if s}

    salida["bolsa"] = {}
    for k, s in bolsa.items():
        if len(s) < 2:
            continue
        d, v = s[-1]
        inicio_anio = valor_en(s, f"{int(d[:4]) - 1}-12-31")
        hace_un_anio = valor_en(s, f"{int(d[:4]) - 1}{d[4:]}")
        ultimo_anio = [x for f, x in s if f > f"{int(d[:4]) - 1}{d[4:]}"]
        salida["bolsa"][k] = {
            "fecha": d, "cierre": v, "anterior": s[-2][1],
            "var_dia": round((v / s[-2][1] - 1) * 100, 2),
            "var_anio": round((v / inicio_anio - 1) * 100, 2) if inicio_anio else None,
            "var_12m": round((v / hace_un_anio - 1) * 100, 2) if hace_un_anio else None,
            "max_12m": max(ultimo_anio), "min_12m": min(ultimo_anio),
            "historico": [[f, x] for f, x in s[-300:]],
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(salida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    l12 = salida["letras"].get("12", {})
    ib = salida["bolsa"].get("ibex", {})
    resumen = (f"BCE depósito {salida['bce'].get('deposito', {}).get('valor')} % · Letras 12m {l12.get('tipo')} % ({l12.get('fecha')}) · "
               f"Bono 10a {salida['secundario'].get('bono_10a', {}).get('valor')} % · Ibex {ib.get('cierre')} ({ib.get('fecha')})")
    print("✓", resumen)
    if os.environ.get("GITHUB_ACTIONS"):
        print(f"::notice title=Mercados::{resumen}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
