# Al Final de Mes — alfinaldemes.com

Web de noticias y herramientas de economía doméstica en España (pensiones, paro y ayudas, Hacienda y luz).
Misma base que Zona Leonida: web estática (Astro) publicada en Cloudflare Pages + robots en GitHub Actions.

## Cómo funciona

```
Cada 2 h (de 7 a 23 h) → el radar (scripts/radar.py) lee el BOE del día y las fuentes de scripts/feeds.json
                       → se queda con lo que afecta al bolsillo y no está ya publicado
                       → Claude redacta un artículo ORIGINAL con la fuente oficial enlazada y su portada
                       → te llega una propuesta (pull request) y un aviso por Telegram
Tú                     → la revisas en la app de GitHub (sobre todo cifras y fechas) y pulsas "Merge"
Cloudflare             → publica la web en ~1 minuto, y el canal de Telegram recibe el artículo

Cada noche y cada tarde → scripts/luz.py descarga el precio de la luz de Red Eléctrica
                         → si cambia, se publica directamente (es un dato oficial, sin redacción)
```

## Dónde se cambia cada cosa

| Qué | Archivo |
|---|---|
| Nombre, dominio, autor, AdSense, redes | `src/config.ts` (el dominio también en `astro.config.mjs`) |
| Artículos | `src/content/posts/*.md` (uno por archivo) |
| Fuentes y palabras clave del robot | `scripts/feeds.json` |
| Normas de redacción de la IA | `SYSTEM` en `scripts/radar.py` |
| Frecuencia de los robots | `cron` en `.github/workflows/*.yml` |
| Portadas automáticas | `scripts/portada.py` (`python scripts/portada.py --fijas` rehace las fijas) |

### Formato de un artículo

```markdown
---
title: "Titular concreto con la cifra o la fecha"
description: "Entradilla que ya responde (130-160 caracteres)"
date: 2026-10-20T10:00:00+02:00     # si pones una fecha futura, se publica ese día
updated: 2026-10-21T09:00:00+02:00  # opcional
category: pensiones                 # luz | pensiones | paro | hacienda
tags: [paga-extra, jubilacion]
guia: false                         # true = guía viva (se actualiza en la misma dirección)
pendiente: false                    # true = anunciado pero aún no publicado en el BOE
image: /img/articulos/mi-portada.webp
sources:
  - name: "BOE: Real Decreto ..."
    url: "https://www.boe.es/..."
correcciones:                       # opcional: se muestran en el artículo y en /correcciones/
  - fecha: 2026-10-21
    texto: "La cuantía correcta es 480 euros, no 450."
---

Texto en Markdown con subtítulos ## ...
```

## Conexión con Claude

Sin claves: federación de identidades. En la consola de Claude están el espacio de trabajo **Al Final de Mes**
(con su propio límite de gasto), la cuenta de servicio `robot-al-final-de-mes` y la regla `robot-al-final-de-mes`,
que solo acepta este repositorio y la rama `main`. Los identificadores están en `.github/workflows/radar.yml`.

## Secretos y variables de GitHub (Settings → Secrets and variables → Actions)

| Nombre | Tipo | Para qué |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Secreto | El mismo bot de Zona Leonida |
| `TELEGRAM_AVISOS_CHAT_ID` | Secreto | Tu chat privado: avisos de borradores y fallos |
| `TELEGRAM_CHAT` | Variable | El canal público, por ejemplo `@alfinaldemes` |
| `MAX_PER_RUN` | Variable | Artículos máximos por pasada (2 por defecto) |
