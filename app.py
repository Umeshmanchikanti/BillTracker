from flask import Flask, request, render_template, jsonify, send_file
import sqlite3
import pandas as pd
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
def init_db():
    with sqlite3.connect("transactions.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                amount REAL,
                description TEXT,
                image_path TEXT
            )
        """)
init_db()

# Homepage
@app.route('/')
def index():
    return render_template("index.html")

# Add Transaction
@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    data = request.form
    date = data['date']
    amount = float(data['amount'])
    description = data['description']
    image_file = request.files.get('image')

    image_path = None
    if image_file:
        filename = secure_filename(image_file.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(image_path)

    with sqlite3.connect("transactions.db") as conn:
        conn.execute("""
            INSERT INTO transactions (date, amount, description, image_path)
            VALUES (?, ?, ?, ?)
        """, (date, amount, description, image_path))
    return jsonify({"message": "Transaction added successfully!"})

# Export to Excel
@app.route('/export', methods=['GET'])
def export_to_excel():
    with sqlite3.connect("transactions.db") as conn:
        df = pd.read_sql_query("SELECT * FROM transactions", conn)
    export_path = "transactions.xlsx"
    df.to_excel(export_path, index=False)
    return send_file(export_path, as_attachment=True)

# Fetch Transactions
@app.route('/transactions', methods=['GET'])
def get_transactions():
    with sqlite3.connect("transactions.db") as conn:
        cursor = conn.execute("SELECT * FROM transactions")
        rows = cursor.fetchall()
    return jsonify(rows)

if __name__ == "__main__":
    app.run(debug=True)
