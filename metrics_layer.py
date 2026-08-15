"""
metrics_layer.py

A "semantic layer" — one place where every business metric used across the
app is defined exactly once, with its official SQL. Both the dashboard
(KPI cards) and the AI chatbot (Ask AI) are made to read from these same
definitions, so their numbers can never quietly disagree with each other.

This file does not touch mydb.py or change anything about how the raw
flight-search / chart data is fetched — it only covers "official" summary
metrics (totals, averages, top values), the kind of number that shows up
on a KPI card or gets asked about in the chatbot.
"""

import pandas as pd
from nl_query_layer import get_engine

# ---------------------------------------------------------------------
# Metric definitions — the single source of truth.
#
# Each metric has:
#   sql      - the one official query that defines this metric
#   kind     - "scalar" (one number) or "table" (a small result set)
#   label    - human-readable name, used in display and in explanations
#   aliases  - phrases that, if found in a user's question, mean
#              "this question is asking for this metric"
# ---------------------------------------------------------------------

METRICS = {
    "total_flights": {
        "sql": "SELECT COUNT(*) AS total_flights FROM flights",
        "kind": "scalar",
        "label": "Total Flights",
        "aliases": ["total flights", "how many flights", "number of flights"],
    },
    "total_airlines": {
        "sql": "SELECT COUNT(DISTINCT airline) AS total_airlines FROM flights",
        "kind": "scalar",
        "label": "Total Airlines",
        "aliases": ["total airlines", "how many airlines", "number of airlines"],
    },
    "total_routes": {
        "sql": "SELECT COUNT(DISTINCT CONCAT(Source, destination)) AS total_routes FROM flights",
        "kind": "scalar",
        "label": "Total Routes",
        "aliases": ["total routes", "how many routes", "number of routes"],
    },
    "avg_price": {
        "sql": "SELECT ROUND(AVG(Price), 0) AS avg_price FROM flights",
        "kind": "scalar",
        "label": "Average Price",
        "aliases": ["average price", "avg price", "mean price"],
    },
    "nonstop_rate": {
        "sql": """
            SELECT ROUND(
                100.0 * SUM(CASE WHEN Total_stops = 'non-stop' THEN 1 ELSE 0 END) / COUNT(*),
                1
            ) AS nonstop_rate
            FROM flights
        """,
        "kind": "scalar",
        "label": "Non-stop Flight Rate (%)",
        "aliases": ["nonstop rate", "non-stop rate", "% non-stop", "percent non-stop", "percentage of non-stop flights"],
    },
    "busiest_route": {
        "sql": """
            SELECT CONCAT(Source, ' -> ', destination) AS route, COUNT(*) AS flights
            FROM flights
            GROUP BY route
            ORDER BY flights DESC
            LIMIT 1
        """,
        "kind": "table",
        "label": "Busiest Route",
        "aliases": ["busiest route", "most popular route", "route with the most flights"],
    },
    "busiest_airport": {
        "sql": """
            SELECT Source AS airport, COUNT(*) AS flights
            FROM flights
            GROUP BY Source
            ORDER BY flights DESC
            LIMIT 1
        """,
        "kind": "table",
        "label": "Busiest Airport",
        "aliases": ["busiest airport", "busiest city", "airport with the most flights"],
    },
    "avg_price_by_airline": {
        "sql": """
            SELECT airline, ROUND(AVG(Price), 0) AS avg_price
            FROM flights
            GROUP BY airline
            ORDER BY avg_price DESC
        """,
        "kind": "table",
        "label": "Average Price by Airline",
        "aliases": ["average price per airline", "average price by airline", "avg price per airline", "price by airline"],
    },
    "cheapest_flight_by_route": {
        "sql": """
            SELECT CONCAT(Source, ' -> ', destination) AS route, MIN(Price) AS cheapest_price
            FROM flights
            GROUP BY route
            ORDER BY cheapest_price ASC
        """,
        "kind": "table",
        "label": "Cheapest Flight per Route",
        "aliases": ["cheapest flight per route", "cheapest flight by route", "lowest price per route"],
    },
}


def run_metric(metric_key):
    """Runs a metric's official SQL and returns the raw DataFrame."""
    metric = METRICS[metric_key]
    engine = get_engine()
    return pd.read_sql(metric["sql"], engine)


def get_scalar_metric(metric_key):
    """For 'scalar' metrics — runs the query and returns just the single value."""
    df = run_metric(metric_key)
    return df.iloc[0, 0]


def match_question_to_metric(question):
    """
    Very lightweight keyword matching: if the question contains a phrase
    that's a known alias for a metric, return that metric's key. Otherwise
    return None, meaning "no official metric matches — let the LLM write
    custom SQL instead."

    Deliberately simple (substring matching, not NLU) — good enough to
    demonstrate the concept without adding fragile complexity.
    """
    question_lower = question.lower()
    for metric_key, metric in METRICS.items():
        for alias in metric["aliases"]:
            if alias in question_lower:
                return metric_key
    return None


def get_kpis():
    """Convenience function for the dashboard's 4 KPI cards."""
    total_flights = get_scalar_metric("total_flights")
    total_airlines = get_scalar_metric("total_airlines")
    total_routes = get_scalar_metric("total_routes")
    avg_price = get_scalar_metric("avg_price")
    return total_flights, total_airlines, total_routes, avg_price


if __name__ == "__main__":
    for key in METRICS:
        print(key, "->")
        print(run_metric(key))
        print()