from pydantic import BaseModel, Field, field_validator, model_validator 
from typing import Optional


# Define the data model
class HouseAdvertisement(BaseModel):
    # Basic fields (already in English)
    name: str
    price: Optional[float] = None
    description: str
    url: str
    code_number: int
    number_visit: int
    publish_date: str
    last_update: str

    # Extra characteristic fields with English attribute names
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

    @field_validator("price", mode="before")
    def parse_price(cls, value):
        """
        Convert the price string to a float.
        - If the string contains "U$S", assume it's in USD.
        - Otherwise, assume the value is in Argentine Pesos and convert it to USD by dividing by 1200.
        """
        if isinstance(value, str):
            value = value.strip()
            if "Consultar" in value:
                return None
            elif "U$S" in value:
                # Remove the currency marker and convert to float
                value = (
                    value.replace("U$S", "").replace(".", "").replace(",", ".").strip()
                )
                try:
                    return float(value)
                except ValueError:
                    raise ValueError(f"Price value is not a valid float: {value}")
            else:
                # Assume the price is in Argentine Pesos and convert to USD
                try:
                    numeric_value = float(
                        value.replace("$", "").replace(".", "").replace(",", ".")
                    )
                    return numeric_value / 1200
                except ValueError:
                    raise ValueError(f"Price value is not a valid float: {value}")
        return value

    @field_validator(
        "name", "description", "publish_date", "last_update", mode="before"
    )
    def strip_string_fields(cls, v):
        """Strip extra whitespace from key string fields."""
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator(
        "total_area",
        "covered_area",
        "age",
        "bathrooms",
        "rooms",
        "garages",
        "bedrooms",
        "orientation",
        "credit_approved",
        "private_neighborhood",
        "street",
        "neighborhood",
        "number",
        "apartment",
        "comment",
        mode="before",
    )
    def strip_optional_fields(cls, v):
        """Strip extra whitespace from optional fields if they are provided."""
        if isinstance(v, str):
            return v.strip()
        return v
    

    @model_validator(mode="before")
    def combine_name_and_description(cls, values):
        name = values.get("name")
        description = values.get("description")
        if name is not None and description is not None:
            # Create a new description in the format: "name:\noriginal description"
            values["description"] = f"{name}:\n{description}"
        return values
