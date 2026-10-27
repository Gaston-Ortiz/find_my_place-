# Standard library imports
from datetime import date, datetime, UTC
from decimal import Decimal

# Third party imports
import pytest
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

# Local imports
from web_scraper import settings
from web_scraper.db.models import (
    Base,
    Listing,
    ListingSnapshot,
    RawApiResponse,
    ScrapeRun,
)


@pytest.fixture(scope="module")
def engine():
    """Postgres from DATABASE_URL, migrated with `alembic upgrade head`.

    Skipped when the database is not reachable (e.g. `docker compose up -d postgres`
    was not run).
    """
    engine = create_engine(settings.DATABASE_URL)
    try:
        with engine.connect():
            pass
    except OperationalError:
        pytest.skip("Postgres is not reachable at DATABASE_URL")
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine):
    """Session inside a transaction that is rolled back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    transaction.rollback()
    connection.close()


def make_listing(**overrides):
    values = {
        "code": 2641638,
        "property_type": "house",
        "title": "Venta. Casa en barrio privado",
        "url": "https://www.compraensanjuan.com/anuncio_in/2641638/x",
        "department": "Rivadavia",
        "lat": Decimal("-31.5234132"),
        "lon": Decimal("-68.5856938"),
        "total_area_m2": Decimal("367"),
        "services": ["gas", "agua"],
        "price_amount": Decimal("220000"),
        "currency": "USD",
        "price_usd": Decimal("220000"),
        "raw_api": {"cod_pub": "2641638", "moneda": "U$S"},
    }
    values.update(overrides)
    return Listing(**values)


def test_migrations_match_models(engine):
    """Every model table exists in the migrated database"""
    tables = set(inspect(engine).get_table_names())
    assert set(Base.metadata.tables) <= tables


def test_listing_with_snapshot_and_raw_response(session):
    run = ScrapeRun(category=10003)
    session.add(run)
    session.flush()

    session.add(
        RawApiResponse(
            run_id=run.id,
            category=10003,
            page=1,
            request_params={"cat": "10003", "pagina": "1"},
            http_status=200,
            response={"ok": True, "data": {"total": 1, "rows": [{"cod_pub": "1"}]}},
        )
    )
    session.add(make_listing())
    session.flush()
    session.add(
        ListingSnapshot(
            code=2641638,
            snapshot_date=date(2026, 10, 27),
            run_id=run.id,
            price_amount=Decimal("220000"),
            currency="USD",
            price_usd=Decimal("220000"),
            ars_per_usd=Decimal("1558.0000"),
            visits=2313,
            site_updated_at=datetime(2026, 10, 27, 7, 57, tzinfo=UTC),
        )
    )
    session.flush()

    listing = session.get(Listing, 2641638)
    assert listing.is_active is True
    assert listing.price_on_request is False
    assert listing.field_sources == {}
    assert listing.services == ["gas", "agua"]
    assert listing.raw_api["moneda"] == "U$S"
    assert [s.visits for s in listing.snapshots] == [2313]

    raw = session.scalars(select(RawApiResponse).where(RawApiResponse.run_id == run.id)).one()
    assert raw.response["data"]["rows"][0]["cod_pub"] == "1"
    assert run.status == "running"


@pytest.mark.parametrize(
    "overrides", [{"property_type": "flat"}, {"currency": "U$S"}]
)
def test_listing_rejects_invalid_values(session, overrides):
    session.add(make_listing(**overrides))
    with pytest.raises(IntegrityError):
        session.flush()


def test_one_snapshot_per_listing_and_day(session):
    session.add(make_listing())
    session.flush()
    day = date(2026, 10, 27)
    session.add(ListingSnapshot(code=2641638, snapshot_date=day))
    session.flush()
    session.add(ListingSnapshot(code=2641638, snapshot_date=day))
    with pytest.raises(IntegrityError):
        session.flush()
