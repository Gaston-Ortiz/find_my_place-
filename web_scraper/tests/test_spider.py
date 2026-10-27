# Standard library imports
import json
import math
import os
from unittest.mock import patch

# Third party imports
import pytest
import scrapy

# Local imports
from web_scraper.dependencies.items import HouseAdvertisement
from web_scraper.spiders.house_spider import HouseSpider

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def read_fixture(name):
    with open(os.path.join(FIXTURES, name), "r", encoding="utf-8") as f:
        return f.read()


def make_response(url, body, **kwargs):
    return scrapy.http.HtmlResponse(
        url=url,
        body=body,
        encoding="utf-8",
        request=scrapy.http.Request(url=url, **kwargs),
    )


@pytest.fixture
def spider():
    return HouseSpider()


@pytest.fixture
def search_response():
    return make_response(
        "https://www.compraensanjuan.com/b.php?cat=100&orden=0&pagina=1",
        read_fixture("sample_search_page.html"),
    )


@pytest.fixture
def api_payload():
    return json.loads(read_fixture("sample_api_response.json"))


def api_response(payload):
    return make_response(
        "https://www.compraensanjuan.com/api/busqueda?pagina=1",
        json.dumps(payload),
    )


@pytest.fixture
def mock_detail_response():
    return make_response(
        "https://www.compraensanjuan.com/aviso_12345.html",
        read_fixture("sample_detail_page.html"),
    )


def test_spider_attributes(spider):
    """Test basic spider attributes"""
    assert spider.name == "house_spider"
    assert "compraensanjuan.com" in spider.allowed_domains
    assert spider.current_page == 0


def test_current_page_is_per_instance():
    first, second = HouseSpider(), HouseSpider()
    first.current_page = 3
    assert second.current_page == 0


def test_start_requests(spider):
    requests = list(spider.start_requests())
    assert len(requests) == 1
    assert "b.php" in requests[0].url
    assert "cat=100" in requests[0].url
    assert "st=" not in requests[0].url


def test_parse_extracts_token_and_requests_api(spider, search_response):
    """parse() reads the st token from b.php and requests the first API page"""
    results = list(spider.parse(search_response))

    assert len(results) == 1
    request = results[0]
    assert request.url.startswith("https://www.compraensanjuan.com/api/busqueda?")
    assert "st=TOKEN_abc-123_xyz" in request.url
    assert "pagina=1" in request.url
    assert "cat=100" in request.url
    assert request.callback == spider.parse_api
    assert request.cb_kwargs["token"] == "TOKEN_abc-123_xyz"


def test_parse_without_token_stops_cleanly(spider):
    response = make_response("https://www.compraensanjuan.com/b.php", "<html></html>")
    with patch("web_scraper.spiders.house_spider.logger") as mock_logger:
        assert list(spider.parse(response)) == []
    mock_logger.error.assert_called_once()


def test_parse_api_follows_rows_and_next_page(spider, api_payload):
    results = list(
        spider.parse_api(api_response(api_payload), page=1, token="tok", referer="r")
    )

    details = [r for r in results if r.callback == spider.parse_product_details]
    pages = [r for r in results if r.callback == spider.parse_api]

    assert [r.url for r in details] == [
        "https://www.compraensanjuan.com/aviso_12345.html",
        "https://www.compraensanjuan.com/aviso_67890.html",
    ]
    assert details[0].cb_kwargs["row"]["titulo"] == "Beautiful House for Sale"
    assert len(pages) == 1
    assert "pagina=2" in pages[0].url
    assert "st=tok" in pages[0].url
    assert spider.current_page == 1


def test_parse_api_stops_at_last_page(spider, api_payload):
    last = math.ceil(api_payload["data"]["total"] / 21)  # 3 pages
    results = list(
        spider.parse_api(api_response(api_payload), page=last, token="t", referer="r")
    )
    assert all(r.callback == spider.parse_product_details for r in results)


def test_parse_api_respects_page_limit(api_payload):
    spider = HouseSpider(total_pages_to_scrape=1)
    results = list(
        spider.parse_api(api_response(api_payload), page=1, token="t", referer="r")
    )
    assert all(r.callback == spider.parse_product_details for r in results)


def test_parse_api_error_stops_cleanly(spider):
    payload = {"ok": False, "error": "La sesión ha expirado."}
    with patch("web_scraper.spiders.house_spider.logger") as mock_logger:
        results = list(
            spider.parse_api(api_response(payload), page=1, token="t", referer="r")
        )
    assert results == []
    mock_logger.error.assert_called_once()


def test_parse_api_invalid_json_stops_cleanly(spider):
    response = make_response("https://www.compraensanjuan.com/api/busqueda", "<html>")
    assert list(spider.parse_api(response, page=1, token="t", referer="r")) == []


def test_parse_product_details(spider, mock_detail_response):
    """Test the spider's parse_product_details method"""
    with patch("web_scraper.spiders.house_spider.logger") as mock_logger:
        results = list(spider.parse_product_details(mock_detail_response))

    assert len(results) == 1
    item = results[0]
    assert isinstance(item, HouseAdvertisement)
    assert item.name == "Beautiful House for Sale"
    assert item.price == 150000.0
    assert item.code_number == 12345
    assert item.number_visit == 42
    assert item.total_area == "200m²"
    assert item.bathrooms == "2"
    assert mock_logger.info.called


def test_parse_product_details_falls_back_to_api_row(spider):
    """Fields missing in the detail HTML come from the API row"""
    html = (
        '<html><body><p class="codigo m-0">C: <span>999</span></p>'
        '<p class="comentario-caracteristicas-anuncio">Desc</p></body></html>'
    )
    response = make_response("https://www.compraensanjuan.com/aviso_999.html", html)
    row = {
        "titulo": "From API",
        "precio": "120000",
        "moneda": "U$S ",
        "visitas": 5,
        "fchpub": "01/01/2023",
        "fchact_original": "02/01/2023",
    }

    (item,) = list(spider.parse_product_details(response, row=row))

    assert item.name == "From API"
    assert item.price == 120000.0
    assert item.number_visit == 5
    assert item.publish_date == "01/01/2023"


def test_parse_product_details_invalid_ad_is_skipped(spider):
    response = make_response(
        "https://www.compraensanjuan.com/aviso_1.html", "<html></html>"
    )
    with patch("web_scraper.spiders.house_spider.logger") as mock_logger:
        assert list(spider.parse_product_details(response)) == []
    mock_logger.error.assert_called_once()
