"""
Corrige los enlaces internos de los artículos que apuntan a la sección equivocada
(por ejemplo /hacienda/x/ cuando el artículo x está en /luz/). Avisa de los que no existen.
Uso: python scripts/arreglar_enlaces.py
"""
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "src" / "content" / "posts"
PAGINAS = ROOT / "src" / "pages"
SECCIONES = ("luz", "pensiones", "paro", "vivienda", "hacienda")
ENLACE = re.compile(r"\]\(/(" + "|".join(SECCIONES) + r")/([a-z0-9-]+)/\)")

categoria = {}
for f in POSTS.glob("*.md"):
    m = re.search(r"^category:\s*(\S+)", f.read_text(encoding="utf-8"), re.M)
    if m:
        categoria[f.stem] = m.group(1)

cambios = 0
for f in POSTS.glob("*.md"):
    texto = f.read_text(encoding="utf-8")

    def arreglar(m):
        global cambios
        seccion, slug = m.group(1), m.group(2)
        real = categoria.get(slug)
        if real and real != seccion:
            cambios += 1
            print(f"{f.name}: /{seccion}/{slug}/ → /{real}/{slug}/")
            return f"](/{real}/{slug}/)"
        if not real and not (PAGINAS / seccion / f"{slug}.astro").exists() and not (PAGINAS / seccion / slug).is_dir():
            aviso = f"{f.name}: enlace a /{seccion}/{slug}/, que no existe"
            print(aviso)
            if os.environ.get("GITHUB_ACTIONS"):
                print(f"::warning title=Enlace roto::{aviso}")
        return m.group(0)

    nuevo = ENLACE.sub(arreglar, texto)
    if nuevo != texto:
        f.write_text(nuevo, encoding="utf-8")
print(f"Enlaces corregidos: {cambios}")
