import json
import math
import re
from urllib.parse import urlencode, urljoin

import scrapy
from pydantic import ValidationError

# Local import
from web_scraper.dependencies import items
from web_scraper.log import logger

SITE_URL = "https://www.compraensanjuan.com/"
SEARCH_PAGE_URL = "https://www.compraensanjuan.com/b.php"
SEARCH_API_URL = "https://www.compraensanjuan.com/api/busqueda"
ROWS_PER_PAGE = 21  # Page size used by the site's own pagination
SESSION_TOKEN_RE = re.compile(r'"st"\s*:\s*"([^"]+)"')


class HouseSpider(scrapy.Spider):
    """A spider for scraping house listings from compraensanjuan.com.

    The site renders its listings in the browser from the ``/api/busqueda`` JSON
    endpoint, which needs a session token (``st``) embedded in ``b.php`` plus the
    session cookie (kept by Scrapy). The spider therefore:
    1. requests ``b.php`` and extracts the ``st`` token,
    2. pages through ``/api/busqueda`` using the same parameters as the site's JS,
    3. follows the ``url`` of every row to extract the full ad details.

    Attributes:
        name (str): Identifier for this spider, used by Scrapy
        allowed_domains (list): List of domains this spider is restricted to
        category (int): Site category to scrape (100 = houses)
        total_pages_to_scrape (int): Maximum number of listing pages to crawl
        current_page (int): Number of listing pages crawled so far (per instance)
    """

    name = "house_spider"
    allowed_domains = ["compraensanjuan.com"]
    category = 100
    total_pages_to_scrape = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_page = 0
        self.total_pages_to_scrape = int(self.total_pages_to_scrape)

    def _query_params(self, page: int, token: str = "") -> dict:
        """Parameters sent by the site's JS (booleans are serialised as text)."""
        return {
            "texto": "",
            "pagina": str(page),
            "cat": str(self.category),
            "foto": "false",
            "envio": "false",
            "precio": "false",
            "orden": "0",
            "estado": "Todos",
            "st": token,
        }

    def start_requests(self):
        params = self._query_params(1)
        params.pop("st")
        yield scrapy.Request(
            f"{SEARCH_PAGE_URL}?{urlencode(params)}", callback=self.parse
        )

    def parse(self, response: scrapy.http.Response):
        """Extract the session token from b.php and request the first API page."""
        match = SESSION_TOKEN_RE.search(response.text)
        if not match:
            logger.error(f"Session token (st) not found in {response.url}")
            return
        yield self._api_request(1, match.group(1), referer=response.url)

    def _api_request(self, page: int, token: str, referer: str) -> scrapy.Request:
        url = f"{SEARCH_API_URL}?{urlencode(self._query_params(page, token))}"
        return scrapy.Request(
            url,
            callback=self.parse_api,
            headers={
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": referer,
            },
            cb_kwargs={"page": page, "token": token, "referer": referer},
        )

    def parse_api(
        self, response: scrapy.http.Response, page: int, token: str, referer: str
    ):
        """Follow every ad of the listing page and request the next one."""
        try:
            payload = json.loads(response.text)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from the search API (page {page})")
            return

        if not payload.get("ok"):
            logger.error(
                f"Search API error (page {page}): "
                f"{payload.get('error') or payload.get('msg')}"
            )
            return

        data = payload.get("data") or {}
        rows = data.get("rows") or []
        total = int(data.get("total") or 0)
        self.current_page += 1
        logger.info(f"Found {len(rows)} houses in page {page} (total: {total})")

        for row in rows:
            link = row.get("url")
            if not link:
                continue
            # Row URLs are relative to the site root, not to /api/
            yield scrapy.Request(
                urljoin(SITE_URL, link),
                callback=self.parse_product_details,
                cb_kwargs={"row": row},
            )

        last_page = min(math.ceil(total / ROWS_PER_PAGE), self.total_pages_to_scrape)
        if rows and page < last_page:
            logger.info(f"Scraping the next page: {page + 1}")
            yield self._api_request(page + 1, token, referer)

    @staticmethod
    def _row_price(row: dict):
        """Build a price string like the one shown on the ad from an API row."""
        if not row:
            return None
        try:
            amount = int(float(row.get("precio") or 0))
        except (TypeError, ValueError):
            return None
        if amount == 0:
            return "Consultar"
        return f"{row.get('moneda', '')}{amount:,}".replace(",", ".")

    def parse_product_details(self, response, row=None):
        """Extract house details from individual ad pages."""
        row = row or {}
        logger.info("Parsing the individual product details")
        description = response.css("p.comentario-caracteristicas-anuncio::text").getall()

        item = {
            "name": response.css("h2[class*='anuncio-title']::text").get()
            or row.get("titulo"),
            "price": response.css("h3.text-center.precio::text").get()
            or self._row_price(row),
            "description": " ".join(description),
            "url": response.url,
            "code_number": response.css("p.codigo.m-0 span::text").get(),
            "number_visit": response.css("p.visitas.m-0 span::text").get()
            or row.get("visitas"),
            "publish_date": response.css("p.publicado.m-0 span::text").get()
            or row.get("fchpub"),
            "last_update": response.css("p.actualizado.m-0 span::text").get()
            or row.get("fchact_original"),
        }

        # Select all <p> elements with the class 'name-caracteristica' inside any container div.
        for p in response.css("div.mx-auto p.name-caracteristica"):
            # The label (e.g., "Superficie total:") is the text node before the <span>
            label = (p.xpath("text()").get() or "").strip(" :\n\t")
            if not label:
                continue
            # The value is inside the <span class="caracteristica">
            item[label] = p.css("span.caracteristica::text").get(default="")

        # Validate and convert the scraped data to the defined model
        try:
            yield items.HouseAdvertisement(**item)
        except ValidationError as error:
            logger.error(f"Invalid ad skipped ({response.url}): {error}")
