#!/usr/bin/env python3
"""
Recover SNPs from the scraper error log.
"""

import sqlite3
import requests
import time
from datetime import datetime
import os
import re

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(PROJECT_ROOT, 'snpedia.db')
ERROR_LOG_PATH = os.path.join(PROJECT_ROOT, 'scraper_errors.log')

def parse_error_log():
    """Parse the error log to extract unique SNPs that had errors."""
    if not os.path.exists(ERROR_LOG_PATH):
        print("No error log found!")
        return []
    
    error_snps = {}
    
    with open(ERROR_LOG_PATH, 'r') as f:
        for line in f:
            # Skip header lines
            if line.startswith('#') or line.startswith('-'):
                continue
            
            # Parse error line: timestamp | rsid | error_type | error_message
            parts = line.strip().split(' | ')
            if len(parts) >= 4:
                timestamp = parts[0]
                rsid = parts[1]
                error_type = parts[2]
                error_msg = parts[3]
                
                # Store the latest error for each SNP
                error_snps[rsid] = {
                    'timestamp': timestamp,
                    'error_type': error_type,
                    'error_msg': error_msg
                }
    
    return error_snps

def check_missing_snps(error_snps):
    """Check which error SNPs are actually missing from the database."""
    conn = sqlite3.connect(DB_PATH)
    
    missing = []
    found = []
    
    print("=== Checking Error Log SNPs ===")
    print(f"Total unique SNPs with errors: {len(error_snps)}")
    print()
    
    # Count by error type
    error_types = {}
    for rsid, info in error_snps.items():
        error_type = info['error_type']
        error_types[error_type] = error_types.get(error_type, 0) + 1
    
    print("Errors by type:")
    for error_type, count in error_types.items():
        print(f"  {error_type}: {count}")
    print()
    
    # Check which are missing
    for rsid in error_snps.keys():
        cursor = conn.execute("SELECT 1 FROM snps WHERE rsid = ?", (rsid,))
        if cursor.fetchone():
            found.append(rsid)
        else:
            missing.append(rsid)
    
    conn.close()
    
    print(f"✓ Found in database: {len(found)}")
    print(f"✗ Missing from database: {len(missing)}")
    print()
    
    if missing:
        print("Missing SNPs:")
        for rsid in missing[:20]:  # Show first 20
            info = error_snps[rsid]
            print(f"  - {rsid} ({info['error_type']} at {info['timestamp']})")
        if len(missing) > 20:
            print(f"  ... and {len(missing) - 20} more")
    
    return missing

def recover_missing_snps(missing_list):
    """Attempt to recover the missing SNPs."""
    
    if not missing_list:
        print("\nNo SNPs to recover!")
        return
    
    print(f"\n=== Recovering {len(missing_list)} Missing SNPs ===")
    
    api_url = "https://bots.snpedia.com/api.php"
    recovered = 0
    failed = []
    
    for i, rsid in enumerate(missing_list):
        print(f"\r[{i+1}/{len(missing_list)}] Recovering {rsid}...", end='', flush=True)
        
        try:
            params = {
                'action': 'query',
                'prop': 'revisions',
                'rvprop': 'content',
                'format': 'json',
                'titles': rsid
            }
            
            response = requests.get(api_url, params=params, headers={
                'User-Agent': 'Mozilla/5.0 (Error Log Recovery Script)'
            })
            
            # Try to get data regardless of status code
            try:
                data = response.json()
                
                if 'query' in data and 'pages' in data['query']:
                    page_id = list(data['query']['pages'].keys())[0]
                    
                    if page_id != '-1':  # Page exists
                        content = data['query']['pages'][page_id]['revisions'][0]['*']
                        
                        # Save to database
                        conn = sqlite3.connect(DB_PATH)
                        conn.execute(
                            'INSERT INTO snps (rsid, content, scraped_at) VALUES (?, ?, ?)',
                            (rsid, content, datetime.now())
                        )
                        conn.commit()
                        conn.close()
                        
                        recovered += 1
                        print(f"\r[{i+1}/{len(missing_list)}] ✓ Recovered {rsid}    ")
                    else:
                        failed.append((rsid, "Page does not exist in SNPedia"))
                        print(f"\r[{i+1}/{len(missing_list)}] ✗ {rsid} - Page not found    ")
                else:
                    failed.append((rsid, "Invalid API response"))
                    print(f"\r[{i+1}/{len(missing_list)}] ✗ {rsid} - Invalid response    ")
                    
            except Exception as e:
                failed.append((rsid, f"Parse error: {str(e)}"))
                print(f"\r[{i+1}/{len(missing_list)}] ✗ {rsid} - Parse error    ")
                
        except Exception as e:
            failed.append((rsid, f"Request error: {str(e)}"))
            print(f"\r[{i+1}/{len(missing_list)}] ✗ {rsid} - Request failed    ")
        
        # Respect rate limit
        time.sleep(3)
    
    print(f"\n\n=== Recovery Summary ===")
    print(f"✓ Successfully recovered: {recovered}")
    print(f"✗ Failed to recover: {len(failed)}")
    
    if failed:
        print("\nFailed SNPs (first 10):")
        for rsid, error in failed[:10]:
            print(f"  {rsid}: {error}")
        
        # Save failed list
        with open('failed_error_log_recovery.txt', 'w') as f:
            for rsid, error in failed:
                f.write(f"{rsid}: {error}\n")
        print(f"\nAll {len(failed)} failed SNPs saved to: failed_error_log_recovery.txt")
    
    return recovered, failed

def archive_error_log():
    """Archive the current error log after recovery."""
    if os.path.exists(ERROR_LOG_PATH):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archive_name = f'scraper_errors_processed_{timestamp}.log'
        archive_path = os.path.join(PROJECT_ROOT, archive_name)
        
        # Copy current log to archive
        with open(ERROR_LOG_PATH, 'r') as f:
            content = f.read()
        with open(archive_path, 'w') as f:
            f.write(content)
        
        print(f"\nError log archived to: {archive_name}")
        
        response = input("Clear current error log? (y/N): ")
        if response.lower() == 'y':
            os.remove(ERROR_LOG_PATH)
            print("Error log cleared.")

def main():
    print("=== SNPedia Error Log Recovery Tool ===")
    print("\nThis tool will recover SNPs from the scraper error log.")
    
    if not os.path.exists(ERROR_LOG_PATH):
        print("\nNo error log found at:", ERROR_LOG_PATH)
        print("The scraper will create this file when it encounters errors.")
        return
    
    # Parse error log
    error_snps = parse_error_log()
    
    if not error_snps:
        print("\nNo errors found in the log!")
        return
    
    # Check which SNPs are missing
    missing = check_missing_snps(error_snps)
    
    if missing:
        print(f"\nFound {len(missing)} SNPs that need recovery.")
        response = input("Attempt to recover these SNPs? (y/N): ")
        
        if response.lower() == 'y':
            recovered, failed = recover_missing_snps(missing)
            
            # Final check
            print("\n=== Final Verification ===")
            still_missing = []
            conn = sqlite3.connect(DB_PATH)
            for rsid in missing:
                cursor = conn.execute("SELECT 1 FROM snps WHERE rsid = ?", (rsid,))
                if not cursor.fetchone():
                    still_missing.append(rsid)
            conn.close()
            
            if still_missing:
                print(f"Still missing after recovery: {len(still_missing)}")
            else:
                print("All error log SNPs successfully recovered!")
            
            # Offer to archive the log
            archive_error_log()
    else:
        print("\nGreat news! All error log SNPs are already in the database.")
        print("No recovery needed.")
        
        # Still offer to archive
        response = input("\nArchive the error log? (y/N): ")
        if response.lower() == 'y':
            archive_error_log()

if __name__ == "__main__":
    main()
