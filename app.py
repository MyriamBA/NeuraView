from flask import Flask, request, jsonify
import pandas as pd

app = Flask(__name__)

# Maximum file size for upload (5MB in this example)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        # For now, we're supporting CSV files, but you can extend to Excel, JSON, etc.
        df = pd.read_csv(file)
        # Pass the DataFrame to validation function (see step 3)
        # Save it for further analysis
        # You can store it in memory or a database (SQLite, PostgreSQL)
        return jsonify({"message": "File successfully uploaded", "data_head": df.head().to_dict()}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
