-- PostgreSQL initialization script for stock_screener database

-- Create database if it doesn't exist
-- Note: This needs to be run as a PostgreSQL superuser
-- CREATE DATABASE stock_screener;

-- Connect to the database
\c stock_screener;

-- Create enum types
CREATE TYPE exchange_type AS ENUM ('SP500', 'NASDAQ', 'NYSE');
CREATE TYPE time_frame_type AS ENUM ('daily', 'weekly', 'monthly');

-- Create stocks table
CREATE TABLE IF NOT EXISTS stocks (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255),
    exchange VARCHAR(20),
    sector VARCHAR(100),
    industry VARCHAR(100),
    market_cap FLOAT,
    pe_ratio FLOAT,
    pb_ratio FLOAT,
    dividend_yield FLOAT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes on stocks table
CREATE INDEX IF NOT EXISTS idx_stocks_symbol ON stocks(symbol);

-- Create stock_prices table
CREATE TABLE IF NOT EXISTS stock_prices (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    open FLOAT NOT NULL,
    high FLOAT NOT NULL,
    low FLOAT NOT NULL,
    close FLOAT NOT NULL,
    adjusted_close FLOAT NOT NULL,
    volume INTEGER NOT NULL,
    time_frame VARCHAR(10) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_stock_date_timeframe UNIQUE (stock_id, date, time_frame)
);

-- Create indexes on stock_prices table
CREATE INDEX IF NOT EXISTS idx_stock_prices_stock_id ON stock_prices(stock_id);
CREATE INDEX IF NOT EXISTS idx_stock_prices_date ON stock_prices(date);
CREATE INDEX IF NOT EXISTS idx_stock_prices_timeframe ON stock_prices(time_frame);

-- Create filtered_stocks table
CREATE TABLE IF NOT EXISTS filtered_stocks (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    filter_date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    time_frame VARCHAR(10) NOT NULL,
    bias_value FLOAT,
    rsi_value FLOAT,
    macd_value FLOAT,
    macd_signal FLOAT,
    macd_histogram FLOAT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes on filtered_stocks table
CREATE INDEX IF NOT EXISTS idx_filter_date_timeframe ON filtered_stocks(filter_date, time_frame);
CREATE INDEX IF NOT EXISTS idx_stock_filter_date ON filtered_stocks(stock_id, filter_date);

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create a trigger to automatically update the updated_at column
CREATE TRIGGER update_stocks_updated_at
BEFORE UPDATE ON stocks
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Grant privileges (adjust as needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- Output success message
\echo 'Database schema created successfully!'