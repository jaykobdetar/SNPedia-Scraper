# backend.py
from flask import Flask, render_template_string, jsonify, request
from flask_cors import CORS
import threading
import sqlite3
import requests
import time
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# Global status
scraper_status = {
    "running": False,
    "paused": False,
    "count": 0,
    "current": "",
    "total": 110000,
    "logs": []
}

scraper_thread = None

class SNPediaScraper:
    def __init__(self):
        self.db_path = 'snpedia.db'
        self.api_url = "https://bots.snpedia.com/api.php"
        self.setup_db()
        
    def setup_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute('''CREATE TABLE IF NOT EXISTS snps 
                       (rsid TEXT PRIMARY KEY, content TEXT, scraped_at TIMESTAMP)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS progress 
                       (key TEXT PRIMARY KEY, value TEXT)''')
        conn.commit()
        conn.close()
        
    def get_progress(self, key):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute('SELECT value FROM progress WHERE key = ?', (key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
        
    def save_progress(self, key, value):
        conn = sqlite3.connect(self.db_path)
        conn.execute('INSERT OR REPLACE INTO progress (key, value) VALUES (?, ?)', 
                     (key, str(value)))
        conn.commit()
        conn.close()
        
    def scrape(self):
        global scraper_status
        
        # Get list of SNPs
        params = {
            'action': 'query',
            'list': 'categorymembers',
            'cmtitle': 'Category:Is_a_snp',
            'cmlimit': 500,
            'format': 'json'
        }
        
        # Resume from saved position
        last_continue = self.get_progress('cmcontinue')
        if last_continue:
            params['cmcontinue'] = last_continue
            
        count = int(self.get_progress('count') or 0)
        scraper_status['count'] = count
        
        while scraper_status['running']:
            if scraper_status['paused']:
                time.sleep(1)
                continue
                
            try:
                # Get SNP list
                r = requests.get(self.api_url, params=params)
                data = r.json()
                
                for page in data['query']['categorymembers']:
                    if not scraper_status['running']:
                        break
                        
                    while scraper_status['paused']:
                        time.sleep(1)
                        
                    rsid = page['title']
                    scraper_status['current'] = rsid
                    
                    # Check if already scraped
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.execute('SELECT 1 FROM snps WHERE rsid = ?', (rsid,))
                    exists = cursor.fetchone()
                    conn.close()
                    
                    if not exists:
                        # Get page content
                        page_url = f"https://www.snpedia.com/index.php/{rsid}?action=raw"
                        content = requests.get(page_url).text
                        
                        # Save to database
                        conn = sqlite3.connect(self.db_path)
                        conn.execute('INSERT INTO snps (rsid, content, scraped_at) VALUES (?, ?, ?)',
                                   (rsid, content, datetime.now()))
                        conn.commit()
                        conn.close()
                        
                        count += 1
                        scraper_status['count'] = count
                        scraper_status['logs'].append({
                            'time': datetime.now().strftime('%H:%M:%S'),
                            'message': f'Scraped {rsid}'
                        })
                        
                        # Save progress every 10 SNPs
                        if count % 10 == 0:
                            self.save_progress('count', count)
                            
                        # Respect robots.txt
                        time.sleep(3)
                
                # Check for more pages
                if 'continue' in data:
                    params['cmcontinue'] = data['continue']['cmcontinue']
                    self.save_progress('cmcontinue', params['cmcontinue'])
                else:
                    break
                    
            except Exception as e:
                scraper_status['logs'].append({
                    'time': datetime.now().strftime('%H:%M:%S'),
                    'message': f'Error: {str(e)}'
                })
                time.sleep(30)
                
        scraper_status['running'] = False

# Routes
@app.route('/')
def index():
    with open('index.html', 'r') as f:
        return f.read()

@app.route('/status')
def get_status():
    return jsonify(scraper_status)

@app.route('/start', methods=['POST'])
def start_scraping():
    global scraper_thread, scraper_status
    
    if not scraper_status['running']:
        scraper_status['running'] = True
        scraper_status['paused'] = False
        scraper = SNPediaScraper()
        scraper_thread = threading.Thread(target=scraper.scrape)
        scraper_thread.start()
        
    return jsonify({"status": "started"})

@app.route('/pause', methods=['POST'])
def pause_scraping():
    global scraper_status
    scraper_status['paused'] = not scraper_status['paused']
    return jsonify({"paused": scraper_status['paused']})

@app.route('/stop', methods=['POST'])
def stop_scraping():
    global scraper_status
    scraper_status['running'] = False
    return jsonify({"status": "stopped"})

if __name__ == '__main__':
    # Save the HTML from the artifact as index.html
    app.run(debug=True, port=5000)
