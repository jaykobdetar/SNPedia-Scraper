# Contributing to SNPedia Scraper

Thank you for your interest in contributing to SNPedia Scraper! This document provides guidelines for contributing to the project.

## Code of Conduct

This project is intended for educational and research purposes. All contributors must:

- Respect SNPedia's terms of service and rate limits
- Follow ethical scraping practices
- Ensure contributions maintain the 3-second delay between requests
- Not modify the scraper to bypass or ignore robots.txt

## Getting Started

1. Fork the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate it: `source venv/bin/activate` (or `venv\Scripts\activate` on Windows)
4. Install dependencies: `pip install -r requirements.txt`

## Making Changes

### Code Style
- Follow PEP 8 Python style guidelines
- Use meaningful variable and function names
- Add comments for complex logic
- Maintain the existing code structure

### Testing
- Test your changes with all three interfaces (CLI, GUI, web)
- Ensure the scraper can resume from interruption
- Verify rate limiting is maintained (3-second delays)

### Documentation
- Update README.md if adding new features
- Update CLAUDE.md for architectural changes
- Include docstrings for new functions/classes

## Submitting Changes

1. Create a descriptive branch name: `feature/your-feature-name`
2. Make your changes in small, logical commits
3. Test thoroughly
4. Submit a pull request with:
   - Clear description of changes
   - Why the change is needed
   - Any potential impacts

## What We're Looking For

### Welcome Contributions
- Bug fixes
- Performance improvements
- Better error handling
- Documentation improvements
- Code cleanup and refactoring
- Additional monitoring/logging features

### Please Avoid
- Changes that increase request rate or bypass delays
- Modifications that violate SNPedia's robots.txt
- Features that could be used to overwhelm SNPedia's servers
- Breaking changes without discussion

## Questions?

If you have questions about contributing, please open an issue for discussion before starting work on major changes.

## Legal Considerations

By contributing, you agree that:
- Your contributions will be licensed under the MIT License
- You understand that scraped data remains under SNPedia's CC-BY-NC-SA license
- You will not contribute code that violates SNPedia's terms of service