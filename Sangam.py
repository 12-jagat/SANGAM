import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os
from datetime import datetime
from sqlite3 import Error

# Streamlit Configuration
st.set_page_config(page_title="Sales Analytics Dashboard", page_icon="📊", layout="wide")

# Custom CSS
st.markdown(
    """
    <style>
    /* Add CSS for improved styling here */
    </style>
    """, 
    unsafe_allow_html=True
)

# Database Setup
DB_FILE = "sales_data.db"

def setup_database():
    """Initialize SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    try:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS datasets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            upload_date TEXT
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS sales_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id INTEGER,
            order_date TEXT,
            sales REAL,
            profit REAL,
            category TEXT,
            region TEXT,
            sub_category TEXT,
            quantity INTEGER,
            discount REAL,
            FOREIGN KEY(dataset_id) REFERENCES datasets(id)
        )
        """)
        conn.commit()
    except Error as e:
        st.error(f"Database setup error: {e}")
    finally:
        conn.close()

setup_database()

# Utility Functions
def load_data(file):
    """Load data from the uploaded file."""
    try:
        ext = file.name.split('.')[-1]
        if ext == "csv":
            return pd.read_csv(file, encoding="ISO-8859-1")
        elif ext in ["xls", "xlsx"]:
            return pd.read_excel(file)
        else:
            st.error("Unsupported file format. Upload a CSV or Excel file.")
            return None
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

def validate_columns(dataframe, required_columns):
    """Check if required columns exist in the dataset."""
    missing_columns = [col for col in required_columns if col not in dataframe.columns]
    if missing_columns:
        st.error(f"Missing required columns: {', '.join(missing_columns)}")
        return False
    return True

def save_to_database(dataset_name, dataframe):
    """Save uploaded dataset to the database."""
    conn = sqlite3.connect(DB_FILE)
    try:
        # Insert dataset record
        upload_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("INSERT INTO datasets (name, upload_date) VALUES (?, ?)", (dataset_name, upload_date))
        dataset_id = conn.execute("SELECT id FROM datasets WHERE name = ?", (dataset_name,)).fetchone()[0]

        # Insert sales data
        dataframe.to_sql("sales_data", conn, if_exists="append", index=False,
                         chunksize=1000,
                         dtype={
                             "order_date": "TEXT",
                             "sales": "REAL",
                             "profit": "REAL",
                             "category": "TEXT",
                             "region": "TEXT",
                             "sub_category": "TEXT",
                             "quantity": "INTEGER",
                             "discount": "REAL"
                         })
        conn.commit()
        st.success("Dataset uploaded and saved to the database.")
    except sqlite3.IntegrityError:
        st.error("Dataset name already exists. Please use a unique name.")
    except Error as e:
        st.error(f"Database error: {e}")
    finally:
        conn.close()

def fetch_dataset_names():
    """Fetch available dataset names from the database."""
    conn = sqlite3.connect(DB_FILE)
    datasets = conn.execute("SELECT name FROM datasets").fetchall()
    conn.close()
    return [d[0] for d in datasets]

def fetch_data(dataset_name):
    """Fetch sales data for a specific dataset."""
    conn = sqlite3.connect(DB_FILE)
    dataset_id = conn.execute("SELECT id FROM datasets WHERE name = ?", (dataset_name,)).fetchone()
    if not dataset_id:
        return None
    dataset_id = dataset_id[0]
    query = "SELECT * FROM sales_data WHERE dataset_id = ?"
    dataframe = pd.read_sql_query(query, conn, params=(dataset_id,))
    conn.close()
    return dataframe

# Main Application
st.title("📊 Sales Analytics Dashboard")

# Upload Dataset
st.sidebar.header("Upload Data")
uploaded_file = st.sidebar.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx", "xls"])
dataset_name = st.sidebar.text_input("Enter a unique name for the dataset")

if st.sidebar.button("Upload Dataset"):
    if uploaded_file and dataset_name:
        data = load_data(uploaded_file)
        if data is not None:
            required_columns = ["Order Date", "Sales", "Profit", "Category", "Region", "Sub-Category", "Quantity", "Discount"]
            if validate_columns(data, required_columns):
                data.rename(columns=lambda x: x.strip().lower().replace(" ", "_"), inplace=True)
                data["order_date"] = pd.to_datetime(data["order_date"], errors="coerce")
                data.dropna(subset=["order_date"], inplace=True)  # Drop rows with invalid dates
                save_to_database(dataset_name, data)
    else:
        st.sidebar.error("Please upload a file and provide a unique dataset name.")

# Select Dataset
st.sidebar.header("Choose Dataset")
available_datasets = fetch_dataset_names()
selected_dataset = st.sidebar.selectbox("Select a Dataset", available_datasets)

if selected_dataset:
    df = fetch_data(selected_dataset)
    if df is not None and not df.empty:
        st.subheader(f"Dataset: {selected_dataset}")
        st.dataframe(df.head())

        # Filters
        start_date, end_date = st.date_input("Filter by Date Range:", [df["order_date"].min(), df["order_date"].max()])
        df_filtered = df[(df["order_date"] >= start_date) & (df["order_date"] <= end_date)]

        # Visualizations
        st.subheader("Visualizations")
        category_sales = df_filtered.groupby("category")["sales"].sum().reset_index()
        region_sales = df_filtered.groupby("region")["sales"].sum().reset_index()

        col1, col2 = st.columns(2)
        with col1:
            st.write("Category-wise Sales")
            fig1 = px.bar(category_sales, x="category", y="sales")
            st.plotly_chart(fig1)
        with col2:
            st.write("Region-wise Sales")
            fig2 = px.pie(region_sales, names="region", values="sales")
            st.plotly_chart(fig2)

        # Download Processed Data
        csv = df_filtered.to_csv(index=False).encode("utf-8")
        st.download_button("Download Filtered Data", csv, f"{selected_dataset}_filtered.csv", "text/csv")
    else:
        st.error("No data available for the selected dataset.")