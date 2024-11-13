from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import sqlite3
import os
from datetime import datetime, timezone
import uuid
import pandas as pd  # For content validation in CSV files
from fastapi.middleware.cors import CORSMiddleware


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
    upload_time = datetime.now(timezone.utc)
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

        return JSONResponse(content={"message": f"File '{file.filename}' uploaded and metadata stored successfully."})
    
    except HTTPException as e:
        return JSONResponse(content={"message": str(e.detail)}, status_code=e.status_code)
    except Exception as e:
        print(e)
        return JSONResponse(content={"message": "There was an error uploading the file."}, status_code=500)

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
