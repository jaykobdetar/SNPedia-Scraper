# dashboard.py
# A simple, read-only dashboard for monitoring the scraper.

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
from werkzeug.exceptions import HTTPException

# --- Path Setup ---
# Use an absolute path to ensure we always find the correct files.
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(PROJECT_ROOT, 'snpedia.db')

app = Flask(__name__)
# Configure CORS more restrictively
CORS(app, origins=['http://localhost:5000', 'http://127.0.0.1:5000'])

# Security headers
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    if not os.path.exists(DB_PATH):
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Enable read-only mode for safety
    conn.execute("PRAGMA query_only = ON")
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
        app.logger.error(f"Database error: {e}")
        return jsonify({
            "count": 0, "total": 110000, "current": "Error",
            "logs": [{"time": "", "message": "Database error occurred"}]
        }), 500
    finally:
        if conn:
            conn.close()
            
    return jsonify(status)

@app.route('/')
def index():
    """Serves the main dashboard page."""
    return send_from_directory(PROJECT_ROOT, 'index.html')

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(Exception)
def handle_error(e):
    if isinstance(e, HTTPException):
        return jsonify({"error": e.description}), e.code
    app.logger.error(f"Unhandled exception: {e}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # Production recommendations:
    # - Use a production WSGI server (gunicorn, uwsgi)
    # - Consider adding authentication if exposed to network
    # - Use HTTPS in production
    print("Starting dashboard on http://localhost:5000")
    print("WARNING: This is a development server. Use a production WSGI server for deployment.")
    app.run(host='127.0.0.1', port=5000, debug=False)
