import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from mydb import DB

db = DB()

st.set_page_config(
    page_title="Indian Flight Analytics",
    page_icon="🛫",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.title('flights analytics')
user_option = st.sidebar.selectbox('menu', ['Select One', 'Check Flights', 'Show Analytics'])

#CHECK FLIGHTS 
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
            # total count + cheapest
            st.success(f"{len(data)} flights found | Cheapest: ₹{min([row[7] for row in data])}")

            # dataframe with column names
            df = pd.DataFrame(data, columns=[
                'Airline', 'Date', 'Route',
                'Departure', 'Arrival',
                'Duration', 'Stops', 'Price'
            ])

            # sort options
            sort_by = st.selectbox('Sort by', ['Price', 'Duration'])
            if sort_by == 'Price':
                df = df.sort_values('Price')
            elif sort_by == 'Duration':
                df = df.sort_values('Duration')

            # filter by airline
            airlines = df['Airline'].unique().tolist()
            selected_airlines = st.multiselect('Filter by Airline', airlines, default=airlines)
            df = df[df['Airline'].isin(selected_airlines)]

            # highlight cheapest
            def highlight_cheapest(row):
                if row['Price'] == df['Price'].min():
                    return ['background-color: #d4edda'] * len(row)
                return [''] * len(row)

            st.dataframe(df.style.apply(highlight_cheapest, axis=1), use_container_width=True)

#  ANALYTICS 
elif user_option == 'Show Analytics':
    st.title('Analytics')

    # KPI Cards
    total_flights, total_airlines, total_routes, avg_price = db.fetch_kpi()
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Flights", total_flights)
    k2.metric("Total Airlines", total_airlines)
    k3.metric("Total Routes", total_routes)
    k4.metric("Avg Price", f"₹{avg_price}")

    st.divider()

    # Row 1 - Pie + Avg Price per Airline
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

    # Full width - Busiest Airports
    city, frequency1 = db.busy_airport()
    fig3 = px.bar(x=city, y=frequency1, labels={'x': 'City', 'y': 'Flights'})
    st.subheader("Busiest Airports")
    st.plotly_chart(fig3, use_container_width=True)

    st.divider()

    # Row 2 - Flights Over Time + COVID Impact
    col5, col6 = st.columns(2)

    date, frequency2 = db.daily_frequency()
    fig4 = px.line(x=date, y=frequency2, labels={'x': 'Month', 'y': 'Flights'})
    with col5:
        st.subheader("Flights Over Time")
        st.plotly_chart(fig4, use_container_width=True)

    year, frequency3 = db.fetch_covid_impact()
    fig5 = px.line(x=year, y=frequency3, markers=True, labels={'x': 'Year', 'y': 'Flights'})
    with col6:
        st.subheader("COVID Impact (Year wise)")
        st.plotly_chart(fig5, use_container_width=True)

    st.divider()

    # Full width - Top 10 Busiest Routes
    route, frequency4 = db.fetch_busiest_routes()
    fig6 = px.bar(x=route, y=frequency4, labels={'x': 'Route', 'y': 'Flights'})
    st.subheader("Top 10 Busiest Routes")
    st.plotly_chart(fig6, use_container_width=True)

# HOME 
else:
    st.title('Indian Flight Analytics')
    st.write('Use the sidebar to navigate.')






import streamlit as st
import seaborn as sns
import pandas as pd
import plotly.express as px 
import plotly.graph_objects as go
from mydb import DB

db=DB()


import streamlit as st

st.set_page_config(
    page_title="Indian Flight Analytics",
    page_icon="🛫",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.title('flights analytics')
user_option=st.sidebar.selectbox('menu',['Select One','Check Flights','Show Analytics'])

if user_option =='Check Flights':
    st.title("Check Flights")

    col1,col2=st.columns(2)
    source,destination=db.fetch_city_name()
    with col1:
        src=st.selectbox('choose source',sorted(source))

    with col2:
        dest=st.selectbox('choose destination',sorted(destination))
    
    if st.button('show'):
        data=db.fetch_all_flights(src,dest)
        st.dataframe(data)

elif user_option == 'Show Analytics':
    st.title('Analytics')

    total_flights, total_airlines, total_routes, avg_price = db.fetch_kpi()
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Flights", total_flights)
    k2.metric("Total Airlines", total_airlines)
    k3.metric("Total Routes", total_routes)
    k4.metric("Avg Price", f"₹{avg_price}")

    #st.divider()

    col3, col4 = st.columns(2)

    airline, frequency = db.airline_frequncy()
    fig1 = go.Figure(go.Pie(
        labels=airline,
        values=frequency,
        hoverinfo="label+percent",
        textinfo="value"
    ))
    with col3:
        st.header("Flights per Airline")
        st.plotly_chart(fig1, use_container_width=True)

    city, frequency1 = db.busy_airport()
    fig2 = px.bar(x=city, y=frequency1)
    with col4:
        st.header("Busiest Airports")
        st.plotly_chart(fig2, use_container_width=True)


    date, frequency2 = db.daily_frequency()
    fig3 = px.line(x=date, y=frequency2)
    st.header("Flights Over Time")
    st.plotly_chart(fig3, use_container_width=True)

    airline2, price = db.avg_price_per_airline()
    fig3 = px.bar(x=airline2, y=price, labels={'x': 'Airline', 'y': 'Avg Price (₹)'})
    st.subheader("Avg Price per Airline")
    st.plotly_chart(fig3, use_container_width=True)

    


else:
    st.title('Tell about the project')