
from mcp.server import MCPServer
import json
import os

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()   

# Set up the MCP server with a name and description.
mcp = MCPServer("Weather & Disaster Intelligence")

# Add a resource to provide a catalog of the weather database datasets and limitations.
@mcp.resource(
    "weather://database/catalog",
    name="Weather Database Catalog",
    description="Describes the weather forecast and disaster alert datasets available to the MCP server.",
    mime_type="application/json",
)

# Add a resource to provide a catalog of the weather database datasets and limitations.
def get_weather_database_catalog() -> str:
    """Return a JSON catalog of the weather database datasets and limitations."""
    catalog = {
        "datasets": [
            {
                "name": "district_wise_7dayfc_severity",
                "table": "weatherdata.district_wise_7dayfc_severity",
                "description": "District-wise 7-day weather forecasts and severity levels.",
                "available_fields": [
                    "days",
                    "date",
                    "district",
                    "temp_min",
                    "temp_max",
                    "rain_percent",
                    "rain_precip",
                    "wind",
                    "humidity",
                    "visibility",
                    "condition_text",
                ],
            },
            {
                "name": "disaster_ndma",
                "table": "weatherdata.disaster_ndma",
                "description": "Normalized NDMA disaster alerts.",
                "available_fields": [
                    "district",
                    "state_ut",
                    "severity",
                    "effective_start_time",
                    "effective_end_time",
                    "disaster_type",
                    "warning_message",
                    "alert_source",
                    "inserted_at",
                ],
            },
        ],
        "limitations": [
            "The forecast dataset contains only the available 7-day forecasts.",
            "A forecast beyond the available dates requires another forecast source or a validated predictive model.",
            "Historical observations must be available separately for historical trend analysis or model training.",
        ],
    }

    return json.dumps(catalog, indent=2)

# Define a prompt for analyzing weather risk in a district, focusing on forecast and active disaster alerts.
@mcp.prompt()
def analyze_weather_risk(
    district: str,
    focus: str = "forecast and active disaster alerts",
) -> str:
    """Analyze a district's weather forecast and disaster risks."""

    return f"""
You are a Weather and Disaster Intelligence Assistant.

Analyze the weather situation for the district: {district}

Analysis focus: {focus}

Instructions:
1. Use get_district_forecast to retrieve the available forecast.
2. Use get_disaster_alerts to retrieve relevant disaster alerts.
3. Use get_district_disaster_summary if a combined district summary is useful.
4. Explain temperature, rainfall, wind, visibility, and relevant severity levels
   using only the data returned by the tools.
5. Clearly identify active alerts and their effective times when available.
6. If a tool returns no data, state that the information is unavailable.
7. Do not invent forecast values or claim to predict weather beyond the
   available forecast period.
8. Distinguish retrieved weather data from your own explanation.

Present the answer with:
- Forecast summary
- Relevant disaster alerts
- Potential risks
- Practical precautions
- Data limitations
"""

def get_db_connection():
    """Create a PostgreSQL connection using environment variables."""
    return psycopg.connect(
        host=os.environ["PGHOST"],
        port=int(os.getenv("PGPORT", "5432")),
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        sslmode=os.getenv("PGSSLMODE", "prefer"),
        connect_timeout=10,
        row_factory=dict_row,
    )


@mcp.tool()
def get_district_forecast(
    district: str,
    limit: int = 7,
) -> str:
    """Get current and upcoming forecast records for a district
    from the PostgreSQL weather database.

    Args:
        district: District name, for example Korba.
        limit: Maximum number of records to return, from 1 to 50.
    """
    district = district.strip()

    if not district:
        raise ValueError("District name cannot be empty.")

    if not 1 <= limit <= 50:
        raise ValueError("Limit must be between 1 and 50.")

    query = """
        SELECT
            date,
            days,
            district,
            circle,
            indus_circle,
            temp_min,
            temp_max,
            rain_percent,
            rain_precip,
            wind,
            visibility,
            humidity,
            temp_min_severity,
            temp_max_severity,
            rain_severity,
            wind_severity,
            visibility_severity,
            condition_text
        FROM weatherdata.district_wise_7dayfc_severity
        WHERE district ILIKE %s
          AND inserted_at::Date >= CURRENT_DATE
        ORDER BY inserted_at ASC, days ASC
        LIMIT %s;
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (district, limit))
            rows = cur.fetchall()

    return json.dumps(
        {
            "district": district,
            "record_count": len(rows),
            "forecasts": rows,
        },
        default=str,
        indent=2,
    )



@mcp.tool()
def get_high_risk_districts(
    limit: int = 100,
) -> str:
    """Find districts with High or Extreme forecast severity.

    Checks temperature, rainfall, wind, and visibility severity.
    Returns the forecast date, district, hazard type, and severity.

    Args:
        limit: Maximum number of risk records, from 1 to 100.
    """
   

    if not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100.")

    query = """
        SELECT
            f.date,
            f.days,
            f.district,
            f.circle,
            f.indus_circle,
            risks.hazard,
            risks.severity
        FROM weatherdata.district_wise_7dayfc_severity AS f
        CROSS JOIN LATERAL (
            VALUES
                ('Minimum Temperature', f.temp_min_severity),
                ('Maximum Temperature', f.temp_max_severity),
                ('Rainfall', f.rain_severity),
                ('Wind', f.wind_severity),
                ('Visibility', f.visibility_severity)
        ) AS risks(hazard, severity)
        WHERE f.inserted_at::Date >= CURRENT_DATE
          AND risks.severity IN ('High', 'Extreme')
        ORDER BY
            f.inserted_at ASC,
            CASE risks.severity
                WHEN 'Extreme' THEN 2
                WHEN 'High' THEN 1
                ELSE 0
            END DESC,
            f.district ASC
        LIMIT %s;
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (limit,))
            rows = cur.fetchall()

    return json.dumps(
        {
            "record_count": len(rows),
            "risk_records": rows,
        },
        default=str,
        indent=2,
    )



@mcp.tool()
def get_disaster_alerts(
    disaster_type: str = "",
    district: str = "",
    state_ut: str = "",
    active_only: bool = True,
    limit: int = 50,
) -> str:
    """Retrieve NDMA disaster alerts from PostgreSQL.

    Args:
        disaster_type: Optional disaster type, such as Lightning or Cyclone.
        district: Optional district name.
        state_ut: Optional state or union territory.
        active_only: Return alerts active at the current database time.
        limit: Maximum records to return, from 1 to 100.
    """

    if not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100.")

    conditions = []
    params = []

    if disaster_type.strip():
        conditions.append("disaster_type ILIKE %s")
        params.append(f"%{disaster_type.strip()}%")

    if district.strip():
        conditions.append("district ILIKE %s")
        params.append(district.strip())

    if state_ut.strip():
        conditions.append("state_ut ILIKE %s")
        params.append(state_ut.strip())

    if active_only:
        conditions.extend([
            "effective_start_time <= CURRENT_TIMESTAMP",
            "effective_end_time >= CURRENT_TIMESTAMP",
        ])

    where_clause = (
        "WHERE " + " AND ".join(conditions)
        if conditions else ""
    )

    query = f"""
        SELECT
            identifier,
            district,
            state_ut,
            indus_circle,
            disaster_type,
            severity,
            severity_level,
            effective_start_time,
            effective_end_time,
            area_description,
            warning_message,
            severity_color,
            alert_source,
            alert_from,
            area_covered,
            inserted_at
        FROM weatherdata.disaster_ndma
        {where_clause}
        ORDER BY effective_start_time DESC NULLS LAST
        LIMIT %s;
    """

    params.append(limit)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, tuple(params))
            rows = cur.fetchall()

    return json.dumps(
        {
            "record_count": len(rows),
            "active_only": active_only,
            "filters": {
                "disaster_type": disaster_type,
                "district": district,
                "state_ut": state_ut,
            },
            "alerts": rows,
        },
        default=str,
        indent=2,
    )


@mcp.tool()
def get_district_disaster_summary(district: str) -> str:
    """Combine a district's seven-day forecast and active NDMA alerts.

    Args:
        district: District name, for example Korba or Raipur.
    """

    district = district.strip()

    if not district:
        raise ValueError("District name cannot be empty.")

    forecast_query = """
        SELECT
            "date",
            days,
            district,
            circle,
            indus_circle,
            temp_min,
            temp_max,
            rain_percent,
            rain_precip,
            wind,
            visibility,
            humidity,
            temp_min_severity,
            temp_max_severity,
            rain_severity,
            wind_severity,
            visibility_severity,
            condition_text
        FROM weatherdata.district_wise_7dayfc_severity
        WHERE district ILIKE %s
          AND inserted_at::Date >= CURRENT_DATE
        ORDER BY inserted_at ASC
        LIMIT 7;
    """

    alerts_query = """
        SELECT
            identifier,
            district,
            state_ut,
            disaster_type,
            severity,
            severity_level,
            effective_start_time,
            effective_end_time,
            area_description,
            warning_message,
            alert_source
        FROM weatherdata.disaster_ndma
        WHERE (
            district ILIKE %s
            OR (
                district IS NULL
                AND area_description ILIKE %s
            )
        )
          AND effective_start_time <= CURRENT_TIMESTAMP
          AND effective_end_time >= CURRENT_TIMESTAMP
        ORDER BY effective_start_time DESC
        LIMIT 50;
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(forecast_query, (district,))
            forecasts = cur.fetchall()

            cur.execute(
                alerts_query,
                (district, f"%{district}%"),
            )
            alerts = cur.fetchall()

    severity_rank = {
        "No Risk": 0,
        "Low": 1,
        "Moderate": 2,
        "High": 3,
        "Extreme": 4,
    }

    forecast_severity_fields = [
        "temp_min_severity",
        "temp_max_severity",
        "rain_severity",
        "wind_severity",
        "visibility_severity",
    ]

    forecast_severities = [
        str(row[field]).strip()
        for row in forecasts
        for field in forecast_severity_fields
        if row.get(field) is not None
    ]

    highest_forecast_severity = max(
        forecast_severities,
        key=lambda value: severity_rank.get(value, -1),
        default=None,
    )

    return json.dumps(
        {
            "district": district,
            "forecast": {
                "record_count": len(forecasts),
                "highest_severity": highest_forecast_severity,
                "records": forecasts,
            },
            "ndma_alerts": {
                "active_alert_count": len(alerts),
                "alerts": alerts,
            },
            "data_status": {
                "forecast_available": len(forecasts) > 0,
                "active_alerts_found": len(alerts) > 0,
            },
        },
        default=str,
        indent=2,
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
