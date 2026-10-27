import json
import math
import re
from datetime import datetime
from typing import Optional
from urllib.parse import urlencode

import scrapy

# Local imports
from web_scraper.dependencies import parsing
from web_scraper.dependencies.listing_items import ApiPageItem, ListingItem
from web_scraper.log import logger

SEARCH_PAGE_URL = "https://www.compraensanjuan.com/b.php"
SEARCH_API_URL = "https://www.compraensanjuan.com/api/busqueda"
ROWS_PER_PAGE = 21  # Page size used by the site's own pagination
SESSION_TOKEN_RE = re.compile(r'"st"\s*:\s*"([^"]+)"')
# Sale subcategories (``cat`` parameter) and the property type stored on each ad
SALE_CATEGORIES = {10003: "house", 10403: "land"}


def load_known_listings() -> dict[int, Optional[datetime]]:
    """`site_updated_at` of the ads whose page was already fetched, by code."""
    # Imported here so the spider can run (and be tested) without a database
    from sqlalchemy import select

    from web_scraper.db.models import Listing
    from web_scraper.db.session import SessionLocal

    with SessionLocal() as session:
        rows = session.execute(
            select(Listing.code, Listing.site_updated_at).where(
                Listing.detail_fetched_at.is_not(None)
            )
        )
        return dict(rows.all())


class ListingsSpider(scrapy.Spider):
    """Crawls every sale ad of houses and land on compraensanjuan.com.

    For each sale subcategory it:
    1. requests ``b.php`` to get the session token (``st``) the API needs,
    2. pages through ``/api/busqueda`` and yields every response as an ``ApiPageItem``,
    3. yields a ``ListingItem`` per ad. The ad page is only requested for new ads or
       ads whose ``fchact_original`` changed since the last crawl (unless
       ``-a full_refresh=1``), so a daily crawl fetches a few hundred pages instead
       of ~7,000.

    Arguments (``-a name=value``):
        categories: comma-separated subcategories (default "10003,10403")
        max_pages: listing pages per category (default: all)
        full_refresh: "1" to fetch every ad page
    """

    name = "listings"
    allowed_domains = ["compraensanjuan.com"]
    custom_settings = {
        "ITEM_PIPELINES": {"web_scraper.postgres_pipeline.PostgresPipeline": 300},
    }
    categories = ",".join(str(c) for c in SALE_CATEGORIES)
    max_pages = None
    full_refresh = "0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.categories = [int(c) for c in str(self.categories).split(",") if c.strip()]
        unknown = set(self.categories) - set(SALE_CATEGORIES)
        if unknown:
            raise ValueError(f"Unknown sale categories: {sorted(unknown)}")
        self.max_pages = int(self.max_pages) if self.max_pages else None
        self.full_refresh = str(self.full_refresh) == "1"
        self.known_listings: dict[int, Optional[datetime]] = {}
        # Per category progress, read by the pipeline when the crawl closes
        self.expected_pages = {c: None for c in self.categories}
        self.pages_done = {c: 0 for c in self.categories}
        # Listing page errors make the crawl incomplete; ad page errors don't
        self.errors = {c: 0 for c in self.categories}
        self.detail_errors = {c: 0 for c in self.categories}

    @staticmethod
    def property_type(category: int) -> str:
        return SALE_CATEGORIES[category]

    def is_complete(self, category: int) -> bool:
        """Whether every listing page of the category was crawled without errors."""
        expected = self.expected_pages[category]
        return (
            expected is not None
            and self.max_pages is None
            and self.pages_done[category] >= expected
            and self.errors[category] == 0
        )

    def _query_params(self, page: int, category: int, token: str = "") -> dict:
        """Parameters sent by the site's JS (booleans are serialised as text)."""
        return {
            "texto": "",
            "pagina": str(page),
            "cat": str(category),
            "foto": "false",
            "envio": "false",
            "precio": "false",
            "orden": "0",
            "estado": "Todos",
            "st": token,
        }

    def start_requests(self):
        if not self.full_refresh:
            try:
                self.known_listings = load_known_listings()
            except Exception as error:  # Without the DB, fetch every ad page
                logger.warning(f"Could not load known listings, fetching all: {error}")
        logger.info(f"{len(self.known_listings)} listings already have their ad page")

        # One b.php request per category, each with its own session token
        for category in self.categories:
            params = self._query_params(1, category)
            params.pop("st")
            yield scrapy.Request(
                f"{SEARCH_PAGE_URL}?{urlencode(params)}",
                callback=self.parse,
                errback=self.on_error,
                cb_kwargs={"category": category},
                # Separate cookie session per category so tokens don't clash
                meta={"cookiejar": category},
                dont_filter=True,
            )

    def on_error(self, failure):
        category = failure.request.cb_kwargs.get("category")
        if category in self.errors:
            self.errors[category] += 1
        logger.error(f"Request failed ({failure.request.url}): {failure.value!r}")

    def parse(self, response: scrapy.http.Response, category: int):
        """Extract the session token from b.php and request the first API page."""
        match = SESSION_TOKEN_RE.search(response.text)
        if not match:
            self.errors[category] += 1
            logger.error(f"Session token (st) not found in {response.url}")
            return
        yield self._api_request(1, category, match.group(1), response.url)

    def _api_request(
        self, page: int, category: int, token: str, referer: str
    ) -> scrapy.Request:
        params = self._query_params(page, category, token)
        return scrapy.Request(
            f"{SEARCH_API_URL}?{urlencode(params)}",
            callback=self.parse_api,
            errback=self.on_error,
            headers={
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": referer,
            },
            meta={"cookiejar": category},
            cb_kwargs={
                "page": page,
                "category": category,
                "token": token,
                "referer": referer,
            },
        )

    def parse_api(
        self,
        response: scrapy.http.Response,
        page: int,
        category: int,
        token: str,
        referer: str,
    ):
        """Store the raw page, yield its ads and request the next page."""
        params = self._query_params(page, category)  # without the session token
        try:
            payload = json.loads(response.text)
        except json.JSONDecodeError:
            payload = None
        yield ApiPageItem(category, page, params, response.status, payload)

        if not payload or not payload.get("ok"):
            self.errors[category] += 1
            error = (payload or {}).get("error") or "invalid JSON"
            logger.error(f"Search API error (category {category} page {page}): {error}")
            return

        data = payload.get("data") or {}
        rows = data.get("rows") or []
        total = int(data.get("total") or 0)
        self.expected_pages[category] = math.ceil(total / ROWS_PER_PAGE)
        self.pages_done[category] += 1
        logger.info(
            f"Category {category} page {page}/{self.expected_pages[category]}: "
            f"{len(rows)} ads (total: {total})"
        )

        property_type = SALE_CATEGORIES[category]
        for row in rows:
            try:
                api = parsing.api_values(row, property_type)
            except (KeyError, ValueError) as error:
                self.errors[category] += 1
                logger.error(f"Invalid API row skipped ({row.get('cod_pub')}): {error}")
                continue
            values, sources = api
            if self._needs_detail(values):
                yield scrapy.Request(
                    values["url"],
                    callback=self.parse_detail,
                    errback=self.on_detail_error,
                    cb_kwargs={"category": category, "api": api},
                )
            else:
                yield ListingItem(category, values, sources)

        last_page = self.expected_pages[category]
        if self.max_pages:
            last_page = min(last_page, self.max_pages)
        if rows and page < last_page:
            yield self._api_request(page + 1, category, token, referer)

    def _needs_detail(self, values: dict) -> bool:
        code = values["code"]
        if self.full_refresh or code not in self.known_listings:
            return True
        return self.known_listings[code] != values["site_updated_at"]

    def parse_detail(self, response: scrapy.http.Response, category: int, api: tuple):
        """Complete the API values with the ad page."""
        code = api[0]["code"]
        values, sources = parsing.merge_values(api, parsing.detail_values(response, code))
        yield ListingItem(category, values, sources, has_detail=True)

    def on_detail_error(self, failure):
        """Keep the API data (price, visits) of ads whose page failed."""
        category = failure.request.cb_kwargs["category"]
        self.detail_errors[category] += 1
        logger.error(f"Ad page failed ({failure.request.url}): {failure.value!r}")
        values, sources = failure.request.cb_kwargs["api"]
        yield ListingItem(category, values, sources)
