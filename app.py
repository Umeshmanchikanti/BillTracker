from PIL import Image
import pytesseract
from flask import Flask, request, render_template, jsonify, send_file
import sqlite3
import pandas as pd
from werkzeug.utils import secure_filename
import os
import re
from datetime import datetime

# Configure Tesseract OCR executable path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Helper function to parse date from text
def parse_date_from_text(text):
    date_patterns = [r'\d{1,2}/\d{1,2}/\d{4}', r'\d{4}-\d{1,2}-\d{1,2}']
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return datetime.strptime(match.group(), "%d/%m/%Y").date()
            except ValueError:
                pass
            try:
                return datetime.strptime(match.group(), "%Y-%m-%d").date()
            except ValueError:
                pass
    return None

# Helper function to parse amount from text
def parse_amount_from_text(text):
    match = re.search(r'\d{1,3}(?:,\d{3})*(?:\.\d{2})?', text)  # Allow commas in numbers
    return float(match.group().replace(',', '')) if match else None

# Helper function to parse description from text
def parse_description_from_text(text):
    lines = text.splitlines()
    for line in lines:
        if len(line.strip()) > 5:  # Use a heuristic to find a meaningful description
            return line.strip()
    return "No description found"

# Flask app initialization
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
def init_db():
    with sqlite3.connect("transactions_v2.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                amount REAL,
                description TEXT,
                image_path TEXT,
                transaction_type TEXT
            )
        """)
init_db()

# Homepage route
@app.route('/')
def index():
    return render_template("index.html")

# Add Transaction (Manual or Automatic Mode)
@app.route('/add_transaction', methods=["POST"])
def add_transaction():
    form_data = request.form
    transaction_type = form_data.get('transaction_Type')
    date = form_data.get('date')
    amount = form_data.get('amount')
    description = form_data.get('description')
    image_file = request.files.get('image')

    image_path = None

    # Automatic Mode: Extract details using OCR if an image is provided
    if transaction_type == "automatic" and image_file:
        filename = secure_filename(image_file.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(image_path)

        # Perform OCR on the uploaded image
        extracted_text = pytesseract.image_to_string(Image.open(image_path))
        print("Extracted Text:", extracted_text)  # Debugging

        # Parse details from extracted text
        date = parse_date_from_text(extracted_text)
        print("Parsed Date:", date)  # Debugging
        amount = parse_amount_from_text(extracted_text)
        print("Parsed Amount:", amount)  # Debugging
        description = parse_description_from_text(extracted_text)
        print("Parsed Description:", description)  # Debugging

    # Validate input or extracted data
    if not date or not amount or not description:
        print("Error: Missing data - Date:", date, "Amount:", amount, "Description:", description)  # Debugging
        return jsonify({"error": "Insufficient data to save transaction"}), 400

    # Insert transaction into the database
    with sqlite3.connect("transactions_v2.db") as conn:
        conn.execute("""
            INSERT INTO transactions (date, amount, description, image_path, transaction_type)
            VALUES (?, ?, ?, ?, ?)
        """, (date, amount, description, image_path or "NO_IMAGE", transaction_type))

    return jsonify({"message": "Transaction added successfully!"})

# Export to Excel
@app.route('/export', methods=['GET'])
def export_to_excel():
    with sqlite3.connect("transactions_v2.db") as conn:
        df = pd.read_sql_query("SELECT * FROM transactions", conn)
    export_path = "transactions.xlsx"
    df.to_excel(export_path, index=False)
    return send_file(export_path, as_attachment=True)

# Fetch Transactions
@app.route('/transactions', methods=['GET'])
def get_transactions():
    with sqlite3.connect("transactions_v2.db") as conn:
        cursor = conn.execute("SELECT * FROM transactions")
        rows = cursor.fetchall()
    return jsonify(rows)

# Initialize the app
if __name__ == "__main__":
    app.run(debug=True)
