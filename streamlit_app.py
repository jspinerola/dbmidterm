import streamlit as st

st.title("Welcome to FoodReach")
st.write(
    "I'm gonna start my test here to load a supabase instances as a table"
)

import psycopg2
from dotenv import load_dotenv
import os
import pandas as pd

load_dotenv()

USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
DB_NAME = os.getenv("dbName")
PORT = os.getenv("port")

try:
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT
    )
    st.success("Connected to the database successfully!")
    cursor = conn.cursor()
    cursor.execute('SELECT county_id, state_id, county_name FROM "County" LIMIT 25;') 
    result = cursor.fetchall()
    table = pd.DataFrame(result, columns=['county_id', 'state_id', 'county_name'])

    another_cursor = conn.cursor()
    another_cursor.execute('SELECT * FROM "Demographics";')
    results = another_cursor.fetchall()
    demographics_table = pd.DataFrame(results, columns=[desc[0] for desc in another_cursor.description])
    

    st.write("Sample data from County table:")
    st.dataframe(demographics_table)
    st.dataframe(table)
except Exception as e:
    st.error(f"Error connecting to the database: {e}")
    st.stop()
