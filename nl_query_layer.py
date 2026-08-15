import json
import re
import os
import pandas as pd
import plotly.express as px
import requests
from urllib.parse import quote_plus
from sqlalchemy import create_engine


def get_engine():
    password = os.environ.get("DB_PASSWORD", "@amit03")
    safe_password = quote_plus(password)
    return create_engine(f"mysql+pymysql://root:{safe_password}@localhost:3306/flights")


SCHEMA_DESCRIPTION = """
Table: flights
Columns:
  - airline (VARCHAR)
  - date_of_journey (DATE)
  - Source (VARCHAR)
  - destination (VARCHAR)
  - route (VARCHAR)
  - dep_time (TIME)
  - Arrival_time (TIME)
  - Duration (VARCHAR)
  - Total_stops (VARCHAR)
  - Price (INT)
"""

ALLOWED_TABLES = {"flights"}

GEMINI_MODEL = "gemini-3-flash-preview"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


def is_safe_select(sql):
    cleaned = sql.strip().rstrip(";")

    if not cleaned.lower().startswith("select"):
        return False

    forbidden = ["insert", "update", "delete", "drop", "alter", "create",
                 "truncate", "grant", "attach", "pragma", ";"]
    lowered = cleaned.lower()
    if any(word in lowered for word in forbidden):
        return False

    tables_mentioned = set(re.findall(r"from\s+([a-zA-Z_][a-zA-Z0-9_]*)", lowered)) | \
                        set(re.findall(r"join\s+([a-zA-Z_][a-zA-Z0-9_]*)", lowered))
    if not tables_mentioned.issubset(ALLOWED_TABLES):
        return False

    return True


def call_llm(prompt, max_tokens=500):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    response = requests.post(
        f"{GEMINI_API_URL}?key={api_key}",
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens},
        },
    )
    data = response.json()

    if "candidates" not in data:
        error_message = data.get("error", {}).get("message", str(data))
        raise RuntimeError(f"Gemini API error: {error_message}")

    return data["candidates"][0]["content"]["parts"][0]["text"]


def question_to_sql(question):
    prompt = f"""You write MySQL SELECT queries only.

Schema:
{SCHEMA_DESCRIPTION}

Rules:
- Only use the table and columns listed above.
- Only write a single SELECT statement. No semicolons, no comments.
- Use standard MySQL syntax.
- Return ONLY the raw SQL, nothing else.

Question: {question}
SQL:"""
    sql = call_llm(prompt, max_tokens=300).strip()
    sql = re.sub(r"^```sql|```$|^```", "", sql.strip(), flags=re.MULTILINE).strip()
    return sql


def explain_result(question, df):
    sample = df.head(20).to_dict(orient="records")
    prompt = f"""A user asked: "{question}"

The query returned this data (showing up to 20 rows):
{json.dumps(sample, default=str)}

Write a short, plain-English answer (2-4 sentences) directly addressing
the question, using only these numbers. Do not invent any data not shown here.
If the data doesn't fully answer the question, say so."""
    return call_llm(prompt, max_tokens=300).strip()


def make_chart(df):
    if df.empty or df.shape[1] < 2:
        return None
    x_col = df.columns[0]
    y_col = df.columns[1]
    try:
        if pd.api.types.is_numeric_dtype(df[y_col]):
            if df.shape[0] <= 15:
                return px.bar(df, x=x_col, y=y_col)
            return px.line(df, x=x_col, y=y_col)
    except Exception:
        return None
    return None


def ask_question(question, engine):
    # Check the metrics layer first: if this question matches a known,
    # officially-defined metric, use that metric's exact SQL instead of
    # letting the LLM guess its own. This guarantees the chatbot's answer
    # always matches what the dashboard's KPI cards show for the same
    # metric — no drift between the two.
    from metrics_layer import match_question_to_metric, METRICS

    matched_key = match_question_to_metric(question)

    if matched_key:
        sql = METRICS[matched_key]["sql"].strip()
        try:
            df = pd.read_sql(sql, engine)
        except Exception as e:
            return {
                "sql": sql,
                "data": pd.DataFrame(),
                "explanation": f"The query failed to run: {e}",
                "chart": None,
            }
        explanation = explain_result(question, df)
        chart = make_chart(df)
        return {"sql": sql, "data": df, "explanation": explanation, "chart": chart}

    sql = question_to_sql(question)

    if not is_safe_select(sql):
        return {
            "sql": sql,
            "data": pd.DataFrame(),
            "explanation": "I couldn't safely answer that. Try rephrasing the question.",
            "chart": None,
        }

    try:
        df = pd.read_sql(sql, engine)
    except Exception as e:
        return {
            "sql": sql,
            "data": pd.DataFrame(),
            "explanation": f"The query failed to run: {e}",
            "chart": None,
        }

    explanation = explain_result(question, df)
    chart = make_chart(df)

    return {"sql": sql, "data": df, "explanation": explanation, "chart": chart}