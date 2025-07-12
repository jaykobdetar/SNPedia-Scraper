# SNPedia Scraper

A comprehensive tool for scraping genetic variant data from [SNPedia.com](https://www.snpedia.com), with multiple user interfaces and robust resume capabilities.

## Features

- **Multiple Interfaces**: Command-line, GUI, and web-based interfaces
- **Resume Capability**: Automatically saves progress every 10 SNPs
- **Respectful Scraping**: 3-second delays between requests to honor robots.txt
- **SQLite Storage**: Efficient local database storage
- **Progress Monitoring**: Real-time progress tracking and logging

## Quick Start

### Prerequisites

- Python 3.6+
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

#### Command Line Interface
```bash
python src/snpedia_scraper.py
```

#### GUI Application
```bash
python src/gui.py
```

#### Web Interface
```bash
python backend.py
```
Then open http://localhost:5000 in your browser.

## Performance

- **Full scrape time**: ~90-100 hours for ~110,000 SNPs
- **Database size**: ~1-2GB when complete
- **Rate limit**: 3 seconds per request (respects robots.txt)

## Monitoring Progress

```bash
# Check current progress
sqlite3 snpedia.db "SELECT COUNT(*) FROM snps;"

# View recent entries
sqlite3 snpedia.db "SELECT rsid, scraped_at FROM snps ORDER BY scraped_at DESC LIMIT 10;"
```

## Building Distribution

### Linux AppImage
```bash
./build_appimage.sh
```

## Database Schema

### `snps` table
- `rsid` (TEXT PRIMARY KEY): SNP identifier
- `content` (TEXT): Raw wiki content
- `scraped_at` (TIMESTAMP): When the SNP was scraped

### `progress` table
- `key` (TEXT PRIMARY KEY): Progress key
- `value` (TEXT): Progress value for resumption

## Ethical Considerations

- This scraper respects SNPedia's robots.txt with 3-second delays
- SNPedia content is licensed under CC-BY-NC-SA
- Consider supporting [SNPedia/Promethease](https://www.snpedia.com/index.php/Donate) if you find the data useful

## Common Issues

- **Long-running process**: Use `screen` or `tmux` for background execution
- **Virtual environment**: Required on Ubuntu 24.04+ due to PEP 668
- **Database growth**: Ensure adequate disk space (~2GB)

## Contributing

This project is designed for personal research and education. Please ensure any contributions maintain respect for SNPedia's terms of service and rate limits.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for educational and research purposes. Users are responsible for complying with SNPedia's terms of service and applicable laws. The scraped data retains SNPedia's CC-BY-NC-SA licensing.