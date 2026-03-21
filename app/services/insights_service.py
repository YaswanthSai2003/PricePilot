from collections import defaultdict

import requests
from sqlmodel import Session, select

from app.core.config import settings
from app.db.models import Booking, Property


def build_insight_context(session: Session) -> str:
    properties = session.exec(select(Property)).all()
    bookings = session.exec(select(Booking)).all()

    if not properties or not bookings:
        return "No sufficient data is available yet."

    property_map = {p.id: p for p in properties}

    total_revenue = sum(b.price for b in bookings)
    total_bookings = len(bookings)

    city_revenue = defaultdict(float)
    city_bookings = defaultdict(int)

    property_revenue = defaultdict(float)
    property_bookings = defaultdict(int)

    total_booked_nights = 0

    for booking in bookings:
        property_obj = property_map.get(booking.property_id)
        city = property_obj.city if property_obj else "Unknown"
        property_name = (
            property_obj.name if property_obj else f"Property {booking.property_id}"
        )

        city_revenue[city] += booking.price
        city_bookings[city] += 1

        property_revenue[property_name] += booking.price
        property_bookings[property_name] += 1

        stay_nights = (booking.check_out - booking.check_in).days
        total_booked_nights += stay_nights

    average_booking_value = (
        total_revenue / total_bookings if total_bookings > 0 else 0.0
    )
    average_length_of_stay = (
        total_booked_nights / total_bookings if total_bookings > 0 else 0.0
    )

    top_city_by_revenue = (
        max(city_revenue.items(), key=lambda x: x[1])[0] if city_revenue else "N/A"
    )
    top_city_by_bookings = (
        max(city_bookings.items(), key=lambda x: x[1])[0] if city_bookings else "N/A"
    )

    top_property_by_revenue = (
        max(property_revenue.items(), key=lambda x: x[1])[0]
        if property_revenue
        else "N/A"
    )
    top_property_by_bookings = (
        max(property_bookings.items(), key=lambda x: x[1])[0]
        if property_bookings
        else "N/A"
    )

    city_revenue_lines = [
        f"{city}: revenue={revenue}"
        for city, revenue in sorted(
            city_revenue.items(), key=lambda x: x[1], reverse=True
        )
    ]

    city_booking_lines = [
        f"{city}: bookings={count}"
        for city, count in sorted(
            city_bookings.items(), key=lambda x: x[1], reverse=True
        )
    ]

    property_revenue_lines = [
        f"{property_name}: revenue={revenue}"
        for property_name, revenue in sorted(
            property_revenue.items(), key=lambda x: x[1], reverse=True
        )
    ]

    property_booking_lines = [
        f"{property_name}: bookings={count}"
        for property_name, count in sorted(
            property_bookings.items(), key=lambda x: x[1], reverse=True
        )
    ]

    context = f"""
Revenue Intelligence Summary

Total bookings: {total_bookings}
Total revenue: {total_revenue}
Average booking value: {average_booking_value}
Total booked nights: {total_booked_nights}
Average length of stay: {average_length_of_stay}

Top city by revenue: {top_city_by_revenue}
Top city by bookings: {top_city_by_bookings}
Top property by revenue: {top_property_by_revenue}
Top property by bookings: {top_property_by_bookings}

City booking breakdown:
{chr(10).join(city_booking_lines)}

City revenue breakdown:
{chr(10).join(city_revenue_lines)}

Property booking breakdown:
{chr(10).join(property_booking_lines)}

Property revenue breakdown:
{chr(10).join(property_revenue_lines)}
""".strip()

    return context


def call_openrouter(prompt: str) -> str:
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": settings.site_url or "http://localhost:8000",
            "X-OpenRouter-Title": settings.site_name or "PricePilot",
        },
        json={
            "model": settings.openai_model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        },
        timeout=20,
    )

    response.raise_for_status()
    data = response.json()

    answer = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

    if not answer:
        raise ValueError("Empty response from LLM provider")

    return answer


def ask_llm(question: str, context: str) -> tuple[str, str]:
    if not settings.openai_api_key:
        return generate_fallback_answer(question, context), "fallback"

    prompt = f"""
You are a revenue intelligence assistant.
Answer only from the provided context.
Be precise and concise.
If the answer is not available in the context, say that clearly.
If there are ranking-style questions such as highest bookings or highest revenue, use the relevant booking or revenue breakdowns from the context.

Context:
{context}

Question:
{question}
""".strip()

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": settings.site_url or "http://localhost:8000",
                "X-OpenRouter-Title": settings.site_name or "PricePilot",
            },
            json={
                "model": settings.openai_model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            },
            timeout=20,
        )

        response.raise_for_status()
        data = response.json()

        answer = (
            data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        )

        if not answer:
            return generate_fallback_answer(question, context), "fallback"

        return answer, "llm"

    except requests.RequestException:
        return generate_fallback_answer(question, context), "fallback"
    except Exception:
        return generate_fallback_answer(question, context), "fallback"
