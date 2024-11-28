# Utility Functions
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
        # Standardize DataFrame column names to match database schema
        dataframe.rename(columns=lambda x: x.strip().lower().replace(" ", "_"), inplace=True)

        # Ensure the DataFrame only contains columns that match the sales_data table
        valid_columns = [
            "order_date", "sales", "profit", "category", "region", 
            "sub_category", "quantity", "discount"
        ]
        dataframe = dataframe[valid_columns]

        # Convert order_date to text (ensure it's compatible with SQLite)
        dataframe["order_date"] = dataframe["order_date"].astype(str)

        # Insert dataset record
        upload_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("INSERT INTO datasets (name, upload_date) VALUES (?, ?)", (dataset_name, upload_date))
        dataset_id = conn.execute("SELECT id FROM datasets WHERE name = ?", (dataset_name,)).fetchone()[0]

        # Add dataset_id column to the DataFrame
        dataframe["dataset_id"] = dataset_id

        # Save to the database
        dataframe.to_sql("sales_data", conn, if_exists="append", index=False,
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
            # Required columns for the sales_data table
            required_columns = ["Order Date", "Sales", "Profit", "Category", "Region", "Sub-Category", "Quantity", "Discount"]
            if validate_columns(data, required_columns):
                # Standardize column names and clean the data
                data.rename(columns=lambda x: x.strip().lower().replace(" ", "_"), inplace=True)
                data["order_date"] = pd.to_datetime(data["order_date"], errors="coerce")
                data.dropna(subset=["order_date"], inplace=True)  # Drop rows with invalid dates

                # Save to database
                save_to_database(dataset_name, data)
    else:
        st.sidebar.error("Please upload a file and provide a unique dataset name.")
