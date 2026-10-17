"""Prueba fuentes de datos desde los servidores de GitHub. Resultado en las anotaciones de la ejecución."""
import requests
UA = "Mozilla/5.0 (compatible; DineroEnClaro/1.0; +https://dineroenclaro.com)"
CLAVES = ("Pan", "Leche", "Aceite de oliva", "Huevos", "Carne de vacuno", "Frutas frescas", "Café")
for t in (76128, 76147, 79184, 76159):
    try:
        d = requests.get(f"https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/{t}?nult=2", headers={"User-Agent": UA}, timeout=90).json()
    except Exception as e:  # noqa: BLE001
        print(f"::notice title={t}::{type(e).__name__}"); continue
    ej = [s for s in d if any(k in s.get("Nombre", "") for k in CLAVES)][:8]
    txt = " || ".join(f"{s['COD']} {s['Nombre'][:90]} = " + ", ".join(f"{x.get('Anyo')}-{x.get('FK_Periodo')}:{x.get('Valor')}" for x in s.get("Data", [])) for s in ej)
    print(f"::notice title={t} ({len(d)} series)::{txt[:3800]}")
