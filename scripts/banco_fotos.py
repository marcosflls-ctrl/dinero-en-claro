"""
Banco de fotos con licencia libre (Wikimedia Commons) para las portadas.

Discover muestra mejor las fotos reales que las portadas con texto. Este script:
  buscar   → busca candidatas por tema en Commons y las deja en banco_candidatas/ con sus datos
             (se ejecuta en GitHub, que sí llega a Commons; luego se revisan a mano)
  preparar → convierte las elegidas (lista en scripts/banco_elegidas.json) a portadas 1600x900
             con sus versiones pequeñas y recortes, y escribe scripts/banco.json

Solo se aceptan licencias que permiten el uso comercial: dominio público, CC0, CC BY y CC BY-SA.
Cada foto guarda su autor y licencia, que se muestran bajo la imagen.
"""
from __future__ import annotations

import io
import json
import re
import sys
import time
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CAND = ROOT / "banco_candidatas"
DEST = ROOT / "public" / "img" / "banco"
BANCO = ROOT / "scripts" / "banco.json"
ELEGIDAS = ROOT / "scripts" / "banco_elegidas.json"
API = "https://commons.wikimedia.org/w/api.php"
UA = "DineroEnClaro/1.0 (https://dineroenclaro.com; banco de portadas)"

# tema → (búsquedas en Commons, palabras del titular que lo señalan, secciones)
TEMAS: dict[str, dict] = {
    "bolsa-madrid": {"q": ["Palacio de la Bolsa de Madrid", "Bolsa de Madrid edificio"], "palabras": ["bolsa", "ibex", "acciones", "cotiza", "mercado"], "secciones": ["bolsa"]},
    "bce-frankfurt": {"q": ["European Central Bank headquarters Frankfurt", "Banco Central Europeo sede"], "palabras": ["bce", "banco central europeo", "lagarde", "tipos de interés", "tipos"], "secciones": ["bolsa", "ahorro"]},
    "pantalla-bolsa": {"q": ["stock market display board", "stock exchange screen numbers"], "palabras": ["bolsa", "mercados", "índice", "wall street", "caída", "subida"], "secciones": ["bolsa", "fondos"]},
    "cnmv": {"q": ["Comisión Nacional del Mercado de Valores sede", "CNMV Madrid edificio"], "palabras": ["cnmv", "supervisor", "advertencia", "chiringuito"], "secciones": ["fondos", "bolsa"]},
    "hucha": {"q": ["piggy bank coins", "hucha monedas"], "palabras": ["ahorro", "ahorrar", "ahorradores", "hucha"], "secciones": ["ahorro", "jubilacion"]},
    "oro": {"q": ["gold bars", "lingotes de oro"], "palabras": ["oro"], "secciones": ["bolsa"]},
    "jubilados": {"q": ["elderly couple walking Spain seaside", "retired people walking park"], "palabras": ["jubila", "pensión", "plan de pensiones", "retiro"], "secciones": ["jubilacion"]},
    "billetes-euro": {"q": ["euro banknotes"], "palabras": ["ahorro", "ahorradores", "dinero", "rentabilidad", "intereses", "depósito", "cuenta remunerada"], "secciones": ["ahorro", "fondos"]},
    "monedas-euro": {"q": ["euro coins"], "palabras": ["inflación", "ipc", "precios", "euro", "ahorro", "dividendo"], "secciones": ["bolsa", "ahorro"]},
    "calculadora": {"q": ["calculator documents desk"], "palabras": ["impuesto", "irpf", "renta", "declaración", "tributa", "fiscal", "comisiones", "plusvalía"], "secciones": ["impuestos", "fondos"]},
    "banco-de-espana": {"q": ["Banco de España edificio Madrid"], "palabras": ["banco de españa", "euríbor", "tipos", "hipoteca", "deuda", "bono", "letras", "tesoro"], "secciones": ["ahorro", "bolsa"]},
}
LICENCIAS_OK = re.compile(r"^(cc0|public domain|pd|cc[ -]by(-sa)?[ -]?[234](\.\d)?( [a-z]+)?)$", re.I)


def limpiar(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html or "")).strip()


def buscar() -> None:
    CAND.mkdir(exist_ok=True)
    s = requests.Session()
    s.headers["User-Agent"] = UA
    datos = []
    for tema, cfg in TEMAS.items():
        vistos, n = set(), 0
        for q in cfg["q"]:
            params = {
                "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
                "gsrsearch": f"{q} filetype:bitmap", "gsrlimit": 30,
                "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 1600,
            }
            try:
                r = s.get(API, params=params, timeout=60)
                pages = (r.json().get("query") or {}).get("pages", {})
            except Exception as e:  # noqa: BLE001
                print(f"! {tema} {q}: {e}")
                continue
            for p in sorted(pages.values(), key=lambda p: p.get("index", 0)):
                ii = (p.get("imageinfo") or [{}])[0]
                titulo = p.get("title", "")
                if titulo in vistos or ii.get("mime") != "image/jpeg":
                    continue
                w, h = ii.get("width", 0), ii.get("height", 0)
                if w < 1600 or not (1.25 <= w / max(h, 1) <= 2.1):
                    continue
                meta = ii.get("extmetadata", {})
                lic = limpiar(meta.get("LicenseShortName", {}).get("value", ""))
                if not LICENCIAS_OK.match(lic):
                    continue
                vistos.add(titulo)
                n += 1
                nombre = f"{tema}-{n:02d}.jpg"
                try:
                    img = s.get(ii["thumburl"], timeout=60).content
                    Image.open(io.BytesIO(img)).convert("RGB").save(CAND / nombre, "JPEG", quality=82)
                except Exception as e:  # noqa: BLE001
                    print(f"! descarga {titulo}: {e}")
                    continue
                datos.append({
                    "archivo": nombre, "tema": tema, "titulo": titulo,
                    "pagina": ii.get("descriptionurl", ""),
                    "autor": limpiar(meta.get("Artist", {}).get("value", ""))[:120],
                    "licencia": lic, "licencia_url": meta.get("LicenseUrl", {}).get("value", ""),
                    "descripcion": limpiar(meta.get("ImageDescription", {}).get("value", ""))[:200],
                })
                time.sleep(0.3)
                if n >= 8:
                    break
            if n >= 8:
                break
        print(f"{tema}: {n} candidatas")
    (CAND / "candidatas.json").write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Total: {len(datos)}")


def preparar() -> None:
    """Pasa las elegidas a public/img/banco/ en 1600x900 y escribe scripts/banco.json."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from miniaturas import make_variants, make_crops

    cand = {c["archivo"]: c for c in json.loads((CAND / "candidatas.json").read_text(encoding="utf-8"))}
    elegidas = json.loads(ELEGIDAS.read_text(encoding="utf-8"))
    DEST.mkdir(parents=True, exist_ok=True)
    banco = []
    for e in elegidas:
        c = cand[e["archivo"]]
        slug = Path(e["archivo"]).stem
        with Image.open(CAND / e["archivo"]) as im:
            im = im.convert("RGB")
            escala = max(1600 / im.width, 900 / im.height)
            im = im.resize((round(im.width * escala), round(im.height * escala)), Image.LANCZOS)
            x, y = (im.width - 1600) // 2, round((im.height - 900) * e.get("y", 0.5))
            salida = DEST / f"{slug}.webp"
            im.crop((x, y, x + 1600, y + 900)).save(salida, "WEBP", quality=70, method=6)
        make_variants(salida)
        make_crops(salida)
        tema = TEMAS[c["tema"]]
        banco.append({
            "slug": slug, "tema": c["tema"], "alt": e["alt"],
            "palabras": tema["palabras"], "secciones": tema["secciones"],
            "credito": f"{e.get('autor') or c['autor'] or 'Autor desconocido'} / Wikimedia Commons ({c['licencia']})",
            "pagina": c["pagina"],
        })
    BANCO.write_text(json.dumps({"imagenes": banco}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(banco)} fotos en el banco")


if __name__ == "__main__":
    {"buscar": buscar, "preparar": preparar}[sys.argv[1]]()
