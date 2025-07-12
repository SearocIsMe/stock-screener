# Stock Screener

A comprehensive stock screening application that filters stocks based on technical indicators and financial metrics.

## Features

- Fetch stock data from Yahoo Finance API
- Calculate technical indicators (BIAS, RSI, MACD, MA, Bollinger Bands, DMI, OBV) 
- Filter stocks based on technical indicators and financial metrics
- Calculate portfolio performance metrics and return on investment
- Financial metrics filtering (毛利率/Gross Profit Margin, 净资产收益率/Return on Equity, 研发比率/R&D Ratio)
- Store filtered results in PostgreSQL and Redis
- RESTful API for accessing filtered stocks
- Multiple free data sources with automatic fallback
- Enhanced weekly and monthly filtering criteria

## Recent Updates

- **Database Migration**: Added financial metrics columns (gross_margin, roe, rd_ratio) to support advanced filtering
- **Rate Limit Handling**: Added robust retry mechanism with exponential backoff for Yahoo Finance API rate limits
- **API Improvements**: Enhanced `/api/retrieve_filtered_stocks` to properly perform AND operations when multiple timeframes are specified
- **Data Structure**: Fixed response structure to ensure FinancialMetrics and metaData are consistently at the same level as timeframes
- **Error Handling**: Improved JSON parsing in `/api/performance_retreat` endpoint to handle special characters and formatting issues
- **Free Data Sources**: Implemented multiple free data sources (yfinance, pandas-datareader, akshare) with automatic fallback
- **Enhanced Filtering**: Added sophisticated weekly and monthly filtering criteria with multiple technical indicators

## Technical Stack

- **Backend**: Python
- **Database**: PostgreSQL, Redis
- **Data Source**: Yahoo Finance (via yfinance), pandas-datareader, akshare
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

2. Set up PostgreSQL and Redis:
   
   #### For WSL (Windows Subsystem for Linux) users:
   
   **Installing PostgreSQL:**
   ```bash
   # Update package list
   sudo apt update
   
   # Install PostgreSQL
   sudo apt install postgresql postgresql-contrib
   
   # Start PostgreSQL service
   sudo service postgresql start
   
   # Set up postgres user password
   sudo -u postgres psql
   postgres=# \password postgres
   postgres=# \q
   ```
   
   **Creating stock_user:**
   ```bash
   # Switch to postgres user
   sudo -u postgres psql
   
   # Create user with password
   CREATE USER stock_user WITH PASSWORD '7788';
   
   # Grant permissions
   ALTER USER stock_user WITH LOGIN;
   ALTER USER stock_user CREATEDB;
   
   # Create database
   CREATE DATABASE stock_screener OWNER stock_user;
   
   # Grant privileges
   GRANT ALL PRIVILEGES ON DATABASE stock_screener TO stock_user;
   
   # Exit
   \q
   ```
   
   **Installing Redis:**
   ```bash
   # Install Redis
   sudo apt install redis-server
   
   # Start Redis service
   sudo service redis-server start
   ```
   
   **Auto-start services in WSL:**
   Add to your `~/.bashrc`:
   ```bash
   sudo service postgresql start
   sudo service redis-server start
   ```

3. Run the automatic database setup script:
   ```bash
   ./setup_db.sh
   ```
   
   This script will:
   - Create the database if it doesn't exist
   - Create the necessary tables and indexes
   - Run database migrations to add financial metrics columns
   - Install required Python packages

4. **Manual Setup Alternative:**
   
   If you prefer manual setup:
   ```bash
   # Create database
   psql -U postgres -c "CREATE DATABASE stock_screener;"
   
   # Run initialization script
   psql -U postgres -d stock_screener -f init_db.sql
   
   # Run migrations
   cd migrations
   chmod +x run_migration.sh
   ./run_migration.sh
   
   # Or run migration directly
   PGPASSWORD=7788 psql -h localhost -p 5432 -U stock_user -d stock_screener -f migrations/add_financial_metrics.sql
   
   # Install Python packages
   pip install -r requirements.txt
   ```

5. Start the application:
   ```bash
   python run.py
   ```

6. Access the API at http://localhost:8000

## Configuration

The application configuration is stored in `config/config.yaml`. You can modify this file to adjust:

### Database Configuration
```yaml
database:
  postgres:
    host: localhost
    port: 5432
    username: stock_user
    password: 7788
    database: stock_screener
  redis:
    host: localhost
    port: 6379
    password: ""
    db: 0
    expiration_days: 30
```

### Technical Indicators Configuration
- **EMA/MA periods**: Configurable for daily, weekly, monthly timeframes
- **BIAS thresholds**: Different thresholds for each timeframe
- **RSI parameters**: Period, oversold/overbought levels
- **MACD parameters**: Fast/slow/signal periods
- **Bollinger Bands**: Period and standard deviation
- **DMI**: Period for trend analysis

### Financial Metrics Thresholds
```yaml
financial_metrics:
  gross_margin_threshold: 0.3  # 毛利率 (30%)
  roe_threshold: 0.05         # 净资产收益率 (5%)
  rd_ratio_threshold: 0.07    # 研发比率 (7%)
  enable_financial_filtering: true
```

### Weekly and Monthly Filtering Criteria

**Weekly Combinations (any of 3):**
1. **Double MA + MACD Golden Cross**
   - MA10 > MA20 (bullish alignment)
   - MACD just formed golden cross
   - Volume increased year-over-year

2. **Monthly trend up + Weekly volume breakout**
   - MA10 > MA20 (bullish alignment)
   - Volume breakout of resistance
   - MACD approaching golden cross
   - DMI positive turn

3. **Monthly RSI + Bollinger squeeze breakout**
   - Breakout above Bollinger middle/upper band
   - OBV trending upward

**Monthly Conditions (any of 3):**
1. **3 consecutive green candles OR above 20MA**
2. **Bollinger squeeze → expansion**
3. **RSI momentum from 50 towards 60**

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

#### 1. Trigger Fetch and Filtering
`POST /api/trigger_fetch_filtering`

Fetches stock data and applies filtering criteria.

**Request:**
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

#### 2. Retrieve Filtered Stocks
`POST /api/retrieve_filtered_stocks`

Retrieves filtered stocks from Redis cache.

**Request:**
```json
{
  "job_id": "optional_job_id",
  "timeFrame": ["daily", "weekly", "monthly"],
  "stockNameOnly": false,
  "recentDay": 1
}
```

**Response Example:**
<details>
<summary>Click to expand response structure</summary>

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
        "FinancialMetrics": {
          "gross_margin": 0.45,
          "roe": 0.22,
          "rd_ratio": 0.15,
          "thresholds": {
            "gross_margin": 0.3,
            "roe": 0.15,
            "rd_ratio": 0.1
          }
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
          }
        }
      }
    }
  }
}
```
</details>

#### 3. Fetch Stock History
`POST /api/fetch_stock_history`

Fetches historical stock data for specified symbols.

**Request:**
```json
{
  "symbols": ["AAPL", "MSFT"] or ["all"],
  "timeRange": {
    "start": "2023-01-01",
    "end": "2023-12-31"
  }
}
```

#### 4. Calculate Portfolio Performance
`POST /api/performance_retreat`

Calculates performance metrics for a portfolio of stocks.

**Request:**
```json
{
  "stocks": [
    {"symbol": "ACHC", "percentage": 20},
    {"symbol": "COO", "percentage": 20},
    {"symbol": "ELTK", "percentage": 20},
    {"symbol": "IMXI", "percentage": 20},
    {"symbol": "SGC", "percentage": 20}
  ],
  "total_money": 10000,
  "start_date": "2025-03-13",
  "end_date": "2025-03-19"
}
```

**Response includes:**
- Initial and final portfolio values
- Total gain/loss and percentage
- Individual stock performances
- Daily performance tracking for each stock
- Contribution percentage of each stock to total returns

### Example API Requests

```bash
# Trigger filtering for all stocks
curl -X POST "http://localhost:8000/api/trigger_fetch_filtering" \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["all"], "timeFrame": ["daily", "weekly", "monthly"]}'

# Calculate portfolio performance
curl -X POST "http://localhost:8000/api/performance_retreat" \
  -H "Content-Type: application/json" \
  -d '{"stocks": [{"symbol": "AAPL", "percentage": 40}, {"symbol": "MSFT", "percentage": 30}, {"symbol": "GOOGL", "percentage": 30}], 
       "total_money": 10000, "start_date": "2024-01-01", "end_date": "2024-03-01"}'
```

## Project Structure

```
stock-screener/
├── config/
│   ├── config.yaml              # Main configuration
│   ├── enhanced_data_config.yaml # Enhanced data source config
│   └── free_data_config.yaml    # Free data sources config
├── src/
│   ├── api/                     # API endpoints
│   │   └── routes.py
│   ├── data/                    # Data acquisition and storage
│   │   ├── acquisition.py
│   │   ├── database.py
│   │   ├── models.py
│   │   └── free_data_sources.py
│   ├── filters/                 # Stock filtering logic
│   │   ├── stock_filter.py
│   │   └── trend_strategy.py
│   ├── indicators/              # Technical indicators
│   │   └── technical.py
│   └── utils/                   # Utility functions
│       ├── async_job.py
│       ├── hash_utils.py
│       └── logging_config.py
├── migrations/                  # Database migrations
│   ├── add_financial_metrics.sql
│   └── run_migration.sh
├── examples/                    # Usage examples
├── init_db.sql                  # Database initialization
├── setup_db.sh                  # Automated setup script
├── run.py                       # Application entry point
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Database Schema

### stocks table
- Basic information: symbol, name, exchange, sector, industry
- Financial metrics: market_cap, pe_ratio, pb_ratio, dividend_yield
- **New columns**: gross_margin, roe, rd_ratio

### stock_prices table
- Historical price data: open, high, low, close, adjusted_close, volume
- Supports multiple timeframes: daily, weekly, monthly

### filtered_stocks table
- Stores filtering results with technical indicators
- Includes BIAS, RSI, MACD values
- **New columns**: gross_margin, roe, rd_ratio

## Troubleshooting

### Common Issues and Solutions

1. **Database Connection Error**
   - Ensure PostgreSQL is running: `sudo service postgresql status`
   - Check credentials in `config/config.yaml`
   - Verify database exists: `psql -U stock_user -d stock_screener -c "\l"`

2. **Missing Database Columns Error**
   - Run the migration: `cd migrations && ./run_migration.sh`
   - This adds the financial metrics columns (gross_margin, roe, rd_ratio)

3. **Redis Connection Error**
   - Ensure Redis is running: `sudo service redis-server status`
   - Check Redis configuration in `config/config.yaml`

4. **API Rate Limit Issues**
   - The application automatically handles rate limits with exponential backoff
   - Uses multiple free data sources with automatic fallback

5. **Insufficient Historical Data**
   - The system requires minimum data points for reliable indicators
   - Automatically extends data collection periods when needed

## Free Data Sources

The application uses multiple free data sources to avoid API rate limits:

1. **yfinance** - Primary source for historical price data
2. **pandas-datareader** - Fallback for various data sources
3. **akshare** - Specialized for Chinese stocks

All sources are completely free and require no API keys.

## Practice History

Example of filtered stocks from May 28, 2025:

| Symbol | Gross Margin | ROE | Weekly BIAS | Weekly RSI |
|--------|--------------|-----|-------------|------------|
| AEHR   | 47.47%      | 20.94% | -13.01    | 37.60      |
| PDD    | 60.92%      | 44.92% | -12.89    | 41.19      |
| TGTX   | 88.30%      | 12.22% | -18.83    | 35.89      |
| MNSO   | 44.94%      | 26.97% | -24.09    | 37.03      |

## License

This project is licensed under the MIT License - see the LICENSE file for details.