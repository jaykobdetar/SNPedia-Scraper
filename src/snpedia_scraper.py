import requests
import sqlite3
import time
import json
from datetime import datetime
import os
import sys

class SNPediaScraper:
    def __init__(self, db_path='snpedia.db'):
        self.conn = sqlite3.connect(db_path)
        self.api_url = "https://bots.snpedia.com/api.php"
        self.create_tables()
        
    def create_tables(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS snps (
                rsid TEXT PRIMARY KEY,
                content TEXT,
                scraped_at TIMESTAMP
            )
        ''')
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS progress (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        self.conn.commit()
        
    def scrape(self):
        print("Getting list of all SNPs...")
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
            print(f"Resuming from: {last_continue}")
        
        snp_count = int(self.get_progress('snp_count') or 0)
        
        while True:
            try:
                r = requests.get(self.api_url, params=params)
                data = r.json()
                
                for page in data['query']['categorymembers']:
                    rsid = page['title']
                    
                    if self.already_scraped(rsid):
                        continue
                    
                    page_url = f"https://www.snpedia.com/index.php/{rsid}?action=raw"
                    content = requests.get(page_url).text
                    
                    self.conn.execute(
                        'INSERT INTO snps (rsid, content, scraped_at) VALUES (?, ?, ?)',
                        (rsid, content, datetime.now())
                    )
                    
                    snp_count += 1
                    if snp_count % 10 == 0:
                        self.conn.commit()
                        self.save_progress('snp_count', str(snp_count))
                        print(f"Scraped {snp_count} SNPs... Latest: {rsid}")
                    
                    time.sleep(3)
                
                if 'continue' in data:
                    params['cmcontinue'] = data['continue']['cmcontinue']
                    self.save_progress('cmcontinue', params['cmcontinue'])
                else:
                    break
                
                time.sleep(3)
                
            except KeyboardInterrupt:
                print("\nPausing... Progress saved. Run again to resume.")
                self.conn.commit()
                sys.exit(0)
            except Exception as e:
                print(f"Error: {e}. Retrying in 30 seconds...")
                time.sleep(30)
        
        self.conn.commit()
        print(f"Done! Scraped {snp_count} total SNPs")
        
    def already_scraped(self, rsid):
        cursor = self.conn.execute('SELECT 1 FROM snps WHERE rsid = ?', (rsid,))
        return cursor.fetchone() is not None
        
    def save_progress(self, key, value):
        self.conn.execute(
            'INSERT OR REPLACE INTO progress (key, value) VALUES (?, ?)',
            (key, value)
        )
        self.conn.commit()
        
    def get_progress(self, key):
        cursor = self.conn.execute('SELECT value FROM progress WHERE key = ?', (key,))
        row = cursor.fetchone()
        return row[0] if row else None

if __name__ == "__main__":
    scraper = SNPediaScraper()
    print("=== SNPedia Scraper ===")
    print("This will take ~90 hours to complete")
    print("Press Ctrl+C anytime to pause (progress is saved)")
    print("="*30)
    scraper.scrape()
