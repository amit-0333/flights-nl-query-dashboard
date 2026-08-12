import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from mydb import DB

db = DB()

st.set_page_config(
    page_title="Indian Flight Analytics",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.title('**flights analytics**')
user_option = st.sidebar.selectbox('**Menu**', ['Select One', 'Check Flights', 'Show Analytics', 'Ask AI'])



if user_option == 'Check Flights':
    st.title("Check Flights")

    col1, col2 = st.columns(2)
    source, destination = db.fetch_city_name()
    with col1:
        src = st.selectbox('choose source', sorted(source))
    with col2:
        dest = st.selectbox('choose destination', sorted(destination))

    if st.button('show'):
        data = db.fetch_all_flights(src, dest)

        if len(data) == 0:
            st.warning("No flights found for this route!")
        else:
            st.success(f"{len(data)} flights found | Cheapest: ₹{min([row[7] for row in data])}")

            df = pd.DataFrame(data, columns=[
                'Airline', 'Date', 'Route',
                'Departure', 'Arrival',
                'Duration', 'Stops', 'Price'
            ])

            sort_by = st.selectbox('Sort by', ['Price', 'Duration'])
            if sort_by == 'Price':
                df = df.sort_values('Price')
            elif sort_by == 'Duration':
                df = df.sort_values('Duration')

            airlines = df['Airline'].unique().tolist()
            selected_airlines = st.multiselect('Filter by Airline', airlines, default=airlines)
            df = df[df['Airline'].isin(selected_airlines)]

            def highlight_cheapest(row):
                if row['Price'] == df['Price'].min():
                    return ['background-color: #d4edda'] * len(row)
                return [''] * len(row)

            st.dataframe(df.style.apply(highlight_cheapest, axis=1), use_container_width=True)



elif user_option == 'Show Analytics':
    st.title('Analytics')

    total_flights, total_airlines, total_routes, avg_price = db.fetch_kpi()
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Flights", total_flights)
    k2.metric("Total Airlines", total_airlines)
    k3.metric("Total Routes", total_routes)
    k4.metric("Avg Price", f"₹{avg_price}")

    st.divider()

    col3, col4 = st.columns(2)

    airline, frequency = db.airline_frequncy()
    fig1 = go.Figure(go.Pie(
        labels=airline,
        values=frequency,
        hoverinfo="label+percent",
        textinfo="value"
    ))
    with col3:
        st.subheader("Flights per Airline")
        st.plotly_chart(fig1, use_container_width=True)

    airline2, price = db.avg_price_per_airline()
    fig2 = px.bar(x=airline2, y=price, labels={'x': 'Airline', 'y': 'Avg Price (₹)'})
    with col4:
        st.subheader("Avg Price per Airline")
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    col5, col6 = st.columns(2)

    city, frequency1 = db.busy_airport()
    fig3 = px.bar(x=city, y=frequency1, labels={'x': 'City', 'y': 'Flights'})
    with col5:
        st.subheader("Busiest Airports")
        st.plotly_chart(fig3, use_container_width=True)

    route, frequency4 = db.fetch_busiest_routes()
    fig6 = px.bar(x=route, y=frequency4, labels={'x': 'Route', 'y': 'Flights'})
    with col6:
        st.subheader("Top 10 Busiest Routes")
        st.plotly_chart(fig6, use_container_width=True)

    st.divider()

    col7, col8 = st.columns(2)

    date, frequency2 = db.daily_frequency()
    fig4 = px.line(x=date, y=frequency2, labels={'x': 'Month', 'y': 'Flights'})
    with col7:
        st.subheader("Flights Over Time")
        st.plotly_chart(fig4, use_container_width=True)

    year, frequency3 = db.fetch_covid_impact()
    fig5 = px.line(x=year, y=frequency3, markers=True, labels={'x': 'Year', 'y': 'Flights'})
    with col8:
        st.subheader("COVID Impact (Year wise)")
        st.plotly_chart(fig5, use_container_width=True)

elif user_option == 'Ask AI':
    from nl_query_layer import ask_question, get_engine
    engine = get_engine()

    st.title("Ask a question about the flights data")
    user_question = st.text_input("e.g. 'Which airline has the most flights from Delhi?'")
    if user_question:
        with st.spinner("Thinking..."):
            result = ask_question(user_question, engine)
        st.write(result["explanation"])
        st.code(result["sql"], language="sql")
        st.dataframe(result["data"], use_container_width=True)
        if result["chart"] is not None:
            st.plotly_chart(result["chart"], use_container_width=True)

else:
    st.title('Indian Flight Analytics')

    st.markdown("### Dataset Info")
    total_flights, total_airlines, total_routes, avg_price = db.fetch_kpi()

    source, destination = db.fetch_city_name()

    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Total Records", total_flights)
    d2.metric("Airlines Covered", total_airlines)
    d3.metric("Unique Routes", total_routes)
    d4.metric("Cities Covered", len(source))

    st.markdown("""
    ### About This Project
    **Indian Flight Analytics** is an interactive dashboard built to explore and analyze 
    domestic flight data across India. It helps users search for flights and discover 
    meaningful insights from the data.
    """)


    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Check Flights")
        st.markdown("""
        - Search flights by **Source & Destination**
        - View all available flights on a route
        - **Sort** by Price or Duration
        - **Filter** by Airline
        - Cheapest flight is **highlighted in green**
        - Shows total flights found
        """)

    with col2:
        st.markdown("### Show Analytics")
        st.markdown("""
        - **KPI Cards** — Total Flights, Airlines, Routes, Avg Price
        - **Pie Chart** — Flights per Airline
        - **Bar Chart** — Avg Price per Airline
        - **Bar Chart** — Busiest Airports
        - **Bar Chart** — Top 10 Busiest Routes
        - **Line Chart** — Flights Over Time (Monthly)
        - **Line Chart** — COVID Impact (Year wise)
        """)

    st.markdown("""
    ### Tech Stack
    | Layer | Technology |
    |---|---|
    | Database | MySQL |
    | Backend | Python + mysql-connector |
    | Processing | Pandas |
    | Charts | Plotly |
    | Dashboard | Streamlit |
    """)



    st.caption("Built by Amit | Indian Flight Analytics Dashboard")