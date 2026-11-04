"""Postgres schema for the daily sale listings dataset (see PLAN.md)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Money and areas: exact decimals, wide enough for ARS amounts
Money = Numeric(18, 2)
Area = Numeric(12, 2)


class Base(DeclarativeBase):
    pass


class ScrapeRun(Base):
    """One crawl of one site category."""

    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    category: Mapped[int] = mapped_column(Integer)
    pages: Mapped[int] = mapped_column(Integer, server_default="0")
    listings_seen: Mapped[int] = mapped_column(Integer, server_default="0")
    details_fetched: Mapped[int] = mapped_column(Integer, server_default="0")
    errors: Mapped[int] = mapped_column(Integer, server_default="0")
    status: Mapped[str] = mapped_column(Text, server_default="running")

    raw_responses: Mapped[list["RawApiResponse"]] = relationship(back_populates="run")

    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'finished', 'failed')", name="status_valid"
        ),
    )


class RawApiResponse(Base):
    """Full /api/busqueda response for one listing page, stored as returned."""

    __tablename__ = "raw_api_responses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("scrape_runs.id", ondelete="CASCADE"))
    category: Mapped[int] = mapped_column(Integer)
    page: Mapped[int] = mapped_column(Integer)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    request_params: Mapped[dict[str, Any]] = mapped_column(JSONB)
    http_status: Mapped[int] = mapped_column(SmallInteger)
    response: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)

    run: Mapped[ScrapeRun] = relationship(back_populates="raw_responses")

    __table_args__ = (Index("ix_raw_api_responses_run_page", "run_id", "page"),)


class Listing(Base):
    """Current state of each ad, one row per ad (keyed by the site's code)."""

    __tablename__ = "listings"

    code: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    property_type: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)

    # Location
    department: Mapped[Optional[str]] = mapped_column(Text)
    neighborhood: Mapped[Optional[str]] = mapped_column(Text)
    street: Mapped[Optional[str]] = mapped_column(Text)
    street_number: Mapped[Optional[str]] = mapped_column(Text)
    lat: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7))
    lon: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7))

    # Characteristics
    total_area_m2: Mapped[Optional[Decimal]] = mapped_column(Area)
    covered_area_m2: Mapped[Optional[Decimal]] = mapped_column(Area)
    semi_covered_area_m2: Mapped[Optional[Decimal]] = mapped_column(Area)
    bedrooms: Mapped[Optional[int]] = mapped_column(SmallInteger)
    bathrooms: Mapped[Optional[int]] = mapped_column(SmallInteger)
    rooms: Mapped[Optional[int]] = mapped_column(SmallInteger)
    garages: Mapped[Optional[int]] = mapped_column(SmallInteger)
    age_bucket: Mapped[Optional[str]] = mapped_column(Text)
    orientation: Mapped[Optional[str]] = mapped_column(Text)
    credit_approved: Mapped[Optional[bool]]
    private_neighborhood: Mapped[Optional[bool]]
    services: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))

    # Price
    price_amount: Mapped[Optional[Decimal]] = mapped_column(Money)
    currency: Mapped[Optional[str]] = mapped_column(Text)
    price_usd: Mapped[Optional[Decimal]] = mapped_column(Money)
    price_ars: Mapped[Optional[Decimal]] = mapped_column(Money)
    price_on_request: Mapped[bool] = mapped_column(server_default="false")

    # Site metadata
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    site_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    visits: Mapped[Optional[int]] = mapped_column(Integer)
    featured: Mapped[Optional[bool]]
    photo_count: Mapped[Optional[int]] = mapped_column(SmallInteger)

    # Process tracking
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    is_active: Mapped[bool] = mapped_column(server_default="true")
    detail_fetched_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )

    # Which source filled each field (api / detail / regex / llm), and raw data
    field_sources: Mapped[dict[str, str]] = mapped_column(JSONB, server_default="{}")
    raw_api: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    raw_detail: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)

    snapshots: Mapped[list["ListingSnapshot"]] = relationship(back_populates="listing")

    __table_args__ = (
        CheckConstraint(
            "property_type IN ('house', 'land')", name="property_type_valid"
        ),
        CheckConstraint("currency IN ('USD', 'ARS')", name="currency_valid"),
        Index("ix_listings_type_department", "property_type", "department"),
        Index("ix_listings_is_active", "is_active"),
    )


class ListingSnapshot(Base):
    """Daily price and visits of each ad, for price history."""

    __tablename__ = "listing_snapshots"

    code: Mapped[int] = mapped_column(
        ForeignKey("listings.code", ondelete="CASCADE"), primary_key=True
    )
    snapshot_date: Mapped[date] = mapped_column(Date, primary_key=True)
    run_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("scrape_runs.id", ondelete="SET NULL")
    )
    price_amount: Mapped[Optional[Decimal]] = mapped_column(Money)
    currency: Mapped[Optional[str]] = mapped_column(Text)
    price_usd: Mapped[Optional[Decimal]] = mapped_column(Money)
    # Site's implied exchange rate that day (median precio_pesos / precio of USD ads)
    ars_per_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    visits: Mapped[Optional[int]] = mapped_column(Integer)
    site_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(server_default="true")

    listing: Mapped[Listing] = relationship(back_populates="snapshots")

    __table_args__ = (Index("ix_listing_snapshots_date", "snapshot_date"),)
