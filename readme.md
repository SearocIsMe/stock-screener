# Stock Screener

A comprehensive stock screening application that filters stocks based on technical indicators.

## Features

- Fetch stock data from Yahoo Finance API
- Calculate technical indicators (BIAS, RSI, MACD)
- Filter stocks based on predefined criteria
- Store filtered results in PostgreSQL and Redis
- RESTful API for accessing filtered stocks

## Technical Stack

- **Backend**: Python
- **Database**: PostgreSQL, Redis
- **Data Source**: Yahoo Finance (via yfinance)
- **API Framework**: FastAPI

## Getting Started

### Prerequisites

- Python 3.8 or higher
- PostgreSQL 12 or higher
- Redis 6.0 or higher

### Installation and Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/stock-screener.git
   cd stock-screener
   ```

2. Set up PostgreSQL and Redis (see [Database Setup](README_DB_SETUP.md) for detailed instructions):
   ```bash
   # For WSL users
   sudo apt update
   sudo apt install postgresql postgresql-contrib redis-server
   sudo service postgresql start
   sudo service redis-server start
   ```

3. Run the database setup script:
   ```bash
   ./setup_db.sh
   ```

4. Start the application:
   ```bash
   python run.py
   ```

5. Access the API at http://localhost:8000

For detailed setup instructions, especially for WSL users, see [Database Setup](README_DB_SETUP.md).

## Configuration

The application configuration is stored in `config/config.yaml`. You can modify this file to adjust:

- Database connection parameters
- API settings
- Data fetching parameters
- Technical indicator parameters

## Usage

### API Endpoints

- `GET /api/stocks`: Get all stocks
- `GET /api/stocks/{symbol}`: Get a specific stock
- `GET /api/filter`: Get filtered stocks
- `POST /api/filter`: Filter stocks based on parameters

### Example API Request

```bash
curl -X POST "http://localhost:8000/api/filter" \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["all"], "time_frames": ["daily", "weekly", "monthly"]}'
```

## Project Structure

```
stock-screener/
├── config/
│   └── config.yaml         # Configuration file
├── src/
│   ├── api/                # API endpoints
│   ├── data/               # Data acquisition and storage
│   ├── filters/            # Stock filtering logic
│   ├── indicators/         # Technical indicators
│   └── utils/              # Utility functions
├── init_db.sql             # SQL initialization script
├── setup_db.sh             # Database setup script
├── run.py                  # Application entry point
└── README.md               # This file
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.