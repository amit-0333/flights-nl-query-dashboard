<div align="center">

```
██╗███╗   ██╗██████╗ ██╗ █████╗ ███╗   ██╗    ███████╗██╗     ██╗ ██████╗ ██╗  ██╗████████╗███████╗
██║████╗  ██║██╔══██╗██║██╔══██╗████╗  ██║    ██╔════╝██║     ██║██╔════╝ ██║  ██║╚══██╔══╝██╔════╝
██║██╔██╗ ██║██║  ██║██║███████║██╔██╗ ██║    █████╗  ██║     ██║██║  ███╗███████║   ██║   ███████╗
██║██║╚██╗██║██║  ██║██║██╔══██║██║╚██╗██║    ██╔══╝  ██║     ██║██║   ██║██╔══██║   ██║   ╚════██║
██║██║ ╚████║██████╔╝██║██║  ██║██║ ╚████║    ██║     ███████╗██║╚██████╔╝██║  ██║   ██║   ███████║
╚═╝╚═╝  ╚═══╝╚═════╝ ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝    ╚═╝     ╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝
```

### 🛫 Indian Flight Analytics — with AI-Powered Natural Language Queries

> An interactive Streamlit dashboard for exploring Indian domestic flight data, extended with an AI layer that lets you ask questions in plain English and get real, grounded answers — not guesses.

<br/>

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini_API-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)
![Status](https://img.shields.io/badge/Status-Complete-brightgreen?style=for-the-badge)

</div>

---

## 📌 About

Most BI dashboards are static — they show a fixed set of charts, and if someone wants to ask something the dashboard wasn't built for, they either can't find the answer or have to wait on an analyst. This project explores fixing that.

It's a two-part system built on top of a MySQL database of **15,000+ Indian domestic flight records** across **10 airlines** and **380+ routes**:

1. **A traditional analytics dashboard** — flight search, filtering, sorting, and six visualizations covering pricing, routes, airports, and time trends.
2. **A natural language query layer** — type a question in plain English, and the system converts it into a real SQL query, runs it against the live database, explains the result in grounded plain English, and auto-generates a chart when the data supports one.

The core design challenge wasn't calling an LLM — it was making sure it **couldn't hallucinate or do anything unsafe**. See [Safety Design](#-safety-design) below.

---

## ⚙️ Features

**Check Flights**
- Search flights by Source & Destination
- Sort by Price or Duration
- Filter by Airline
- Cheapest flight highlighted in green
- Shows total flights found

**Show Analytics**
- KPI Cards — Total Flights, Airlines, Routes, Avg Price
- Pie Chart — Flights per Airline
- Bar Chart — Avg Price per Airline
- Bar Chart — Busiest Airports
- Bar Chart — Top 10 Busiest Routes
- Line Chart — Flights Over Time (Monthly)
- Line Chart — COVID Impact (Year wise)

**Ask AI**
- Ask any question about the flight data in plain English
- Converts the question into real MySQL, using the database's actual schema
- Runs the query live and returns real results — never invented numbers
- Generates a plain-English explanation grounded only in the returned data
- Auto-generates a bar or line chart when the result supports one

---

## 🔒 Safety Design

The AI layer is deliberately restricted so it can't do anything beyond answering questions:

- **Read-only enforcement** — INSERT / UPDATE / DELETE / DROP / ALTER are blocked at the code level, not just discouraged in the prompt
- **Table whitelisting** — the model can only ever query the `flights` table, nothing else
- **Grounded explanations** — the AI only writes its answer after the real SQL has run, using the actual returned rows, so it has nothing to hallucinate from
- **Graceful failure** — questions outside the schema (e.g. "which flights have wifi?") are declined instead of answered with made-up data

---

## 🗺️ Repository Structure

```
indian-flight-analytics-ai/
│
├── 📄 app.py                 # Main Streamlit dashboard (Check Flights, Analytics, Ask AI)
├── 📄 mydb.py                 # MySQL connection + query methods for the dashboard
├── 📄 nl_query_layer.py       # Natural language → SQL → explanation → chart pipeline
├── 📄 requirements.txt        # Python dependencies
├── 📄 .env.example            # Template for API key / DB password (copy to .env)
├── 📄 .gitignore
└── 📄 README.md
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Database | MySQL |
| Backend | Python, SQLAlchemy, PyMySQL |
| AI Layer | Google Gemini API (free tier) — NL→SQL translation & explanation generation |
| Data Processing | Pandas |
| Visualization | Plotly |
| Dashboard | Streamlit |

---

## ▶️ Run Locally

```bash
git clone https://github.com/YOUR-USERNAME/indian-flight-analytics-ai.git
cd indian-flight-analytics-ai
pip install -r requirements.txt
```

1. Copy `.env.example` to `.env`
2. Add your free Gemini API key ([get one here](https://aistudio.google.com)) and your MySQL password
3. Import the `flights` dataset into your local MySQL instance
4. Run:

```bash
streamlit run app.py
```

---

## 🚧 What I'd Improve Next

- Multi-table joins so questions can span more than one table
- Conversation memory, so follow-up questions ("what about just IndiGo?") work without repeating context
- Caching for repeated questions to reduce API calls

---

## 👨‍💻 Author

**Amit**

[![GitHub](https://img.shields.io/badge/GitHub-YOUR--USERNAME-181717?style=flat&logo=github)](#)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Amit-0077B5?style=flat&logo=linkedin)](#)

---

<div align="center">

> 📝 *Built as part of my Data Analytics learning journey.*

⭐ **Star this repo if you found it useful!**

</div>
