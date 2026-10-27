# Standard library imports
import json
import os
from unittest.mock import MagicMock, patch

# Third party imports
import pytest
import scrapy
from scrapy.http import HtmlResponse, TextResponse

# Local imports
from web_scraper.dependencies import parsing
from web_scraper.dependencies.listing_items import ApiPageItem, ListingItem
from web_scraper.spiders.listings_spider import ListingsSpider

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def read_fixture(name, mode="r"):
    encoding = "utf-8" if "b" not in mode else None
    with open(os.path.join(FIXTURES, name), mode, encoding=encoding) as f:
        return f.read()


@pytest.fixture
def api_payload():
    return json.loads(read_fixture("api_busqueda_land.json"))


def api_response(payload, page=1, category=10403):
    url = f"https://www.compraensanjuan.com/api/busqueda?pagina={page}&cat={category}"
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    return TextResponse(url=url, body=body, encoding="utf-8", request=scrapy.Request(url))


def run_parse_api(spider, payload, page=1, category=10403):
    return list(
        spider.parse_api(
            api_response(payload, page, category),
            page=page,
            category=category,
            token="tok",
            referer="https://www.compraensanjuan.com/b.php",
        )
    )


@pytest.fixture
def spider():
    return ListingsSpider()


def test_defaults_are_sale_categories_without_page_limit(spider):
    assert spider.name == "listings"
    assert spider.categories == [10003, 10403]
    assert spider.max_pages is None
    assert spider.full_refresh is False


def test_rejects_unknown_category():
    with pytest.raises(ValueError):
        ListingsSpider(categories="100")


def test_start_requests_one_per_category(spider):
    with patch(
        "web_scraper.spiders.listings_spider.load_known_listings", return_value={1: None}
    ):
        requests = list(spider.start_requests())

    assert [r.cb_kwargs["category"] for r in requests] == [10003, 10403]
    assert all("b.php" in r.url and "st=" not in r.url for r in requests)
    assert [r.meta["cookiejar"] for r in requests] == [10003, 10403]
    assert spider.known_listings == {1: None}


def test_start_requests_without_database_fetches_everything(spider):
    with patch(
        "web_scraper.spiders.listings_spider.load_known_listings",
        side_effect=RuntimeError("no db"),
    ):
        list(spider.start_requests())
    assert spider.known_listings == {}


def test_full_refresh_skips_the_database():
    spider = ListingsSpider(full_refresh="1")
    loader = MagicMock()
    with patch("web_scraper.spiders.listings_spider.load_known_listings", loader):
        list(spider.start_requests())
    loader.assert_not_called()


def test_parse_reads_token(spider):
    response = HtmlResponse(
        url="https://www.compraensanjuan.com/b.php",
        body=b'<script>var cfg = {"st": "TOKEN_1"};</script>',
    )
    (request,) = list(spider.parse(response, category=10403))
    assert "st=TOKEN_1" in request.url
    assert "cat=10403" in request.url
    assert request.callback == spider.parse_api


def test_parse_without_token_counts_an_error(spider):
    response = HtmlResponse(url="https://www.compraensanjuan.com/b.php", body=b"<html/>")
    assert list(spider.parse(response, category=10403)) == []
    assert spider.errors[10403] == 1


def test_parse_api_stores_raw_page_and_requests_new_ads(spider, api_payload):
    results = run_parse_api(spider, api_payload)

    raw = results[0]
    assert isinstance(raw, ApiPageItem)
    assert raw.response == api_payload
    assert raw.http_status == 200
    assert raw.request_params["st"] == ""  # the session token is not stored

    details = [r for r in results if isinstance(r, scrapy.Request) and r.callback == spider.parse_detail]
    assert len(details) == 3
    assert details[0].url.startswith("https://www.compraensanjuan.com/anuncio_in/")

    pages = [r for r in results if isinstance(r, scrapy.Request) and r.callback == spider.parse_api]
    assert len(pages) == 1
    assert "pagina=2" in pages[0].url
    assert spider.expected_pages[10403] == 182
    assert spider.pages_done[10403] == 1


def test_parse_api_skips_unchanged_ads(spider, api_payload):
    """Ads whose fchact_original did not change only get their API values"""
    rows = api_payload["data"]["rows"]
    unchanged = rows[0]
    spider.known_listings = {
        int(unchanged["cod_pub"]): parsing.parse_site_datetime(unchanged["fchact_original"]),
        int(rows[1]["cod_pub"]): None,  # changed since last crawl
    }

    results = run_parse_api(spider, api_payload)

    items = [r for r in results if isinstance(r, ListingItem)]
    assert [i.values["code"] for i in items] == [int(unchanged["cod_pub"])]
    assert items[0].has_detail is False
    details = [r for r in results if isinstance(r, scrapy.Request) and r.callback == spider.parse_detail]
    assert len(details) == 2


def test_parse_api_stops_at_max_pages(api_payload):
    spider = ListingsSpider(max_pages="1")
    results = run_parse_api(spider, api_payload)
    assert not any(isinstance(r, scrapy.Request) and r.callback == spider.parse_api for r in results)
    assert spider.is_complete(10403) is False


def test_parse_api_error_is_stored_and_counted(spider):
    payload = {"ok": False, "error": "La sesión ha expirado."}
    results = run_parse_api(spider, payload)

    assert len(results) == 1
    assert results[0].response == payload
    assert spider.errors[10403] == 1


def test_parse_api_invalid_json(spider):
    results = run_parse_api(spider, b"<html>not json</html>")
    assert results[0].response is None
    assert spider.errors[10403] == 1


def test_is_complete(spider, api_payload):
    api_payload["data"]["total"] = 3  # a single page
    run_parse_api(spider, api_payload)
    assert spider.is_complete(10403) is True
    assert spider.is_complete(10003) is False  # never crawled

    spider.errors[10403] = 1
    assert spider.is_complete(10403) is False


def test_detail_errors_do_not_make_the_crawl_incomplete(spider, api_payload):
    api_payload["data"]["total"] = 3
    run_parse_api(spider, api_payload)
    spider.detail_errors[10403] = 2
    assert spider.is_complete(10403) is True


def test_parse_detail_merges_api_and_page(spider, api_payload):
    row = api_payload["data"]["rows"][0]
    api = parsing.api_values(row, "land")
    response = HtmlResponse(
        url=api[0]["url"],
        body=read_fixture("detail_land_2696069.html", "rb"),
        headers={"Content-Type": "text/html; charset=iso-8859-1"},
    )

    (item,) = list(spider.parse_detail(response, category=10403, api=api))

    assert item.has_detail is True
    assert item.values["price_usd"] == api[0]["price_usd"]
    assert item.values["lat"] is not None
    assert item.field_sources["price_usd"] == "api"
    assert item.field_sources["lat"] == "detail"


def test_detail_error_keeps_api_values(spider, api_payload):
    api = parsing.api_values(api_payload["data"]["rows"][0], "land")
    failure = MagicMock()
    failure.request = scrapy.Request(api[0]["url"], cb_kwargs={"category": 10403, "api": api})

    (item,) = list(spider.on_detail_error(failure))

    assert item.values["code"] == 2696069
    assert item.has_detail is False
    assert spider.detail_errors[10403] == 1
    assert spider.errors[10403] == 0
