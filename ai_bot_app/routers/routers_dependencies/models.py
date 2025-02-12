from pydantic import BaseModel, Field, field_validator
from typing import Optional


class BaseHouse(BaseModel):
    # Extra characteristic fields
    total_area: Optional[str] = Field(None, alias="Superficie total")
    covered_area: Optional[str] = Field(None, alias="Superficie cubierta")
    age: Optional[str] = Field(None, alias="Antiguedad")
    bathrooms: Optional[str] = Field(None, alias="Baños")
    rooms: Optional[str] = Field(None, alias="Ambientes")
    garages: Optional[str] = Field(None, alias="Garages")
    bedrooms: Optional[str] = Field(None, alias="Dormitorios")
    orientation: Optional[str] = Field(None, alias="Orientación")
    credit_approved: Optional[str] = Field(None, alias="Apto crédito")
    private_neighborhood: Optional[str] = Field(None, alias="En barrio privado")
    street: Optional[str] = Field(None, alias="Calle")
    neighborhood: Optional[str] = Field(None, alias="Barrio")
    number: Optional[str] = Field(None, alias="Número")
    apartment: Optional[str] = Field(None, alias="Departamento")
    comment: Optional[str] = Field(None, alias="Comentario")


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
