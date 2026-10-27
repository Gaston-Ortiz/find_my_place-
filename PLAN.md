# Plan: detección de oportunidades de compra inmobiliaria

## Objetivo

Obtener a diario **todos** los avisos de **venta** de casas y terrenos de compraensanjuan.com,
guardarlos en **Postgres** como un set de datos limpio y completo (lo menos nulos posible),
con historial de precios. Sobre ese set, más adelante, un modelo detectará oportunidades
de compra: avisos cuyo precio está claramente por debajo de lo que valen propiedades
comparables.

**Prioridad actual: el set de datos.** El modelo viene después, sobre datos confiables.

## Alcance de los datos

| Tipo     | Categoría del sitio | Subcategoría de venta | Avisos (oct 2026) | Páginas de API (21/página) |
|----------|---------------------|-----------------------|-------------------|----------------------------|
| Casas    | 100                 | **10003**             | ~3.255            | ~155                       |
| Terrenos | 104                 | **10403**             | ~3.809            | ~182                       |

- Se scrapean directamente las subcategorías de venta (10003 y 10403). Así el alquiler
  (10001 temporada, 10002 y otras) queda fuera desde el origen, sin filtrar por título.
- Cada subcategoría tiene hijas por departamento de San Juan (p. ej. 1000306 = Santa Lucía),
  que también vienen en cada aviso.

## Fuentes de datos (en orden de preferencia)

Para minimizar nulos, cada campo se toma de la fuente más confiable y se completa con las siguientes:

1. **API `/api/busqueda`** (fila del listado): `cod_pub`, `titulo`, `precio`, `moneda`,
   `precio_pesos`, `fchpub`, `fchact_original`, `visitas`, `destacado`, `url`, `url_foto`,
   `Categoria` (operación y departamento).
2. **Página de detalle** (`/anuncio_in/<código>/...`): descripción, características
   (superficies, dormitorios, baños, ambientes, garages, antigüedad, orientación,
   apto crédito, barrio privado, calle, número, barrio, departamento, comentario),
   **coordenadas** del mapa (`L.marker([lat, lon])`), cantidad de fotos, datos del anunciante.
3. **Reglas sobre título y descripción** (regex): superficie ("1750 mts2", "916 m"),
   dormitorios, servicios ("gas, agua, luz, cloaca"), escritura, financiación, permuta.
4. **LLM** sobre la descripción: solo para lo que las reglas no resuelven.
5. **Valor explícito "desconocido"** solo cuando ninguna fuente lo tiene. Se registra
   de qué fuente salió cada campo para poder medir la calidad.

## Esquema en Postgres

### `listings`: estado actual de cada aviso (1 fila por aviso)

| Campo | Tipo | Origen |
|---|---|---|
| `code` (PK) | bigint | API `cod_pub` |
| `property_type` | text (`house` / `land`) | categoría |
| `title`, `description`, `url` | text | API / detalle |
| `department` | text | API `Categoria` (Santa Lucía, Rivadavia, ...) |
| `neighborhood`, `street`, `street_number` | text | detalle |
| `lat`, `lon` | double | marcador del mapa en el detalle |
| `total_area_m2`, `covered_area_m2`, `semi_covered_area_m2` | numeric | detalle, si falta título/descripción |
| `bedrooms`, `bathrooms`, `rooms`, `garages` | int | detalle, si falta descripción |
| `age_bucket` | text | detalle ("Menos de 5 años", "A estrenar", ...) |
| `orientation` | text | detalle |
| `credit_approved`, `private_neighborhood` | bool | detalle |
| `services` | text[] | descripción (gas, agua, luz, cloaca) |
| `price_amount`, `currency` | numeric, text | API `precio`, `moneda` |
| `price_usd`, `price_ars` | numeric | calculados (ver "Moneda") |
| `price_on_request` | bool | precio = 0 ("Consultar") |
| `published_at`, `site_updated_at` | timestamptz | API `fchpub`, `fchact_original` |
| `visits`, `featured`, `photo_count` | int, bool, int | API / detalle |
| `first_seen_at`, `last_seen_at`, `is_active` | timestamptz, bool | proceso |
| `field_sources` | jsonb | de qué fuente salió cada campo |
| `raw_api`, `raw_detail` | jsonb | datos crudos, para reprocesar sin volver a scrapear |

### `listing_snapshots`: historial diario (1 fila por aviso y día)

`code`, `snapshot_date` (PK compuesta), `price_amount`, `currency`, `price_usd`,
`visits`, `site_updated_at`, `is_active`.
Con esta tabla salen las bajas de precio, los días publicado y las republicaciones.

### `raw_api_responses`: respuestas crudas de la API (1 fila por página pedida)

`id`, `run_id` (→ `scrape_runs`), `category`, `page`, `fetched_at`, `request_params` (jsonb),
`http_status`, `response` (jsonb completo, tal cual lo devuelve `/api/busqueda`).
Se guarda **todo** lo que devuelve la API, incluidos campos que hoy no usamos
(`categories`, `score`, `precio_promo`, `cod_categoria`, `url_foto`, ...), para poder
buscar información nueva más adelante sin volver a scrapear. Además, cada aviso guarda
su fila cruda en `listings.raw_api`.

### `scrape_runs`: control de cada corrida

`id`, `started_at`, `finished_at`, `category`, `pages`, `listings_seen`,
`details_fetched`, `errors`, `status`.

## Moneda

- `price_usd` = `precio` si `moneda` = `U$S`.
- Si está en pesos, se convierte con el **tipo de cambio implícito del propio sitio**:
  la mediana de `precio_pesos / precio` de los avisos en USD de ese día. Se guarda en
  cada snapshot. Esto reemplaza el valor fijo de 1200 que hay hoy en `items.py`.
- Avisos con precio "Consultar" (precio 0): se guardan con `price_on_request = true`
  y se excluyen del modelo, pero se cuentan.

## Fases

### Fase 0: infraestructura
- [x] Agregar servicio `postgres` al `docker-compose.yaml` (con volumen) y `DATABASE_URL` por entorno.
- [x] Sacar el pipeline de Elasticsearch de `ITEM_PIPELINES` (queda en pausa, sin borrar el código).
- [x] Migraciones del esquema con Alembic (`web_scraper/migrations`); el contenedor las aplica al arrancar.
- [x] Modelos SQLAlchemy en `web_scraper/db/models.py`, con tests contra Postgres (`tests/test_db.py`).

### Fase 1: ingesta completa de venta
- [x] Spider `listings` (`spiders/listings_spider.py`) sobre las subcategorías 10003 y 10403,
      sin límite de páginas (`-a max_pages=N` para pruebas).
- [x] Extraer todos los campos de la API y del detalle, incluidas coordenadas y cantidad de fotos
      (`dependencies/parsing.py`). La API tiene prioridad; el detalle completa lo que falta.
- [x] **Detalle incremental:** la API se recorre completa cada día (~340 páginas, da
      precio y visitas de todos los avisos). La página de detalle solo se pide para avisos
      nuevos o cuyo `fchact_original` cambió (`-a full_refresh=1` pide todas).
- [x] Guardar cada respuesta de la API completa en `raw_api_responses` (sin el token de sesión).
- [x] Pipeline de Postgres (`postgres_pipeline.py`): upsert en `listings`, un snapshot por
      aviso y día, registro en `scrape_runs`. Al cerrar convierte ARS → USD con el tipo de
      cambio implícito del día y, solo si la categoría se recorrió completa y sin errores en
      el listado, marca `is_active = false` los avisos que no aparecieron.
- [x] Guardar `raw_api` y `raw_detail` para poder reprocesar.
- [x] `department` en Postgres. El modelo de Elasticsearch (`items.py`) sigue con `apartment`
      porque el bot lo usa; se corrige si se reactiva Elasticsearch.
- [ ] Primera corrida completa (~7.000 páginas de detalle, unas 2-3 horas con 1 pedido por segundo).

Notas:
- `house_spider` y el pipeline de Elasticsearch quedan como estaban, en pausa.
- El cron sigue apuntando a `house_spider`; se cambia a `listings` en la Fase 5.
- Precio "Consultar": se guarda `price_on_request = true` y la moneda. En la muestra son
  ~25% de los avisos; muchos tienen el precio en la descripción (Fase 2/3).

### Fase 2: limpieza y normalización
- [ ] Parsers: superficies a m² numéricos ("150m2 y 80m2 semicub" → 150 cubiertos + 80 semicubiertos),
      booleanos ("SI"/"NO"), "Sin especificar" → desconocido, textos normalizados.
- [ ] Reglas regex sobre título y descripción para completar huecos.
- [ ] Validaciones de rango: precio/m² absurdo, superficie 0, coordenadas fuera de San Juan.
- [ ] Detección de duplicados: la misma propiedad publicada por varias inmobiliarias
      (coordenadas + superficie + precio parecidos).
- [ ] Revisar inconsistencias de precio (precio del aviso ≠ precio en la descripción).

### Fase 3: enriquecimiento con LLM
- [ ] LLM **open source y gratis**, detrás de LangChain para poder cambiar de modelo
      solo con configuración (proveedor y modelo por variables de entorno, p. ej. con
      `init_chat_model`). Opción inicial: Ollama en Docker con un modelo chico
      (Qwen, Llama o Mistral) y salida estructurada con un esquema pydantic.
- [ ] Extraer de la descripción, en formato estructurado: servicios, escritura, estado,
      pileta, financiación, permuta, urgencia, superficies o ambientes faltantes.
- [ ] Cachear por `code` + hash de la descripción: solo se procesan avisos nuevos o editados.
- [ ] Tabla `listing_features` con el resultado y la versión del prompt/modelo.

### Fase 4: calidad del set de datos
- [ ] Reporte de completitud por campo y por tipo (% de nulos, fuente de cada valor).
- [ ] Metas de completitud, p. ej. superficie total, precio, departamento y coordenadas > 95%.
- [ ] Tests de parsers y del pipeline con fixtures reales.

### Fase 5: corrida diaria
- [ ] Cron una vez por día, de noche, en Docker. Ojo: cron no hereda las variables de entorno
      del contenedor (`DATABASE_URL`); hay que pasárselas explícitamente.
- [ ] Logs y alerta si una corrida falla o trae muchos menos avisos que el día anterior.

### Después (fuera del alcance actual)
- Precio de referencia en USD/m² por tipo y zona (mediana de comparables).
- Modelo de valuación (gradient boosting), separado para casas y terrenos.
- Puntaje de oportunidad: descuento contra el modelo + bajas de precio + días publicado + confianza.
- Reporte o alerta diaria y explicación desde el bot.

## Decisiones tomadas

- Solo avisos de **venta**, de casas y terrenos.
- Todo se guarda en **Postgres**.
- Primero un set de datos limpio y completo; el modelo después.
- Postgres corre en Docker (docker-compose).
- Elasticsearch queda **en pausa**: no se alimenta ni se borra.
- LLM open source y gratis, intercambiable vía LangChain.
- Se guardan las respuestas crudas completas de la API.
- Los datos del anunciante quedan fuera por ahora (igual quedan en lo crudo si la API los trae).

## Preguntas abiertas

- ¿Qué modelo open source concreto rinde mejor extrayendo datos de las descripciones?
  Se decide en la Fase 3 comparando 2 o 3 modelos sobre una muestra revisada a mano.
