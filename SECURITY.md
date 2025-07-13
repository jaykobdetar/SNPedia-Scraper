**# Security Policy

## Scope

This is a local web scraper that runs on your machine. Security concerns are minimal but worth noting.

## Security Considerations

### Local Dashboard (port 5000)
- The dashboard uses Flask with CORS restricted to localhost origins
- Read-only access to the database (enforced with `PRAGMA query_only = ON`)
- No authentication required (local use only)
- Security headers are set (X-Content-Type-Options, X-Frame-Options, X-XSS-Protection)

### Database
- SQLite database stores scraped content locally
- No sensitive data is collected or stored
- Backups contain the same public data from SNPedia

### API Interactions
- Uses HTTPS requests to SNPedia's public API (https://bots.snpedia.com/api.php)
- No authentication tokens or credentials required
- User agent identifies the scraper appropriately

## Reporting Security Issues

This tool processes only public data and runs locally. However, if you discover a security concern:

1. Open an issue describing the concern
2. Do not include sensitive details in public issues
3. For critical issues, include "SECURITY:" in the issue title

## Best Practices

- Run the scraper in a Python virtual environment (required on Ubuntu 24.04+)
- Keep dependencies updated: `pip install --upgrade -r requirements.txt`
- Don't expose the dashboard port (5000) to external networks
- Review code before running if downloaded from forks**
