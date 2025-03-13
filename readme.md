# Stock Screener

A comprehensive stock screening application that filters stocks based on technical indicators.

## Features

- Fetch stock data from Yahoo Finance API
- Calculate technical indicators (BIAS, RSI, MACD) 
- Filter stocks based on technical indicators and financial metrics
- Financial metrics filtering (毛利率/Gross Profit Margin, 净资产收益率/Return on Equity, 研发比率/R&D Ratio)
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
- Financial metrics thresholds:
  - `gross_margin_threshold`: Minimum acceptable 毛利率/gross profit margin (default: 0.3 or 30%)
  - `roe_threshold`: Minimum acceptable 净资产收益率/return on equity (default: 0.15 or 15%)
  - `rd_ratio_threshold`: Minimum acceptable 研发比率/R&D to revenue ratio (default: 0.1 or 10%)
  - `enable_financial_filtering`: Enable/disable financial metrics filtering

## Usage

### API Endpoints
All endpoints are prefixed with `/api` and return a standardized response format:

```json
{
  "success": true,
  "message": "Success message",
  "data": {
    // Response data
  }
}
```

- `POST /api/trigger_fetch_filtering`: Trigger fetching and filtering of stocks
  - Fetches stock data if not already in Redis
  - Calculates indicators for each stock
  - Filters stocks based on indicators and financial metrics
  - Stores filtered results in Redis
  - Request body:
    ```json
    {
      "symbols": ["AAPL", "MSFT"] or ["all"],
      "timeFrame": ["daily", "weekly", "monthly"],
      "financialFilters": {
        "gross_margin_threshold": 0.3,
        "roe_threshold": 0.15,
        "rd_ratio_threshold": 0.1
      }
    }
    ```

- `POST /api/retrieve_filtered_stocks`: Retrieve filtered stocks from Redis
  - Scans Redis for filtered stocks
  - Filters by time frame
  - Returns filtered stocks
  - Request body:
    ```json
    {
      "timeFrame": ["daily", "weekly", "monthly"],
      "recentDay": 1
    }
    ```
  - Response body (with "daily", "weekly" must to meet):
    <details>
    <summary>Collapse for the filtered stocks </summary>
    ```json
      {
      "success": true,
      "message": "Successfully retrieved 88 filtered stocks",
      "data": {
         "filtered_stocks": {
            "PUBM": {
            "metaData": {
               "stock": "PUBM",
               "filterTime": "2025-03-12T14:32:49.035766"
            },
            "daily": {
               "BIAS": {
                  "bias": -15.794040576424631
               },
               "RSI": {
                  "value": 18.564055122174523,
                  "period": 14
               },
               "MACD": {
                  "value": -1.5234014344971847,
                  "signal": -1.090363937702842,
                  "histogram": -0.43303749679434267,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               },
               "FinancialMetrics": {
                  "gross_margin": 0.45,
                  "roe": 0.22,
                  "rd_ratio": 0.15,
                  "thresholds": {
                    "gross_margin": 0.3,
                    "roe": 0.15,
                    "rd_ratio": 0.1
                  }
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -27.599479497090577
               },
               "RSI": {
                  "value": 28.62853198352002,
                  "period": 14
               },
               "MACD": {
                  "value": -1.3868694305196243,
                  "signal": -0.8667288557902623,
                  "histogram": -0.520140574729362,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               },
               "FinancialMetrics": {
                  "gross_margin": 0.45,
                  "roe": 0.22,
                  "rd_ratio": 0.15,
                  "thresholds": {
                    "gross_margin": 0.3,
                    "roe": 0.15,
                    "rd_ratio": 0.1
                  }
               }
            }
            }
         }
      }
      }
    ```
    </details>

- `POST /api/fetch_stock_history`: Fetch stock history for specified symbols
  - Fetches stock history for specified symbols
  - Stores in database
  - Request body:
    ```json
    {
      "symbols": ["AAPL", "MSFT"] or ["all"],
      "timeRange": {
        "start": "2023-01-01",
        "end": "2023-12-31"
      }
    }
    ```

### Example API Request

```bash
curl -X POST "http://localhost:8000/api/trigger_fetch_filtering" \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["all"], "timeFrame": ["daily", "weekly", "monthly"], "financialFilters": {"gross_margin_threshold": 0.3, "roe_threshold": 0.15, "rd_ratio_threshold": 0.1}}'
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