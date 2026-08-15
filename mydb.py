import mysql.connector

class DB:
    def __init__(self):
        try:
            self.conn = mysql.connector.connect(
                host="localhost",
                user="root",
                password="@amit03",
                database="flights"
            )
            print('Database Connected Successfully')
            self.cursor = self.conn.cursor()
        except:
            print("Database Connection Error")


    def fetch_city_name(self):
        source=[]
        src=self.cursor.execute("SELECT DISTINCT(Source) FROM flights")
        data = self.cursor.fetchall()

        for item in data:
            source.append(item[0])
        #print(source)

        destination=[]
        dest=self.cursor.execute("SELECT DISTINCT(destination) FROM flights")
        data = self.cursor.fetchall()

        for item in data:
            destination.append(item[0])
        #print(destination)

        return source, destination
    

    def fetch_all_flights(self,source,destination):
        self.cursor.execute("""
            SELECT airline,date_of_journey,
            route,dep_time,Arrival_time,
            Duration,Total_stops,Price
            FROM flights
            WHERE Source = '{}' AND destination = '{}'
            """.format(source,destination))
        
        data=self.cursor.fetchall()
        return data
    
    def airline_frequncy(self):
        airline=[]
        frequency=[]
        self.cursor.execute("""
                            SELECT airline , COUNT(*) FROM flights
                            GROUP BY airline
                            """)
        data=self.cursor.fetchall()

        for a,f in data:
            airline.append(a)
            frequency.append(f)

        return airline,frequency
    
    def busy_airport(self):

        city = []
        frequency = []

        self.cursor.execute("""
                            SELECT Source , COUNT(*) FROM flights
                            GROUP BY Source
                            ORDER BY COUNT(*) DESC
                        """)
        data=self.cursor.fetchall()

        for c,f in data:
            city.append(c)
            frequency.append(f)
        return city,frequency
    


    def daily_frequency(self):
        self.cursor.execute("""
            SELECT DATE_FORMAT(date_of_journey, '%Y-%m') AS month, COUNT(*) 
            FROM flights 
            GROUP BY month
            ORDER BY month
        """)
        data = self.cursor.fetchall()

        date = []
        frequency = []

        for d, f in data:
            date.append(d)
            frequency.append(f)
        
        return date, frequency
    
    def avg_price_per_airline(self):
        self.cursor.execute("""
            SELECT airline, ROUND(AVG(Price), 0)
            FROM flights
            GROUP BY airline
            ORDER BY AVG(Price) DESC
        """)
        data = self.cursor.fetchall()

        airline = []
        price = []

        for a, p in data:
            airline.append(a)
            price.append(p)

        return airline, price


    def fetch_kpi(self):
        self.cursor.execute("SELECT COUNT(*) FROM flights")
        total_flights = self.cursor.fetchone()[0]

        self.cursor.execute("SELECT COUNT(DISTINCT airline) FROM flights")
        total_airlines = self.cursor.fetchone()[0]

        self.cursor.execute("SELECT COUNT(DISTINCT CONCAT(Source, destination)) FROM flights")
        total_routes = self.cursor.fetchone()[0]

        self.cursor.execute("SELECT ROUND(AVG(Price), 0) FROM flights")
        avg_price = self.cursor.fetchone()[0]

        return total_flights, total_airlines, total_routes, avg_price


    def fetch_busiest_routes(self):
        self.cursor.execute("""
                        SELECT CONCAT(Source, ' → ', destination) AS route, COUNT(*) 
                        FROM flights
                        GROUP BY CONCAT(Source, ' → ', destination)
                        ORDER BY COUNT(*) DESC
                        LIMIT 10
                        """)
        data = self.cursor.fetchall()
        route = []
        frequency = []
        for r, f in data:
            route.append(r)
            frequency.append(f)
        return route, frequency
    
    def fetch_all_flights_raw(self):
        self.cursor.execute("""
            SELECT airline, route, Price, Duration, Total_stops
            FROM flights
        """)
        data = self.cursor.fetchall()
        return data


    def fetch_covid_impact(self):
        self.cursor.execute("""
            SELECT YEAR(date_of_journey) AS year, COUNT(*) 
            FROM flights
            GROUP BY year
            ORDER BY year
        """)
        data = self.cursor.fetchall()
        year = []
        frequency = []
        for y, f in data:
            year.append(y)
            frequency.append(f)
        return year, frequency



        


if __name__ == "__main__":
    db = DB()
    db.fetch_city_name()