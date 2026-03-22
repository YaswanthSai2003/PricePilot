# PricePilot

Revenue Intelligence API for Short-Term Rental Analytics.

## Live API
https://pricepilot-api-cek2.onrender.com/

## Features

- FastAPI backend
- Property CRUD APIs
- Filtering and pagination
- CSV booking data upload
- Pandas-based ingestion pipeline
- Revenue and occupancy analytics
- Pricing recommendation engine
- Redis caching
- AI-powered insights endpoint

## Tech Stack

- Python
- FastAPI
- SQLModel / SQLAlchemy
- SQLite (local) / PostgreSQL (production)
- Pandas
- Redis
- OpenAI-compatible LLM integration

## Run locally

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Environment Variables

```bash
DATABASE_URL=your_database_url
REDIS_URL=your_redis_url
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=your_model_name
APP_NAME=Pricepilot
APP_VERSION=1.0.0
DEBUG=true
```

## API Endpoints

- `/` - Root endpoint
- `/docs` - Swagger UI
- `/api/properties` - Property CRUD APIs
- `/api/upload/bookings` - Upload booking CSV
- `/api/analytics/revenue` - Revenue analytics
- `/api/analytics/revenue/by-property` - Revenue by property
- `/api/analytics/revenue/by-city` - Revenue by city
- `/api/analytics/occupancy` - Occupancy summary
- `/api/recommendations/pricing/{property_id}` - Pricing recommendation
- `/api/insights/query` - Natural-language insights

## Example Use Cases

- Upload bookings CSV
- View revenue summaries
- View city-wise analytics
- Get pricing recommendations
- Ask natural-language business questions

## Test Locally

Open these in browser:

- http://127.0.0.1:8000/
- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/api/analytics/revenue

## Sample Bookings CSV

```csv
property_id,check_in,check_out,price,booked_on
1,2026-03-01,2026-03-03,9000,2026-02-20
1,2026-03-05,2026-03-07,9500,2026-02-25
2,2026-03-02,2026-03-04,6000,2026-02-18
3,2026-03-10,2026-03-12,7000,2026-02-28
```
