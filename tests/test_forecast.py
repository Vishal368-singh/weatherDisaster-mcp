
from unittest.mock import patch
from server import get_district_forecast


@patch("server.fetch_forecast_from_database")
def test_forecast_success(mock_fetch):

    mock_fetch.return_value = [
        {
            "district": "Korba",
            "temp_max": 34,
            "temp_min": 23,
            "rain_precip": 12.5
        }
    ]

    result = get_district_forecast(
        district="Korba",
        limit=7
    )

    assert result["success"] is True
    assert result["data"]["district"] == "Korba"
    assert len(result["data"]["forecast"]) == 1

    mock_fetch.assert_called_once_with("Korba", 7)


@patch("server.fetch_forecast_from_database")
def test_forecast_no_records(mock_fetch):

    mock_fetch.return_value = []

    result = get_district_forecast(
        district="UnknownDistrict",
        limit=7
    )

    assert result["success"] is True
    assert result["data"]["forecast"] == []
