from datetime import date
from typing import Optional

from sqlmodel import Field, SQLModel


class Property(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    city: str
    property_type: str
    base_price: float
    bedrooms: int
    accommodates: int


class Booking(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    property_id: int
    check_in: date
    check_out: date
    price: float
    booked_on: date
