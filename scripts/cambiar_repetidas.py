"""Cambia las portadas repetidas del banco por fotos libres nuevas (Pixabay u Openverse).

De cada foto del banco que es portada de varios artículos, la conserva el más antiguo y a los demás
se les busca una foto libre que no use ningún otro artículo. Si no se encuentra, se deja como estaba.
Se ejecuta a mano desde GitHub (Actions → «Cambiar portadas repetidas») y propone los cambios en una
pull request para revisarlos antes de publicar.

Con el modo «antiguas» cambia, en cambio, las fotos libres de Pixabay anteriores a 2020 (se ven anticuadas)
y las de edificios o símbolos de otros países (un parlamento alemán en una noticia del Congreso). Las de
gobierno y parlamento vuelven a una foto del banco propio, que son de España.

Uso: python scripts/cambiar_repetidas.py [máximo, por defecto 40] [repetidas|antiguas]"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from banco import BANCO  # noqa: E402
from fotos_libres import EVITAR, PIXABAY_ID_MINIMO, buscar, pixabay_id  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "src" / "content" / "posts"

# búsqueda en inglés y texto alternativo genérico para cada tema del banco
TEMAS = {
    "aceite-oliva": ("olive oil bottle", "Botella de aceite de oliva"),
    "agencia-tributaria": ("tax forms paperwork", "Documentos de impuestos sobre una mesa"),
    "banco-de-espana": ("bank building facade", "Fachada de un edificio bancario"),
    "billetes-euro": ("euro banknotes", "Billetes de euro"),
    "bombilla": ("light bulb", "Bombilla encendida"),
    "calculadora": ("calculator budget", "Calculadora y cuentas domésticas"),
    "calendario": ("calendar planning", "Calendario sobre una mesa"),
    "carro-compra": ("shopping cart supermarket", "Carro de la compra en un supermercado"),
    "coche-electrico": ("electric car charging", "Coche eléctrico cargando"),
    "congreso": ("parliament chamber", "Hemiciclo de un parlamento"),
    "contador-luz": ("electricity meter", "Contador de la luz"),
    "edificio-viviendas": ("apartment building", "Edificio de viviendas"),
    "fachada-balcones": ("apartment balconies", "Fachada con balcones"),
    "gruas": ("construction cranes", "Grúas de construcción"),
    "loteria": ("lottery tickets", "Boletos de lotería"),
    "mercado-fruta": ("fruit market stall", "Puesto de fruta en un mercado"),
    "ministerio-hacienda": ("government building", "Edificio oficial"),
    "moncloa": ("government building", "Edificio oficial"),
    "monedas-euro": ("euro coins", "Monedas de euro"),
    "oficina-empleo": ("job interview office", "Oficina de empleo"),
    "placas-solares": ("solar panels roof", "Placas solares en un tejado"),
    "radiador": ("home radiator heating", "Radiador de calefacción"),
    "se-alquila": ("for rent sign", "Cartel de se alquila"),
    "seguridad-social": ("retired couple", "Pareja de jubilados"),
    "supermercado": ("supermarket aisle", "Pasillo de un supermercado"),
    "surtidor": ("gas station pump", "Surtidor de gasolinera"),
    "torres-electricas": ("power lines towers", "Torres eléctricas"),
}
TEMA_DE = {b["slug"]: b["tema"] for b in BANCO}


def campo(texto: str, nombre: str) -> str:
    m = re.search(rf"^{nombre}:\s*\"?([^\"\n]*)\"?", texto, re.M)
    return m.group(1).strip() if m else ""


def yaml_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').strip() + '"'


# Búsqueda para las fotos antiguas según palabras de la dirección de la foto vieja o, si no, la sección
POR_PALABRA = [
    (r"electric|meter|power|energy|light-bulb|bulb", "contador-luz"), (r"solar", "placas-solares"),
    (r"elderly|senior|old-people|old-couple|retire|pension", "seguridad-social"),
    (r"office|business|startup|job", "oficina-empleo"),
    (r"apartment|balcon|building|real-estate|keys|house|home", "edificio-viviendas"),
    (r"calculat|tax|paperwork|insurance", "calculadora"), (r"coin|cent", "monedas-euro"),
    (r"bill|banknote|money|cash|currency|piggy|cashbox|euro", "billetes-euro"),
    (r"bank|banking|national-bank", "banco-de-espana"),
    (r"supermarket|shopping|cart", "supermercado"), (r"radiator|heating", "radiador"),
]
POR_SECCION = {"luz": "contador-luz", "pensiones": "seguridad-social", "paro": "oficina-empleo",
               "vivienda": "edificio-viviendas", "hacienda": "calculadora", "oposiciones": "oficina-empleo",
               "ahorro": "monedas-euro", "fondos": "calculadora", "bolsa": "billetes-euro",
               "jubilacion": "seguridad-social", "impuestos": "calculadora"}
GOBIERNO = re.compile(r"parliament|government|city-hall|town-hall|capitol|chancellery|bundestag|federal-eagle|vienna", re.I)


def antiguas(maximo: int) -> int:
    """Cambia las portadas de Pixabay anteriores a 2020 o con edificios o símbolos de otros países."""
    banco_por_tema: dict[str, list[dict]] = {}
    for b in BANCO:
        banco_por_tema.setdefault(b["tema"], []).append(b)
    cambiadas = 0
    candidatas = []
    for f in sorted(POSTS.glob("*.md")):
        t = f.read_text(encoding="utf-8")
        url = campo(t, "imageCreditUrl")
        if "pixabay.com" not in url:
            continue
        if pixabay_id(url) < PIXABAY_ID_MINIMO or EVITAR.search(url.replace("-", " ")):
            candidatas.append((f, t, url))
    print(f"{len(candidatas)} portadas antiguas o de otros países")
    for f, t, url in candidatas[:maximo]:
        if GOBIERNO.search(url):
            # gobierno o parlamento: foto del banco propio (Congreso o Moncloa), aunque se repita
            opciones = banco_por_tema.get("congreso", []) + banco_por_tema.get("moncloa", [])
            if not opciones:
                continue
            b = opciones[cambiadas % len(opciones)]
            ruta, alt, credito, pagina = f"/img/banco/{b['slug']}.webp", b["alt"], b["credito"], b["pagina"]
        else:
            tema = next((tm for pat, tm in POR_PALABRA if re.search(pat, url, re.I)), None) or POR_SECCION.get(campo(t, "category"), "")
            if tema not in TEMAS:
                print(f"  – {f.stem}: sin búsqueda, se deja")
                continue
            consulta, alt = TEMAS[tema]
            print(f"· {f.stem} → «{consulta}»")
            libre = buscar(consulta, f.stem)
            if not libre:
                continue
            ruta, credito, pagina = libre["ruta"], libre["credito"], libre["pagina"]
        t = re.sub(r"^(imageAlt|imageCredit|imageCreditUrl):.*\n", "", t, flags=re.M)
        t = re.sub(r"^image:.*$", f"image: {ruta}\nimageAlt: {yaml_str(alt)}\n"
                   f"imageCredit: {yaml_str(credito)}\nimageCreditUrl: {yaml_str(pagina)}",
                   t, count=1, flags=re.M)
        f.write_text(t, encoding="utf-8")
        cambiadas += 1
    return cambiadas


def main() -> int:
    maximo = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    if len(sys.argv) > 2 and sys.argv[2] == "antiguas":
        cambiadas = antiguas(maximo)
        print(f"Cambiadas: {cambiadas}")
        with open(__import__("os").environ.get("GITHUB_OUTPUT", "/dev/null"), "a") as o:
            o.write(f"count={cambiadas}\n")
        return 0
    por_foto: dict[str, list[tuple[str, Path]]] = {}
    for f in POSTS.glob("*.md"):
        t = f.read_text(encoding="utf-8")
        m = re.search(r"^image:\s*/img/banco/([\w-]+)\.webp", t, re.M)
        if m:
            por_foto.setdefault(m.group(1), []).append((campo(t, "date"), f))
    repetidas = [(foto, sorted(arts)[1:]) for foto, arts in por_foto.items() if len(arts) > 1]
    pendientes = [(foto, f) for foto, resto in repetidas for _, f in resto]
    print(f"{len(pendientes)} portadas repetidas en {len(repetidas)} fotos del banco")
    cambiadas = 0
    for foto, f in pendientes[:maximo]:
        tema = TEMA_DE.get(foto, "")
        if tema not in TEMAS:
            print(f"  – {f.stem}: tema «{tema}» sin búsqueda, se deja")
            continue
        consulta, alt = TEMAS[tema]
        print(f"· {f.stem} ({foto}) → «{consulta}»")
        libre = buscar(consulta, f.stem)
        if not libre:
            continue
        t = f.read_text(encoding="utf-8")
        t = re.sub(r"^(imageAlt|imageCredit|imageCreditUrl):.*\n", "", t, flags=re.M)
        t = re.sub(r"^image:.*$", f"image: {libre['ruta']}\nimageAlt: {yaml_str(alt)}\n"
                   f"imageCredit: {yaml_str(libre['credito'])}\nimageCreditUrl: {yaml_str(libre['pagina'])}",
                   t, count=1, flags=re.M)
        f.write_text(t, encoding="utf-8")
        cambiadas += 1
    print(f"Cambiadas: {cambiadas}")
    with open(__import__("os").environ.get("GITHUB_OUTPUT", "/dev/null"), "a") as o:
        o.write(f"count={cambiadas}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
