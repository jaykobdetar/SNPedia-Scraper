#!/usr/bin/env python3
"""
Automated backup script for SNPedia scraper database.
Runs in background and creates periodic backups based on selected strategy.
"""

import sqlite3
import shutil
import os
import time
from datetime import datetime
import sys
import glob

# Path setup
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(PROJECT_ROOT, 'snpedia.db')
BACKUP_DIR = os.path.join(PROJECT_ROOT, 'backups')

class BackupMonitor:
    def __init__(self, strategy='rolling', keep_count=5, interval=1000):
        self.strategy = strategy
        self.keep_count = keep_count
        self.interval = interval
        self.last_count = 0
        
        # Create backup directory
        os.makedirs(BACKUP_DIR, exist_ok=True)
        
    def get_snp_count(self):
        """Get current number of SNPs in database."""
        if not os.path.exists(DB_PATH):
            return 0
            
        try:
            conn = sqlite3.connect(DB_PATH)
            count = conn.execute('SELECT COUNT(*) FROM snps').fetchone()[0]
            conn.close()
            return count
        except:
            return 0
    
    def create_backup(self, count):
        """Create a backup of the database."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f'snpedia_backup_{count}_snps_{timestamp}.db'
        backup_path = os.path.join(BACKUP_DIR, backup_name)
        
        try:
            shutil.copy2(DB_PATH, backup_path)
            print(f"✓ Backup created: {backup_name}")
            return backup_path
        except Exception as e:
            print(f"✗ Backup failed: {e}")
            return None
    
    def cleanup_backups_rolling(self):
        """Keep only the most recent N backups."""
        backups = sorted(glob.glob(os.path.join(BACKUP_DIR, 'snpedia_backup_*.db')))
        
        if len(backups) > self.keep_count:
            for old_backup in backups[:-self.keep_count]:
                os.remove(old_backup)
                print(f"  Removed old backup: {os.path.basename(old_backup)}")
    
    def cleanup_backups_progressive(self, current_count):
        """Keep backups at progressive intervals."""
        backups = glob.glob(os.path.join(BACKUP_DIR, 'snpedia_backup_*.db'))
        
        for backup in backups:
            # Extract count from filename
            try:
                parts = os.path.basename(backup).split('_')
                backup_count = int(parts[2])
                
                # Determine if this backup should be kept
                keep = False
                
                # Keep all backups under 10k
                if backup_count <= 10000:
                    if backup_count % 1000 == 0:
                        keep = True
                # Keep every 5k between 10k-50k
                elif backup_count <= 50000:
                    if backup_count % 5000 == 0:
                        keep = True
                # Keep every 10k above 50k
                else:
                    if backup_count % 10000 == 0:
                        keep = True
                
                # Always keep the most recent backup
                if backup_count == current_count:
                    keep = True
                
                if not keep:
                    os.remove(backup)
                    print(f"  Removed intermediate backup: {os.path.basename(backup)}")
                    
            except (IndexError, ValueError):
                continue
    
    def should_backup(self, current_count):
        """Determine if a backup is needed based on strategy."""
        if self.strategy == 'all':
            # Backup every N SNPs
            return current_count >= self.last_count + self.interval
            
        elif self.strategy == 'rolling':
            # Backup every N SNPs (same logic, different cleanup)
            return current_count >= self.last_count + self.interval
            
        elif self.strategy == 'progressive':
            # Progressive intervals
            if current_count <= 10000:
                interval = 1000
            elif current_count <= 50000:
                interval = 5000
            else:
                interval = 10000
            
            return current_count % interval < (self.last_count % interval)
            
        elif self.strategy == 'hourly':
            # Check if an hour has passed since last backup
            backups = sorted(glob.glob(os.path.join(BACKUP_DIR, 'snpedia_backup_*.db')))
            if not backups:
                return True
                
            # Get modification time of most recent backup
            last_backup_time = os.path.getmtime(backups[-1])
            return (time.time() - last_backup_time) >= 3600
            
        return False
    
    def run(self):
        """Main monitoring loop."""
        print(f"\n=== Starting Backup Monitor ===")
        print(f"Strategy: {self.strategy}")
        if self.strategy in ['all', 'rolling']:
            print(f"Interval: Every {self.interval} SNPs")
        if self.strategy == 'rolling':
            print(f"Keep count: {self.keep_count} most recent backups")
        elif self.strategy == 'progressive':
            print(f"Intervals: 1k (≤10k), 5k (10-50k), 10k (>50k)")
        elif self.strategy == 'hourly':
            print(f"Keeping backups from last 24 hours")
        print(f"Backup directory: {BACKUP_DIR}")
        print(f"Monitoring: {DB_PATH}")
        print("\nPress Ctrl+C to stop monitoring")
        print("=" * 40)
        
        while True:
            try:
                current_count = self.get_snp_count()
                
                if current_count > 0 and self.should_backup(current_count):
                    backup_path = self.create_backup(current_count)
                    
                    if backup_path:
                        # Cleanup based on strategy
                        if self.strategy == 'rolling':
                            self.cleanup_backups_rolling()
                        elif self.strategy == 'progressive':
                            self.cleanup_backups_progressive(current_count)
                        elif self.strategy == 'hourly':
                            # Keep last 24 hours
                            cutoff_time = time.time() - (24 * 3600)
                            backups = glob.glob(os.path.join(BACKUP_DIR, 'snpedia_backup_*.db'))
                            for backup in backups:
                                if os.path.getmtime(backup) < cutoff_time:
                                    os.remove(backup)
                                    print(f"  Removed old backup: {os.path.basename(backup)}")
                        
                        # Calculate total backup size
                        total_size = sum(os.path.getsize(f) for f in 
                                       glob.glob(os.path.join(BACKUP_DIR, '*.db')))
                        print(f"  Total backup size: {total_size / 1024 / 1024:.1f} MB")
                    
                    self.last_count = current_count
                
                # Check every 30 seconds
                time.sleep(30)
                
            except KeyboardInterrupt:
                print("\n\nBackup monitor stopped.")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(60)

def get_user_choice(prompt, options, default=None):
    """Get user choice from a list of options."""
    print(f"\n{prompt}")
    for i, (key, desc) in enumerate(options.items(), 1):
        print(f"  {i}. {desc}")
    
    if default:
        print(f"\nDefault: {default}")
        
    while True:
        choice = input("\nEnter choice (number): ").strip()
        
        if not choice and default:
            return default
            
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return list(options.keys())[idx]
        except ValueError:
            pass
            
        print("Invalid choice. Please enter a number from the list.")

def get_number_input(prompt, min_val, max_val, default):
    """Get numeric input from user."""
    print(f"\n{prompt}")
    print(f"Range: {min_val} - {max_val}")
    print(f"Default: {default}")
    
    while True:
        value = input("\nEnter value (or press Enter for default): ").strip()
        
        if not value:
            return default
            
        try:
            num = int(value)
            if min_val <= num <= max_val:
                return num
            else:
                print(f"Please enter a number between {min_val} and {max_val}")
        except ValueError:
            print("Please enter a valid number")

def main():
    print("=== SNPedia Backup Monitor Setup ===")
    print("\nThis tool will create automatic backups of your SNPedia database")
    print("while the scraper is running.")
    
    # Check if database exists
    if not os.path.exists(DB_PATH):
        print(f"\n⚠️  Warning: Database not found at {DB_PATH}")
        print("Make sure the scraper is running or has created the database.")
        response = input("\nContinue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Exiting...")
            sys.exit(0)
    
    # Strategy selection
    strategies = {
        'rolling': 'Rolling - Keep only N most recent backups (recommended)',
        'progressive': 'Progressive - Smart intervals that increase with database size',
        'all': 'All - Keep every backup (WARNING: ~110GB for full scrape)',
        'hourly': 'Hourly - Time-based backups, keep last 24 hours'
    }
    
    strategy = get_user_choice("Select backup strategy:", strategies, 'rolling')
    
    # Configure based on strategy
    keep_count = 5
    interval = 1000
    
    if strategy == 'rolling':
        keep_count = get_number_input(
            "How many backups to keep?", 
            1, 100, 5
        )
        interval = get_number_input(
            "Create backup every N SNPs:", 
            100, 10000, 1000
        )
        
    elif strategy == 'all':
        print("\n⚠️  WARNING: 'All' strategy will keep EVERY backup!")
        total_backups = 110000 // 1000
        estimated_size = (total_backups * (total_backups + 1) // 2) * 15 // 1024
        print(f"⚠️  Estimated total size for full scrape: ~{estimated_size} GB")
        
        response = input("\nAre you sure you want to keep ALL backups? (y/N): ")
        if response.lower() != 'y':
            print("Returning to strategy selection...")
            return main()
            
        interval = get_number_input(
            "Create backup every N SNPs:", 
            100, 10000, 1000
        )
    
    elif strategy == 'progressive':
        print("\nProgressive strategy will automatically backup at:")
        print("  - Every 1,000 SNPs for first 10k")
        print("  - Every 5,000 SNPs for 10k-50k")
        print("  - Every 10,000 SNPs for 50k+")
        print("\nNo additional configuration needed.")
        
    elif strategy == 'hourly':
        print("\nHourly backups will be created every hour")
        print("and backups older than 24 hours will be removed.")
        print("\nNo additional configuration needed.")
    
    # Summary
    print("\n=== Configuration Summary ===")
    print(f"Strategy: {strategies[strategy].split(' - ')[0]}")
    if strategy in ['all', 'rolling']:
        print(f"Interval: Every {interval:,} SNPs")
    if strategy == 'rolling':
        print(f"Keep: {keep_count} most recent backups")
    
    print(f"\nBackups will be saved to: {BACKUP_DIR}")
    
    response = input("\nStart backup monitoring? (Y/n): ")
    if response.lower() == 'n':
        print("Exiting...")
        sys.exit(0)
    
    # Start monitor
    monitor = BackupMonitor(
        strategy=strategy,
        keep_count=keep_count,
        interval=interval
    )
    
    monitor.run()

if __name__ == "__main__":
    main()
