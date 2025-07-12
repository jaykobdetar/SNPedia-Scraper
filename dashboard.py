# dashboard.py
# A simple, read-only dashboard for monitoring the scraper.

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os

# --- Path Setup ---
# Use an absolute path to ensure we always find the correct files.
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(PROJECT_ROOT, 'snpedia.db')

app = Flask(__name__)
CORS(app)

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    if not os.path.exists(DB_PATH):
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/status')
def get_status():
    """Reads the latest progress from the database and returns it."""
    conn = get_db_connection()
    
    if conn is None:
        return jsonify({
            "count": 0,
            "total": 110000,
            "current": "N/A",
            "logs": [{"time": "", "message": "Database not found. Run the scraper to begin."}]
        })

    try:
        count = conn.execute('SELECT COUNT(*) FROM snps').fetchone()[0]
        latest_snp = conn.execute('SELECT rsid, scraped_at FROM snps ORDER BY scraped_at DESC LIMIT 1').fetchone()
        log_rows = conn.execute('SELECT rsid, scraped_at FROM snps ORDER BY scraped_at DESC LIMIT 10').fetchall()
        
        logs = [
            {"time": row['scraped_at'].split(' ')[1].split('.')[0], "message": f"Scraped {row['rsid']}"}
            for row in log_rows
        ]

        status = {
            "count": count,
            "total": 110000,
            "current": latest_snp['rsid'] if latest_snp else "N/A",
            "logs": logs
        }
    except Exception as e:
        return jsonify({
            "count": 0, "total": 110000, "current": "Error",
            "logs": [{"time": "", "message": f"An error occurred: {e}"}]
        })
    finally:
        if conn:
            conn.close()
            
    return jsonify(status)

@app.route('/')
def index():
    """Serves the main dashboard page."""
    return send_from_directory(PROJECT_ROOT, 'index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
