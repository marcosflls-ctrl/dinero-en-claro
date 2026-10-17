"""Prueba desde los servidores de GitHub que cada fuente de scripts/feeds.json responde.

Resultado en las anotaciones de la ejecución: una línea por fuente con el número de
entradas, la más reciente y cuántas coinciden con las palabras clave del robot.
"""
import json
import pathlib

import feedparser
import requests

UA = "Mozilla/5.0 (compatible; DineroEnClaro/1.0; +https://dineroenclaro.com)"
cfg = json.loads((pathlib.Path(__file__).parent / "feeds.json").read_text(encoding="utf-8"))
claves = [k.lower() for k in cfg.get("keywords", [])]

ok, fallan = [], []
for feed in cfg["feeds"]:
    nombre = feed["name"]
    try:
        r = requests.get(feed["url"], headers={"User-Agent": UA}, timeout=60)
        d = feedparser.parse(r.content)
        entradas = d.entries
        if r.status_code != 200 or not entradas:
            fallan.append(f"{nombre}: HTTP {r.status_code}, {len(entradas)} entradas")
            continue
        coinciden = sum(1 for e in entradas if any(k in (e.get("title", "") + " " + e.get("summary", "")).lower() for k in claves))
        primera = entradas[0]
        fecha = primera.get("published", primera.get("updated", "sin fecha"))
        ok.append(f"{nombre}: {len(entradas)} entradas, {coinciden} con palabras clave. Última: {primera.get('title', '')[:70]} ({fecha})")
    except Exception as e:  # noqa: BLE001
        fallan.append(f"{nombre}: {type(e).__name__}: {str(e)[:120]}")

# GitHub muestra como mucho 10 avisos por paso: todo en dos anotaciones
print(f"::notice title=Funcionan ({len(ok)})::" + " %0A".join(ok))
if fallan:
    print(f"::warning title=Fallan ({len(fallan)})::" + " %0A".join(fallan))
