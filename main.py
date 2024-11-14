from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
import sqlite3
import os
import uuid
import pandas as pd  
import numpy as np
from sklearn.preprocessing import LabelEncoder
from fastapi.middleware.cors import CORSMiddleware
from io import StringIO


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allow the React frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database path and file storage directory
DB_PATH = "uploads_metadata.db"
UPLOAD_DIRECTORY = "uploaded_files"
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

# Initialize the SQLite database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS file_metadata (
    id TEXT PRIMARY KEY,
    filename TEXT,
    storage_path TEXT,
    upload_time TEXT,
    file_type TEXT
)
""")
conn.commit()
conn.close()


# File validation parameters
ALLOWED_FILE_TYPES = {"text/csv": "csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "excel"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
REQUIRED_COLUMNS = ["Name", "Age", "Salary"]

def save_metadata(file_id, filename, storage_path, file_type):
    """Save file metadata to SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Convert datetime to a string to avoid datetime adapter issues
    upload_time = datetime.now().isoformat()
    cursor.execute("INSERT INTO file_metadata (id, filename, storage_path, upload_time, file_type) VALUES (?, ?, ?, ?, ?)",
                   (file_id, filename, storage_path, upload_time, file_type))
    conn.commit()
    conn.close()

def validate_file(file: UploadFile):
    """Validates file type, size, and (optionally) content."""
    # Check file type
    ##if file.content_type not in ALLOWED_FILE_TYPES:
      #  raise HTTPException(status_code=400, detail="Unsupported file type. Only CSV and Excel files are allowed.")
    
    # Check file size
    #if file.spool_max_size > MAX_FILE_SIZE:
       # raise HTTPException(status_code=400, detail="File size exceeds the 5 MB limit.")

    # Optional content validation for CSV files
    if file.content_type == "text/csv":
        try:
            # Read a portion of the CSV to validate its structure
            content = pd.read_csv(file.file, nrows=0)  # Only read headers
            missing_columns = [col for col in REQUIRED_COLUMNS if col not in content.columns]
            if missing_columns:
                raise HTTPException(status_code=400, detail=f"CSV file is missing required columns: {', '.join(missing_columns)}")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid CSV content.")

    # Reset the file pointer after reading
    file.file.seek(0)

# Data cleaning and processing
def clean_and_process_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and process the uploaded data.

    Steps include:
    - Handling missing values
    - Removing duplicates
    - Standardizing formats
    - Encoding categorical variables
    - Scaling numerical features (if needed)

    Args:
        df (pd.DataFrame): The dataframe containing the raw uploaded data.

    Returns:
        pd.DataFrame: The cleaned and processed dataframe.
    """

    # Step 1: Handle missing values
    # Example: Fill numeric columns with the median, categorical with the mode
    for column in df.columns:
        if df[column].dtype == 'object':  # Categorical column
            df[column].fillna(df[column].mode()[0], inplace=True)  # Fill with mode
        else:  # Numerical column
            df[column].fillna(df[column].median(), inplace=True)  # Fill with median

    # Step 2: Remove duplicate rows
    df.drop_duplicates(inplace=True)

    # Step 3: Standardize date formats (if applicable)
    for column in df.columns:
        if 'date' in column.lower() and df[column].dtype == 'object':
            df[column] = pd.to_datetime(df[column], errors='coerce')  # Convert to datetime

    # Step 4: Handle outliers (example: using IQR to filter out outliers)
    for column in df.select_dtypes(include=[np.number]).columns:
        Q1 = df[column].quantile(0.25)
        Q3 = df[column].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        df = df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]

    # Step 5: Encode categorical variables
    for column in df.select_dtypes(include=['object']).columns:
        encoder = LabelEncoder()
        df[column] = encoder.fit_transform(df[column])

    # Step 6: Optional - Scaling numerical features (if needed)
    # from sklearn.preprocessing import StandardScaler
    # scaler = StandardScaler()
    # df[df.select_dtypes(include=[np.number]).columns] = scaler.fit_transform(df[df.select_dtypes(include=[np.number]).columns])

    return df

def extract_date_features(df, date_column):
    df[date_column] = pd.to_datetime(df[date_column])  # Ensure date format
    df["year"] = df[date_column].dt.year
    df["month"] = df[date_column].dt.month
    df["day"] = df[date_column].dt.day
    df["weekday"] = df[date_column].dt.weekday
    return df

def aggregate_by_category(df, groupby_column, numeric_column):
    aggregated_df = df.groupby(groupby_column)[numeric_column].agg(['mean', 'sum', 'count']).reset_index()
    aggregated_df.columns = [groupby_column, f"{numeric_column}_mean", f"{numeric_column}_sum", f"{numeric_column}_count"]
    return df.merge(aggregated_df, on=groupby_column, how="left")

def encode_categorical(df, categorical_columns):
    label_encoders = {}
    for column in categorical_columns:
        le = LabelEncoder()
        df[column] = le.fit_transform(df[column])
        label_encoders[column] = le  # Store for inverse transformation if needed
    return df, label_encoders

def create_interaction_features(df, columns):
    for i, col1 in enumerate(columns):
        for col2 in columns[i+1:]:
            df[f"{col1}_x_{col2}"] = df[col1] * df[col2]
    return df

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Validate the file
       # validate_file(file)

        # Generate a unique ID and file path
        file_id = str(uuid.uuid4())
        file_path = os.path.join(UPLOAD_DIRECTORY, f"{file_id}_{file.filename}")
        
        # Save the file to local storage
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Save metadata to SQLite
        save_metadata(file_id, file.filename, file_path, file.content_type)

          # Attempt to read the file into a DataFrame, specifying a delimiter if necessary
        try:
            df = pd.read_csv(StringIO(content.decode("utf-8")))
        except pd.errors.ParserError:
            raise HTTPException(status_code=400, detail="Failed to parse file. Please check the file format.")
        except pd.errors.EmptyDataError:
            raise HTTPException(status_code=400, detail="The uploaded file appears to be empty or improperly formatted.")

        # Check if DataFrame is empty
        if df.empty:
            raise HTTPException(status_code=400, detail="The uploaded file contains no data.")
         # Clean and process the data

        cleaned_df = clean_and_process_data(df)

        # Save cleaned file
        file_id = str(uuid.uuid4())
        storage_path = os.path.join(UPLOAD_DIRECTORY, f"{file_id}_{file.filename}")
        cleaned_df.to_csv(storage_path, index=False)

        # Save metadata with string-formatted datetime
        save_metadata(file_id, file.filename, storage_path, file.content_type)

        return JSONResponse(content={"message": f"File '{file.filename}' uploaded and cleaned successfully.", "storage_path": storage_path})

    except HTTPException as e:
        return JSONResponse(content={"message": str(e.detail)}, status_code=e.status_code)
    except Exception as e:
        print(e)
        return JSONResponse(content={"message": "There was an error uploading or processing the file."}, status_code=500)

@app.post("/feature-engineering")
async def feature_engineering():
    # Load the cleaned data
    data_path = "../uploaded_files"
    data = pd.read_csv(data_path)
    
    # Apply feature engineering steps
    if "transaction_date" in data.columns:
        data = extract_date_features(data, "transaction_date")
    if "customer_id" in data.columns and "transaction_amount" in data.columns:
        data = aggregate_by_category(data, "customer_id", "transaction_amount")
    categorical_columns = ["product_category", "region"]  # Update with actual columns
    data, encoders = encode_categorical(data, categorical_columns)
    numeric_columns = ["transaction_amount", "customer_age"]  # Update as needed
    data = create_interaction_features(data, numeric_columns)

    # Save the engineered data
    engineered_data_path = "path/to/engineered_data.csv"
    data.to_csv(engineered_data_path, index=False)

    return {"message": "Feature extraction and engineering completed.", "path": engineered_data_path}

@app.get("/files")
async def list_files():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, storage_path, upload_time, file_type FROM file_metadata")
    files = cursor.fetchall()
    conn.close()
    
    # Structure the output as a list of dictionaries
    files_list = [
        {"id": file[0], "filename": file[1], "storage_path": file[2], "upload_time": file[3], "file_type": file[4]}
        for file in files
    ]
    return {"files": files_list}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
