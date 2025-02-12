from pydantic import BaseModel, Field, field_validator
from typing import Optional


class BaseHouse(BaseModel):
    # Extra characteristic fields
    total_area: Optional[str] = None
    covered_area: Optional[str] = None
    age: Optional[str] = None
    bathrooms: Optional[str] = None
    rooms: Optional[str] = None
    garages: Optional[str] = None
    bedrooms: Optional[str] = None
    orientation: Optional[str] = None
    credit_approved: Optional[str] = None
    private_neighborhood: Optional[str] = None
    street: Optional[str] = None
    neighborhood: Optional[str] = None
    number: Optional[str] = None
    apartment: Optional[str] = None
    comment: Optional[str] = None


# Define the data model
class HouseAdvertisementCreate(BaseHouse):
    # Basic fields (already in English)
    name: str
    price: Optional[float] = None
    description: str
    url: str
    code_number: int
    number_visit: int
    publish_date: str
    last_update: str


class HouseAdvertisementUpdate(BaseHouse):
    """
    Update an existing house document. code_number and url cannot be updated.
    """

    name: Optional[str] = None
    price: Optional[float] = None
    description: Optional[str] = None
    number_visit: Optional[int] = None
    publish_date: Optional[str] = None
    last_update: Optional[str] = None
