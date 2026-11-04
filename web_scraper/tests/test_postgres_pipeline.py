# Standard library imports
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

# Third party imports
import pytest
from sqlalchemy import create_engine, func, select, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

# Local imports
from web_scraper import settings
from web_scraper.db.models import Listing, ListingSnapshot, RawApiResponse, ScrapeRun
from web_scraper.dependencies.listing_items import ApiPageItem, ListingItem
from web_scraper.postgres_pipeline import PostgresPipeline
from web_scraper.spiders.listings_spider import SALE_CATEGORIES


@pytest.fixture(scope="module")
def engine():
    engine = create_engine(settings.DATABASE_URL)
    try:
        with engine.connect():
            pass
    except OperationalError:
        pytest.skip("Postgres is not reachable at DATABASE_URL")
    yield engine
    engine.dispose()


@pytest.fixture
def connection(engine):
    """Everything the pipeline writes is rolled back after the test"""
    connection = engine.connect()
    transaction = connection.begin()
    yield connection
    transaction.rollback()
    connection.close()


def make_session(connection):
    return Session(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


class FakeSpider(SimpleNamespace):
    property_type = staticmethod(SALE_CATEGORIES.get)

    def is_complete(self, category):
        return self.complete


def make_spider(complete=False):
    return FakeSpider(
        categories=[10403],
        complete=complete,
        pages_done={10403: 1},
        errors={10403: 0},
        detail_errors={10403: 0},
    )


def open_pipeline(connection, spider):
    pipeline = PostgresPipeline()
    with patch(
        "web_scraper.postgres_pipeline.SessionLocal", lambda: make_session(connection)
    ):
        pipeline.open_spider(spider)
    return pipeline


def listing_item(code, has_detail=True, **overrides):
    values = {
        "code": code,
        "property_type": "land",
        "title": f"Lote {code}",
        "url": f"https://www.compraensanjuan.com/anuncio_in/{code}/x",
        "currency": "USD",
        "price_amount": Decimal("33000"),
        "price_usd": Decimal("33000"),
        "price_ars": Decimal("51414000"),
        "price_on_request": False,
        "visits": 10,
    }
    sources = {key: "api" for key in values}
    if has_detail:
        values.update(description="Lote con servicios", lat=Decimal("-31.5"))
        sources.update(description="detail", lat="detail")
    values.update(overrides)
    return ListingItem(10403, values, sources, has_detail=has_detail)


def test_stores_raw_page_listing_and_snapshot(connection):
    spider = make_spider()
    pipeline = open_pipeline(connection, spider)
    raw = {"ok": True, "data": {"total": 1, "rows": [{"cod_pub": "1"}]}}

    pipeline.process_item(ApiPageItem(10403, 1, {"cat": "10403"}, 200, raw), spider)
    pipeline.process_item(listing_item(1), spider)
    pipeline.close_spider(spider)

    # The database may hold real crawls too: only look at what this test wrote
    run_id = pipeline.runs[10403].id
    session = make_session(connection)
    stored = select(RawApiResponse.response).where(RawApiResponse.run_id == run_id)
    assert session.scalars(stored).one() == raw
    listing = session.get(Listing, 1)
    assert listing.description == "Lote con servicios"
    assert listing.detail_fetched_at is not None
    assert listing.field_sources["lat"] == "detail"
    snapshot = session.scalars(select(ListingSnapshot).where(ListingSnapshot.code == 1)).one()
    assert snapshot.price_usd == Decimal("33000")
    assert snapshot.ars_per_usd == Decimal("1558.0000")
    run = session.get(ScrapeRun, run_id)
    assert (run.status, run.pages, run.listings_seen, run.details_fetched) == (
        "finished",
        1,
        1,
        1,
    )


def test_api_only_update_keeps_ad_page_columns(connection):
    spider = make_spider()
    pipeline = open_pipeline(connection, spider)
    pipeline.process_item(listing_item(1), spider)
    pipeline.process_item(
        listing_item(1, has_detail=False, price_amount=Decimal("30000"), price_usd=Decimal("30000")),
        spider,
    )
    pipeline.close_spider(spider)

    listing = make_session(connection).get(Listing, 1)
    assert listing.price_usd == Decimal("30000")
    assert listing.description == "Lote con servicios"
    assert listing.field_sources["description"] == "detail"


def test_ars_prices_are_converted_with_the_site_rate(connection):
    spider = make_spider()
    pipeline = open_pipeline(connection, spider)
    pipeline.process_item(listing_item(1), spider)  # USD ad: rate 1558
    pipeline.process_item(
        listing_item(
            2,
            currency="ARS",
            price_amount=Decimal("155800000"),
            price_usd=None,
            price_ars=Decimal("155800000"),
        ),
        spider,
    )
    pipeline.close_spider(spider)

    session = make_session(connection)
    assert session.get(Listing, 2).price_usd == Decimal("100000.00")
    snapshot = session.scalars(select(ListingSnapshot).where(ListingSnapshot.code == 2)).one()
    assert snapshot.price_usd == Decimal("100000.00")


@pytest.mark.parametrize("complete, expected_active", [(True, False), (False, True)])
def test_unseen_ads_are_deactivated_only_after_a_complete_crawl(
    connection, complete, expected_active
):
    # An ad from a previous crawl...
    spider = make_spider()
    pipeline = open_pipeline(connection, spider)
    pipeline.process_item(listing_item(99), spider)
    pipeline.close_spider(spider)
    session = make_session(connection)
    session.execute(
        update(Listing).values(last_seen_at=func.now() - timedelta(days=1))
    )
    session.commit()

    # ...that is not in today's crawl
    spider = make_spider(complete=complete)
    pipeline = open_pipeline(connection, spider)
    pipeline.process_item(listing_item(1), spider)
    pipeline.close_spider(spider)

    session = make_session(connection)
    assert session.get(Listing, 99).is_active is expected_active
    assert session.get(Listing, 1).is_active is True
