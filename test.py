#!/usr/bin/env python3
"""
Analyze SNPedia scraping progress and data quality.
"""

import sqlite3
import os
from datetime import datetime, timedelta
from collections import Counter

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(PROJECT_ROOT, 'snpedia.db')

def analyze_database():
    """Comprehensive analysis of the scraped data."""
    
    if not os.path.exists(DB_PATH):
        print("❌ Database not found!")
        return
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    print("=== SNPedia Scraping Analysis ===\n")
    
    # Basic stats
    total_snps = conn.execute('SELECT COUNT(*) FROM snps').fetchone()[0]
    print(f"📊 Total SNPs scraped: {total_snps:,}")
    
    # Time analysis
    first = conn.execute('SELECT MIN(scraped_at) FROM snps').fetchone()[0]
    last = conn.execute('SELECT MAX(scraped_at) FROM snps').fetchone()[0]
    
    if first and last:
        first_time = datetime.fromisoformat(first)
        last_time = datetime.fromisoformat(last)
        duration = last_time - first_time
        
        print(f"⏱️  First scrape: {first_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  Last scrape: {last_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  Duration: {duration.days}d {duration.seconds//3600}h {(duration.seconds//60)%60}m")
        
        if total_snps > 1:
            avg_time = duration.total_seconds() / (total_snps - 1)
            print(f"⏱️  Average time per SNP: {avg_time:.1f} seconds")
    
    # Progress estimation
    estimated_total = 110000
    progress = (total_snps / estimated_total) * 100
    print(f"\n📈 Progress: {progress:.1f}% ({total_snps:,} / {estimated_total:,})")
    
    if total_snps > 0 and progress < 100:
        remaining = estimated_total - total_snps
        if total_snps > 1 and last_time and first_time:
            avg_time = (last_time - first_time).total_seconds() / (total_snps - 1)
            eta_seconds = remaining * avg_time
            eta = timedelta(seconds=int(eta_seconds))
            print(f"⏳ Estimated time remaining: {eta.days}d {eta.seconds//3600}h")
    
    # Content analysis
    print("\n📄 Content Analysis:")
    
    # Check for empty content
    empty = conn.execute('SELECT COUNT(*) FROM snps WHERE content = "" OR content IS NULL').fetchone()[0]
    if empty > 0:
        print(f"  ⚠️  Empty content: {empty} SNPs")
    
    # Content size distribution
    sizes = conn.execute('''
        SELECT 
            COUNT(CASE WHEN LENGTH(content) < 100 THEN 1 END) as tiny,
            COUNT(CASE WHEN LENGTH(content) BETWEEN 100 AND 1000 THEN 1 END) as small,
            COUNT(CASE WHEN LENGTH(content) BETWEEN 1000 AND 5000 THEN 1 END) as medium,
            COUNT(CASE WHEN LENGTH(content) > 5000 THEN 1 END) as large,
            AVG(LENGTH(content)) as avg_size,
            MIN(LENGTH(content)) as min_size,
            MAX(LENGTH(content)) as max_size
        FROM snps
    ''').fetchone()
    
    print(f"  📏 Average content size: {sizes['avg_size']:.0f} characters")
    print(f"  📏 Range: {sizes['min_size']} - {sizes['max_size']:,} characters")
    print(f"  📊 Distribution:")
    print(f"     <100 chars: {sizes['tiny']:,} SNPs")
    print(f"     100-1K: {sizes['small']:,} SNPs")
    print(f"     1K-5K: {sizes['medium']:,} SNPs")
    print(f"     >5K: {sizes['large']:,} SNPs")
    
    # Potential issues
    if sizes['tiny'] > 0:
        print(f"\n⚠️  Found {sizes['tiny']} SNPs with suspiciously small content (<100 chars)")
        tiny_examples = conn.execute('''
            SELECT rsid, LENGTH(content) as size 
            FROM snps 
            WHERE LENGTH(content) < 100 
            LIMIT 5
        ''').fetchall()
        for row in tiny_examples:
            print(f"     - {row['rsid']}: {row['size']} chars")
    
    # Database size
    db_size = os.path.getsize(DB_PATH) / (1024 * 1024)
    print(f"\n💾 Database size: {db_size:.1f} MB")
    if total_snps > 0:
        print(f"💾 Average per SNP: {db_size * 1024 / total_snps:.1f} KB")
    
    # Recent activity
    print("\n📅 Recent Activity (last 10 entries):")
    recent = conn.execute('''
        SELECT rsid, scraped_at, LENGTH(content) as size
        FROM snps 
        ORDER BY scraped_at DESC 
        LIMIT 10
    ''').fetchall()
    
    for row in recent:
        time_str = row['scraped_at'].split('.')[0]  # Remove microseconds
        print(f"  {time_str} - {row['rsid']} ({row['size']:,} chars)")
    
    conn.close()
    
    # Analyze backups
    analyze_backups()
    
    print("\n" + "="*40)

def analyze_backups():
    """Analyze backup files if they exist."""
    backup_dir = os.path.join(PROJECT_ROOT, 'backups')
    
    if not os.path.exists(backup_dir):
        return
    
    backups = sorted(glob.glob(os.path.join(backup_dir, 'snpedia_backup_*.db')))
    
    if not backups:
        return
    
    print("\n💾 Backup Analysis:")
    print(f"  Total backups: {len(backups)}")
    
    # Calculate total size
    total_size = sum(os.path.getsize(f) for f in backups)
    print(f"  Total backup size: {total_size / (1024**3):.2f} GB")
    
    # Show backup progression
    print("\n  Backup progression:")
    for i, backup in enumerate(backups[-5:]):  # Show last 5
        try:
            # Extract SNP count from filename
            parts = os.path.basename(backup).split('_')
            snp_count = int(parts[2])
            size_mb = os.path.getsize(backup) / (1024**2)
            
            # Get timestamp
            timestamp = '_'.join(parts[4:]).replace('.db', '')
            
            print(f"    {snp_count:6,} SNPs - {size_mb:6.1f} MB - {timestamp}")
        except:
            continue
    
    if len(backups) > 5:
        print(f"    ... and {len(backups) - 5} more backups")

if __name__ == "__main__":
    import glob
    analyze_database()
