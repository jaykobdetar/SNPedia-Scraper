# Security Policy

## Scope

This is a local web scraper with an integrated dashboard that runs on your machine. Security concerns are minimal but worth noting.

## Security Considerations

### Web Dashboard (port 5000)
- Flask application with CORS restricted to localhost origins only
- Read-only database access enforced with `PRAGMA query_only = ON`
- No authentication required (local use only)
- Security headers implemented:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`
  - Cache control headers to prevent stale data

### Database
- SQLite database stores scraped content locally
- No sensitive data is collected or stored
- Backups contain the same public data from SNPedia
- Write operations limited to scraper and backup functions

### Backup System
- Integrated backup manager runs in the dashboard process
- File operations sanitized to prevent directory traversal
- Backup deletion requires user confirmation in UI
- Configuration stored in local JSON file

### API Interactions
- Uses HTTPS requests to SNPedia's public API (https://bots.snpedia.com/api.php)
- No authentication tokens or credentials required
- User agent identifies the scraper appropriately
- 3-second delay enforced between requests

## Security Best Practices

### For Users
- Run in a Python virtual environment (required on Ubuntu 24.04+)
- Keep dependencies updated: `pip install --upgrade -r requirements.txt`
- Don't expose port 5000 to external networks
- Review code before running if downloaded from forks
- Ensure adequate disk space for backups

### For the Dashboard
- Only accessible on localhost (127.0.0.1)
- No user input is executed as code
- File paths are sanitized in backup operations
- React frontend uses production builds

## Reporting Security Issues

This tool processes only public data and runs locally. However, if you discover a security concern:

1. Open an issue describing the concern
2. Do not include sensitive details in public issues
3. For critical issues, include "SECURITY:" in the issue title

## Dependencies

Current dependencies and their purposes:
- `flask`: Web dashboard framework
- `flask-cors`: CORS handling (restricted to localhost)
- `requests`: HTTP client for SNPedia API
- Frontend uses React 18 from unpkg CDN

## Known Limitations

- No authentication system (by design - local use only)
- No HTTPS for dashboard (unnecessary for localhost)
- Backup files are not encrypted (contain only public data)
