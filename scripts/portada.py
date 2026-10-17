"""
Imagen de portada (1600x900, WebP) con el titular, para artículos sin foto propia.
Discover necesita imágenes grandes: esta es la que se ve en la tarjeta.

Uso desde otro script:  from portada import crear; crear("Titular", "pensiones", Path("public/img/articulos/x.webp"))
Uso directo:            python scripts/portada.py "Titular" pensiones salida.webp
También genera las imágenes fijas de la web:  python scripts/portada.py --fijas
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FUENTES = Path(__file__).resolve().parent / "fuentes"
VERDE, VERDE_OSC, CLARO, BLANCO = (31, 78, 121), (22, 58, 92), (184, 204, 224), (255, 255, 255)  # azul de la marca
ETIQUETAS = {"inicio": "Dinero en Claro", "ahorro": "Ahorro", "fondos": "Fondos y ETF", "bolsa": "Bolsa y mercados", "jubilacion": "Jubilación", "impuestos": "Impuestos"}


def fuente(nombre: str, tam: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FUENTES / f"{nombre}.woff"), tam)


def partir(draw: ImageDraw.ImageDraw, texto: str, f: ImageFont.FreeTypeFont, ancho: int) -> list[str]:
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        if draw.textlength(prueba, font=f) <= ancho:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


def marca(draw: ImageDraw.ImageDraw, x: float, y: float, s: float) -> None:
    """El icono de la web (tres barras que suben), en blanco."""
    for bx, by in ((8, 17), (14, 13), (20, 8)):
        draw.rounded_rectangle([x + bx * s, y + by * s, x + (bx + 4) * s, y + 25 * s], radius=1 * s, fill=BLANCO)

def crear(titulo: str, categoria: str, salida: Path, ancho: int = 1600, alto: int = 900, subtitulo: str = "") -> Path:
    """Portada sobria: fondo verde de la marca, sección arriba, titular en serif y la marca abajo."""
    e = ancho / 1600
    img = Image.new("RGB", (ancho, alto), VERDE)
    d = ImageDraw.Draw(img)
    m = round(100 * e)
    # sección, con una raya fina encima
    d.line([m, m, m + 64 * e, m], fill=BLANCO, width=max(2, round(4 * e)))
    fe = fuente("sans-500", round(34 * e))
    d.text((m, m + 26 * e), ETIQUETAS.get(categoria, categoria.capitalize()), font=fe, fill=CLARO)
    # titular: baja de tamaño si es largo para que quepa en 4 líneas
    y0, y1 = m + 110 * e, alto - 190 * e
    for tam in (100, 90, 82, 74, 66, 58):
        ft = fuente("serif-600", round(tam * e))
        lineas = partir(d, titulo, ft, ancho - 2 * m)
        alto_linea = round(tam * 1.2 * e)
        if len(lineas) <= 4 and len(lineas) * alto_linea <= y1 - y0:
            break
    y = y0
    for linea in lineas[:4]:
        d.text((m, y), linea, font=ft, fill=BLANCO)
        y += alto_linea
    if subtitulo:
        d.text((m, y + 18 * e), subtitulo, font=fuente("sans-400", round(36 * e)), fill=CLARO)
    # pie: línea, marca y dominio
    yp = alto - m - 40 * e
    d.line([m, yp - 30 * e, ancho - m, yp - 30 * e], fill=(70, 110, 150), width=max(1, round(2 * e)))
    marca(d, m - 6 * e, yp - 4 * e, 1.5 * e)
    d.text((m + 52 * e, yp + 20 * e), "dineroenclaro.com", font=fuente("sans-500", round(32 * e)), fill=BLANCO, anchor="lm")
    salida.parent.mkdir(parents=True, exist_ok=True)
    if salida.suffix == ".png":
        img.save(salida, "PNG", optimize=True)
    else:
        img.save(salida, "WEBP", quality=86, method=6)
    return salida


def icono(tam: int, salida: Path) -> None:
    img = Image.new("RGBA", (tam, tam), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = tam / 32
    d.rounded_rectangle([0, 0, tam - 1, tam - 1], radius=5 * s, fill=VERDE)
    marca(d, 0, 0, s)
    img.save(salida, "PNG", optimize=True)


def fijas() -> None:
    """Portadas de cada sección, imagen por defecto para redes e iconos."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from miniaturas import make_variants

    textos = {
        "ahorro": ("Depósitos, cuentas y Letras del Tesoro", "Cuánto rinde de verdad tu dinero"),
        "fondos": ("Fondos de inversión y ETF", "Cómo funcionan y cuánto cuestan"),
        "bolsa": ("Bolsa y mercados", "Lo que mueve tus ahorros, explicado"),
        "jubilacion": ("Planes de pensiones y jubilación", "Ahorro a largo plazo sin letra pequeña"),
        "impuestos": ("Impuestos del ahorro y la inversión", "Intereses, dividendos y ganancias"),
    }
    for cat, (t, sub) in textos.items():
        p = crear(t, cat, ROOT / "public" / "img" / "portadas" / f"{cat}.webp", subtitulo=sub)
        make_variants(p)
    crear("Ahorro, inversión y mercados explicados sin letra pequeña", "inicio", ROOT / "public" / "og-default.png", 1200, 630,
          subtitulo="")
    for tam, nombre in ((48, "favicon-48.png"), (180, "apple-touch-icon.png"), (192, "icon-192.png"), (512, "icon-512.png")):
        icono(tam, ROOT / "public" / nombre)
    print("Imágenes fijas creadas")


def miniatura(categoria: str, salida: Path, ancho: int = 480, alto: int = 360) -> Path:
    """Miniatura sin titular para las tarjetas pequeñas del móvil: solo la marca y el nombre de la sección."""
    img = Image.new("RGB", (ancho, alto), VERDE)
    d = ImageDraw.Draw(img)
    etiqueta = ETIQUETAS.get(categoria, categoria)
    m = 36
    d.line([(m, m + 6), (m + 44, m + 6)], fill=CLARO, width=4)
    tam = 64
    while tam > 30:
        f = fuente("serif-600", tam)
        lineas = partir(d, etiqueta, f, ancho - 2 * m)
        if len(lineas) <= 3:
            break
        tam -= 4
    alto_l = tam * 1.12
    y = alto - m - alto_l * len(lineas)
    for i, l in enumerate(lineas):
        d.text((m, y + i * alto_l), l, font=f, fill=BLANCO)
    salida.parent.mkdir(parents=True, exist_ok=True)
    img.save(salida, "WEBP", quality=82, method=6)
    return salida


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--miniaturas":
        for c in ETIQUETAS:
            if c != "inicio":
                print(miniatura(c, ROOT / "public" / "img" / "miniaturas" / f"{c}.webp"))
        sys.exit(0)
    if sys.argv[1:] == ["--fijas"]:
        fijas()
    elif len(sys.argv) == 4:
        salida = crear(sys.argv[1], sys.argv[2], Path(sys.argv[3]))
        # Versiones pequeñas para el móvil y recortes 4:3 y 1:1 para Discover
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from miniaturas import make_variants, make_crops
        make_variants(salida.resolve()); make_crops(salida.resolve())
        print(salida)
    else:
        print(__doc__)
