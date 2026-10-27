"""
Radar de noticias de Dinero en Claro.

1. Lee el sumario del BOE de hoy y los feeds de scripts/feeds.json
2. Se queda con lo que afecta al ahorro y la inversión de los particulares y aún no ha procesado
3. Descarga el texto y le pide a Claude un artículo ORIGINAL siguiendo la política editorial
4. Lo guarda como borrador .md en src/content/posts/ (con su imagen de portada)
   → GitHub te abre una propuesta para revisarlo antes de publicar

Uso:
  python scripts/radar.py              # normal (en GitHub usa la federación de identidades, sin clave;
                                       # en tu PC puedes usar ANTHROPIC_API_KEY=...)
  python scripts/radar.py --dry-run    # solo lista lo que encontraría
  python scripts/radar.py --url URL    # redacta solo esa noticia
Variables opcionales: MAX_PER_RUN (1), MAX_PER_DAY (2), MODEL (claude-sonnet-5-5)
"""
from __future__ import annotations

import argparse
import calendar
import difflib
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from portada import crear as crear_portada  # noqa: E402
from filtro import prefiltrar  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FEEDS_FILE = ROOT / "scripts" / "feeds.json"
STATE_FILE = ROOT / "scripts" / "state" / "seen.json"
POSTS_DIR = ROOT / "src" / "content" / "posts"
IMG_DIR = ROOT / "public" / "img" / "articulos"
MADRID = ZoneInfo("Europe/Madrid")

MAX_AGE_HOURS = 36            # lo más antiguo ya no es noticia
MAX_PER_RUN = int(os.environ.get("MAX_PER_RUN", "1"))
# Tope de artículos al día: publicar mucho y rápido hace que Google desconfíe de una web nueva
MAX_PER_DAY = int(os.environ.get("MAX_PER_DAY", "2"))
# Ahorro: cuánto texto de la fuente lee el redactor y cuántos artículos recientes ve para enlazar y no repetir
MAX_FUENTE = int(os.environ.get("MAX_FUENTE", "12000"))
RECIENTES = int(os.environ.get("RECIENTES", "50"))
MODEL = os.environ.get("MODEL", "claude-sonnet-5-5")
MIN_SOURCE_CHARS = 500        # si no hay texto suficiente, no se escribe (evita inventar)
SIMILARITY_SKIP = 0.6         # títulos muy parecidos = misma noticia ya cubierta
UA = "Mozilla/5.0 (compatible; DineroEnClaroRadar/1.0; +https://dineroenclaro.com)"
CATEGORIES = ["ahorro", "fondos", "bolsa", "jubilacion", "impuestos"]
BOE_API = "https://www.boe.es/datosabiertos/api/boe/sumario/{fecha}"
BOE_SECCIONES = {"1", "3"}    # I. Disposiciones generales · III. Otras disposiciones


# ---------- utilidades ----------
def slugify(text: str, max_len: int = 75) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    if len(text) > max_len:
        corte = text[:max_len + 1]
        # Cortar siempre en un guion para no dejar palabras a medias
        text = corte[:corte.rfind("-")] if "-" in corte else text[:max_len]
        # Y no terminar en palabras vacías ("...para-reclamar-el")
        vacias = {"a", "al", "con", "de", "del", "el", "en", "la", "las", "lo", "los",
                  "o", "para", "por", "que", "se", "su", "un", "una", "y"}
        partes = text.split("-")
        while len(partes) > 1 and partes[-1] in vacias:
            partes.pop()
        text = "-".join(partes)
    return text.rstrip("-") or "articulo"


def norm_title(t: str) -> str:
    return re.sub(r"\W+", " ", unicodedata.normalize("NFKD", t.lower())).strip()


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"urls": [], "titles": []}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["urls"] = state["urls"][-4000:]
    state["titles"] = state["titles"][-2000:]
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def existing_posts() -> list[dict]:
    """Títulos y direcciones de lo ya escrito, para evitar duplicados y sugerir enlaces internos."""
    out = []
    for f in POSTS_DIR.glob("*.md"):
        txt = f.read_text(encoding="utf-8")
        if re.search(r"^draft:\s*true", txt, re.M):
            continue
        t = re.search(r'^title:\s*"?(.*?)"?\s*$', txt, re.M)
        c = re.search(r"^category:\s*(\w+)", txt, re.M)
        g = re.search(r"^guia:\s*true", txt, re.M)
        d = re.search(r"^date:\s*(\S+)", txt, re.M)
        if t and c:
            out.append({"title": t.group(1), "url": f"/{c.group(1)}/{f.stem}/", "guia": bool(g), "_fecha": d.group(1) if d else ""})
    # lo más reciente primero: es lo que más se puede repetir (en GitHub todos los archivos tienen la misma fecha de
    # modificación, así que se ordena por la fecha del artículo)
    out.sort(key=lambda x: x["_fecha"], reverse=True)
    return [{k: v for k, v in x.items() if k != "_fecha"} for x in out]


def _para_enlazar(posts: list[dict]) -> list[dict]:
    """Los artículos más recientes y, además, todas las guías (para que los enlaces a guías no se pierdan)."""
    recientes = posts[:RECIENTES]
    return recientes + [p for p in posts[RECIENTES:] if p.get("guia")]


def is_similar(title: str, known: list[str]) -> bool:
    n = norm_title(title)
    return any(difflib.SequenceMatcher(None, n, k).ratio() >= SIMILARITY_SKIP for k in known)


def matches(text: str, kws: list[str]) -> bool:
    t = f" {text.lower()} "
    return any(re.search(rf"(?<!\w){re.escape(k)}(?!\w)", t) for k in kws)


SIN_OFICIAL: list[str] = []  # borradores que solo citan al medio, sin documento oficial
RESUMEN: list[str] = []  # qué ha respondido cada fuente (se muestra en GitHub)


# ---------- 1. BOE ----------
def boe_items(cfg: dict, kws: list[str]) -> list[dict]:
    """Disposiciones del BOE de hoy de los departamentos elegidos que hablan de los temas de la web."""
    import requests

    fecha = datetime.now(MADRID).strftime("%Y%m%d")
    r = requests.get(BOE_API.format(fecha=fecha), headers={"Accept": "application/json", "User-Agent": UA}, timeout=30)
    if r.status_code == 404:
        RESUMEN.append("BOE de hoy aún no publicado")
        return []  # todavía no ha salido (se publica de madrugada) o es domingo
    r.raise_for_status()
    deps = [d.lower() for d in cfg.get("boe", {}).get("departamentos", [])]
    out: list[dict] = []

    def walk(o, seccion="", depto=""):
        if isinstance(o, list):
            for x in o:
                walk(x, seccion, depto)
            return
        if not isinstance(o, dict):
            return
        if "identificador" in o and "titulo" in o:
            if seccion in BOE_SECCIONES and any(d in depto.lower() for d in deps) and matches(o["titulo"], kws):
                url = o.get("url_html") or f"https://www.boe.es/diario_boe/txt.php?id={o['identificador']}"
                out.append({"source": "BOE", "title": o["titulo"], "url": url, "oficial": True})
            return
        if "codigo" in o and "departamento" in o:         # sección
            seccion = str(o.get("codigo", ""))
        elif "codigo" in o and "nombre" in o:              # departamento (los epígrafes no llevan código)
            depto = o.get("nombre", depto)
        for v in o.values():
            walk(v, seccion, depto)

    walk(r.json().get("data", {}))
    return out


# ---------- 1. feeds ----------
def collect_candidates(cfg: dict, state: dict, posts: list[dict]) -> list[dict]:
    import feedparser

    kws = [k.lower() for k in cfg["keywords"]]
    known_titles = state["titles"] + [norm_title(p["title"]) for p in posts]
    found = []

    def add(item: dict) -> None:
        if item["url"] in state["urls"]:
            return
        if is_similar(item["title"], known_titles):
            state["urls"].append(item["url"])
            return
        found.append(item)
        known_titles.append(norm_title(item["title"]))

    try:
        boe = boe_items(cfg, kws)
        print(f"  · BOE: {len(boe)} disposiciones de interés")
        RESUMEN.append(f"BOE {len(boe)}")
        for it in boe:
            add(it)
    except Exception as e:  # noqa: BLE001
        print(f"  ! BOE: {e}")
        RESUMEN.append(f"BOE error {type(e).__name__}")

    for feed in cfg["feeds"]:
        try:
            entries = feedparser.parse(feed["url"], agent=UA).entries
        except Exception as e:  # noqa: BLE001
            print(f"  ! {feed['name']}: {e}")
            RESUMEN.append(f"{feed['name']} error")
            continue
        print(f"  · {feed['name']}: {len(entries)} entradas")
        # Fuente recién añadida ("arranque": true): la primera vez solo se apunta lo que ya tenía publicado,
        # para no escribir sobre noticias antiguas (algunas fuentes, como el INE, no ponen fecha a sus entradas)
        if feed.get("arranque") and feed["url"] not in state.setdefault("feeds_iniciados", []):
            state["urls"].extend(x.get("link", "") for x in entries if x.get("link"))
            state["feeds_iniciados"].append(feed["url"])
            print("    (fuente nueva: se apuntan sus entradas actuales y se empieza a vigilar desde ahora)")
            continue
        RESUMEN.append(f"{feed['name']} {len(entries)}")
        for e in entries[:40]:
            link, title = e.get("link", ""), e.get("title", "")
            pub = e.get("published_parsed") or e.get("updated_parsed")
            if pub and (time.time() - calendar.timegm(pub)) > MAX_AGE_HOURS * 3600:
                continue
            if not link or not matches(f"{title} {e.get('summary', '')}", kws):
                continue
            add({"source": feed["name"], "title": title, "url": link, "oficial": bool(feed.get("oficial"))})
    # lo oficial primero
    found.sort(key=lambda x: not x.get("oficial"))
    return found


# ---------- 2. leer la fuente ----------
def fetch_page(url: str) -> tuple[str, str]:
    """Devuelve (html, texto limpio)."""
    import requests
    import trafilatura

    try:
        html = requests.get(url, headers={"User-Agent": UA}, timeout=25).text
    except Exception:  # noqa: BLE001
        return "", ""
    return html, trafilatura.extract(html, include_comments=False, include_tables=True) or ""


def _domain(url: str) -> str:
    from urllib.parse import urlparse
    return urlparse(url).netloc.lower().removeprefix("www.")


def official_links(html: str) -> list[str]:
    """Enlaces a organismos oficiales que cita la fuente (para que la IA los use como fuente principal)."""
    dominios = ("boe.es", "bde.es", "ecb.europa.eu", "tesoro.es", "cnmv.es", "agenciatributaria.", "ine.es", "lamoncloa.gob.es", "gob.es")
    links = re.findall(r'href=["\'](https?://[^"\']+)["\']', html or "")
    out = []
    for l in links:
        if any(d in _domain(l) for d in dominios) and l not in out:
            out.append(l)
    return out[:8]


# Webs oficiales en las que la IA puede buscar el documento original
DOMINIOS_OFICIALES = ('boe.es', 'bde.es', 'ecb.europa.eu', 'tesoro.es', 'cnmv.es', 'agenciatributaria.gob.es', 'agenciatributaria.es', 'ine.es', 'lamoncloa.gob.es', 'hacienda.gob.es', 'economia.gob.es', 'dgsfp.mineco.es', 'fgd.es', 'poderjudicial.es', 'eur-lex.europa.eu')

# ---------- 3. redactar con IA ----------
SYSTEM = """Eres redactor de Dinero en Claro, una web española que explica a particulares las noticias de ahorro e \
inversión: depósitos, Letras del Tesoro, tipos de interés, fondos y ETF, bolsa, planes de pensiones, neobancos y \
brókeres online e impuestos del ahorro. Escribes en español de España, tuteando al lector, con tono claro, sereno y riguroso. Frases cortas. Sin \
jerga innecesaria: si usas un término técnico (TAE, TER, prima de riesgo), explícalo en una frase. Nada de muletillas.

PRINCIPIOS (obligatorios):
- RESPUESTA ARRIBA: la entradilla y el primer párrafo dan ya el dato principal (cuánto, cuándo, a quién afecta).
- SOLO HECHOS DE LA FUENTE: usa únicamente los datos del texto fuente. Nada de inventar cifras, fechas, rentabilidades \
ni citas. Un cálculo sencillo deducido de los datos (por ejemplo, cuánto ganan 10.000 € a ese tipo) vale si dices que \
es un ejemplo.
- NADA DE RECOMENDACIONES DE INVERSIÓN: nunca digas que conviene comprar, vender o mantener un valor, fondo o \
producto, ni des precios objetivo, ni presentes una inversión como segura o garantizada si no lo es. Si la fuente \
recoge recomendaciones de analistas, puedes mencionarlas atribuidas ("según X") pero sin hacerlas tuyas, y añade que \
no son una recomendación de esta web. Si hablas de rentabilidades pasadas, recuerda que no garantizan las futuras.
- SIN MARCAS GRATIS: no promociones bancos, brókeres ni productos concretos. Si una noticia trata de una entidad, \
informa del hecho (una nueva comisión, una sanción de la CNMV, un cambio de tipo) sin hacer publicidad. \
En neobancos y brókeres, di desde cuándo se aplica el cambio, a quién afecta y, si la fuente lo dice, qué fondo de \
garantía protege el dinero (el español o el de otro país). Nunca digas cuál es «el mejor».
- REDACCIÓN 100 % PROPIA: no copies frases ni la estructura del original.
- APORTA ALGO PROPIO (obligatorio, y es lo primero que se mira): el artículo tiene que incluir (a) un ejemplo con cifras calculado a partir de los datos de la fuente o del documento oficial (cuánto rinden 10.000 € a ese tipo después de impuestos, cuánto se lleva una comisión en 10 años), diciendo que es un ejemplo, o (b) un dato concreto del documento oficial que el medio no da. Además, si encaja, explica qué significa para quien ya tiene ese producto, sin recomendar, y enlaza la calculadora o guía nuestra que le deja calcular su caso. Un enlace o un comentario general NO bastan. Si no puedes aportar (a) ni (b), o si la noticia solo repite lo que ya cuentan otros medios o lo que ya publicamos, descártala con {"skip": true, "reason": "sin valor propio: ..."}. Es mejor no publicar que publicar una noticia más.
- FUENTE OFICIAL: si la fuente es un medio y menciona un organismo o una norma (BCE, Banco de España, Tesoro, CNMV, \
BOE, Agencia Tributaria, INE…), atribúyelo a ese organismo y enlázalo si tienes su enlace. Si no, "según publica X".
- ANUNCIADO ≠ APROBADO: si es una propuesta o un cambio pendiente, dilo claramente y pon "pendiente": true.
- NEUTRALIDAD: no opines sobre partidos ni sobre si una medida es buena o mala; recoge las posturas atribuidas.
- TITULAR HONESTO: con el dato (el tipo, la cifra, la fecha) y que se cumpla en el texto. Prohibidos los titulares \
que prometen ganancias ("gana un 10 %"), meten miedo ("desplome", "pánico") sin dato que lo justifique o esconden de \
qué se habla.
- A QUIÉN AFECTA, EN EL TITULAR: si afecta a un grupo concreto, nómbralo ("ahorradores", "quien tiene un plan de \
pensiones", "hipotecados", "inversores en fondos").

QUÉ SE DESCARTA ({"skip": true, "reason": "..."}):
- Lo que no le sirve a un ahorrador o inversor particular en España: resultados de una empresa concreta sin interés \
general (ver la excepción de RESULTADOS más abajo), operaciones corporativas, movimientos de un día de un valor, macroeconomía sin efecto en el ahorro, otros \
países (salvo el BCE o la Reserva Federal cuando mueven los tipos o los mercados).
- Nombramientos, trámites internos, correcciones de errores menores.
- Hipotecas, euríbor para hipotecados, alquiler y vivienda: los cubre nuestra web hermana Al Final de Mes (alfinaldemes.com). Escribe del euríbor o de los tipos solo desde el punto de vista del ahorrador o el inversor (depósitos, Letras, bonos) y, si hablas de hipotecas, enlaza https://alfinaldemes.com/vivienda/euribor-hoy/.
- Las crónicas diarias de bolsa (cómo cerró el Ibex o los mercados un día concreto): para eso está la página /bolsa/ibex-35-hoy/. Solo escribe de bolsa si hay un movimiento excepcional o una novedad que afecte al ahorrador.
- Lo que ya cubre una de nuestras guías sin aportar un dato nuevo importante: ese dato se añade a la guía, no se publica como noticia suelta. Google valora la web por su contenido propio, no por el número de noticias.
- Lo que trata de lo mismo que un artículo ya publicado, salvo que aporte un dato nuevo relevante. \
  Cuenta como repetición aunque el título sea distinto: el mismo informe, entrevista o reportaje contado por \
otro medio (por ejemplo, el mismo reportaje de Bloomberg o las mismas declaraciones de un directivo), o un \
detalle secundario de una noticia ya publicada. Revisa sobre todo los primeros de la lista, que son los más recientes.
- Opiniones, previsiones sin datos, rumores y contenido promocional de una entidad.

RESULTADOS (excepción): solo escribe sobre los resultados trimestrales de las empresas más grandes y con más \
pequeños accionistas (Santander, BBVA, CaixaBank, Iberdrola, Inditex, Telefónica, Repsol, Endesa, Naturgy; Apple, \
Microsoft, Nvidia, Alphabet, Amazon, Meta, Coca-Cola, Johnson & Johnson) y solo si anuncian algo que cambia lo que \
recibe o puede esperar el accionista: un dividendo nuevo, subido o recortado, recompras de acciones, un cambio de \
previsiones o de política de reparto. Escríbelo como un análisis para el pequeño accionista, no como una crónica del \
beneficio: qué recibirá, cuándo (fechas del dividendo), cómo tributa y qué conviene vigilar. Enlaza la guía de \
dividendos y el calendario de resultados. Unos resultados sin novedades para el accionista se descartan.

LONGITUD: un dato, 400-500 palabras como mínimo, con el contexto y lo que significa para el lector; un cambio con condiciones, 500-900. Nunca rellenes.

ESTRUCTURA: subtítulos ## con preguntas reales ("¿Cuánto rinden ahora?", "¿Cómo afecta a mi hipoteca?", "¿Cómo \
tributa?"). Una tabla si hay cifras que comparar. Termina con lo siguiente que conviene vigilar (la próxima reunión del \
BCE, la próxima subasta), sin frases hechas.

SECCIÓN (category):
- ahorro: depósitos, cuentas remuneradas, Letras y bonos del Tesoro para particulares, tipos de interés y su efecto en el ahorro.
- fondos: fondos de inversión, ETF, comisiones, traspasos, gestoras.
- bolsa: bolsa, Ibex 35 y otros índices, BCE y Reserva Federal, inflación y mercados.
- jubilacion: planes de pensiones individuales y de empleo, límites, rescates, ahorro a largo plazo, pensión pública y su complemento.
- impuestos: fiscalidad de intereses, dividendos y ganancias, declaración de la renta del inversor, impuestos sobre el patrimonio.

CIFRAS CON SU ORIGEN: di siempre de qué dato es cada cifra y de qué fecha (subasta o mercado secundario; tipo marginal o medio; dato diario o media mensual). Si la noticia es de un medio sobre un dato oficial (subasta del Tesoro, tipos del BCE, euríbor, IPC, CNMV), da la cifra oficial y enlaza la fuente primaria o nuestra página de datos; si el medio y el dato oficial no coinciden, explica por qué.
BUSCA LA FUENTE OFICIAL: si la noticia trata de una norma, una ayuda, una sentencia, un dato o una decisión de un organismo y no tienes el enlace al documento, usa la búsqueda web (solo busca en webs oficiales) para encontrarlo. Puedes usar los datos del documento oficial; si no coinciden con los del medio, manda el oficial y dilo en el texto. Si no lo encuentras en dos o tres búsquedas, sigue sin él. Responde al final solo con el JSON.
FUENTE OFICIAL: en "official_source" pon solo un enlace a la página concreta del documento o dato oficial, nunca la portada de un organismo. Si no lo tienes, null.

ENLACES INTERNOS: incluye 1-3 enlaces a artículos de la lista "ya publicados" o a estas herramientas si encajan: \
/ahorro/letras-del-tesoro/, /ahorro/calculadora-depositos/, /ahorro/calculadora-interes-compuesto/, \
/bolsa/tipos-de-interes/, /bolsa/ibex-35-hoy/, /bolsa/dividendos-que-son-cuando-se-cobran-y-como-tributan/, \
/bolsa/calendario-de-resultados/, /fondos/comisiones/, /impuestos/calculadora-impuestos-inversiones/, \
/jubilacion/calculadora-plan-de-pensiones/.

FORMATO DE RESPUESTA: solo un objeto JSON válido, sin texto alrededor:
{
  "skip": false,
  "category": "ahorro" | "fondos" | "bolsa" | "jubilacion" | "impuestos",
  "pendiente": true | false,
  "title": "titular de 45-60 caracteres (Google corta a partir de unos 60), concreto, con la cifra o fecha si existe. Nunca pongas en el título el medio de origen ni «según X»: la atribución va en el texto",
  "card_title": "versión corta del titular para la imagen de portada, máximo 70 caracteres",
  "foto": "tema de la foto de portada que mejor encaja, de esta lista: {temas_foto}; o \"\" si ninguno encaja de verdad",
  "foto_busqueda": "siempre (se usa si las fotos del banco de ese tema ya están repetidas): 2-4 palabras EN INGLÉS para buscar en un banco de fotos libres una foto real y genérica que encaje (ej. \"electricity bill\", \"retired couple walking\", \"stock market screen\"); sin marcas, logotipos, políticos ni personas concretas; \"\" si la noticia no admite una foto genérica",
  "foto_alt": "descripción breve en español de esa escena genérica, para el texto alternativo (ej. \"Factura de la luz sobre una mesa\")",
  "description": "entradilla de 130-160 caracteres que ya responde a la pregunta",
  "tags": ["3-5 etiquetas en minúsculas"],
  "slug": "dirección corta: 4-8 palabras clave en minúsculas separadas por guiones, sin tildes, sin artículos ni preposiciones sueltas, máximo 60 caracteres y sin cortar palabras",
  "official_source": {"name": "nombre del documento u organismo oficial", "url": "enlace oficial"} | null,
  "body": "artículo en Markdown, sin el título como # al principio"
}"""
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from banco import TEMAS as _TEMAS_FOTO, elegir as elegir_foto
except Exception:  # noqa: BLE001
    _TEMAS_FOTO, elegir_foto = [], None
SYSTEM = SYSTEM.replace("{temas_foto}", ", ".join(_TEMAS_FOTO) or "(ninguno)")


# Caché de Claude: las instrucciones y la lista de artículos son iguales en todas las llamadas de una
# ejecución, así que a partir de la segunda se cobran a una fracción del precio.
SYSTEM_CACHE = [{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}]


def con_cache(contexto: str, resto: str) -> list[dict]:
    return [{"type": "text", "text": contexto, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": resto}]

_CLIENT = None


def refresh_github_identity() -> None:
    """En GitHub Actions, pide un pase de identidad nuevo (caduca en minutos y es de un solo uso)."""
    import requests

    url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL")
    req_token = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    path = os.environ.get("ANTHROPIC_IDENTITY_TOKEN_FILE")
    if not (url and req_token and path):
        return
    r = requests.get(url, params={"audience": "https://api.anthropic.com"},
                     headers={"Authorization": f"Bearer {req_token}"}, timeout=15)
    r.raise_for_status()
    Path(path).write_text(r.json()["value"], encoding="utf-8")


def get_client():
    global _CLIENT
    if _CLIENT is None:
        import anthropic
        refresh_github_identity()
        _CLIENT = anthropic.Anthropic()
    return _CLIENT


def datos_oficiales() -> str:
    """Resumen de los datos oficiales que ya descarga la web (Banco de España, BCE, Tesoro), con su fecha,
    para que la IA cite la cifra oficial en lugar de la de un medio y diga de qué dato y fecha se trata."""
    lineas = []
    try:
        m = json.loads((ROOT / "src" / "data" / "mercados.json").read_text(encoding="utf-8"))
        b = m.get("bce", {})
        if b.get("deposito"):
            lineas.append(f"- BCE, facilidad de depósito: {b['deposito']['valor']} % desde el {b['deposito']['desde']}")
        for plazo, l in sorted(m.get("letras", {}).items(), key=lambda x: int(x[0])):
            lineas.append(f"- Letras a {plazo} meses, última subasta (emisión {l['fecha']}): tipo marginal {l['tipo']} % "
                          f"(el tipo medio que reciben los particulares suele ser unas centésimas menor) → /ahorro/letras-del-tesoro/")
        nombres = {"letra_1a": "Letra a 1 año", "bono_3a": "Bono a 3 años", "bono_5a": "Bono a 5 años", "bono_10a": "Bono a 10 años"}
        for k, s in m.get("secundario", {}).items():
            lineas.append(f"- {nombres.get(k, k)}, mercado secundario (no subasta), {s['fecha']}: {s['valor']} % → /bolsa/tipos-de-interes/")
    except (OSError, ValueError, KeyError):
        pass
    try:
        e = json.loads((ROOT / "src" / "data" / "euribor.json").read_text(encoding="utf-8"))
        lineas.append(f"- Euríbor a 12 meses, dato diario del {e['fecha']}: {e['valor']} %; media de {e['mes']} hasta ahora: {e['media_mes']} % → /bolsa/tipos-de-interes/")
    except (OSError, ValueError, KeyError):
        pass
    if not lineas:
        return ""
    return ("DATOS OFICIALES AL DÍA (Banco de España, con datos del Tesoro y del BCE; úsalos y cítalos si la noticia trata de "
            "estos tipos, diciendo siempre de qué dato y de qué fecha es cada cifra):\n" + "\n".join(lineas) + "\n\n")


def write_article(item: dict, source_text: str, oficiales: list[str], posts: list[dict]) -> dict | None:
    client = get_client()
    refresh_github_identity()
    related = "\n".join(f"- {'[GUÍA] ' if p['guia'] else ''}{p['title']} → {p['url']}" for p in _para_enlazar(posts)) or "(ninguno aún)"
    hoy = datetime.now(MADRID).date().isoformat()
    contexto = f"ARTÍCULOS YA PUBLICADOS EN LA WEB:\n{related}"
    user = (
        f"HOY ES: {hoy}\n"
        f"FUENTE: {item['source']}{' (oficial)' if item.get('oficial') else ''}\nTÍTULO ORIGINAL: {item['title']}\nURL: {item['url']}\n"
        + (f"ENLACES OFICIALES QUE CITA LA FUENTE:\n" + "\n".join(oficiales) + "\n" if oficiales else "")
        + f"\nTEXTO FUENTE:\n\"\"\"\n{source_text[:MAX_FUENTE]}\n\"\"\""
    )
    mensajes = [{"role": "user", "content": con_cache(contexto, user)}]
    try:
        # Búsqueda solo en webs oficiales, para encontrar el documento (BOE, nota de prensa, tabla…) cuando el medio no lo enlaza
        msg = client.messages.create(model=MODEL, max_tokens=16000, system=SYSTEM_CACHE, messages=mensajes,
                                     tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3,
                                             "allowed_domains": list(DOMINIOS_OFICIALES)}])
        for _ in range(3):  # si la búsqueda se alarga, la API pausa el turno: se le deja seguir
            if msg.stop_reason != "pause_turn":
                break
            mensajes = mensajes + [{"role": "assistant", "content": msg.content}]
            msg = client.messages.create(model=MODEL, max_tokens=16000, system=SYSTEM_CACHE, messages=mensajes,
                                         tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3,
                                                 "allowed_domains": list(DOMINIOS_OFICIALES)}])
    except Exception as e:  # noqa: BLE001  (si la búsqueda no está disponible, se redacta como antes)
        print(f"  · sin búsqueda de fuente oficial ({type(e).__name__}): se redacta solo con la fuente")
        msg = client.messages.create(model=MODEL, max_tokens=16000, system=SYSTEM_CACHE, messages=mensajes)
    textos = [b.text for b in msg.content if b.type == "text"]
    raw = (textos[-1] if textos else "").strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.M).strip()
    if not raw.startswith("{") and "{" in raw:  # por si la IA comenta algo antes del JSON
        raw = raw[raw.index("{"): raw.rindex("}") + 1]
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("  ! respuesta no válida de la IA, se omite")
        return None
    if data.get("skip"):
        print(f"  – descartada: {data.get('reason', '')}")
        return None
    if data.get("category") not in CATEGORIES or not data.get("title") or not data.get("body"):
        print("  ! faltan campos, se omite")
        return None
    return data


def yaml_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').strip() + '"'


def save_post(data: dict, item: dict) -> Path:
    slug = slugify(data.get("slug") or data["title"], 60)
    path = POSTS_DIR / f"{slug}.md"
    i = 2
    while path.exists():
        path = POSTS_DIR / f"{slug}-{i}.md"
        i += 1
    slug = path.stem

    # Portada: una foto real del banco si encaja con la noticia (Discover las prefiere);
    # si no, la portada con el titular
    img_lines = ""
    foto = None
    try:
        foto = elegir_foto(data["title"], data["category"], data.get("foto") or "", repetir=False) if elegir_foto else None
    except Exception as e:  # noqa: BLE001
        print(f"  ! no se pudo elegir foto: {e}")
    if foto:
        img_lines = (f"image: /img/banco/{foto['slug']}.webp\nimageAlt: {yaml_str(foto['alt'])}\n"
                     f"imageCredit: {yaml_str(foto['credito'])}\nimageCreditUrl: {yaml_str(foto['pagina'])}\n")
    # Si ninguna foto del banco encaja: una foto libre de Pixabay u Openverse buscada con lo que propone la IA
    if not foto and data.get("foto_busqueda"):
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from fotos_libres import buscar as buscar_foto_libre
            libre = buscar_foto_libre(data["foto_busqueda"], slug)
            if libre:
                alt = (data.get("foto_alt") or data["title"])[:150]
                img_lines = (f"image: {libre['ruta']}\nimageAlt: {yaml_str(alt)}\n"
                             f"imageCredit: {yaml_str(libre['credito'])}\nimageCreditUrl: {yaml_str(libre['pagina'])}\n")
        except Exception as e:  # noqa: BLE001
            print(f"  ! no se pudo buscar foto libre: {e}")
    # Sin foto libre: una del banco aunque ya esté usada, antes que la portada con el titular
    if not img_lines and elegir_foto:
        try:
            foto = elegir_foto(data["title"], data["category"], data.get("foto") or "", repetir=True)
        except Exception as e:  # noqa: BLE001
            print(f"  ! no se pudo elegir foto: {e}")
            foto = None
        if foto:
            img_lines = (f"image: /img/banco/{foto['slug']}.webp\nimageAlt: {yaml_str(foto['alt'])}\n"
                         f"imageCredit: {yaml_str(foto['credito'])}\nimageCreditUrl: {yaml_str(foto['pagina'])}\n")
    if not img_lines:
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from miniaturas import make_variants, make_crops
            img = crear_portada(data.get("card_title") or data["title"], data["category"], IMG_DIR / f"{slug}.webp")
            make_variants(img)
            make_crops(img)
            img_lines = f"image: /img/articulos/{slug}.webp\nimageAlt: {yaml_str(data['title'][:140])}\n"
        except Exception as e:  # noqa: BLE001
            print(f"  ! no se pudo crear la portada: {e}")

    fuentes = []
    of = data.get("official_source") or {}
    from urllib.parse import urlparse
    concreta = len(urlparse(of.get("url", "")).path.strip("/")) > 0  # nada de portadas tipo "https://www.ine.es"
    if of.get("url", "").startswith("http") and of.get("name") and concreta:
        fuentes.append((of["name"], of["url"]))
    if not any(u == item["url"] for _, u in fuentes):
        fuentes.append((f"{item['source']}: {item['title'][:100]}", item["url"]))
    if len(fuentes) == 1 and fuentes[0][1] == item["url"] and not item.get("oficial"):
        SIN_OFICIAL.append(slug)  # solo el medio: se avisa en la propuesta
    src_yaml = "".join(f"  - name: {yaml_str(n)}\n    url: {yaml_str(u)}\n" for n, u in fuentes)

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    tags = ", ".join(yaml_str(slugify(t, 30)) for t in data.get("tags", [])[:5])  # entre comillas: "2027" es texto
    fm = (
        "---\n"
        f"title: {yaml_str(data['title'][:110])}\n"
        f"description: {yaml_str(data['description'][:170])}\n"
        f"date: {now}\n"
        f"category: {data['category']}\n"
        f"tags: [{tags}]\n"
        f"pendiente: {'true' if data.get('pendiente') else 'false'}\n"
        f"{img_lines}"
        f"sources:\n{src_yaml}"
        "---\n\n"
    )
    path.write_text(fm + data["body"].strip() + "\n", encoding="utf-8")
    return path


# ---------- main ----------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="solo listar candidatos, sin IA ni escritura")
    ap.add_argument("--url", default="", help="redactar solo esta noticia (enlace)")
    args = ap.parse_args()

    cfg = json.loads(FEEDS_FILE.read_text(encoding="utf-8"))
    state = load_state()
    posts = existing_posts()
    # también los borradores de ejecuciones anteriores que aún esperan aprobación (no están publicados)
    vistos_urls = {x["url"] for x in posts}
    for e in reversed(state.get("escritos", [])):
        if e["url"] not in vistos_urls:
            posts.insert(0, e)

    print("Buscando novedades…")
    url_forzada = (args.url or os.environ.get("RADAR_URL", "")).strip()
    if url_forzada:
        print(f"Noticia indicada a mano: {url_forzada}")
        html_tmp, _ = fetch_page(url_forzada)
        t = re.search(r"<title[^>]*>(.*?)</title>", html_tmp or "", re.I | re.S)
        oficial = any(d in _domain(url_forzada) for d in ("boe.es", "bde.es", "ecb.europa.eu", "tesoro.es", "cnmv.es", "agenciatributaria.", "gob.es"))
        candidates = [{"source": _domain(url_forzada) or "fuente", "url": url_forzada, "oficial": oficial,
                       "title": re.sub(r"\s+", " ", t.group(1)).strip() if t else url_forzada}]
    else:
        candidates = collect_candidates(cfg, state, posts)
    print(f"{len(candidates)} candidatas nuevas")
    if os.environ.get("GITHUB_ACTIONS"):
        # resumen visible en la página de la ejecución (anotaciones de GitHub)
        print(f"::notice title=Fuentes::{' · '.join(RESUMEN) or 'noticia indicada a mano'}")
        print(f"::notice title=Candidatas ({len(candidates)})::" + " | ".join(f"[{c['source']}] {c['title'][:80]}" for c in candidates[:12]))
    if args.dry_run:
        for c in candidates:
            print(f"  - [{c['source']}] {c['title']}\n    {c['url']}")
        return 0
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_IDENTITY_TOKEN_FILE")):
        print("Faltan credenciales: ANTHROPIC_API_KEY o la federación de identidades (ANTHROPIC_IDENTITY_TOKEN_FILE)")
        return 1

    hoy_madrid = datetime.now(MADRID).date().isoformat()
    por_dia = {d: n for d, n in state.get("por_dia", {}).items() if d >= (datetime.now(MADRID).date() - timedelta(days=10)).isoformat()}
    state["por_dia"] = por_dia
    if not url_forzada and por_dia.get(hoy_madrid, 0) >= MAX_PER_DAY:
        print(f"Ya hay {por_dia[hoy_madrid]} artículos hoy (tope {MAX_PER_DAY}): no se escribe más hasta mañana")
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"::notice title=Tope diario::Ya hay {por_dia[hoy_madrid]} artículos hoy (tope {MAX_PER_DAY})")
        save_state(state)
        return 0
    restantes = MAX_PER_DAY - por_dia.get(hoy_madrid, 0) if not url_forzada else MAX_PER_RUN

    if not url_forzada and len(candidates) > 1:
        candidates, quitadas = prefiltrar(get_client(), candidates, posts, SYSTEM)
        for c, motivo in quitadas:  # se recuerdan como vistas para no volver a revisarlas
            state["urls"].append(c["url"])
            state["titles"].append(norm_title(c["title"]))

    written, errors, intentos = [], 0, 0
    for item in candidates:
        # cada candidata cuesta una consulta a la IA aunque se descarte: tope para no gastar de más
        if len(written) >= min(MAX_PER_RUN, restantes) or intentos >= MAX_PER_RUN * 4:
            break
        print(f"→ [{item['source']}] {item['title']}")
        state["urls"].append(item["url"])
        state["titles"].append(norm_title(item["title"]))
        html, text = fetch_page(item["url"])
        if len(text) < MIN_SOURCE_CHARS:
            print("  – texto insuficiente, se omite")
            continue
        intentos += 1
        try:
            data = write_article(item, text, official_links(html), posts)
        except Exception as e:  # noqa: BLE001
            print(f"  ! error al redactar: {type(e).__name__}: {str(e)[:200]}")
            state["urls"].remove(item["url"])
            state["titles"].pop()
            errors += 1
            if errors >= 2:
                print("  ! dos errores seguidos, se detiene esta ejecución")
                break
            continue
        if data:
            p = save_post(data, item)
            written.append(p)
            por_dia[hoy_madrid] = por_dia.get(hoy_madrid, 0) + 1
            nuevo = {"title": data["title"], "url": f"/{data['category']}/{p.stem}/", "guia": False}
            posts.insert(0, nuevo)
            # se recuerda en la memoria del robot, que se guarda en main, para que la próxima ejecución lo vea
            # aunque el borrador aún no se haya aprobado
            state.setdefault("escritos", []).append(nuevo)
            state["escritos"] = state["escritos"][-80:]
            print(f"  ✓ {p.relative_to(ROOT)}")

    save_state(state)
    print(f"\nArtículos nuevos: {len(written)}\n" + "\n".join(f"- {p.stem}" for p in written))
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as fh:
            fh.write(f"count={len(written)}\n")
            fh.write("titulos=" + " | ".join(p.stem for p in written) + "\n")
            fh.write("sin_oficial=" + ", ".join(SIN_OFICIAL) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
