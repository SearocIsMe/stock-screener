# Database Setup for Stock Screener

This document provides instructions on how to set up the PostgreSQL database for the Stock Screener application.

## Prerequisites

- PostgreSQL 12 or higher
- Python 3.8 or higher
- pip (Python package manager)
- Redis 6.0 or higher

## Setting up PostgreSQL and Redis in WSL (Windows Subsystem for Linux)

### Installing PostgreSQL in WSL

1. Update your package list:
   ```bash
   sudo apt update
   ```

2. Install PostgreSQL and its dependencies:
   ```bash
   sudo apt install postgresql postgresql-contrib
   ```

3. Start the PostgreSQL service:
   ```bash
   sudo service postgresql start
   ```

4. Verify the installation:
   ```bash
   sudo -u postgres psql -c "SELECT version();"
   ```

5. Set up a password for the postgres user:
   ```bash
   sudo -u postgres psql
   postgres=# \password postgres
   # Enter your desired password (default in config is 'postgres')
   postgres=# \q
   ```

### Installing Redis in WSL

1. Update your package list if you haven't already:
   ```bash
   sudo apt update
   ```

2. Install Redis:
   ```bash
   sudo apt install redis-server
   ```

3. Start the Redis service:
   ```bash
   sudo service redis-server start
   ```

## Database Configuration

The database configuration is stored in `config/config.yaml`. You can modify this file to match your PostgreSQL setup:

```yaml
database:
  postgres:
    host: localhost
    port: 5432
    username: postgres
    password: postgres
    database: stock_screener
  redis:
    host: localhost
    port: 6379
    password: ""
    db: 0
    expiration_days: 30
```

### Starting Services Automatically in WSL

To ensure PostgreSQL and Redis start automatically when you open WSL, add these lines to your `~/.bashrc` file:

```bash
sudo service postgresql start
sudo service redis-server start
```

## Automatic Setup

We provide a shell script that automates the database setup process:

1. Make sure PostgreSQL is running
2. Run the setup script:

```bash
./setup_db.sh
```

This script will:
- Create the database if it doesn't exist
- Create the necessary tables and indexes
- Install required Python packages

## Manual Setup

If you prefer to set up the database manually, follow these steps:

### 1. Create the Database

```bash
psql -U postgres -c "CREATE DATABASE stock_screener;"
```

### 2. Run the SQL Initialization Script

```bash
psql -U postgres -d stock_screener -f init_db.sql
```

### 3. Install Required Python Packages

```bash
pip install -r requirements.txt
```

## Database Schema

The application uses the following tables:

### stocks

Stores information about stocks:

- `id`: Primary key
- `symbol`: Stock symbol (e.g., AAPL)
- `name`: Company name
- `exchange`: Stock exchange (SP500, NASDAQ, NYSE)
- `sector`: Industry sector
- `industry`: Specific industry
- `market_cap`: Market capitalization
- `pe_ratio`: Price-to-earnings ratio
- `pb_ratio`: Price-to-book ratio
- `dividend_yield`: Dividend yield
- `created_at`: Record creation timestamp
- `updated_at`: Record update timestamp

### stock_prices

Stores historical price data for stocks:

- `id`: Primary key
- `stock_id`: Foreign key to stocks table
- `date`: Date of the price data
- `open`: Opening price
- `high`: Highest price
- `low`: Lowest price
- `close`: Closing price
- `adjusted_close`: Adjusted closing price
- `volume`: Trading volume
- `time_frame`: Time frame (daily, weekly, monthly)
- `created_at`: Record creation timestamp

### filtered_stocks

Stores filtered stocks based on technical indicators:

- `id`: Primary key
- `stock_id`: Foreign key to stocks table
- `filter_date`: Date when the filter was applied
- `time_frame`: Time frame (daily, weekly, monthly)
- `bias_value`: BIAS indicator value
- `rsi_value`: RSI indicator value
- `macd_value`: MACD line value
- `macd_signal`: MACD signal line value
- `macd_histogram`: MACD histogram value
- `created_at`: Record creation timestamp

## Running the Application

After setting up the database, you can run the application:

```bash
python run.py
```

This will start the API server, which you can access at http://localhost:8000.

## Troubleshooting

If you encounter any issues during the setup process:

1. Check that PostgreSQL is running
2. Verify your PostgreSQL credentials in `config/config.yaml`
3. Ensure you have the necessary permissions to create databases and tables
4. Check the PostgreSQL logs for any error messages

### Common WSL Issues

1. **Services not starting**: If PostgreSQL or Redis services fail to start, try:
   ```bash
   sudo service postgresql status
   sudo service redis-server status
   ```
   to see detailed error messages.