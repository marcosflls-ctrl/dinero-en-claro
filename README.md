# Dinero en Claro — dineroenclaro.com

Web de ahorro e inversión para particulares en España: depósitos y Letras, fondos y ETF, bolsa y tipos de interés,
planes de pensiones e impuestos del inversor. Explica productos, costes e impuestos con datos oficiales,
**sin recomendar productos concretos**.

Misma base que Zona Leonida y Al Final de Mes (web estática con Astro + robots en GitHub Actions), con una diferencia:
**se publica en Bunny.net, no en Cloudflare Pages** (Bunny no lo bloquean los operadores durante el fútbol).

## Cómo funciona

```
Cada 2 h (de 8 a 22 h) → el radar (scripts/radar.py) lee el BOE del día y las fuentes de scripts/feeds.json
                       → se queda con lo que afecta al ahorro y la inversión y no está ya publicado
                       → Claude redacta un artículo ORIGINAL con su fuente y su portada
                       → arreglar_enlaces.py corrige los enlaces internos que apunten a la sección equivocada
                       → te llega una propuesta (pull request) y un aviso por Telegram
Tú                     → la revisas en la app de GitHub (sobre todo cifras y fechas) y pulsas "Merge"
Bunny.net              → «Publicar en Bunny» construye la web y la sube en unos minutos

Lunes a sábado, varias veces al día:
  scripts/euribor.py   → euríbor a 12 meses del Banco de España (dato diario y media del mes)
  scripts/mercados.py  → tipos del BCE, subastas de Letras, bonos, Ibex 35 y Bolsa de Madrid
                       → si cambian, se publican directamente (son datos oficiales, sin redacción)
```

## Tareas automáticas (pestaña Actions)

| Tarea | Cuándo | Qué hace |
|---|---|---|
| Radar de noticias | Cada 2 h, de 8 a 22 h | Busca noticias y propone borradores. Con «Run workflow» puedes pegar un enlace concreto o marcar «solo listar» |
| Euríbor | L-S, 5 veces al día | Actualiza `src/data/euribor.json` |
| Datos de mercado | L-S, 4 veces al día | Actualiza `src/data/mercados.json` |
| Publicar en Bunny | Con cada cambio, tras los robots, cada mañana (7:07) y a mano | Construye y sube la web; publica los artículos programados |
| Publicar en Telegram | Al publicar artículos nuevos, o a mano con nombres de archivo | Los anuncia en el canal |
| Banco de fotos | A mano | Busca fotos con licencia libre en Wikimedia Commons para las portadas |
| Probar fuentes | A mano | Comprueba qué fuentes de `feeds.json` responden |
| Descargar documento | A mano | Descarga un documento oficial a la rama `descargas` cuando no se alcanza desde otro sitio |

Si algo falla, el bot de Telegram te avisa en privado.

## Dónde se cambia cada cosa

| Qué | Archivo |
|---|---|
| Nombre, dominio, AdSense, redes, webs hermanas del pie | `src/config.ts` (el dominio también en `astro.config.mjs`) |
| Secciones (ahorro, fondos, bolsa, jubilación, impuestos) | `CATEGORIES` en `src/config.ts` |
| Artículos y guías | `src/content/posts/*.md` (uno por archivo) |
| Calculadoras que salen en el menú y la portada | `src/data/herramientas.ts` |
| Datos de los fondos y ETF de las comparativas | `src/data/fondos.json` |
| Cálculo de impuestos (tramos del ahorro, retenciones) | `src/lib/fiscal.ts` |
| Fuentes y palabras clave del robot | `scripts/feeds.json` |
| Normas de redacción de la IA | `SYSTEM` en `scripts/radar.py` |
| Fotos del banco de portadas | `scripts/banco.json` |
| Redirecciones | `public/_redirects` (el script de Bunny las convierte en páginas que redirigen) |
| Frecuencia de los robots | `cron` en `.github/workflows/*.yml` |

### Calculadoras

Letras del Tesoro, interés compuesto, depósitos y cuentas, impuestos de las inversiones, plan de pensiones,
comisiones de fondos y tipos de interés hoy (con gráfico del euríbor y el BCE de los últimos tres años).
Usan los datos de `src/data/` y las reglas fiscales de 2026: en enero hay que revisar `src/lib/fiscal.ts`.

### Formato de un artículo

```markdown
---
title: "Titular concreto con la cifra o la fecha"
description: "Entradilla que ya responde (130-160 caracteres)"
date: 2026-10-20T10:00:00+02:00     # si pones una fecha futura, se publica ese día
updated: 2026-10-21T09:00:00+02:00  # opcional
category: ahorro                    # ahorro | fondos | bolsa | jubilacion | impuestos
tags: [letras-del-tesoro]
guia: false                         # true = guía viva (se actualiza en la misma dirección)
image: /img/articulos/mi-portada.webp
sources:
  - name: "Tesoro Público: resultado de la subasta"
    url: "https://..."
correcciones:                       # opcional: se muestran en el artículo y en /correcciones/
  - fecha: 2026-10-21
    texto: "El tipo correcto es 2,10 %, no 2,01 %."
---

Texto en Markdown con subtítulos ## ...
```

Los artículos los firma «Redacción Dinero en Claro», sin nombre personal.

## Conexión con Claude

Sin claves: federación de identidades. En la consola de Claude están el espacio de trabajo **Dinero en Claro**,
su cuenta de servicio y la regla de federación, que solo acepta este repositorio y la rama `main`.
Sus identificadores se guardan como **variables** (no secretos) del repositorio. **El radar no arranca hasta que
exista la variable `ANTHROPIC_FEDERATION_RULE_ID`.**

## Secretos y variables de GitHub (Settings → Secrets and variables → Actions)

Los valores los pegas tú; nunca van en el chat ni en los archivos.

| Nombre | Tipo | Para qué |
|---|---|---|
| `BUNNY_STORAGE_PASSWORD` | Secreto | Contraseña del almacenamiento de Bunny (FTP & API access) |
| `BUNNY_API_KEY` | Secreto | Clave de la cuenta de Bunny, para limpiar la caché |
| `TELEGRAM_BOT_TOKEN` | Secreto | El mismo bot de las otras webs |
| `TELEGRAM_AVISOS_CHAT_ID` | Secreto | Tu chat privado: avisos de borradores y fallos |
| `TELEGRAM_CHAT` | Variable | El canal público |
| `ANTHROPIC_FEDERATION_RULE_ID`, `ANTHROPIC_SERVICE_ACCOUNT_ID`, `ANTHROPIC_WORKSPACE_ID` | Variables | Conexión con Claude |
| `MAX_PER_RUN` | Variable | Artículos máximos por pasada (2 por defecto) |

El nombre del almacenamiento (`dinero-en-claro`), el número de la distribución y los dominios de Bunny
están en `.github/workflows/publicar-bunny.yml`.

## Últimos cambios (octubre de 2026)

- **17/10:** paso a Bunny.net; las direcciones de los artículos se cortan en un guion, sin palabras sueltas al final.
- **18/10:** gráfico del euríbor y el BCE; guías permanentes (Fondo de Garantía de Depósitos, TAE y TIN, traspaso de
  fondos, opciones de ahorro, deuda del Estado, bróker extranjero en la renta, inflación, MSCI World y S&P 500,
  fondo de emergencia). El robot usa fuentes primarias, evita repeticiones y debe aportar algo propio en cada artículo.
- **19/10:** guías de ETF, tipos de fondos y documento de datos fundamentales; comparativas de fondos indexados,
  ETF y fondos monetarios con fichas individuales y gráfico por años; la Caife pasa a guía viva.
  **Prevención AdSense** (tras el rechazo de Zona Leonida): el robot ya no escribe crónicas diarias de bolsa,
  hace noticias más completas y nunca pone «según X» en el título.

## Probar en tu ordenador

```bash
npm install
npm run dev                         # http://localhost:4321
python scripts/radar.py --dry-run   # ver qué noticias encontraría, sin gastar IA
```
