from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

import pandas as pd

app = Flask(__name__)

# Maximum file size for upload (5MB in this test)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

# Step I : Data Ingestion
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    try:
        df = pd.read_csv(file)
        is_valid, message = validate_data(df)
        if not is_valid:
            return jsonify({"error": message}), 400
        
         # Store the data in the database
        store_data(df, file.filename)
        
        # Proceed with data analysis
        return jsonify({"message": "File successfully uploaded", "data_head": df.head().to_dict()}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# Step II : Data Validation
def validate_data(df):
    # Check for missing values
    if df.isnull().sum().sum() > 0:
        return False, "Dataset contains missing values."

    # Check if the 'Date' column exists and is in proper format
    if 'TransactionDate' not in df.columns or not pd.to_datetime(df['TransactionDate'], errors='coerce').notna().all():
        return False, "'Date' column missing or contains invalid values."
    # Further validations can be added as needed
    return True, "Data is valid."


# Step III : Data Storage

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
db = SQLAlchemy(app)

class Dataset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100))
    data = db.Column(db.PickleType)  # Store the DataFrame as a binary blob

# Create the database tables if they don't exist
with app.app_context():
    db.create_all()

# Step III : Save Data 
def store_data(df, filename):
    dataset = Dataset(filename=filename, data=df.to_dict())
    db.session.add(dataset)
    db.session.commit()



if __name__ == "__main__":
    app.run(debug=True)

