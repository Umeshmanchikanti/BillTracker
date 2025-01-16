from PIL import Image
import pytesseract
from flask import Flask, request, render_template, jsonify, send_file
import sqlite3
import pandas as pd
from werkzeug.utils import secure_filename
import os
import re
from datetime import datetime


pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def parse_date_from_text(text):
    # Try to find dates in formats like DD/MM/YYYY or MM/DD/YYYY
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

def parse_amount_from_text(text):
    import re
    match = re.search(r'\d+\.\d{2}', text)
    return float(match.group()) if match else None

def parse_description_from_text(text):
    return text.splitlines()[0] if text else None

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

# Homepage
@app.route('/')
def index():
    return render_template("index.html")

# Add Transaction
@app.route('/add_transaction_v1', methods=['POST'])
def add_transaction_v1():
    form_data = request.form
    date = form_data.get('date')
    amount = form_data.get('amount')
    description = form_data.get('description')
    image_file = request.files.get('image')

    image_path = None
    if image_file:
        filename = secure_filename(image_file.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(image_path)

        extracted_text = pytesseract.image_to_string(Image.open(image_path))

        if not date:
            date = parse_date_from_text(extracted_text)
        if not amount:
            amount = parse_amount_from_text(extracted_text)
        if not description:
            description = parse_description_from_text(extracted_text)

    if not date or not amount or not description:
        return jsonify({"error": "Insufficient data to save transaction"}), 400
    
    with sqlite3.connect("transactions.db") as conn:
        conn.execute("""
            INSERT INTO transactions (date, amount, description, image_path)
            VALUES (?, ?, ?, ?)
        """, (date, amount, description, image_path))
    return jsonify({"message": "Transaction added successfully!"})

@app.route('/add_transaction', methods=["POST"])
def add_transaction():
    form_data = request.form
    transaction_Type, date, amount, description = form_data.get('transaction_Type'), form_data.get('date'), form_data.get('amount'), form_data.get('description')

    print(transaction_Type, date, amount, description)

    with sqlite3.connect("transactions_v2.db") as conn:
        conn.execute("""
            INSERT INTO transactions (date, amount, description, image_path, transaction_Type)
            VALUES (?, ?, ?, ?, ?)
        """, (date, amount, description, "NO_IMAGE", transaction_Type))

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

if __name__ == "__main__":
    app.run(debug=True)
