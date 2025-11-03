import streamlit as st

st.title("🎈 My new app")
st.write(
    "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
)

import streamlit as st
from st_supabase_connection import SupabaseConnection
from st_supabase_connection import execute_query
conn = st.connection("supabase", type=SupabaseConnection)
try:
    response = conn.table("Root Food Data").select("*").execute()
    
    # Check if data was returned
    if response.data:
        # --- OPTION 1: Interactive Dataframe (Recommended) ---
        st.header("Food Data (Interactive Dataframe)")
        st.dataframe(response.data)

    else:
        st.warning("No data found in the 'Root Food Data' table.")

except Exception as e:
    st.error(f"Error fetching data: {e}")