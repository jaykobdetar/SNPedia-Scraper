import requests
import sqlite3
import time
import json
from datetime import datetime
import os
import sys
import threading

# --- Path Setup ---
# Get the absolute path to the project root directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# Define the absolute path for the database
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, 'snpedia.db')
ERROR_LOG_PATH = os.path.join(PROJECT_ROOT, 'scraper_errors.log')

class SNPediaScraper:
    def __init__(self, db_path=DEFAULT_DB_PATH, status_callback=None, log_callback=None):
        self.db_path = db_path
        self.api_url = "https://bots.snpedia.com/api.php"
        self.total_snps = 110000  # From README
        
        # Callbacks for UI updates
        self.status_callback = status_callback
        self.log_callback = log_callback

        # State management
        self.running = False
        self.paused = False
        self._thread = None

        self._create_tables()
        self._init_error_log()

    def _init_error_log(self):
        """Initialize or append to error log file."""
        if not os.path.exists(ERROR_LOG_PATH):
            with open(ERROR_LOG_PATH, 'w') as f:
                f.write("# SNPedia Scraper Error Log\n")
                f.write(f"# Started: {datetime.now()}\n")
                f.write("# Format: timestamp | rsid | error_type | error_message\n")
                f.write("-" * 80 + "\n")
    
    def _log_error(self, rsid, error_type, error_message):
        """Log an error to the error file."""
        with open(ERROR_LOG_PATH, 'a') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} | {rsid} | {error_type} | {error_message}\n")
            f.flush()  # Ensure it's written immediately

    def _create_tables(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS snps (
                rsid TEXT PRIMARY KEY,
                content TEXT,
                scraped_at TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS progress (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def start(self):
        if not self.running:
            self.running = True
            self.paused = False
            self._thread = threading.Thread(target=self._scrape_loop)
            self._thread.start()
            if self.log_callback: self.log_callback("Scraper started.")

    def pause(self):
        self.paused = True
        if self.log_callback: self.log_callback("Scraper paused.")

    def resume(self):
        self.paused = False
        if self.log_callback: self.log_callback("Scraper resumed.")

    def stop(self):
        self.running = False
        if self.log_callback: self.log_callback("Scraper stopping...")

    def get_current_progress(self):
        count = int(self.get_progress('snp_count') or 0)
        return count, self.total_snps

    def _scrape_loop(self):
        params = {
            'action': 'query',
            'list': 'categorymembers',
            'cmtitle': 'Category:Is_a_snp',
            'cmlimit': 500,
            'format': 'json'
        }

        last_continue = self.get_progress('cmcontinue')
        if last_continue:
            params['cmcontinue'] = last_continue

        snp_count = int(self.get_progress('snp_count') or 0)

        while self.running:
            if self.paused:
                time.sleep(1)
                continue

            try:
                r = requests.get(self.api_url, params=params)
                r.raise_for_status()
                data = r.json()

                for page in data['query']['categorymembers']:
                    if not self.running:
                        break
                    
                    while self.paused:
                        if not self.running: break
                        time.sleep(1)

                    rsid = page['title']
                    rsid = rsid.replace(' ', '_')  # Fix space-encoded rsids to avoid URL issues
                    
                    if self.already_scraped(rsid):
                        if self.status_callback: self.status_callback(snp_count, self.total_snps, f"Skipped {rsid}")
                        continue
                    
                    # Try to fetch the content
                    try:
                        # Use API for raw content - compliant and gets clean wiki markup
                        params_content = {
                            'action': 'query',
                            'prop': 'revisions',
                            'rvprop': 'content',
                            'format': 'json',
                            'titles': rsid
                        }
                        content_response = requests.get(self.api_url, params=params_content, headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                        })
                        
                        # Try to get JSON data even if status code indicates error
                        try:
                            data_content = content_response.json()
                            
                            # Check if we got valid data
                            if 'query' in data_content and 'pages' in data_content['query']:
                                page_id = list(data_content['query']['pages'].keys())[0]
                                if page_id == '-1':  # Page doesn't exist
                                    if self.log_callback: self.log_callback(f"Page not found for {rsid}. Skipping.")
                                    continue
                                    
                                content = data_content['query']['pages'][page_id]['revisions'][0]['*']
                                
                                # Save the content
                                conn = sqlite3.connect(self.db_path)
                                conn.execute(
                                    'INSERT INTO snps (rsid, content, scraped_at) VALUES (?, ?, ?)',
                                    (rsid, content, datetime.now())
                                )
                                conn.commit()
                                conn.close()

                                snp_count += 1
                                if self.status_callback: self.status_callback(snp_count, self.total_snps, rsid)
                                if self.log_callback and snp_count % 10 == 0: self.log_callback(f"Scraped {snp_count} SNPs. Latest: {rsid}")

                                if snp_count % 10 == 0:
                                    self.save_progress('snp_count', str(snp_count))
                            else:
                                # JSON is valid but doesn't contain expected data
                                raise Exception("Invalid response structure")
                                
                        except (json.JSONDecodeError, KeyError) as e:
                            # If we can't parse JSON or access expected keys, check status
                            content_response.raise_for_status()
                            raise e

                    except Exception as e:
                        # Check if we actually saved this SNP despite the error
                        if self.already_scraped(rsid):
                            if self.log_callback: 
                                self.log_callback(f"Got error but {rsid} was saved successfully. Continuing...")
                            snp_count += 1
                            if self.status_callback: 
                                self.status_callback(snp_count, self.total_snps, rsid)
                            # No delay needed - it worked!
                        else:
                            # Real error - SNP wasn't saved
                            if self.log_callback: 
                                self.log_callback(f"Error fetching {rsid}: {e}. Retrying in 30 seconds...")
                            
                            # Log the error for later recovery
                            if "502" in str(e):
                                self._log_error(rsid, "502_ERROR", str(e))
                            else:
                                self._log_error(rsid, "OTHER_ERROR", str(e))
                            
                            time.sleep(30)
                            continue  # Skip the normal delay and retry immediately

                    time.sleep(3)

                if 'continue' in data and data['continue']:
                    params['cmcontinue'] = data['continue']['cmcontinue']
                    self.save_progress('cmcontinue', params['cmcontinue'])
                else:
                    self.running = False # End of the list
                    if self.log_callback: self.log_callback("Scraping complete: Reached end of SNP list.")
                    break
                
                time.sleep(3)

            except KeyboardInterrupt:
                self.stop()
                print("\n\nPausing... Progress saved. Run again to resume.")
                break
            except Exception as e:
                if self.log_callback: self.log_callback(f"Error: {e}. Retrying in 30 seconds...")
                time.sleep(30)
        
        self.running = False
        if self.log_callback: self.log_callback("Scraper stopped.")

    def already_scraped(self, rsid):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute('SELECT 1 FROM snps WHERE rsid = ?', (rsid,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    def save_progress(self, key, value):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            'INSERT OR REPLACE INTO progress (key, value) VALUES (?, ?)',
            (key, str(value))
        )
        conn.commit()
        conn.close()

    def get_progress(self, key):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute('SELECT value FROM progress WHERE key = ?', (key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None


if __name__ == "__main__":
    def console_status_callback(count, total, current_snp):
        # Simple progress bar for the console
        percent = (100 * (count / float(total)))
        bar_length = 50
        filled_length = int(bar_length * count // total)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        sys.stdout.write(f'\rProgress: |{bar}| {percent:.1f}% Complete ({current_snp})')
        sys.stdout.flush()

    def console_log_callback(message):
        sys.stdout.write(f'\n{datetime.now().strftime("%H:%M:%S")} - {message}\n')
        sys.stdout.flush()

    print("=== SNPedia Scraper (CLI) ===")
    print("This will take ~90 hours to complete.")
    print("Press Ctrl+C anytime to pause (progress is saved).")
    print("="*30)

    scraper = SNPediaScraper(
        status_callback=console_status_callback, 
        log_callback=console_log_callback
    )
    
    # Initial progress display
    initial_count, total_snps = scraper.get_current_progress()
    console_status_callback(initial_count, total_snps, "Ready")

    scraper.start()

    try:
        while scraper.running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nCaught Ctrl+C. Shutting down gracefully...")
        scraper.stop()
