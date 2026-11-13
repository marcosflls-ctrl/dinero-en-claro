#!/usr/bin/env python3
"""Cambia las fotos de banco genéricas (/img/fotos/) por portadas propias con la cifra del titular.

Las fotos libres que se buscaban solas muchas veces no tenían nada que ver con la noticia
(una niña en un bosque para el relevo en el BCE, un río para la Fed).
Cada artículo pasa a tener una portada con su dato principal y el color de su sección;
si el titular no lleva ninguna cifra, el titular sobre ese mismo color.

Uso: python3 scripts/portadas_dato.py            (cambia los artículos con foto en /img/fotos/ y rehace las portadas de titular)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import portada  # noqa: E402
from miniaturas import RECORTES, make_variants  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "src" / "content" / "posts"
PUB = ROOT / "public"


def campo(texto: str, nombre: str) -> str:
    m = re.search(rf'^{nombre}:\s*"?(.*?)"?\s*$', texto, re.M)
    return m.group(1).replace('\\"', '"') if m else ""


def generar(slug: str, titulo: str, categoria: str, descripcion: str = "") -> str:
    """Crea la portada (con sus tamaños y recortes) y devuelve su ruta pública."""
    # Solo vale la cifra del titular: la primera que aparece en la descripción puede ser un ejemplo o un dato menor
    con_cifra = bool(portada.cifra_de(titulo))
    destino = PUB / "img" / ("datos" if con_cifra else "articulos") / f"{slug}.webp"
    portada.crear_dato(titulo, categoria, destino)
    for nombre, (w, h) in RECORTES.items():  # los recortes se dibujan a su tamaño: recortar cortaría la cifra
        portada.crear_dato(titulo, categoria, destino.with_name(f"{slug}-{nombre}.webp"), "", w, h)
    make_variants(destino)
    if con_cifra:
        portada.mini_dato(titulo, categoria, destino.with_name(f"{slug}-mini.webp"))
    return "/" + destino.relative_to(PUB).as_posix()


def main() -> int:
    n = 0
    for f in sorted(POSTS.glob("*.md")):
        t = f.read_text(encoding="utf-8")
        m = re.search(r"^image:\s*(/img/(?:fotos|articulos|datos)/\S+\.webp)\s*$", t, re.M)
        if not m:
            continue
        vieja = m.group(1)
        titulo, cat, desc = campo(t, "title"), campo(t, "category"), campo(t, "description")
        ruta = generar(f.stem, titulo, cat, desc)
        t = t.replace(m.group(0), f"image: {ruta}")
        t = re.sub(r"^imageAlt:.*$", "imageAlt: " + '"' + titulo[:140].replace('"', '\\"') + '"', t, count=1, flags=re.M)
        t = re.sub(r"^imageCredit(Url)?:.*\n", "", t, flags=re.M)
        f.write_text(t, encoding="utf-8")
        base = PUB / vieja.lstrip("/")
        if vieja == ruta:
            n += 1
            continue
        for sobra in base.parent.glob(base.stem + "*.webp"):
            if sobra.stem == base.stem or re.fullmatch(re.escape(base.stem) + r"-(400|800|4x3|1x1|16x9|mini)", sobra.stem):
                sobra.unlink()
        n += 1
    print(f"{n} portadas cambiadas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
