from datetime import date

from sqlmodel import SQLModel


class BookingRead(SQLModel):
    id: int
    property_id: int
    check_in: date
    check_out: date
    price: float
    booked_on: date
