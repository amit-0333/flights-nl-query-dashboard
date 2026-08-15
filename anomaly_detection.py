"""
anomaly_detection.py

Finds unusual flights by comparing each flight to other flights on the
SAME route (price, duration, number of stops), then asks Gemini to
write a short plain-English explanation for the most severe anomalies.

Design choices (kept deliberately simple + cheap):
  - Detection itself is 100% local pandas/numpy math. No API calls,
    no cost, can be re-run as many times as you like.
  - Only the final, already-flagged anomalies are sent to Gemini,
    and only the TOP_N most severe ones (see TOP_N below) — this
    protects the free-tier quota.
  - Each Gemini call gets just that one flight's numbers plus its
    own route's average/spread. No cross-route comparison data is
    sent, keeping each prompt small and cheap.
"""

import re
import time
import pandas as pd

from mydb import DB
from nl_query_layer import call_llm

#  tunable settings 
Z_THRESHOLD = 2.0      # how many std devs away counts as "unusual"
MIN_ROUTE_SIZE = 5     # ignore routes with too few flights to trust a z-score
TOP_N = 8             # max anomalies to send to Gemini for explanation


#  step 1: get the data 

def fetch_flight_data():
    """Pulls the columns needed for anomaly detection into a DataFrame."""
    db = DB()
    rows = db.fetch_all_flights_raw()
    df = pd.DataFrame(rows, columns=["Airline", "Route", "Price", "Duration", "Total_stops"])
    return df


#  step 2: turn messy text columns into numbers 

def parse_duration_to_minutes(duration_str):
    """'2h 50m' -> 170. Handles missing hour or minute parts."""
    if pd.isna(duration_str):
        return None
    text = str(duration_str).strip().lower()

    hours_match = re.search(r"(\d+)\s*h", text)
    minutes_match = re.search(r"(\d+)\s*m", text)

    if not hours_match and not minutes_match:
        try:
            return float(text)
        except ValueError:
            return None

    hours = int(hours_match.group(1)) if hours_match else 0
    minutes = int(minutes_match.group(1)) if minutes_match else 0
    return hours * 60 + minutes


def parse_stops_to_int(stops_str):
    """'non-stop' -> 0, '1 stop' -> 1, '2 stops' -> 2, etc."""
    if pd.isna(stops_str):
        return None
    text = str(stops_str).strip().lower()

    if "non" in text:
        return 0

    match = re.search(r"(\d+)", text)
    if match:
        return int(match.group(1))
    return None


#  step 3: z-scores per route 

def compute_zscores(df):
    df = df.copy()
    df["duration_minutes"] = df["Duration"].apply(parse_duration_to_minutes)
    df["stops_num"] = df["Total_stops"].apply(parse_stops_to_int)
    df = df.dropna(subset=["Price", "duration_minutes", "stops_num"])

    # Compute per-route mean/std/size once, then merge back onto every row.
    # (Using groupby().agg() + merge() instead of groupby().apply() — newer
    # pandas versions can silently drop the grouping column when using
    # .apply(), which caused a KeyError on 'Route' further down the pipeline.)
    stats = df.groupby("Route").agg(
        price_mean=("Price", "mean"),
        price_std=("Price", "std"),
        duration_mean=("duration_minutes", "mean"),
        duration_std=("duration_minutes", "std"),
        stops_mean=("stops_num", "mean"),
        stops_std=("stops_num", "std"),
        route_size=("Price", "size"),
    ).reset_index()

    df = df.merge(stats, on="Route", how="left")

    def safe_z(value, mean, std):
        return (value - mean) / std

    df["price_z"] = safe_z(df["Price"], df["price_mean"], df["price_std"])
    df["duration_z"] = safe_z(df["duration_minutes"], df["duration_mean"], df["duration_std"])
    df["stops_z"] = safe_z(df["stops_num"], df["stops_mean"], df["stops_std"])

    # Routes where every flight is identical (std == 0 or NaN) can't have a
    # meaningful z-score — treat those as "not anomalous" rather than NaN/inf.
    for z_col in ["price_z", "duration_z", "stops_z"]:
        df[z_col] = df[z_col].replace([float("inf"), float("-inf")], 0.0).fillna(0.0)

    df["route_avg_price"] = df["price_mean"]
    df["route_avg_duration"] = df["duration_mean"]
    df["route_avg_stops"] = df["stops_mean"]

    return df


#  step 4: flag + score severity 

def flag_anomalies(df, z_threshold=Z_THRESHOLD, min_route_size=MIN_ROUTE_SIZE):
    df = df[df["route_size"] >= min_route_size].copy()

    df["price_flag"] = df["price_z"].abs() > z_threshold
    df["duration_flag"] = df["duration_z"].abs() > z_threshold
    df["stops_flag"] = df["stops_z"].abs() > z_threshold

    df["severity_score"] = (
        df["price_flag"].astype(int)
        + df["duration_flag"].astype(int)
        + df["stops_flag"].astype(int)
    )

    anomalies = df[df["severity_score"] >= 1].copy()
    anomalies["max_abs_z"] = anomalies[["price_z", "duration_z", "stops_z"]].abs().max(axis=1)
    anomalies = anomalies.sort_values(["severity_score", "max_abs_z"], ascending=[False, False])

    severity_label = {1: "Low", 2: "Medium", 3: "High"}
    anomalies["Severity"] = anomalies["severity_score"].map(severity_label)

    return anomalies


#  step 5: Gemini explanation (only for top N) 

def build_explanation_prompt(row):
    return f"""A flight on route {row['Route']} was flagged as a pricing/routing anomaly.

This flight:
- Price: ₹{row['Price']:.0f}
- Duration: {row['duration_minutes']:.0f} minutes
- Stops: {row['stops_num']:.0f}

Normal range for this route (based on {row['route_size']} flights):
- Average price: ₹{row['route_avg_price']:.0f}
- Average duration: {row['route_avg_duration']:.0f} minutes
- Average stops: {row['route_avg_stops']:.1f}

In 1-2 short sentences, explain in plain English why this flight looks unusual
compared to the route's normal pattern. Base your answer only on the numbers
above — do not invent extra facts."""


def generate_explanation(row, retries=2, retry_delay_seconds=8):
    """
    Calls Gemini for one explanation. Free-tier Gemini has a per-minute
    rate limit, and firing many calls back-to-back can hit it partway
    through a batch. If that happens, wait a bit and retry before
    giving up on this particular row.
    """
    prompt = build_explanation_prompt(row)

    last_error = None
    for attempt in range(retries + 1):
        try:
            return call_llm(prompt, max_tokens=120).strip()
        except Exception as e:
            last_error = e
            error_text = str(e).lower()
            is_rate_limit = "429" in error_text or "quota" in error_text or "rate" in error_text
            if is_rate_limit and attempt < retries:
                time.sleep(retry_delay_seconds)
                continue
            break

    return f"(explanation unavailable: {last_error})"


#  main entry point 

def detect_anomalies(top_n=TOP_N, z_threshold=Z_THRESHOLD, min_route_size=MIN_ROUTE_SIZE):
    """
    Runs the full pipeline: fetch -> parse -> z-score -> flag -> explain.
    Returns a DataFrame of the top_n most severe anomalies, with an
    'explanation' column filled in by Gemini.
    """
    df = fetch_flight_data()
    df = compute_zscores(df)
    anomalies = flag_anomalies(df, z_threshold, min_route_size)

    top = anomalies.head(top_n).copy()

    explanations = []
    for i, (_, row) in enumerate(top.iterrows()):
        explanations.append(generate_explanation(row))
        if i < len(top) - 1:
            time.sleep(2)  # small pause between calls to stay under free-tier rate limits
    top["Explanation"] = explanations

    top["Duration (min)"] = top["duration_minutes"].round(0).astype(int)
    top["Stops"] = top["stops_num"].round(0).astype(int)
    top["Price Z"] = top["price_z"].round(2)
    top["Duration Z"] = top["duration_z"].round(2)
    top["Stops Z"] = top["stops_z"].round(2)

    display_cols = [
        "Airline", "Route", "Price", "Duration (min)", "Stops",
        "Severity", "Price Z", "Duration Z", "Stops Z", "Explanation",
    ]
    return top[display_cols].reset_index(drop=True)


if __name__ == "__main__":
    result = detect_anomalies()
    print(result)