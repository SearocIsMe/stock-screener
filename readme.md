# Screening the Stocks for Trading

A backend solution for a stock screening tool based on BIAS indicators and other technical analysis metrics.

## Overview

This application provides a comprehensive stock screening solution with the following features:

- Data acquisition from yfinance API for US stock markets (SP500, NASDAQ, NYSE)
- Technical indicator calculations (EMA, BIAS, RSI, MACD)
- Stock filtering based on technical indicators
- RESTful API for accessing the functionality
- Data storage in PostgreSQL and Redis

## Project Structure

```
stock-screener/
├── config/
│   └── config.yaml         # Configuration file
├── src/
│   ├── api/                # API endpoints
│   │   ├── __init__.py
│   │   └── routes.py       # API routes
│   ├── data/               # Data acquisition and storage
│   │   ├── __init__.py
│   │   ├── acquisition.py  # Data fetching
│   │   ├── database.py     # Database connection
│   │   ├── init_db.py      # Database initialization
│   │   └── models.py       # Database models
│   ├── filters/            # Stock filtering
│   │   ├── __init__.py
│   │   └── stock_filter.py # Stock filtering logic
│   ├── indicators/         # Technical indicators
│   │   ├── __init__.py
│   │   └── technical.py    # Technical indicator calculations
│   └── __init__.py
├── docker-compose.yml      # Docker Compose configuration
├── example.py              # Example usage script
├── main.py                 # Application entry point
├── run.py                  # Script to run the API server
├── requirements.txt        # Dependencies
└── readme.md               # This file
```

## Requirements

- Python 3.8+
- PostgreSQL
- Redis
- Dependencies listed in requirements.txt

## Installation

### Using Docker Compose (Recommended)

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/stock-screener.git
   cd stock-screener
   ```

2. Start PostgreSQL and Redis using Docker Compose:
   ```
   docker-compose up -d
   ```

3. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Configure the application:
   - Edit `config/config.yaml` to set your database credentials and other settings
   - The default configuration works with the Docker Compose setup

5. Initialize the database and run the API server:
   ```
   python run.py
   ```

### Manual Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/stock-screener.git
   cd stock-screener
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Install and configure PostgreSQL and Redis:
   - Install PostgreSQL and Redis on your system
   - Create a PostgreSQL database named `stock_screener`
   - Configure Redis to run on the default port

4. Configure the application:
   - Edit `config/config.yaml` to set your database credentials and other settings

5. Initialize the database:
   ```
   python -m src.data.init_db
   ```

6. Run the application:
   ```
   python run.py
   ```

## Usage

### Running the API Server

To start the API server:

```
python run.py
```

The API will be available at `http://localhost:8000/api/`.

### Example Script

An example script is provided to demonstrate how to use the stock screening tool programmatically:

```
python example.py
```

This script demonstrates:
1. Initializing the database
2. Fetching stock symbols
3. Fetching historical data
4. Filtering stocks based on technical indicators
5. Retrieving filtered stocks from Redis

## API Endpoints

### 1. Trigger Fetch and Filtering

Fetches stock data and filters based on technical indicators.

- **URL**: `/api/trigger_fetch_filtering`
- **Method**: POST
- **Request Body**:
  ```json
  {
    "symbols": ["AAPL", "MSFT"],
    "timeFrame": ["daily", "weekly"]
  }
  ```
  - `symbols`: Array of stock symbols or "all" for all stocks
  - `timeFrame`: Array of time frames ("daily", "weekly", "monthly")

### 2. Retrieve Filtered Stocks

Retrieves stocks that have been filtered and stored in Redis.

- **URL**: `/api/retrieve_filtered_stocks`
- **Method**: POST
- **Request Body**:
  ```json
  {
    "timeFrame": ["daily", "weekly"],
    "recentDay": 1
  }
  ```
  - `timeFrame`: Array of time frames ("daily", "weekly", "monthly")
  - `recentDay`: Number of recent days (0 for today, 1 for yesterday, etc.)

### 3. Fetch Stock History

Fetches historical stock data for specified symbols.

- **URL**: `/api/fetch_stock_history`
- **Method**: POST
- **Request Body**:
  ```json
  {
    "symbols": ["AAPL", "MSFT"],
    "timeRange": {
      "start": "2023-01-01T00:00:00Z",
      "end": "2023-12-31T23:59:59Z"
    }
  }
  ```
  - `symbols`: Array of stock symbols or "all" for all stocks
  - `timeRange`: Optional time range with start and end dates

## Technical Indicators

### BIAS Indicator

The BIAS indicator is calculated as:
```
BIAS = (Price - EMA) / EMA * 100
```

Where:
- Price is the closing price
- EMA is the Exponential Moving Average (default period: 13)

### Filtering Criteria

Stocks are filtered based on the following criteria:

1. BIAS value below the threshold (default: -10)
2. RSI value in the oversold region (default: below 30)
3. MACD value below the signal line

## License

This project is licensed under the MIT License - see the LICENSE file for details.