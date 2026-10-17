"""
Euríbor a 12 meses diario, del Banco de España (tabla TI_1_7, serie D_DNBAF172).
Guarda en src/data/euribor.json el último dato, la media del mes en curso, las medias mensuales
y los últimos 400 días. La media mensual de los datos diarios es el «euríbor hipotecario» que
publica después el Banco de España.

Uso: python scripts/euribor.py
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "src" / "data" / "euribor.json"
URL = "https://www.bde.es/webbe/es/estadisticas/compartido/datos/csv/ti_1_7.csv"
SERIE = "D_DNBAF172"
UA = "Mozilla/5.0 (compatible; DineroEnClaro/1.0; +https://dineroenclaro.com)"
MESES = {"ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6, "JUL": 7, "AGO": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DIC": 12}


def fecha(t: str) -> date | None:
    p = t.strip().split()
    if len(p) != 3 or p[1].upper() not in MESES:
        return None
    try:
        return date(int(p[2]), MESES[p[1].upper()], int(p[0]))
    except ValueError:
        return None


def aviso(tipo: str, texto: str) -> None:
    print(texto)
    if os.environ.get("GITHUB_ACTIONS"):
        print(f"::{tipo} title=Euríbor::{texto}")


def main() -> int:
    try:
        r = requests.get(URL, headers={"User-Agent": UA}, timeout=90)
        r.raise_for_status()
    except Exception as e:  # noqa: BLE001
        aviso("error", f"{type(e).__name__}: {str(e)[:300]}")
        return 1
    filas = list(csv.reader(io.StringIO(r.content.decode("latin-1"))))
    try:
        col = filas[0].index(SERIE)
    except ValueError:
        aviso("error", f"No está la serie {SERIE} en la cabecera")
        return 1
    diarios: dict[str, float] = {}
    for f in filas:
        if len(f) <= col or not (d := fecha(f[0])):
            continue
        try:
            v = float(f[col].replace(",", "."))
        except ValueError:
            continue  # "_" = sin dato
        if -2 < v < 15:
            diarios[d.isoformat()] = v
    if len(diarios) < 200:
        aviso("error", f"Solo {len(diarios)} datos diarios: no se cambia nada")
        return 1

    meses: dict[str, list[float]] = {}
    for d, v in diarios.items():
        meses.setdefault(d[:7], []).append(v)
    medias = {m: round(sum(v) / len(v), 3) for m, v in sorted(meses.items())}
    ultimo = max(diarios)
    mes = ultimo[:7]
    anio_antes = f"{int(mes[:4]) - 1}{mes[4:]}"
    mes_ant = sorted(m for m in medias if m < mes)[-1]
    salida = {
        "fuente": "Banco de España (serie TI_1_7.7, euríbor a 12 meses, dato diario de EMMI)",
        "actualizado": datetime.now(ZoneInfo("Europe/Madrid")).replace(microsecond=0).isoformat(),
        "fecha": ultimo,
        "valor": diarios[ultimo],
        "mes": mes,
        "media_mes": medias[mes],
        "dias_mes": len(meses[mes]),
        "mes_anterior": {"mes": mes_ant, "media": medias[mes_ant]},
        "hace_un_anio": {"mes": anio_antes, "media": medias.get(anio_antes)},
        "medias_mensuales": dict(list(medias.items())[-36:]),
        "diarios": dict(sorted(diarios.items())[-400:]),
    }
    OUT.write_text(json.dumps(salida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    aviso("notice", f"{ultimo}: {diarios[ultimo]} % · media de {mes}: {medias[mes]} % ({len(meses[mes])} días) · {mes_ant}: {medias[mes_ant]} %")
    return 0


if __name__ == "__main__":
    sys.exit(main())
