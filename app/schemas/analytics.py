from sqlmodel import SQLModel


class RevenueSummary(SQLModel):
    total_revenue: float
    total_bookings: int
    average_booking_value: float


class PropertyRevenue(SQLModel):
    property_id: int
    total_revenue: float
    booking_count: int


class CityRevenue(SQLModel):
    city: str
    total_revenue: float
    booking_count: int


class OccupancySummary(SQLModel):
    total_booked_nights: int
    total_bookings: int
    average_length_of_stay: float


class PricingRecommendation(SQLModel):
    property_id: int
    current_base_price: float
    recommended_price: float
    adjustment_type: str
    reason: str
