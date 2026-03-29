from collections import defaultdict
from datetime import date
from typing import List, Optional

import pandas as pd
import requests
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlmodel import Session, select

from app.core.cache import delete_cache, get_cache, set_cache
from app.db.database import get_session
from app.db.models import Booking, Property
from app.schemas.analytics import (CityRevenue, OccupancySummary,
                                   PricingRecommendation, PropertyRevenue,
                                   RevenueSummary)
from app.schemas.insights import InsightQuery, InsightResponse
from app.schemas.property import PropertyCreate, PropertyRead, PropertyUpdate
from app.services.insights_service import ask_llm, build_insight_context

router = APIRouter()


# Health routes
@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "PricePilot API is running",
    }


@router.get("/hello")
def hello():
    return {
        "message": "Welcome to PricePilot",
    }


# Property routes
@router.post("/properties", response_model=PropertyRead)
def create_property(
    property_data: PropertyCreate,
    session: Session = Depends(get_session),
):
    db_property = Property(**property_data.model_dump())
    session.add(db_property)
    session.commit()
    session.refresh(db_property)
    return db_property


@router.get("/properties", response_model=List[PropertyRead])
def list_properties(
    session: Session = Depends(get_session),
    city: Optional[str] = None,
    property_type: Optional[str] = None,
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    statement = select(Property)

    if city:
        statement = statement.where(Property.city == city)

    if property_type:
        statement = statement.where(Property.property_type == property_type)

    statement = statement.offset(offset).limit(limit)

    properties = session.exec(statement).all()
    return properties


@router.get("/properties/{property_id}", response_model=PropertyRead)
def get_property(
    property_id: int,
    session: Session = Depends(get_session),
):
    property_obj = session.get(Property, property_id)
    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found")
    return property_obj


@router.put("/properties/{property_id}", response_model=PropertyRead)
def update_property(
    property_id: int,
    property_data: PropertyUpdate,
    session: Session = Depends(get_session),
):
    property_obj = session.get(Property, property_id)
    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found")

    update_data = property_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(property_obj, key, value)

    session.add(property_obj)
    session.commit()
    session.refresh(property_obj)
    return property_obj


@router.delete("/properties/{property_id}")
def delete_property(
    property_id: int,
    session: Session = Depends(get_session),
):
    property_obj = session.get(Property, property_id)
    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found")

    session.delete(property_obj)
    session.commit()

    return {"message": f"Property with id {property_id} deleted successfully"}


# Upload routes
@router.post(
    "/upload/bookings",
    summary="Upload booking dataset",
    description="""
    Upload a CSV file containing booking records.
    You can use the sample file available in the repository:
    `sample_data/sample_bookings.csv`

    Required columns:
    - property_id
    - check_in (YYYY-MM-DD)
    - check_out (YYYY-MM-DD)
    - price
    - booked_on (YYYY-MM-DD)

    Example CSV:
    
    property_id,check_in,check_out,price,booked_on
    1,2025-03-01,2025-03-05,5000,2025-02-20
    1,2025-03-10,2025-03-12,4500,2025-02-25
    2,2025-03-02,2025-03-06,6000,2025-02-22
    3,2025-03-05,2025-03-07,7000,2025-02-28
    """,
)
def upload_bookings(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    try:
        df = pd.read_csv(file.file)

        required_columns = [
            "property_id",
            "check_in",
            "check_out",
            "price",
            "booked_on",
        ]

        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}",
            )

        df["check_in"] = pd.to_datetime(df["check_in"]).dt.date
        df["check_out"] = pd.to_datetime(df["check_out"]).dt.date
        df["booked_on"] = pd.to_datetime(df["booked_on"]).dt.date

        bookings = []
        for _, row in df.iterrows():
            booking = Booking(
                property_id=int(row["property_id"]),
                check_in=row["check_in"],
                check_out=row["check_out"],
                price=float(row["price"]),
                booked_on=row["booked_on"],
            )
            bookings.append(booking)

        session.add_all(bookings)
        session.commit()

        # Clear cache after upload
        delete_cache("analytics:revenue_summary")
        delete_cache("analytics:revenue_by_property")
        delete_cache("analytics:revenue_by_city")

        return {
            "message": f"{len(bookings)} bookings uploaded successfully"
        }

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to process uploaded CSV")

# Analytics routes
@router.get("/analytics/revenue", response_model=RevenueSummary)
def get_revenue_summary(session: Session = Depends(get_session)):
    cache_key = "analytics:revenue_summary"
    cached_data = get_cache(cache_key)
    if cached_data:
        return cached_data

    bookings = session.exec(select(Booking)).all()

    total_revenue = sum(booking.price for booking in bookings)
    total_bookings = len(bookings)
    average_booking_value = (
        total_revenue / total_bookings if total_bookings > 0 else 0.0
    )

    result = RevenueSummary(
        total_revenue=total_revenue,
        total_bookings=total_bookings,
        average_booking_value=average_booking_value,
    )

    set_cache(cache_key, result.model_dump(), ttl=300)
    return result


@router.get("/analytics/bookings")
def get_booking_count(session: Session = Depends(get_session)):
    bookings = session.exec(select(Booking)).all()
    return {"total_bookings": len(bookings)}


@router.get("/analytics/revenue/by-property", response_model=list[PropertyRevenue])
def get_revenue_by_property(session: Session = Depends(get_session)):
    cache_key = "analytics:revenue_by_property"
    cached_data = get_cache(cache_key)
    if cached_data:
        return cached_data

    bookings = session.exec(select(Booking)).all()

    revenue_map = {}

    for booking in bookings:
        if booking.property_id not in revenue_map:
            revenue_map[booking.property_id] = {
                "total_revenue": 0.0,
                "booking_count": 0,
            }

        revenue_map[booking.property_id]["total_revenue"] += booking.price
        revenue_map[booking.property_id]["booking_count"] += 1

    result = [
        PropertyRevenue(
            property_id=property_id,
            total_revenue=data["total_revenue"],
            booking_count=data["booking_count"],
        )
        for property_id, data in revenue_map.items()
    ]

    set_cache(cache_key, [item.model_dump() for item in result], ttl=300)
    return result


@router.get("/analytics/revenue/filter", response_model=RevenueSummary)
def get_revenue_summary_filtered(
    start_date: date | None = None,
    end_date: date | None = None,
    session: Session = Depends(get_session),
):
    bookings = session.exec(select(Booking)).all()

    filtered_bookings = []
    for booking in bookings:
        if start_date and booking.check_in < start_date:
            continue
        if end_date and booking.check_out > end_date:
            continue
        filtered_bookings.append(booking)

    total_revenue = sum(booking.price for booking in filtered_bookings)
    total_bookings = len(filtered_bookings)
    average_booking_value = (
        total_revenue / total_bookings if total_bookings > 0 else 0.0
    )

    return RevenueSummary(
        total_revenue=total_revenue,
        total_bookings=total_bookings,
        average_booking_value=average_booking_value,
    )


@router.get("/analytics/revenue/by-city", response_model=list[CityRevenue])
def get_revenue_by_city(session: Session = Depends(get_session)):
    cache_key = "analytics:revenue_by_city"
    cached_data = get_cache(cache_key)
    if cached_data:
        return cached_data

    properties = session.exec(select(Property)).all()
    bookings = session.exec(select(Booking)).all()

    property_city_map = {prop.id: prop.city for prop in properties}
    city_map = defaultdict(lambda: {"total_revenue": 0.0, "booking_count": 0})

    for booking in bookings:
        city = property_city_map.get(booking.property_id, "Unknown")
        city_map[city]["total_revenue"] += booking.price
        city_map[city]["booking_count"] += 1

    result = [
        CityRevenue(
            city=city,
            total_revenue=data["total_revenue"],
            booking_count=data["booking_count"],
        )
        for city, data in city_map.items()
    ]

    set_cache(cache_key, [item.model_dump() for item in result], ttl=300)
    return result


@router.get("/analytics/occupancy", response_model=OccupancySummary)
def get_occupancy_summary(session: Session = Depends(get_session)):
    bookings = session.exec(select(Booking)).all()

    total_booked_nights = 0
    for booking in bookings:
        nights = (booking.check_out - booking.check_in).days
        total_booked_nights += nights

    total_bookings = len(bookings)
    average_length_of_stay = (
        total_booked_nights / total_bookings if total_bookings > 0 else 0.0
    )

    return OccupancySummary(
        total_booked_nights=total_booked_nights,
        total_bookings=total_bookings,
        average_length_of_stay=average_length_of_stay,
    )


# Recommendation routes
@router.get(
    "/recommendations/pricing/{property_id}",
    response_model=PricingRecommendation,
)
def get_pricing_recommendation(
    property_id: int,
    session: Session = Depends(get_session),
):
    property_obj = session.get(Property, property_id)
    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found")

    bookings = session.exec(select(Booking)).all()
    properties = session.exec(select(Property)).all()

    property_bookings = [b for b in bookings if b.property_id == property_id]

    property_city_map = {prop.id: prop.city for prop in properties}
    city_bookings = [
        b for b in bookings if property_city_map.get(b.property_id) == property_obj.city
    ]

    current_base_price = property_obj.base_price

    property_avg = (
        sum(b.price for b in property_bookings) / len(property_bookings)
        if property_bookings
        else current_base_price
    )

    city_avg = (
        sum(b.price for b in city_bookings) / len(city_bookings)
        if city_bookings
        else current_base_price
    )

    recommended_price = current_base_price
    adjustment_type = "keep"
    reason = "Current price is aligned with booking trends."

    if property_avg > current_base_price * 1.1 and city_avg >= current_base_price:
        recommended_price = round(current_base_price * 1.1, 2)
        adjustment_type = "increase"
        reason = "Property bookings and city averages suggest strong demand."
    elif property_avg < current_base_price * 0.9:
        recommended_price = round(current_base_price * 0.9, 2)
        adjustment_type = "decrease"
        reason = "Recent booking values are lower than the current base price."
    elif city_avg > current_base_price * 1.05:
        recommended_price = round(current_base_price * 1.05, 2)
        adjustment_type = "increase"
        reason = "City-wide booking trends support a moderate price increase."

    return PricingRecommendation(
        property_id=property_id,
        current_base_price=current_base_price,
        recommended_price=recommended_price,
        adjustment_type=adjustment_type,
        reason=reason,
    )


# Insights routes
@router.post("/insights/query", response_model=InsightResponse)
def query_insights(
    payload: InsightQuery,
    session: Session = Depends(get_session),
):
    context = build_insight_context(session)
    answer, source = ask_llm(payload.question, context)

    return InsightResponse(
        question=payload.question,
        answer=answer,
        context_summary=context,
        source=source,
    )
