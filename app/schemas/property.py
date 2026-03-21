from typing import Optional

from sqlmodel import SQLModel


class PropertyCreate(SQLModel):
    name: str
    city: str
    property_type: str
    base_price: float
    bedrooms: int
    accommodates: int


class PropertyRead(SQLModel):
    id: int
    name: str
    city: str
    property_type: str
    base_price: float
    bedrooms: int
    accommodates: int


class PropertyUpdate(SQLModel):
    name: Optional[str] = None
    city: Optional[str] = None
    property_type: Optional[str] = None
    base_price: Optional[float] = None
    bedrooms: Optional[int] = None
    accommodates: Optional[int] = None
