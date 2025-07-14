# dashboard.py
# A comprehensive dashboard for monitoring and managing the SNPedia scraper.

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime, timedelta
from werkzeug.exceptions import HTTPException
import json
import glob
import shutil
import sys
import threading
import time

# --- Path Setup ---
# Use an absolute path to ensure we always find the correct files.
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(PROJECT_ROOT, 'snpedia.db')
BACKUP_DIR = os.path.join(PROJECT_ROOT, 'backups')
BACKUP_CONFIG_PATH = os.path.join(PROJECT_ROOT, 'backup_config.json')

app = Flask(__name__)
# Configure CORS more restrictively
CORS(app, origins=['http://localhost:5000', 'http://127.0.0.1:5000'])

# Security headers
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# Backup Manager Class
class BackupManager:
    def __init__(self):
        self.running = False
        self.thread = None
        self.config = self.load_config()
        self.last_count = 0
        self.last_backup_time = None
        
    def load_config(self):
        """Load backup configuration."""
        default = {"strategy": "rolling", "keep_count": 5, "interval": 1000}
        if os.path.exists(BACKUP_CONFIG_PATH):
            try:
                with open(BACKUP_CONFIG_PATH, 'r') as f:
                    return json.load(f)
            except:
                pass
        return default
    
    def save_config(self, config):
        """Save backup configuration."""
        self.config = config
        with open(BACKUP_CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
    
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
    
    def create_backup(self, count=None):
        """Create a backup of the database."""
        if not os.path.exists(DB_PATH):
            return None
            
        if count is None:
            count = self.get_snp_count()
            
        os.makedirs(BACKUP_DIR, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f'snpedia_backup_{count}_snps_{timestamp}.db'
        backup_path = os.path.join(BACKUP_DIR, backup_name)
        
        try:
            shutil.copy2(DB_PATH, backup_path)
            self.last_backup_time = datetime.now()
            print(f"✓ Backup created: {backup_name}")
            
            # Cleanup based on strategy
            if self.config['strategy'] == 'rolling':
                self.cleanup_backups_rolling()
            elif self.config['strategy'] == 'progressive':
                self.cleanup_backups_progressive(count)
            elif self.config['strategy'] == 'hourly':
                self.cleanup_backups_hourly()
                
            return backup_path
        except Exception as e:
            print(f"✗ Backup failed: {e}")
            return None
    
    def cleanup_backups_rolling(self):
        """Keep only the most recent N backups."""
        backups = sorted(glob.glob(os.path.join(BACKUP_DIR, 'snpedia_backup_*.db')))
        keep_count = self.config.get('keep_count', 5)
        
        if len(backups) > keep_count:
            for old_backup in backups[:-keep_count]:
                os.remove(old_backup)
                print(f"  Removed old backup: {os.path.basename(old_backup)}")
    
    def cleanup_backups_progressive(self, current_count):
        """Keep backups at progressive intervals."""
        backups = glob.glob(os.path.join(BACKUP_DIR, 'snpedia_backup_*.db'))
        
        for backup in backups:
            try:
                parts = os.path.basename(backup).split('_')
                backup_count = int(parts[2])
                
                keep = False
                if backup_count <= 10000:
                    if backup_count % 1000 == 0:
                        keep = True
                elif backup_count <= 50000:
                    if backup_count % 5000 == 0:
                        keep = True
                else:
                    if backup_count % 10000 == 0:
                        keep = True
                
                if backup_count == current_count:
                    keep = True
                
                if not keep:
                    os.remove(backup)
                    print(f"  Removed intermediate backup: {os.path.basename(backup)}")
            except:
                continue
    
    def cleanup_backups_hourly(self):
        """Keep backups from last 24 hours."""
        cutoff_time = time.time() - (24 * 3600)
        backups = glob.glob(os.path.join(BACKUP_DIR, 'snpedia_backup_*.db'))
        
        for backup in backups:
            if os.path.getmtime(backup) < cutoff_time:
                os.remove(backup)
                print(f"  Removed old backup: {os.path.basename(backup)}")
    
    def should_backup(self, current_count):
        """Determine if a backup is needed based on strategy."""
        strategy = self.config['strategy']
        
        if strategy == 'off':
            return False
            
        elif strategy in ['all', 'rolling']:
            interval = self.config.get('interval', 1000)
            return current_count >= self.last_count + interval
            
        elif strategy == 'progressive':
            if current_count <= 10000:
                interval = 1000
            elif current_count <= 50000:
                interval = 5000
            else:
                interval = 10000
            return current_count % interval < (self.last_count % interval)
            
        elif strategy == 'hourly':
            if self.last_backup_time is None:
                return True
            return (datetime.now() - self.last_backup_time).total_seconds() >= 3600
            
        return False
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        print(f"\n✓ Backup monitor started (strategy: {self.config['strategy']})")
        
        while self.running:
            try:
                current_count = self.get_snp_count()
                
                if current_count > 0 and self.should_backup(current_count):
                    self.create_backup(current_count)
                    self.last_count = current_count
                
                # Check every 30 seconds
                time.sleep(30)
                
            except Exception as e:
                print(f"Backup monitor error: {e}")
                time.sleep(60)
    
    def start(self):
        """Start the backup thread."""
        if not self.running and self.config['strategy'] != 'off':
            self.running = True
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()
            return True
        return False
    
    def stop(self):
        """Stop the backup thread."""
        if self.running:
            self.running = False
            print("\n✓ Backup monitor stopped")
            return True
        return False
    
    def is_running(self):
        """Check if backup monitor is running."""
        return self.running and self.thread and self.thread.is_alive()

# Initialize backup manager
backup_manager = BackupManager()

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
            "logs": [{"time": "", "message": "Database not found. Run the scraper to begin."}],
            "status": "not_started",
            "rate": 0,
            "eta_hours": None
        })

    try:
        # Get all core statistics in one efficient query
        stats = conn.execute('''
            SELECT 
                COUNT(*) as count,
                (SELECT rsid FROM snps ORDER BY scraped_at DESC LIMIT 1) as latest_rsid,
                (SELECT scraped_at FROM snps ORDER BY scraped_at DESC LIMIT 1) as latest_time,
                (SELECT MIN(scraped_at) FROM snps) as first_time,
                (SELECT value FROM progress WHERE key = 'snp_count') as progress_count
            FROM snps
        ''').fetchone()
        
        count = stats['count']
        
        # Use progress count if available (more accurate for resume scenarios)
        if stats['progress_count']:
            try:
                progress_count = int(stats['progress_count'])
                # Use the higher of the two (in case of discrepancy)
                count = max(count, progress_count)
            except ValueError:
                pass
        
        # Get recent logs
        log_rows = conn.execute('SELECT rsid, scraped_at FROM snps ORDER BY scraped_at DESC LIMIT 10').fetchall()
        
        logs = [
            {"time": row['scraped_at'].split(' ')[1].split('.')[0], "message": f"Scraped {row['rsid']}"}
            for row in log_rows
        ]
        
        # Calculate scraping rate and ETA
        rate = 0
        eta_hours = None
        scraper_status = "idle"
        
        if stats['latest_time'] and stats['first_time'] and count > 1:
            # Parse timestamps
            latest = datetime.fromisoformat(stats['latest_time'])
            first = datetime.fromisoformat(stats['first_time'])
            
            # Check if scraper is active (last update within 30 seconds)
            time_since_update = (datetime.now() - latest).total_seconds()
            if time_since_update < 30:
                scraper_status = "active"
            elif time_since_update < 300:  # 5 minutes
                scraper_status = "paused"
            else:
                scraper_status = "stopped"
            
            # Calculate rate (SNPs per hour)
            duration_hours = (latest - first).total_seconds() / 3600
            if duration_hours > 0:
                rate = count / duration_hours
                
                # Calculate ETA
                remaining = 110000 - count
                if rate > 0:
                    eta_hours = remaining / rate

        status = {
            "count": count,
            "total": 110000,
            "current": stats['latest_rsid'] if stats['latest_rsid'] else "N/A",
            "logs": logs,
            "status": scraper_status,
            "rate": round(rate, 1),
            "eta_hours": round(eta_hours, 1) if eta_hours else None,
            "last_update": stats['latest_time'] if stats['latest_time'] else None
        }
        
    except Exception as e:
        app.logger.error(f"Database error: {e}")
        return jsonify({
            "count": 0, 
            "total": 110000, 
            "current": "Error",
            "logs": [{"time": "", "message": f"Database error: {str(e)}"}],
            "status": "error",
            "rate": 0,
            "eta_hours": None
        }), 500
    finally:
        if conn:
            conn.close()
            
    return jsonify(status)

@app.route('/stats')
def get_detailed_stats():
    """Get detailed statistics about the scraping progress."""
    conn = get_db_connection()
    
    if conn is None:
        return jsonify({"error": "Database not found"}), 404
    
    try:
        # Get comprehensive stats
        stats = conn.execute('''
            SELECT 
                COUNT(*) as total_snps,
                COUNT(CASE WHEN rsid LIKE 'Rs%' THEN 1 END) as rs_snps,
                COUNT(CASE WHEN rsid LIKE 'I%' THEN 1 END) as i_snps,
                COUNT(CASE WHEN rsid NOT LIKE 'Rs%' AND rsid NOT LIKE 'I%' THEN 1 END) as other_snps,
                AVG(LENGTH(content)) as avg_content_size,
                MIN(LENGTH(content)) as min_content_size,
                MAX(LENGTH(content)) as max_content_size,
                COUNT(CASE WHEN LENGTH(content) < 100 THEN 1 END) as small_entries,
                MIN(scraped_at) as first_scrape,
                MAX(scraped_at) as last_scrape
            FROM snps
        ''').fetchone()
        
        # Calculate database size
        db_size_mb = os.path.getsize(DB_PATH) / (1024 * 1024) if os.path.exists(DB_PATH) else 0
        
        # Get hourly rate for last 24 hours
        hourly_stats = conn.execute('''
            SELECT 
                strftime('%Y-%m-%d %H:00', scraped_at) as hour,
                COUNT(*) as count
            FROM snps 
            WHERE scraped_at > datetime('now', '-24 hours')
            GROUP BY hour
            ORDER BY hour DESC
        ''').fetchall()
        
        result = {
            "total_snps": stats['total_snps'],
            "breakdown": {
                "rs_snps": stats['rs_snps'],
                "i_snps": stats['i_snps'],
                "other_snps": stats['other_snps']
            },
            "content_stats": {
                "average_size": round(stats['avg_content_size'], 0) if stats['avg_content_size'] else 0,
                "min_size": stats['min_content_size'],
                "max_size": stats['max_content_size'],
                "small_entries": stats['small_entries']
            },
            "time_stats": {
                "first_scrape": stats['first_scrape'],
                "last_scrape": stats['last_scrape']
            },
            "database_size_mb": round(db_size_mb, 1),
            "hourly_progress": [
                {"hour": row['hour'], "count": row['count']} 
                for row in hourly_stats
            ]
        }
        
    except Exception as e:
        app.logger.error(f"Stats error: {e}")
        return jsonify({"error": "Failed to get statistics"}), 500
    finally:
        if conn:
            conn.close()
    
    return jsonify(result)

@app.route('/backup/status')
def get_backup_status():
    """Get current backup system status."""
    try:
        # Get backup list
        backups = []
        if os.path.exists(BACKUP_DIR):
            for backup_file in sorted(glob.glob(os.path.join(BACKUP_DIR, 'snpedia_backup_*.db')), reverse=True):
                stat = os.stat(backup_file)
                basename = os.path.basename(backup_file)
                # Extract SNP count from filename
                try:
                    parts = basename.split('_')
                    snp_count = int(parts[2])
                except:
                    snp_count = 0
                
                backups.append({
                    "filename": basename,
                    "size_mb": round(stat.st_size / (1024 * 1024), 1),
                    "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "snp_count": snp_count
                })
        
        # Calculate total backup size
        total_size_mb = sum(b['size_mb'] for b in backups)
        
        return jsonify({
            "monitor_running": backup_manager.is_running(),
            "config": backup_manager.config,
            "backups": backups[:10],  # Last 10 backups
            "total_backups": len(backups),
            "total_size_mb": round(total_size_mb, 1)
        })
        
    except Exception as e:
        app.logger.error(f"Backup status error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/backup/create', methods=['POST'])
def create_backup():
    """Manually create a backup."""
    if not os.path.exists(DB_PATH):
        return jsonify({"error": "Database not found"}), 404
    
    try:
        count = backup_manager.get_snp_count()
        backup_path = backup_manager.create_backup(count)
        
        if backup_path:
            return jsonify({
                "success": True,
                "backup_name": os.path.basename(backup_path),
                "size_mb": round(os.path.getsize(backup_path) / (1024 * 1024), 1),
                "snp_count": count
            })
        else:
            return jsonify({"error": "Backup creation failed"}), 500
            
    except Exception as e:
        app.logger.error(f"Backup creation error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/backup/config', methods=['POST'])
def update_backup_config():
    """Update backup configuration."""
    try:
        data = request.get_json()
        
        # Validate config
        valid_strategies = ['rolling', 'progressive', 'hourly', 'all', 'off']
        if data.get('strategy') not in valid_strategies:
            return jsonify({"error": "Invalid strategy"}), 400
        
        # Stop monitor if running
        was_running = backup_manager.is_running()
        if was_running:
            backup_manager.stop()
        
        # Save new config
        backup_manager.save_config(data)
        
        # Restart monitor if it was running and strategy isn't 'off'
        if was_running and data.get('strategy') != 'off':
            backup_manager.start()
        
        return jsonify({"success": True, "config": data})
        
    except Exception as e:
        app.logger.error(f"Config update error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/backup/delete/<filename>', methods=['DELETE'])
def delete_backup(filename):
    """Delete a specific backup."""
    # Sanitize filename to prevent directory traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({"error": "Invalid filename"}), 400
    
    backup_path = os.path.join(BACKUP_DIR, filename)
    
    if not os.path.exists(backup_path):
        return jsonify({"error": "Backup not found"}), 404
    
    try:
        os.remove(backup_path)
        return jsonify({"success": True})
    except Exception as e:
        app.logger.error(f"Backup deletion error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/backup/monitor/start', methods=['POST'])
def start_backup_monitor():
    """Start the backup monitor."""
    try:
        if backup_manager.start():
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Monitor already running or strategy is 'off'"}), 400
            
    except Exception as e:
        app.logger.error(f"Monitor start error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/backup/monitor/stop', methods=['POST'])
def stop_backup_monitor():
    """Stop the backup monitor."""
    try:
        if backup_manager.stop():
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Monitor not running"}), 400
            
    except Exception as e:
        app.logger.error(f"Monitor stop error: {e}")
        return jsonify({"error": str(e)}), 500

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
    import logging
    
    # Suppress Flask's default logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    # Check for --verbose flag
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    
    if verbose:
        log.setLevel(logging.INFO)
        print("Running in verbose mode - showing all requests")
    
    # Clear the console and show clean startup message
    print("\033[2J\033[H")  # Clear screen
    print("=" * 60)
    print("🧬 SNPedia Scraper Dashboard")
    print("=" * 60)
    print(f"\n✅ Dashboard running at: http://localhost:5000\n")
    print("📊 Updates every 3 seconds to match scraper timing")
    print("💾 Backup monitor integrated - configure in dashboard")
    print("❌ Press Ctrl+C to stop\n")
    
    if not verbose:
        print("💡 Tip: Run with --verbose to see request logs\n")
    
    print("=" * 60 + "\n")
    
    # Start backup monitor if configured to run on startup
    if os.path.exists(BACKUP_CONFIG_PATH):
        config = backup_manager.load_config()
        if config.get('strategy') != 'off':
            backup_manager.start()
    
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
