# DomainSnipe - Expiring Domain Sniper Bot

A powerful bot that automatically scans expiring domains, analyzes their value using SEO metrics and AI-powered brandability scoring, and registers high-value "gem" domains before they're taken.

## Features

- **Domain Scanner**: Fetches pending delete lists from multiple registrars and sources
- **SEO Analysis**: Checks Domain Authority, backlink quality, and referring domains
- **AI Brandability Scoring**: Uses Claude LLM to score domain brandability and industry fit
- **Automated Registration**: Fires off registration requests using multiple registrar APIs
- **Value Estimation**: Calculates potential ROI and estimated resale value
- **Rich CLI Interface**: Beautiful command-line interface with progress indicators and reports

## The Profit Model

Register valuable domains for ~$10 and flip them at auction for $2,000 - $10,000+ to SEO agencies or new companies. The bot identifies domains with:
- High Domain Authority (SEO value)
- Quality backlink profiles
- Strong brandability scores
- Aged domain history

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/domainsnipe.git
cd domainsnipe

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

## Configuration

1. Copy the environment template:
```bash
cp .env.example .env
```

2. Fill in your API keys in `.env`:
```bash
# SEO Analysis (optional - falls back to simulation)
MOZ_ACCESS_ID=your_moz_access_id
MOZ_SECRET_KEY=your_moz_secret_key

# LLM for Brandability (optional - uses heuristics if not set)
ANTHROPIC_API_KEY=your_anthropic_api_key

# Domain Registrars (for actual registration)
GODADDY_API_KEY=your_godaddy_api_key
GODADDY_API_SECRET=your_godaddy_api_secret
NAMECHEAP_API_USER=your_namecheap_api_user
NAMECHEAP_API_KEY=your_namecheap_api_key
NAMECHEAP_USERNAME=your_namecheap_username
```

## Usage

### Scan for Expiring Domains

```bash
# Scan and analyze 50 expiring domains
domainsnipe scan --count 50

# Save results to JSON
domainsnipe scan --count 100 --output results.json
```

### Find Gem Domains

```bash
# Find high-value "gem" domains
domainsnipe gems --count 100
```

### Analyze a Specific Domain

```bash
# Get detailed analysis of any domain
domainsnipe analyze fastcar.com
```

### Auto-Snipe Mode

```bash
# Dry run - see what would be registered
domainsnipe autosnipe --dry-run --count 100

# Live mode (requires auto_register=True in config)
domainsnipe autosnipe --count 100
```

### Generate Reports

```bash
# Generate comprehensive analysis report
domainsnipe report
```

### View Configuration

```bash
# Display current settings
domainsnipe config-info
```

## How It Works

1. **Scan Phase**: The bot fetches pending delete lists from multiple sources (expireddomains.net, registrar APIs, etc.) and filters domains by TLD, length, age, and spam patterns.

2. **Analysis Phase**: For each domain:
   - Checks SEO metrics (Domain Authority, Domain Rating, backlink count)
   - Evaluates backlink quality (spam detection)
   - Runs AI brandability analysis (memorability, pronounceability, industry fit)
   - Calculates composite score and estimated value

3. **Snipe Phase**: When a "gem" is found (score >= 60 or DA >= 40 with good brandability):
   - Verifies availability across multiple registrars
   - Fires rapid registration requests
   - Retries with exponential backoff
   - Logs results and confirmation IDs

## Project Structure

```
domainsnipe/
├── src/domainsnipe/
│   ├── __init__.py          # Package initialization
│   ├── cli.py               # Command-line interface
│   ├── config.py            # Configuration management
│   ├── models.py            # Data models (Pydantic)
│   ├── scanner.py           # Domain scanning logic
│   ├── analyzer.py          # SEO and brandability analysis
│   ├── sniper.py            # Registration automation
│   └── orchestrator.py      # Main coordination logic
├── .env.example             # Environment template
├── .gitignore               # Git ignore rules
├── pyproject.toml           # Project configuration
├── requirements.txt         # Dependencies
└── README.md               # This file
```

## Safety Features

- **Daily Registration Limits**: Configurable cap on registrations per day
- **Cost Thresholds**: Maximum spend per domain
- **ROI Requirements**: Minimum profit margin before auto-registering
- **Spam Filtering**: Automatic detection and filtering of spam/low-quality domains
- **Dry Run Mode**: Test the system without making purchases
- **Auto-Register Toggle**: Disabled by default for safety

## Scoring System

Domains are scored on a 0-100 scale:
- **SEO Score** (40% weight): Based on DA, DR, and backlink quality
- **Brandability** (30% weight): LLM analysis of name quality
- **Domain Age** (20% weight): Older domains score higher
- **TLD Premium** (10% weight): .com scores highest

A domain is marked as a "gem" if:
- Total score >= 60, OR
- DA >= 40 AND brandability >= 7, OR
- Age >= 10 years AND DA >= 30

## Estimated Values

- Score 80+: $5,000 - $10,000+
- Score 60-80: $1,000 - $5,000
- Score 40-60: $200 - $1,000
- Score <40: Under $200

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## Disclaimer

This tool is for educational and research purposes. Domain investing carries financial risk. Always verify domain availability and value estimates independently before making purchases. The bot uses simulated data when real APIs are not configured.

## License

MIT License
