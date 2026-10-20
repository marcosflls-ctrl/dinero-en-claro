"""
Precio de las principales criptomonedas en euros, de la API pública y gratuita de CoinGecko
(https://www.coingecko.com/en/api), que no necesita clave para este uso.

Guarda en src/data/cripto.json el precio, la capitalización, la variación en 24 horas, 7 días,
30 días y un año, el máximo histórico de cada moneda, y la serie diaria del último año de
bitcoin y ether para los gráficos.

Uso: python scripts/cripto.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "src" / "data" / "cripto.json"
API = "https://api.coingecko.com/api/v3"
UA = "Mozilla/5.0 (compatible; DineroEnClaro/1.0; +https://dineroenclaro.com)"

# Monedas que mostramos, en este orden (identificador de CoinGecko). Sin stablecoins: su precio es fijo.
MONEDAS = ["bitcoin", "ethereum", "ripple", "binancecoin", "solana", "cardano", "dogecoin"]
CON_GRAFICO = ["bitcoin", "ethereum"]


def aviso(tipo: str, texto: str) -> None:
    print(texto)
    if os.environ.get("GITHUB_ACTIONS"):
        print(f"::{tipo} title=Cripto::{texto}")


def pedir(ruta: str, params: dict) -> object:
    # La API gratuita limita las peticiones por minuto: si responde 429, espera y reintenta.
    for intento in range(4):
        r = requests.get(f"{API}{ruta}", params=params, headers={"User-Agent": UA, "Accept": "application/json"}, timeout=60)
        if r.status_code == 429 and intento < 3:
            time.sleep(30)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("demasiadas peticiones")


def main() -> int:
    try:
        mercado = pedir("/coins/markets", {
            "vs_currency": "eur",
            "ids": ",".join(MONEDAS),
            "price_change_percentage": "24h,7d,30d,1y",
        })
        series = {}
        for m in CON_GRAFICO:
            time.sleep(3)
            d = pedir(f"/coins/{m}/market_chart", {"vs_currency": "eur", "days": "365", "interval": "daily"})
            series[m] = {
                datetime.fromtimestamp(t / 1000, tz=timezone.utc).date().isoformat(): round(v, 2)
                for t, v in d.get("prices", [])
            }
    except Exception as e:  # noqa: BLE001
        aviso("error", f"{type(e).__name__}: {str(e)[:300]}")
        return 1

    por_id = {c["id"]: c for c in mercado if isinstance(c, dict)}
    monedas = []
    for m in MONEDAS:
        c = por_id.get(m)
        if not c or c.get("current_price") is None:
            continue
        monedas.append({
            "id": m,
            "simbolo": (c.get("symbol") or "").upper(),
            "nombre": c.get("name"),
            "precio": c["current_price"],
            "capitalizacion": c.get("market_cap"),
            "puesto": c.get("market_cap_rank"),
            "var_24h": c.get("price_change_percentage_24h_in_currency"),
            "var_7d": c.get("price_change_percentage_7d_in_currency"),
            "var_30d": c.get("price_change_percentage_30d_in_currency"),
            "var_1a": c.get("price_change_percentage_1y_in_currency"),
            "maximo": c.get("ath"),
            "fecha_maximo": (c.get("ath_date") or "")[:10],
            "desde_maximo": c.get("ath_change_percentage"),
            "actualizado": c.get("last_updated"),
        })
    if len(monedas) < 5 or any(len(series.get(m, {})) < 200 for m in CON_GRAFICO):
        aviso("error", f"Datos incompletos ({len(monedas)} monedas): no se cambia nada")
        return 1

    salida = {
        "fuente": "CoinGecko",
        "actualizado": datetime.now(ZoneInfo("Europe/Madrid")).replace(microsecond=0).isoformat(),
        "monedas": monedas,
        "series": series,
    }
    OUT.write_text(json.dumps(salida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    btc = monedas[0]
    aviso("notice", f"Bitcoin: {btc['precio']} € ({btc['var_24h']:+.2f} % en 24 h) · {len(monedas)} monedas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
