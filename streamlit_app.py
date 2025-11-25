import streamlit as st
import psycopg2
from dotenv import load_dotenv
import os
import pandas as pd
import decimal

from streamlit_elements import elements, dashboard, mui, nivo

st.set_page_config(layout="wide")
st.title("FoodReach Dashboard")

load_dotenv()

USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
DB_NAME = os.getenv("dbName")
PORT = os.getenv("port")

def convert_decimal(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: convert_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_decimal(i) for i in obj]
    return obj

# -----------------------------
# DATABASE HELPERS
# -----------------------------
@st.cache_data(ttl=0)
def load_demographics(_conn):
    cur = _conn.cursor()
    cur.execute('SELECT * FROM "Demographics" LIMIT 50;')
    results = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    cur.close()
    return pd.DataFrame(results, columns=cols)

@st.cache_data(ttl=0)
def load_lowAccess(_conn):
    cur = _conn.cursor()
    sql = '''
    SELECT
    c.county_name,
    c.county_id,

    -- All LowAccess1Mile columns aggregated
    SUM(la.population1)     AS population1,
    SUM(la."lowIncomei1")   AS "lowIncomei1",
    SUM(la.kids1)           AS kids1,
    SUM(la.seniors1)        AS seniors1,
    SUM(la.white1)          AS white1,
    SUM(la.black1)          AS black1,
    SUM(la.asian1)          AS asian1,
    SUM(la.islander1)       AS islander1,
    SUM(la.americindian1)   AS americindian1,
    SUM(la.other1)          AS other1,
    SUM(la.hisp1)           AS hisp1,
    SUM(la."noVehicle1")    AS "noVehicle1",
    SUM(la.snap1)           AS snap1,

    COUNT(*) AS tract_count

FROM 
    "public"."LowAccess1Mile" la
JOIN 
    "public"."CensusTract" ct ON la.tract_id = ct.tract_id
JOIN 
    "public"."County" c ON ct.county_id = c.county_id

GROUP BY 
    c.county_id,
    c.county_name
ORDER BY 
    county_name;
    '''
    cur.execute(sql)
    results = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    cur.close()
    return pd.DataFrame(results, columns=cols)
@st.cache_data(ttl=0)
def load_no_vehicle_bar(_conn):
    query = """
        SELECT 
            s.state_name,
            c.county_name,
            SUM(la."noVehicle1") AS "Households_NoCar_LowAccess"
        FROM 
            public."State" s
        JOIN 
            public."County" c ON s.state_id = c.state_id
        JOIN 
            public."CensusTract" ct ON c.county_id = ct.county_id
        JOIN 
            public."LowAccess1Mile" la ON ct.tract_id = la.tract_id
        GROUP BY 
            s.state_name, c.county_name
        HAVING 
            SUM(la."noVehicle1") IS NOT NULL
        ORDER BY 
            "Households_NoCar_LowAccess" DESC
        LIMIT 10;
    """

    cur = _conn.cursor()
    cur.execute(query)
    results = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    cur.close()

    return pd.DataFrame(results, columns=cols)


# -----------------------------
# CONNECT
# -----------------------------
try:
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT
    )
    st.success("Connected successfully!")
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

demographics_table = load_demographics(conn)
lowAccess_table = load_lowAccess(conn)
bar_table = load_no_vehicle_bar(conn)
state_table = pd.read_sql('SELECT * FROM "State";', conn)
population_vs_access_sql = """
SELECT 
    s.state_name, 
    SUM(fai."POP2010") AS Total_Population, 
    SUM(fai."LowAccessPopulation1and10") AS Low_Access_Population
FROM 
    "public"."State" s
JOIN 
    "public"."County" c ON s.state_id = c.state_id
JOIN 
    "public"."CensusTract" ct ON c.county_id = ct.county_id
JOIN 
    "public"."FoodAccessIndicator" fai ON ct.tract_id = fai.tract_id
WHERE 
    s.state_name = '{selected_state}' 
GROUP BY 
    s.state_name;
"""

rural_vs_urban_sql = """
SELECT 
    CASE 
        WHEN fai."Urban" = 1 THEN 'Urban' 
        ELSE 'Rural' 
    END AS "Area_Type",
    SUM(fai."POP2010") AS "Total_Population",
    SUM(fai."LowAccessPopulation1and10") AS "Low_Access_Population",
    ROUND(
        (SUM(fai."LowAccessPopulation1and10")::numeric / NULLIF(SUM(fai."POP2010"), 0)) * 100, 
        2
    ) AS "Percentage_Low_Access"
FROM 
    "public"."State" s
JOIN 
    "public"."County" c ON s.state_id = c.state_id
JOIN 
    "public"."CensusTract" ct ON c.county_id = ct.county_id
JOIN 
    "public"."FoodAccessIndicator" fai ON ct.tract_id = fai.tract_id
WHERE 
    s.state_name = '{selected_state}'
GROUP BY 
    fai."Urban";
"""

county_and_state_sql = """
SELECT 
    c.county_id,
    c.county_name,
    s.state_name
FROM
    "public"."County" c 
JOIN 
    "public"."State" s ON c.state_id = s.state_id
;
"""


# Example usage (uncomment and adapt as needed):




# STATE SELECTOR
state_list = state_table["state_name"].dropna().unique()
selected_state = st.selectbox("Select State", state_list, index=0)
population_vs_access_data = pd.read_sql(population_vs_access_sql.format(selected_state=selected_state), conn)
rural_vs_urban_data = pd.read_sql(rural_vs_urban_sql.format(selected_state=selected_state), conn)


st.subheader("Dashboard By State")

with elements("state_food_access"):
    layout = [
        dashboard.Item("pie_chart", 0, 0, 6, 3),
        dashboard.Item("bar_chart", 6, 0, 6, 3),

    ]

    with dashboard.Grid(layout):

        # Pie Chart (Nivo)
        with mui.Paper(key="pie_chart", elevation=1, sx={"padding": 2}):
            mui.Typography(f"Share of {selected_state} Population considered Low Access", variant="h6", sx={"mb": 2})
            PIE_DATA = [
                {"id": "non-access", "label": "Non-Access", "value": float(population_vs_access_data["total_population"][0] - population_vs_access_data["low_access_population"][0])},
                {"id": "low-access", "label": "Low Access", "value": float(population_vs_access_data["low_access_population"][0])},
            ]

            with mui.Box(sx={"height": "100%", "width": "100%"}):
                nivo.Pie(
                    data=PIE_DATA,
                    innerRadius=0.5,
                    padAngle=0.5,
                    margin={"top": 30, "right": 40, "bottom": 40, "left": 40},
                    activeOuterRadiusOffset=8,
                    borderWidth=1,
                    borderColor={"from": "color", "modifiers": [["darker", 0.2]]},
                    arcLinkLabelsSkipAngle=5,
                    arcLinkLabelsTextColor="#FFFFFF",
                    arcLinkLabelsThickness=2,
                    arcLinkLabelsDistance=30,
                    arcLabelsSkipAngle=5,
                    colors={"scheme": "nivo"},
                    theme={
                        "textColor": "#4F4F4F",
                        "tooltip": {
                            "container": {"background": "#ffffffdd", "color": "#222"}
                        },
                    },
                    legends=[
                        {
                            "anchor": "top-left",
                            "direction": "column",
                            "translateX": -50,
                            "translateY": 0,
                            "itemWidth": 80,
                            "itemHeight": 20,
                            "itemTextColor": "#9E9E9E",
                            "symbolSize": 12,
                            "symbolShape": "circle",
                            "effects": [
                                {
                                    "on": "hover",
                                    "style": {
                                        "itemTextColor": "#7997B4"
                                    }
                                }
                            ]
                        }
                    ],
                )

        # Bar Chart
        with mui.Paper(key="bar_chart", elevation=1, sx={"padding": 2}):
            mui.Typography(f"Rural vs Urban Low Access Population in {selected_state}", variant="h6", sx={"mb": 2})

            with mui.Box(sx={"height": "80%", "width": "80%"}):
                BAR_DATA = rural_vs_urban_data.to_dict(orient="records")
                nivo.Bar(
                    data=BAR_DATA,
                    keys=["Low_Access_Population"],
                    indexBy="Area_Type",
                    margin={"top": 40, "right": 80, "bottom": 60, "left": 80},
                    padding=0.3,
                    valueScale={"type": "linear"},
                    indexScale={"type": "band", "round": True},
                    borderColor={"from": "color", "modifiers": [["darker", 1.6]]},
                    axisTop=None,
                    axisRight=None,
                    axisBottom={
                    "tickSize": 5,
                    "tickPadding": 5,
                    "tickRotation": 0,
                    "legend": "Area Type",
                    "legendPosition": "middle",
                    "legendOffset": 40
                    },
                    axisLeft={
                    "tickSize": 5,
                    "tickPadding": 5,
                    "tickRotation": 0,
                    "legend": "Low Access Population",
                    "legendPosition": "middle",
                    "legendOffset": -50
                    },
                    labelSkipWidth=12,
                    labelSkipHeight=12,
                    labelTextColor={"from": "color", "modifiers": [["darker", 1.6]]},
                    colors={"scheme": "nivo"},
                    theme={
                    "axis": {
                        "ticks": {
                        "text": {
                            "fill": "#ffffff"
                        }
                        }
                    }
                    },
                )

# DASHBOARD 
st.subheader("Dashboard By County")

# COUNTY SELECTOR

county_and_state = pd.read_sql(county_and_state_sql, conn)

# Create a mapping: county_id -> "county_name (state_name)"
# Build your dataframe with ids + names
county_display = county_and_state[["county_id", "county_name", "state_name"]]

# Create selectbox that RETURNS county_id but DISPLAYS "County (State)"
selected_county_id = st.selectbox(
    "Select County",
    county_display["county_id"],
    format_func=lambda cid: 
        county_display[county_display["county_id"] == cid][["county_name", "state_name"]]
        .apply(lambda row: f"{row['county_name']} ({row['state_name']})", axis=1)
        .iloc[0]
)

# Get the selected row from lowAccess_table using county_id (SAFE)
selected_row = lowAccess_table[lowAccess_table["county_id"] == selected_county_id]

# Legacy compatibility
selected_county_name = selected_row["county_name"].iloc[0]
selected_county = selected_county_name


# DEBUGGING OUTPUTS
# st.write("Selected county (repr):", repr(selected_county))
# st.write("lowAccess_table columns:", lowAccess_table.columns.tolist())
# st.write("Unique county_name values (first 20):", lowAccess_table["county_name"].unique()[:20])

# selected_row = lowAccess_table[lowAccess_table["county_name"] == selected_county]
# st.write("selected_row shape:", selected_row.shape)
# st.write(selected_row.head())

with elements("foodreach_dashboard"):

    # Layout grid 
    layout = [
        dashboard.Item("radar_chart", 6, 3, 6, 3),
        dashboard.Item("pie_chart", 0, 0, 5, 3),
        dashboard.Item("bar_chart", 6, 0, 7, 3),
        dashboard.Item("data_editor", 0, 3, 6, 3),
    ]

    with dashboard.Grid(layout):

        # Data Editor (editable demographics table)
        with mui.Paper(key="data_editor", elevation=2, sx={"padding": 2}):
            with mui.Box(sx={"height": "100%", "width": "100%"}):
                columns = [
                    {"field": "tract_id", "headerName": "Tract ID", "width": 150},
                    {"field": "TractLowIncome", "headerName": "Low Income", "width": 130, "editable": True},
                    {"field": "TractKids", "headerName": "Kids", "width": 130, "editable": True},
                    {"field": "TractSeniors", "headerName": "Seniors", "width": 130, "editable": True},
                    {"field": "TractSNAP", "headerName": "SNAP", "width": 130, "editable": True}
                ]
                mui.DataGrid(
                    rows=demographics_table.to_dict(orient="records"),
                    columns=columns,
                    pageSize=10,
                    rowsPerPageOptions=[10],
                    checkboxSelection=False,
                    disableSelectionOnClick=True,
                    experimentalFeatures={"newEditingApi": True},
                    # You can add styling through sx={} if needed
                )

        # Radar Chart (Nivo)
        with mui.Paper(key="radar_chart", elevation=2, sx={"padding": 2}):
            DATA = demographics_table.head(8).to_dict(orient="records")
            with mui.Box(sx={"height": "100%", "width": "100%"}):
                nivo.Radar(
                    data=DATA,
                    keys=["TractLowIncome", "TractKids", "TractSeniors", "TractSNAP"],
                    indexBy="id",
                    margin={"top": 40, "right": 80, "bottom": 40, "left": 80},
                    dotBorderWidth=2,
                    gridLabelOffset=20,
                    dotSize=10,
                    colors={"scheme": "nivo"},
                    dotColor={"theme": "background"},
                    motionConfig="wobbly",
                    legends=[
                        {
                            "anchor": "top-left",
                            "direction": "column",
                            "translateX": -50,
                            "translateY": 0,
                            "itemWidth": 80,
                            "itemHeight": 20,
                            "itemTextColor": "#9E9E9E",
                            "symbolSize": 12,
                            "symbolShape": "circle",
                            "effects": [
                                {
                                    "on": "hover",
                                    "style": {
                                        "itemTextColor": "#7997B4"
                                    }
                                }
                            ]
                        }
                    ],
                    theme={
                        "textColor": "#DFDFDF",
                        "gridColor": "#dddddd",
                        "tooltip": {
                            "container": {
                                "background": "#ffffff58",
                                "color": "#333333",
                            }
                        }
                    }
                )

        # Pie Chart (Nivo)
        with mui.Paper(key="pie_chart", elevation=2, sx={"padding": 2}):

            PIE_DATA = [
                {"id": "Kids", "label": "Kids", "value": float(selected_row["kids1"].iloc[0])},
                {"id": "Low Income", "label": "Low Income", "value": float(selected_row["lowIncomei1"].iloc[0])},
                {"id": "Seniors", "label": "Seniors", "value": float(selected_row["seniors1"].iloc[0])},
                {"id": "White", "label": "White", "value": float(selected_row["white1"].iloc[0])},
                {"id": "Black", "label": "Black", "value": float(selected_row["black1"].iloc[0])},
                {"id": "Asian", "label": "Asian", "value": float(selected_row["asian1"].iloc[0])},
                {"id": "Hispanic", "label": "Hispanic", "value": float(selected_row["hisp1"].iloc[0])},
                {"id": "No Vehicle", "label": "No Vehicle", "value": float(selected_row["noVehicle1"].iloc[0])},
            ]

            with mui.Box(sx={"height": "100%", "width": "100%"}):
                nivo.Pie(
                    data=PIE_DATA,
                    innerRadius=0.5,
                    padAngle=0.5,
                    margin={"top": 30, "right": 40, "bottom": 40, "left": 40},
                    activeOuterRadiusOffset=8,
                    borderWidth=1,
                    borderColor={"from": "color", "modifiers": [["darker", 0.2]]},
                    arcLinkLabelsSkipAngle=5,
                    arcLinkLabelsTextColor="#FFFFFF",
                    arcLinkLabelsThickness=2,
                    arcLinkLabelsDistance=30,
                    arcLabelsSkipAngle=5,
                    colors={"scheme": "nivo"},
                    theme={
                        "textColor": "#4F4F4F",
                        "tooltip": {
                            "container": {"background": "#ffffffdd", "color": "#222"}
                        },
                    },
                    legends=[
                        {
                            "anchor": "top-left",
                            "direction": "column",
                            "translateX": -50,
                            "translateY": 0,
                            "itemWidth": 80,
                            "itemHeight": 20,
                            "itemTextColor": "#9E9E9E",
                            "symbolSize": 12,
                            "symbolShape": "circle",
                            "effects": [
                                {
                                    "on": "hover",
                                    "style": {
                                        "itemTextColor": "#7997B4"
                                    }
                                }
                            ]
                        }
                    ],
                )

        # Bar Chart 
        with mui.Paper(key="bar_chart", elevation=2, sx={"padding": 2}):
           BAR_DATA = bar_table.to_dict(orient="records")
           BAR_DATA = convert_decimal(BAR_DATA)
           with mui.Box(sx={"height": "100%", "width": "100%"}):
               nivo.Bar(
                   data=BAR_DATA,
                   keys=["Households_NoCar_LowAccess"],
                    indexBy="county_name",
                    margin={"top": 40, "right": 80, "bottom": 60, "left": 80},
                    padding=0.3,
                    valueScale={"type": "linear"},
                    indexScale={"type": "band", "round": True},
                    borderColor={"from": "color", "modifiers": [["darker", 1.6]]},
                    axisTop=None,
                    axisRight=None,
                    axisBottom={
                        "tickSize": 5,
                        "tickPadding": 5,
                        "tickRotation": 30,
                        "legend": "County",
                        "legendPosition": "middle",
                        "legendOffset": 50
                    },
                    axisLeft={
                        "tickSize": 5,
                        "tickPadding": 5,
                        "tickRotation": 0,
                        "legend": "Households No Vehicle Low Access",
                        "legendPosition": "middle",
                        "legendOffset": -50
                    },
                    labelSkipWidth=12,
                    labelSkipHeight=12,
                    labelTextColor={"from": "color", "modifiers": [["darker", 1.6]]},
                    colors={"scheme": "nivo"},
                    legends=[
                        {
                            "dataFrom": "keys",
                            "anchor": "top-right",
                            "direction": "column",
                            "justify": False,
                            "translateX": 120,
                            "translateY": 0,
                            "itemsSpacing": 2,
                            "itemWidth": 100,
                            "itemHeight": 20,
                            "itemDirection": "left-to-right",
                            "itemOpacity": 0.85,
                            "symbolSize": 20,
                            "effects": [
                                {
                                    "on": "hover",
                                    "style": {
                                        "itemOpacity": 1
                                    }
                                }
                            ]
                        }
                    ],
                    theme={
                        "textColor": "#DFDFDF",
                        "gridColor": "#dddddd",
                        "tooltip": {
                            "container": {
                                "background": "#ffffff58",
                                "color": "#333333",
                            }
                        }
                    },
                )

# SAVE BUTTON FOR DATA EDITOR
if st.button("Save Changes to Demographics"):

    cursor = conn.cursor()

    new_df = st.session_state["demographics"]["edited_rows"]

    for row_index, row_changes in new_df.items():
        row_id = demographics_table.loc[row_index, "id"]

        set_clauses = []
        values = []

        for col, new_val in row_changes.items():
            set_clauses.append(f'"{col}" = %s')
            values.append(new_val)

        query = f"""
            UPDATE "Demographics"
            SET {", ".join(set_clauses)}
            WHERE "id" = %s
        """

        values.append(int(row_id))
        cursor.execute(query, values)

    conn.commit()
    st.success("Changes saved!")
    st.cache_data.clear()
    st.rerun()
