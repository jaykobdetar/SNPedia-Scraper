<img width="878" height="860" alt="image" src="https://github.com/user-attachments/assets/d098aba2-12f8-447c-95d6-e49a1a5d0c1c" />
Get the most recent scrape here: https://zenodo.org/records/16053572 or here https://mega.nz/file/inQBACgT#q9hbymmFIQmc7n0MGyP96v5KjFhGtwvReKHOXnZsRMY or the releases section of this repo.
# SNPedia Scraper

A comprehensive tool for scraping genetic variant data from [SNPedia.com](https://www.snpedia.com), featuring a powerful web dashboard with integrated backup management, real-time monitoring, and robust error recovery.

## Features

### Core Functionality
- **Resume-capable scraping**: Automatically saves progress every 10 SNPs
- **Respectful rate limiting**: 3-second delays between requests (respects robots.txt)
- **Error recovery**: Logs failed SNPs for later recovery
- **SQLite storage**: Efficient local database with ~160MB final size

### Web Dashboard
- **Real-time monitoring**: Live progress updates every 3 seconds
- **Integrated backup system**: No separate scripts needed
- **Debug information**: Data quality checks and performance metrics
- **Status indicators**: Visual feedback for scraper and backup status

### Backup Management
- **Multiple strategies**:
  - Rolling: Keep last N backups
  - Progressive: Smart intervals (1k/5k/10k SNPs)
  - Hourly: Time-based backups
  - All: Keep everything (warning: requires significant disk space)
- **Automatic monitoring**: Runs in background with configurable intervals
- **Manual controls**: Create, delete, and manage backups from the UI

## Quick Start

### Prerequisites
- Python 3.6+
- ~200-300MB free disk space
- Virtual environment recommended (required on Ubuntu 24.04+ due to PEP 668)

### Installation

1. Clone the repository
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Usage

#### 1. Start the Dashboard
```bash
python dashboard.py
```
Open http://localhost:5000 in your browser

For verbose logging:
```bash
python dashboard.py --verbose
```

#### 2. Start the Scraper (in a separate terminal)
```bash
python src/snpedia_scraper.py
```

The dashboard will automatically:
- Monitor scraping progress
- Handle backups based on your configuration
- Show real-time statistics
- Start the backup monitor if configured

## Dashboard Features

### Main View
- SNP count and progress percentage
- Current scraping rate (SNPs/hour)
- Estimated time remaining
- Recent activity log (last 10 SNPs)
- Visual status indicators (active/paused/stopped)

### Debug Information
Click "Show Debug Info" to see:
- SNP type breakdown (Rs, I, Other)
- Data quality metrics
- Storage statistics and projections
- Timing analysis with stall detection

### Backup Management
- Configure backup strategy and intervals
- Start/stop automatic backup monitor
- Create manual backups instantly
- Delete individual backups
- View backup statistics (count, total size, average size)


## Error Recovery

If SNPs fail to scrape, they're automatically logged to `scraper_errors.log`. To recover:

```bash
python error_recover.py
```

This will:
1. Parse the error log
2. Check which SNPs are missing from database
3. Attempt to recover them
4. Report results and save any failures

## Database Schema

### `snps` table
- `rsid` (TEXT PRIMARY KEY): SNP identifier
- `content` (TEXT): Raw wiki content
- `scraped_at` (TIMESTAMP): When the SNP was scraped

### `progress` table
- `key` (TEXT PRIMARY KEY): Progress key (cmcontinue, snp_count)
- `value` (TEXT): Progress value for resumption

## File Structure

```
SNPedia-Scraper/
├── src/
│   └── snpedia_scraper.py    # Main scraper script
├── dashboard.py               # Web dashboard with backup manager
├── index.html                 # Dashboard frontend
├── error_recover.py           # Error recovery tool
├── requirements.txt           # Python dependencies
├── snpedia.db                # SQLite database (created on first run)
├── backup_config.json         # Backup settings (created by dashboard)
├── scraper_errors.log         # Error log (created when errors occur)
└── backups/                   # Backup directory (created when needed)
```

## Configuration Files

- `backup_config.json`: Stores backup strategy settings
- `scraper_errors.log`: Logs failed SNPs with error details

## Tips for Long-Running Scrapes

1. **Use `screen` or `tmux`** for the scraper process to prevent disconnection
2. **Configure backups** before starting (Progressive strategy recommended)
3. **Monitor via dashboard** - accessible from any browser on the machine
4. **Check disk space** - ensure adequate space for database and backups
5. **Network stability** - Use wired connection if possible for 90+ hour scrape

## Data Information

### SNP Types
- **Rs SNPs**: Standard reference SNPs (majority of entries)
- **I SNPs**: 23andMe internal identifiers (minimal wiki content)
- **Other**: Special entries (genes, OMIM references)

### Expected Data
- ~110,000 total SNPs in SNPedia
- Average content size: ~1KB per SNP
- Small entries (<100 chars): Mostly 23andMe mappings

## Troubleshooting

- **Dashboard won't start**: Check if port 5000 is available
- **Scraper seems stuck**: Check dashboard debug info for last update time
- **502 errors**: SNPedia server issues - scraper will retry automatically
- **Backup failures**: Check disk space and write permissions
- **Can't see dashboard**: Ensure you're accessing http://localhost:5000

## Common Issues

- **Import errors**: Activate virtual environment before running
- **Database locked**: Ensure only one scraper instance is running
- **High memory usage**: Normal for large databases, close other applications

## Ethical Considerations

- This scraper respects SNPedia's robots.txt with mandatory 3-second delays
- SNPedia content is licensed under CC-BY-NC-SA 3.0
- Consider supporting [SNPedia/Promethease](https://www.snpedia.com/index.php/SNPedia:General_disclaimer) if you find the data useful
- For research use, ensure compliance with your institution's policies

## Contributing

This project is designed for personal research and education. Please ensure any contributions maintain respect for SNPedia's terms of service and rate limits. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

**Important**: The scraped data remains under SNPedia's CC-BY-NC-SA 3.0 license. This means:
- You must give appropriate credit to SNPedia
- Non-commercial use only
- Share-alike under the same license

## Disclaimer

This tool is for educational and research purposes. Users are responsible for:
- Complying with SNPedia's terms of service
- Respecting the CC-BY-NC-SA license for scraped data
- Following applicable laws and regulations
- Using the data ethically and responsibly
<img width="1100" height="854" alt="image" src="https://github.com/user-attachments/assets/3e2e6951-5230-4f1a-86a4-5b782923c940" />
