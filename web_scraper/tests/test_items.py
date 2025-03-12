from datetime import UTC, datetime

import pytest

from web_scraper.dependencies.items import HouseAdvertisement

house = HouseAdvertisement(
    name="Beautiful house",
    price=150000.0,
    description="A lovely house with a garden",
    url="https://example.com/house/123",
    code_number=123,
    number_visit=42,
    publish_date="2023-01-15",
    last_update="2023-05-20",
)


def test_house_advertisement_creation():
    """Test creating a HouseAdvertisement instance with valid data"""
    assert house.name == "Beautiful house"
    assert house.price == 150000.0
    assert house.description == "Beautiful house:\nA lovely house with a garden"
    assert house.url == "https://example.com/house/123"


def test_price_validator_usd():
    """Test the price validator when price is in USD"""
    house_price = house.model_copy(update={"price": "U$S 150.000"})

    assert house_price.price == 150000.0


def test_price_validator_ars():
    """Test the price validator when price is in ARS"""
    house_price = house.model_copy(update={"price": "$ 180.000.000"})

    # Expecting conversion from ARS to USD (divided by 1200)
    assert house_price.price == 150000.0


def test_price_validator_consultar():
    """Test the price validator when price is 'Consultar'"""
    house_price = house.model_copy(update={"price": "Consultar"})

    assert house_price.price is None


def test_updated_db_default():
    """Test that updated_db gets the current UTC time by default"""
    before = datetime.now(UTC).isoformat()
    house = HouseAdvertisement(
        name="Test House",
        description="Test description",
        url="https://example.com",
        code_number=123,
        number_visit=42,
        publish_date="2023-01-01",
        last_update="2023-01-01",
    )
    after = datetime.now(UTC).isoformat()

    assert before <= house.updated_db <= after
