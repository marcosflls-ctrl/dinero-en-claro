"""Busca una foto libre para la portada cuando ninguna del banco propio encaja con la noticia.

Orden: Pixabay (necesita el secreto PIXABAY_API_KEY) y, si no hay nada, Openverse (sin clave).
Solo se aceptan fotos que permiten uso comercial y modificarlas (recortarlas):
  · Pixabay: licencia de Pixabay (uso comercial, sin atribución obligatoria; la ponemos igual).
  · Openverse: solo CC0, dominio público, CC BY y CC BY-SA (nunca «ND» ni «NC»).
La foto se descarga, se recorta a 16:9 (1280x720, válido para Discover), se guarda en WebP en
public/img/fotos/ con sus versiones pequeñas y recortes, y nunca se repite una que ya sea portada.
Si algo falla devuelve None y el robot usa la portada con el titular, como antes."""
from __future__ import annotations

import io
import os
import re
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "public" / "img" / "fotos"
POSTS = ROOT / "src" / "content" / "posts"
ANCHO, ALTO = 1280, 720
UA = "Mozilla/5.0 (compatible; portadas-bot/1.0)"
# palabras en las etiquetas que delatan marcas, logos, personas famosas o fotos poco serias
EVITAR = re.compile(r"\b(logo|brand|trump|biden|celebrity|famous|sexy|bikini|lingerie|meme|cartoon|"
                    r"illustration|3d|render|ai generated|text|letters|typography|"
                    # montajes de banco de imágenes con fondo blanco o conceptos (se ven anticuados)
                    r"isolated|white background|concept|symbol|icon|clipart|vector|"
                    # edificios, banderas y monedas de otros países: confunden en una noticia española
                    r"germany|german|berlin|bonn|hamburg|munich|bundestag|federal|chancellery|london|england|"
                    r"britain|british|scotland|edinburgh|usa|america|american|washington|capitol|iowa|"
                    r"vienna|austria|switzerland|swiss|paris|france|french|italy|rome|dollar|dollars)\b", re.I)
# Pixabay numera las fotos por orden de subida: por debajo de este número son de antes de 2020 y
# suelen verse anticuadas (móviles viejos, montajes con texto). Solo se aceptan las más recientes.
PIXABAY_ID_MINIMO = 5_000_000


def pixabay_id(pagina: str) -> int:
    m = re.search(r"-(\d+)/?$", pagina or "")
    return int(m.group(1)) if m else 0


def _usadas() -> set[str]:
    """Páginas de origen de las fotos que ya son portada de algún artículo."""
    hechas = set()
    for f in POSTS.glob("*.md"):
        m = re.search(r"^imageCreditUrl:\s*\"?([^\"\n]+)", f.read_text(encoding="utf-8"), re.M)
        if m:
            hechas.add(m.group(1).strip())
    return hechas


def _pixabay(q: str, usadas: set[str]) -> list[dict]:
    key = os.environ.get("PIXABAY_API_KEY", "").strip()
    if not key:
        return []
    r = requests.get("https://pixabay.com/api/", timeout=30, params={
        "key": key, "q": q[:100], "image_type": "photo", "orientation": "horizontal",
        "min_width": ANCHO, "safesearch": "true", "per_page": 200, "lang": "en", "order": "popular",
    })
    r.raise_for_status()
    out = []
    # primero las que más gustan, entre las recientes
    hits = sorted(r.json().get("hits", []), key=lambda h: h.get("likes", 0) + h.get("downloads", 0) / 100, reverse=True)
    for h in hits:
        if h.get("pageURL") in usadas or EVITAR.search(h.get("tags", "")) or EVITAR.search(h.get("pageURL", "")):
            continue
        if h.get("id", 0) < PIXABAY_ID_MINIMO:
            continue
        if h.get("imageWidth", 0) < ANCHO or not 1.3 <= h["imageWidth"] / max(h.get("imageHeight", 1), 1) <= 2.2:
            continue
        out.append({"url": h["largeImageURL"], "pagina": h["pageURL"],
                    "credito": f"{h.get('user') or 'Autor'} / Pixabay"})
    return out


def _openverse(q: str, usadas: set[str]) -> list[dict]:
    r = requests.get("https://api.openverse.org/v1/images/", timeout=15, headers={"User-Agent": UA}, params={
        "q": q[:100], "license": "cc0,pdm,by,by-sa", "category": "photograph",
        "aspect_ratio": "wide", "mature": "false", "page_size": 20,  # sin clave, máximo 20
    })
    r.raise_for_status()
    out = []
    for h in r.json().get("results", []):
        pagina = h.get("foreign_landing_url") or ""
        if not pagina or pagina in usadas or (h.get("width") or 0) < ANCHO:
            continue
        if EVITAR.search(h.get("title") or ""):  # sus etiquetas automáticas son poco fiables: solo el título
            continue
        lic = (h.get("license") or "").lower()
        nombre_lic = {"cc0": "CC0", "pdm": "dominio público"}.get(lic, f"CC {lic.upper()} {h.get('license_version') or ''}".strip())
        fuente = (h.get("source") or h.get("provider") or "Openverse").replace("_", " ").title()
        out.append({"url": h["url"], "pagina": pagina,
                    "credito": f"{(h.get('creator') or 'Autor desconocido')[:80]} / {fuente} ({nombre_lic})"})
    return out


def _guardar(url: str, destino: Path) -> bool:
    r = requests.get(url, timeout=60, headers={"User-Agent": UA})
    r.raise_for_status()
    with Image.open(io.BytesIO(r.content)) as im:
        im = im.convert("RGB")
        if im.width < ANCHO:
            return False
        escala = max(ANCHO / im.width, ALTO / im.height)
        im = im.resize((round(im.width * escala), round(im.height * escala)), Image.LANCZOS)
        x, y = (im.width - ANCHO) // 2, (im.height - ALTO) // 2
        destino.parent.mkdir(parents=True, exist_ok=True)
        im.crop((x, y, x + ANCHO, y + ALTO)).save(destino, "WEBP", quality=72, method=6)
    return True


def buscar(consulta: str, slug: str) -> dict | None:
    """Devuelve {"ruta", "credito", "pagina"} o None. `consulta` va en inglés (2-4 palabras)."""
    consulta = (consulta or "").strip()
    if not consulta:
        return None
    usadas = _usadas()
    for nombre, fuente in (("Pixabay", _pixabay), ("Openverse", _openverse)):
        try:
            candidatas = fuente(consulta, usadas)
        except Exception as e:  # noqa: BLE001
            print(f"  ! {nombre}: {e}")
            continue
        for c in candidatas[:5]:
            destino = DEST / f"{slug}.webp"
            try:
                if not _guardar(c["url"], destino):
                    continue
            except Exception as e:  # noqa: BLE001
                print(f"  ! descarga {nombre}: {e}")
                continue
            try:
                import sys
                sys.path.insert(0, str(Path(__file__).resolve().parent))
                from miniaturas import make_variants, make_crops
                make_variants(destino)
                make_crops(destino)
            except Exception as e:  # noqa: BLE001
                print(f"  ! versiones pequeñas: {e}")
            print(f"  · foto de {nombre} para «{consulta}»: {c['pagina']}")
            return {"ruta": f"/img/fotos/{slug}.webp", "credito": c["credito"], "pagina": c["pagina"]}
    print(f"  · sin foto libre para «{consulta}»")
    return None


if __name__ == "__main__":  # prueba: python scripts/fotos_libres.py "electricity bill" prueba
    import sys
    print(buscar(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "prueba-foto"))
