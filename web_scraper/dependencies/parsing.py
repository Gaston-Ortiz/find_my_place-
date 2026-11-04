"""Parse compraensanjuan.com API rows and ad pages into `listings` columns.

Each `*_values` function returns two dicts: the column values it could fill and,
for each of those columns, the source it came from (stored in `field_sources`).
Values the site marks as unknown ("Sin especificar", empty) become None.
"""

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Optional
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

SITE_URL = "https://www.compraensanjuan.com/"
SITE_TZ = ZoneInfo("America/Argentina/San_Juan")
UNKNOWN_VALUES = {"", "-", "sin especificar", "no especifica", "consultar"}
CURRENCIES = {"U$S": "USD", "$": "ARS"}

MARKER_RE = re.compile(r"L\.marker\(\[\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\]")
NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*")


def clean_text(value: Any) -> Optional[str]:
    """Strip whitespace; the site's "unknown" markers become None."""
    if value is None:
        return None
    text = " ".join(str(value).split())
    if text.lower() in UNKNOWN_VALUES:
        return None
    return text


def parse_number(value: Any) -> Optional[Decimal]:
    """First number in the text: "1.750 m2" -> 1750, "367,5m2" -> 367.5."""
    text = clean_text(value)
    if text is None:
        return None
    match = NUMBER_RE.search(text)
    if not match:
        return None
    number = match.group()
    # "1.750" / "1,750" are thousands; "367,5" / "0.5" are decimals
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", number):
        number = re.sub(r"[.,]", "", number)
    else:
        number = number.replace(",", ".")
        if number.count(".") > 1:
            return None
    try:
        return Decimal(number)
    except InvalidOperation:
        return None


def parse_int(value: Any) -> Optional[int]:
    """Counts like "3" or "5 o más" (-> 5)."""
    number = parse_number(value)
    return int(number) if number is not None else None


def parse_bool(value: Any) -> Optional[bool]:
    text = clean_text(value)
    if text is None:
        return None
    return {"si": True, "sí": True, "no": False}.get(text.lower())


def parse_covered_area(value: Any) -> tuple[Optional[Decimal], Optional[Decimal]]:
    """"150m2 y 80m2 semicub" -> (150, 80); "120" -> (120, None)."""
    text = clean_text(value)
    if text is None:
        return None, None
    parts = re.split(r"\s+y\s+", text, maxsplit=1)
    covered = parse_number(parts[0])
    semi = None
    if len(parts) == 2 and "semi" in parts[1].lower():
        semi = parse_number(parts[1])
    return covered, semi


def parse_site_datetime(value: Any) -> Optional[datetime]:
    """API dates ("2026-10-19 08:55:00") are San Juan local time."""
    text = clean_text(value)
    if text is None:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=SITE_TZ)
    except ValueError:
        return None


def category_description(categories: dict, code_length: int) -> Optional[str]:
    """Description of the row's category with a code of that length.

    Codes nest by length: 3 digits = type (100 Casas), 5 = operation (10003 Venta),
    7 = department (1000306 Santa Lucia).
    """
    for code, category in (categories or {}).items():
        if len(code.strip()) == code_length:
            return clean_text(category.get("description"))
    return None


def ad_url(row: dict) -> str:
    """Absolute ad URL, safe to request.

    The API replaces characters it can't encode (emojis, accents) with "?", which
    would start a query string: "anuncio_in/2613963/???-liquido" requests
    "anuncio_in/2613963/" and gets a 404. The site accepts any non-empty slug.
    """
    slug = (row.get("url") or "").split(f"/{row['cod_pub']}/", 1)[-1]
    slug = slug.replace("?", "").strip("-") or "aviso"
    return urljoin(SITE_URL, f"anuncio_in/{row['cod_pub']}/{slug}")


def api_values(row: dict, property_type: str) -> tuple[dict, dict]:
    """Columns filled from one /api/busqueda row."""
    amount = parse_number(row.get("precio"))
    price_on_request = not amount
    currency = CURRENCIES.get((row.get("moneda") or "").strip())
    price_ars = parse_number(row.get("precio_pesos"))

    values = {
        "code": int(row["cod_pub"]),
        "property_type": property_type,
        "title": clean_text(row.get("titulo")),
        "url": ad_url(row),
        "department": category_description(row.get("Categoria"), 7),
        "price_amount": None if price_on_request else amount,
        "currency": currency,  # kept for "Consultar" ads: the site shows it
        "price_usd": amount if currency == "USD" and not price_on_request else None,
        "price_ars": price_ars or None,
        "price_on_request": price_on_request,
        "published_at": parse_site_datetime(row.get("fchpub")),
        "site_updated_at": parse_site_datetime(row.get("fchact_original")),
        "visits": parse_int(row.get("visitas")),
        "featured": row.get("destacado") == "1",
        "raw_api": row,
    }
    sources = {
        key: "api" for key, value in values.items() if value is not None and key != "raw_api"
    }
    return values, sources


# Ad page characteristic label -> column parser
CHARACTERISTICS = {
    "Superficie total": ("total_area_m2", parse_number),
    "Antiguedad": ("age_bucket", clean_text),
    "Baños": ("bathrooms", parse_int),
    "Ambientes": ("rooms", parse_int),
    "Garages": ("garages", parse_int),
    "Dormitorios": ("bedrooms", parse_int),
    "Orientación": ("orientation", clean_text),
    "Apto crédito": ("credit_approved", parse_bool),
    "En barrio privado": ("private_neighborhood", parse_bool),
    "Calle": ("street", clean_text),
    "Número": ("street_number", clean_text),
    "Barrio": ("neighborhood", clean_text),
    "Departamento": ("department", clean_text),
}


def detail_values(response, code: int) -> tuple[dict, dict]:
    """Columns filled from an ad page (a Scrapy text response)."""
    characteristics = {}
    for p in response.css("div.mx-auto p.name-caracteristica"):
        label = (p.xpath("text()").get() or "").strip(" :\n\t")
        if label:
            characteristics[label] = (p.css("span.caracteristica::text").get() or "").strip()

    description = " ".join(
        " ".join(response.css("p.comentario-caracteristicas-anuncio ::text").getall()).split()
    )
    html = response.text
    marker = MARKER_RE.search(html)
    photos = set(re.findall(rf"fotos_inmuebles/{code}_(\d+)\.", html))

    values: dict[str, Any] = {
        "description": description or None,
        "lat": Decimal(marker.group(1)) if marker else None,
        "lon": Decimal(marker.group(2)) if marker else None,
        "photo_count": len(photos),
    }
    for label, (column, parser) in CHARACTERISTICS.items():
        if label in characteristics:
            values[column] = parser(characteristics[label])
    covered, semi = parse_covered_area(characteristics.get("Superficie cubierta"))
    values["covered_area_m2"] = covered
    values["semi_covered_area_m2"] = semi

    values = {key: value for key, value in values.items() if value is not None}
    sources = {key: "detail" for key in values}
    values["raw_detail"] = {
        "characteristics": characteristics,
        "price_text": clean_text(response.css("h3.text-center.precio::text").get()),
        "visits_text": clean_text(response.css("p.visitas.m-0 span::text").get()),
        "published_text": clean_text(response.css("p.publicado.m-0 span::text").get()),
        "updated_text": clean_text(response.css("p.actualizado.m-0 span::text").get()),
    }
    return values, sources


def merge_values(api: tuple[dict, dict], detail: tuple[dict, dict]) -> tuple[dict, dict]:
    """API values win; the ad page only fills what the API left empty."""
    api_vals, api_sources = api
    detail_vals, detail_sources = detail
    values = dict(api_vals)
    sources = dict(api_sources)
    for key, value in detail_vals.items():
        if values.get(key) is None:
            values[key] = value
            if key in detail_sources:
                sources[key] = detail_sources[key]
    return values, sources
