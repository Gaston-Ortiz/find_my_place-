import pytest

from ai_bot_app.routers.routers_dependencies.models import (
    BaseHouse,
    HouseAdvertisementCreate,
    HouseAdvertisementUpdate,
)


def test_base_house_model():
    """Test the BaseHouse model"""
    house = BaseHouse(total_area="100m²", covered_area="80m²", bedrooms="3")

    assert house.total_area == "100m²"
    assert house.covered_area == "80m²"
    assert house.bedrooms == "3"
    assert house.bathrooms is None  # Optional fields default to None


def test_house_advertisement_create_model():
    """Test the HouseAdvertisementCreate model"""
    house = HouseAdvertisementCreate(
        name="Test House",
        price=150000.0,
        description="A test house",
        url="https://example.com/house/1",
        code_number=123,
        number_visit=42,
        publish_date="2023-01-15",
        last_update="2023-01-15",
        bedrooms="3",
        bathrooms="2",
    )

    assert house.name == "Test House"
    assert house.price == 150000.0
    assert house.description == "A test house"
    assert house.url == "https://example.com/house/1"
    assert house.code_number == 123
    assert house.bedrooms == "3"
    assert house.bathrooms == "2"


def test_house_advertisement_update_model():
    """Test the HouseAdvertisementUpdate model"""
    # Testing with partial fields
    house = HouseAdvertisementUpdate(name="Updated Name", price=160000.0, bedrooms="4")

    assert house.name == "Updated Name"
    assert house.price == 160000.0
    assert house.bedrooms == "4"
    assert house.description is None  # Not provided

    # Verify the model accepts None for optional fields
    house = HouseAdvertisementUpdate(price=None, description="Updated description")

    assert house.price is None
    assert house.description == "Updated description"
