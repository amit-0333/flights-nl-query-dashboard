"""
test_project.py

Tests for the core logic in this project — the parts where a small,
silent mistake could quietly produce a wrong answer instead of an
obvious crash.

These tests do NOT touch the real MySQL database and do NOT call the
Gemini API. They only test plain Python functions with small, made-up
example data, so they run instantly and cost nothing.

How to run:
    pip install pytest --break-system-packages   (one-time setup)
    pytest test_project.py -v

"-v" just shows each individual test name as it runs, so you can see
exactly what passed/failed instead of just a final count.
"""

import pandas as pd
import pytest

from anomaly_detection import (
    parse_duration_to_minutes,
    parse_stops_to_int,
    compute_zscores,
    flag_anomalies,
)
from metrics_layer import match_question_to_metric
from nl_query_layer import is_safe_select



# 1. Duration parsing — "2h 50m" -> 170 minutes


def test_parse_duration_hours_and_minutes():
    assert parse_duration_to_minutes("2h 50m") == 170

def test_parse_duration_hours_only():
    assert parse_duration_to_minutes("5h") == 300

def test_parse_duration_minutes_only():
    assert parse_duration_to_minutes("45m") == 45

def test_parse_duration_missing_value_returns_none():
    assert parse_duration_to_minutes(None) is None

def test_parse_duration_handles_uppercase():
    assert parse_duration_to_minutes("2H 30M") == 150



# 2. Stops parsing — "non-stop" -> 0, "1 stop" -> 1, etc.


def test_parse_stops_nonstop():
    assert parse_stops_to_int("non-stop") == 0

def test_parse_stops_one():
    assert parse_stops_to_int("1 stop") == 1

def test_parse_stops_multiple():
    assert parse_stops_to_int("2 stops") == 2

def test_parse_stops_missing_value_returns_none():
    assert parse_stops_to_int(None) is None



# 3. Severity scoring — the core "is this flight an anomaly?" logic
#
# We build a small, fake dataset by hand (not real data) so we know
# exactly what the "normal" range is, and can check the detector finds
# exactly the anomaly we planted.


def make_fake_flights():
    """
    5 very consistent DEL-BOM flights (the 'normal' baseline), plus
    1 flight that is deliberately priced, timed, AND stopped way outside
    that normal range — this is the planted anomaly.
    """
    data = {
        "Airline": ["IndiGo"] * 6,
        "Route": ["DEL-BOM"] * 6,
        "Price": [5000, 5200, 4900, 5100, 5300, 15000],       # last one is the anomaly
        "Duration": ["2h 30m", "2h 45m", "2h 20m", "2h 35m", "2h 40m", "6h 10m"],
        "Total_stops": ["non-stop", "non-stop", "non-stop", "non-stop", "non-stop", "2 stops"],
    }
    return pd.DataFrame(data)


def test_severity_high_when_all_three_factors_flagged():
    df = make_fake_flights()
    df = compute_zscores(df)
    anomalies = flag_anomalies(df, z_threshold=1.5, min_route_size=5)

    # exactly one flight should be flagged (the planted anomaly)
    assert len(anomalies) == 1
    assert anomalies.iloc[0]["Price"] == 15000
    assert anomalies.iloc[0]["Severity"] == "High"


def test_normal_flights_are_not_flagged():
    df = make_fake_flights()
    df = compute_zscores(df)
    anomalies = flag_anomalies(df, z_threshold=1.5, min_route_size=5)

    # none of the 5 normal flights should appear in the results
    normal_prices = {5000, 5200, 4900, 5100, 5300}
    flagged_prices = set(anomalies["Price"])
    assert normal_prices.isdisjoint(flagged_prices)


def test_route_column_survives_the_pipeline():
    # regression test for the earlier groupby().apply() bug, where the
    # 'Route' column silently disappeared partway through the pipeline
    df = make_fake_flights()
    df = compute_zscores(df)
    assert "Route" in df.columns


def test_small_routes_are_skipped():
    # a route with only 2 flights shouldn't be trusted enough to flag
    data = {
        "Airline": ["IndiGo", "IndiGo"],
        "Route": ["DEL-GOA", "DEL-GOA"],
        "Price": [5000, 50000],  # huge difference, but too few flights to trust
        "Duration": ["2h", "2h"],
        "Total_stops": ["non-stop", "non-stop"],
    }
    df = pd.DataFrame(data)
    df = compute_zscores(df)
    anomalies = flag_anomalies(df, z_threshold=1.5, min_route_size=5)
    assert len(anomalies) == 0




# 4. Metric matching — does a question correctly find its metric?


def test_matches_average_price():
    assert match_question_to_metric("What is the average price?") == "avg_price"

def test_matches_total_flights():
    assert match_question_to_metric("How many total flights are there?") == "total_flights"

def test_matches_busiest_route():
    assert match_question_to_metric("What is the busiest route?") == "busiest_route"

def test_no_match_returns_none_for_unrelated_question():
    result = match_question_to_metric("Show me flights from Mumbai to Delhi under 5000")
    assert result is None

def test_matching_is_case_insensitive():
    assert match_question_to_metric("WHAT IS THE AVERAGE PRICE?") == "avg_price"




# 5. SQL safety check — the boundary protecting the real database

def test_accepts_plain_select():
    assert is_safe_select("SELECT * FROM flights WHERE Price > 5000") is True

def test_rejects_insert():
    assert is_safe_select("INSERT INTO flights VALUES (1,2,3)") is False

def test_rejects_delete():
    assert is_safe_select("DELETE FROM flights WHERE Price > 5000") is False

def test_rejects_drop_table():
    assert is_safe_select("DROP TABLE flights") is False

def test_rejects_stacked_queries():
    assert is_safe_select("SELECT * FROM flights; DROP TABLE flights") is False

def test_rejects_queries_on_other_tables():
    assert is_safe_select("SELECT * FROM users") is False

def test_rejects_non_select_statement():
    assert is_safe_select("UPDATE flights SET Price = 0") is False


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))