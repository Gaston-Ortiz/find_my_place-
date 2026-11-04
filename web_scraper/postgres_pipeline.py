from datetime import datetime
from decimal import Decimal
from statistics import median

from scrapy.exceptions import DropItem
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

# Local imports
from web_scraper.db.models import Listing, ListingSnapshot, RawApiResponse, ScrapeRun
from web_scraper.db.session import SessionLocal
from web_scraper.dependencies.listing_items import ApiPageItem, ListingItem
from web_scraper.dependencies.parsing import SITE_TZ
from web_scraper.log import logger

SNAPSHOT_COLUMNS = (
    "price_amount",
    "currency",
    "price_usd",
    "visits",
    "site_updated_at",
)


class PostgresPipeline:
    """Stores the listings spider output in Postgres (see PLAN.md).

    - every API response goes to `raw_api_responses`,
    - every ad is upserted into `listings` and gets one `listing_snapshots` row per day,
    - one `scrape_runs` row per category tracks the crawl.

    When the crawl closes it converts ARS prices to USD with the site's implied
    exchange rate of the day and, for categories crawled completely, marks the ads
    that were not seen as inactive.
    """

    def open_spider(self, spider):
        self.session = SessionLocal()
        # Database clock, the same one that stamps `last_seen_at`
        self.started_at: datetime = self.session.scalar(select(func.now()))
        self.snapshot_date = self.started_at.astimezone(SITE_TZ).date()
        self.ratios: list[Decimal] = []
        self.runs: dict[int, ScrapeRun] = {}
        for category in spider.categories:
            run = ScrapeRun(category=category)
            self.session.add(run)
            self.runs[category] = run
        self.session.commit()
        self.listings_seen = {c: 0 for c in spider.categories}
        self.details_fetched = {c: 0 for c in spider.categories}

    def process_item(self, item, spider):
        try:
            if isinstance(item, ApiPageItem):
                self._store_api_page(item)
            elif isinstance(item, ListingItem):
                self._store_listing(item)
            self.session.commit()
        except SQLAlchemyError as error:
            self.session.rollback()
            spider.detail_errors[item.category] += 1
            raise DropItem(f"Could not store {type(item).__name__}: {error}") from error
        return item

    def _store_api_page(self, item: ApiPageItem):
        self.session.add(
            RawApiResponse(
                run_id=self.runs[item.category].id,
                category=item.category,
                page=item.page,
                request_params=item.request_params,
                http_status=item.http_status,
                response=item.response,
            )
        )

    def _store_listing(self, item: ListingItem):
        values = dict(item.values)
        values.update(
            last_seen_at=func.now(),
            is_active=True,
            field_sources=item.field_sources,
        )
        if item.has_detail:
            values["detail_fetched_at"] = func.now()

        stmt = insert(Listing).values(**values)
        changes = {key: stmt.excluded[key] for key in values if key != "code"}
        # Keep the sources of columns this crawl did not fill
        changes["field_sources"] = Listing.field_sources.op("||")(
            stmt.excluded.field_sources
        )
        self.session.execute(
            stmt.on_conflict_do_update(index_elements=[Listing.code], set_=changes)
        )

        snapshot = {key: values.get(key) for key in SNAPSHOT_COLUMNS}
        snapshot_stmt = insert(ListingSnapshot).values(
            code=values["code"],
            snapshot_date=self.snapshot_date,
            run_id=self.runs[item.category].id,
            is_active=True,
            **snapshot,
        )
        self.session.execute(
            snapshot_stmt.on_conflict_do_update(
                index_elements=[ListingSnapshot.code, ListingSnapshot.snapshot_date],
                set_={
                    "run_id": snapshot_stmt.excluded.run_id,
                    **{key: snapshot_stmt.excluded[key] for key in SNAPSHOT_COLUMNS},
                },
            )
        )

        self.listings_seen[item.category] += 1
        self.details_fetched[item.category] += item.has_detail
        if values.get("currency") == "USD" and values.get("price_ars"):
            self.ratios.append(values["price_ars"] / values["price_amount"])

    def close_spider(self, spider):
        try:
            self._convert_ars_prices()
            for category, run in self.runs.items():
                self._close_run(spider, category, run)
            self.session.commit()
        finally:
            self.session.close()

    def _convert_ars_prices(self):
        """ARS -> USD with the site's rate of the day (median precio_pesos / precio)."""
        if not self.ratios:
            logger.warning("No USD ads with an ARS price: exchange rate unknown")
            return
        rate = Decimal(median(self.ratios)).quantize(Decimal("0.0001"))
        logger.info(f"Site exchange rate: {rate} ARS per USD")

        self.session.execute(
            update(Listing)
            .where(Listing.currency == "ARS", Listing.last_seen_at >= self.started_at)
            .values(price_usd=func.round(Listing.price_amount / rate, 2))
        )
        today = ListingSnapshot.snapshot_date == self.snapshot_date
        self.session.execute(update(ListingSnapshot).where(today).values(ars_per_usd=rate))
        self.session.execute(
            update(ListingSnapshot)
            .where(today, ListingSnapshot.currency == "ARS")
            .values(price_usd=func.round(ListingSnapshot.price_amount / rate, 2))
        )

    def _close_run(self, spider, category: int, run: ScrapeRun):
        if spider.is_complete(category):
            # Ads of this type not seen in a complete crawl were removed from the site
            result = self.session.execute(
                update(Listing)
                .where(
                    Listing.property_type == spider.property_type(category),
                    Listing.is_active.is_(True),
                    Listing.last_seen_at < self.started_at,
                )
                .values(is_active=False)
            )
            logger.info(f"Category {category}: {result.rowcount} ads marked inactive")
        else:
            logger.info(f"Category {category}: partial crawl, no ads marked inactive")

        run.finished_at = func.now()
        run.pages = spider.pages_done[category]
        run.listings_seen = self.listings_seen[category]
        run.details_fetched = self.details_fetched[category]
        run.errors = spider.errors[category] + spider.detail_errors[category]
        run.status = "failed" if spider.errors[category] else "finished"
