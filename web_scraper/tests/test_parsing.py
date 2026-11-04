# Standard library imports
import json
import os
from datetime import datetime
from decimal import Decimal

# Third party imports
import pytest
from scrapy.http import HtmlResponse

# Local imports
from web_scraper.dependencies import parsing

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def api_rows():
    with open(os.path.join(FIXTURES, "api_busqueda_land.json"), encoding="utf-8") as f:
        return json.load(f)["data"]["rows"]


@pytest.fixture
def detail_response():
    """Real ad page, served by the site as iso-8859-1"""
    with open(os.path.join(FIXTURES, "detail_land_2696069.html"), "rb") as f:
        body = f.read()
    return HtmlResponse(
        url="https://www.compraensanjuan.com/anuncio_in/2696069/x",
        body=body,
        headers={"Content-Type": "text/html; charset=iso-8859-1"},
    )


@pytest.mark.parametrize(
    "value, expected",
    [
        ("930", Decimal("930")),
        ("367m2", Decimal("367")),
        ("1.750 Mts2", Decimal("1750")),
        ("367,5 m2", Decimal("367.5")),
        ("220000.00", Decimal("220000.00")),
        ("Sin especificar", None),
        ("", None),
        (None, None),
        ("sin datos", None),
    ],
)
def test_parse_number(value, expected):
    assert parsing.parse_number(value) == expected


@pytest.mark.parametrize(
    "value, expected", [("3", 3), ("5 o más", 5), ("Sin especificar", None)]
)
def test_parse_int(value, expected):
    assert parsing.parse_int(value) == expected


@pytest.mark.parametrize(
    "value, expected", [("SI", True), ("Sí", True), ("NO", False), ("", None)]
)
def test_parse_bool(value, expected):
    assert parsing.parse_bool(value) is expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("150m2 y 80m2 semicub", (Decimal("150"), Decimal("80"))),
        ("120", (Decimal("120"), None)),
        ("Sin especificar", (None, None)),
    ],
)
def test_parse_covered_area(value, expected):
    assert parsing.parse_covered_area(value) == expected


def test_parse_site_datetime_is_san_juan_time():
    parsed = parsing.parse_site_datetime("2026-10-19 08:55:00")
    assert parsed == datetime(2026, 10, 19, 8, 55, tzinfo=parsing.SITE_TZ)
    assert parsed.utcoffset().total_seconds() == -3 * 3600
    assert parsing.parse_site_datetime("") is None


def test_api_values_usd_row(api_rows):
    values, sources = parsing.api_values(api_rows[0], "land")

    assert values["code"] == 2696069
    assert values["property_type"] == "land"
    assert values["department"] == "Rawson"
    assert values["url"].startswith("https://www.compraensanjuan.com/anuncio_in/2696069/")
    assert values["currency"] == "USD"
    assert values["price_amount"] == values["price_usd"] == Decimal("33000.00")
    assert values["price_ars"] == Decimal("51414000.00")
    assert values["price_on_request"] is False
    assert values["visits"] == 99
    assert values["featured"] is True
    assert values["raw_api"] is api_rows[0]
    assert sources["department"] == "api"
    assert "raw_api" not in sources


@pytest.mark.parametrize(
    "url, expected",
    [
        ("anuncio_in/7/casa-en-venta", "anuncio_in/7/casa-en-venta"),
        ("anuncio_in/7/casa-c?ntrica", "anuncio_in/7/casa-cntrica"),
        ("anuncio_in/7/???-liquido-terreno", "anuncio_in/7/liquido-terreno"),
        ("anuncio_in/7/???", "anuncio_in/7/aviso"),
    ],
)
def test_ad_url_never_breaks_on_question_marks(url, expected):
    assert parsing.ad_url({"cod_pub": "7", "url": url}) == parsing.SITE_URL + expected


def test_api_values_price_on_request(api_rows):
    """precio 0 is "Consultar": no amount, but the currency the site shows is kept"""
    values, _ = parsing.api_values(api_rows[2], "land")

    assert values["price_on_request"] is True
    assert values["price_amount"] is None
    assert values["price_usd"] is None
    assert values["currency"] == "ARS"


def test_detail_values(detail_response):
    values, sources = parsing.detail_values(detail_response, 2696069)

    assert values["description"].startswith("Lotes escriturados")
    assert values["lat"] == Decimal("-31.56579685137893")
    assert values["lon"] == Decimal("-68.58371114743932")
    assert values["photo_count"] == 3
    assert values["total_area_m2"] == Decimal("930")
    assert values["age_bucket"] == "A estrenar"
    assert values["credit_approved"] is False
    assert values["private_neighborhood"] is False
    # "Sin especificar" characteristics are left out, not stored as text
    assert "bathrooms" not in values
    assert "orientation" not in values
    assert values["raw_detail"]["characteristics"]["Baños"] == "Sin especificar"
    assert values["raw_detail"]["price_text"] == "U$S 33.000"
    assert set(sources) == set(values) - {"raw_detail"}
    assert set(sources.values()) == {"detail"}


def test_merge_values_prefers_api():
    api = ({"code": 1, "department": "Rawson", "title": "T"}, {"department": "api", "title": "api"})
    detail = (
        {"department": "Capital", "lat": Decimal("-31.5"), "raw_detail": {}},
        {"department": "detail", "lat": "detail"},
    )

    values, sources = parsing.merge_values(api, detail)

    assert values["department"] == "Rawson"
    assert sources["department"] == "api"
    assert values["lat"] == Decimal("-31.5")
    assert sources["lat"] == "detail"
    assert values["raw_detail"] == {}
