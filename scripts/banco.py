"""Elige una foto del banco (scripts/banco.json) para la portada de un artículo.

Primero el tema que propone la IA; si no, el que más palabras del titular comparte. Nunca repite una
foto que ya sea portada de otro artículo si hay alternativas (Discover muestra menos las repetidas).
Si nada encaja, devuelve None y se usa la portada con el titular."""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANCO = json.loads((ROOT / "scripts" / "banco.json").read_text(encoding="utf-8"))["imagenes"] \
    if (ROOT / "scripts" / "banco.json").exists() else []
TEMAS = sorted({b["tema"] for b in BANCO})


def usadas() -> dict[str, int]:
    """Cuántos artículos usan cada foto del banco como portada."""
    n: dict[str, int] = {}
    for f in (ROOT / "src" / "content" / "posts").glob("*.md"):
        m = re.search(r"^image:\s*/img/banco/([\w-]+)\.webp", f.read_text(encoding="utf-8"), re.M)
        if m:
            n[m.group(1)] = n.get(m.group(1), 0) + 1
    return n


def _n(t: str) -> str:
    return unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode()


def elegir(titulo: str, categoria: str, tema_ia: str = "") -> dict | None:
    if not BANCO:
        return None
    t = _n(titulo)
    def esta(w: str) -> int:
        # la palabra (o su comienzo: «jubila» vale para «jubilación»), no un trozo de otra («gas» en «gastos»)
        m = re.search(r"(?<![a-z])" + re.escape(_n(w)) + (r"(?![a-z])" if len(w) <= 4 else ""), t)
        return m.start() if m else -1
    def puntos(b: dict) -> int:
        p = sum(2 for w in b["palabras"] if esta(w) >= 0)
        if b["tema"] == tema_ia:
            p += 5
        if p and categoria in b["secciones"]:
            p += 1
        return p
    def primera(b: dict) -> int:
        # en caso de empate gana el tema cuya palabra aparece antes en el titular (suele ser el asunto)
        pos = [esta(w) for w in b["palabras"] if esta(w) >= 0]
        return min(pos) if pos else 999
    cands = [(puntos(b), -primera(b), b) for b in BANCO]
    mejor = max(((p, q) for p, q, _ in cands), default=(0, 0))
    if mejor[0] == 0:
        return None
    temas_top = {b["tema"] for p, q, b in cands if (p, q) == mejor}
    opciones = [b for b in BANCO if b["tema"] in temas_top]
    uso = usadas()
    opciones.sort(key=lambda b: (uso.get(b["slug"], 0), b["slug"]))
    return opciones[0]
