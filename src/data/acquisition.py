"""
Data acquisition module for fetching stock data from yfinance API
"""
import os
import json
import logging
import time
from src.utils.logging_config import configure_logging
from datetime import datetime, timedelta
import yaml
import requests

import yfinance as yf
import pandas as pd
import pandas_datareader as pdr
import pandas_datareader.data as web
from sqlalchemy.orm import Session
from .database import get_redis
from .models import Stock, StockPrice, TimeFrame

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)

# Load configuration
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "config.yaml")
with open(config_path, "r") as config_file:
    config = yaml.safe_load(config_file)

# Constants
REDIS_EXPIRATION = config["database"]["redis"]["expiration_days"] * 86400  # Convert days to seconds
BATCH_SIZE = config["data_fetching"]["yfinance"]["batch_size"]
RETRY_ATTEMPTS = config["data_fetching"]["yfinance"]["retry_attempts"]
RETRY_DELAY = config["data_fetching"]["yfinance"]["retry_delay"]

class DataAcquisition:
    """Data acquisition class for fetching stock data"""
    
    def __init__(self, db: Session):
        """Initialize data acquisition with database session"""
        self.db = db
        self.redis = get_redis()
    
    def fetch_stock_symbols(self, exchange=None):
        """
        Fetch stock symbols from specified exchange and store in Redis
        
        Args:
            exchange: Exchange to fetch symbols from (SP500, NASDAQ, NYSE, AMEX)
                     If None, fetch from all exchanges
        
        Returns:
            List of stock symbols
        """
        exchanges = [exchange] if exchange else config["exchanges"]
        all_symbols = []
        
        # First, fetch all symbols from all exchanges
        for exch in exchanges:
            logger.info(f"Fetching stock symbols from {exch}")
            
            try:
                symbols = []
                
                if exch == "SP500":
                    # Fetch S&P 500 symbols from Wikipedia using pandas
                    try:
                        logger.info("Fetching S&P 500 symbols from Wikipedia")
                        sp500_df = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
                        symbols = sp500_df['Symbol'].str.replace('.', '-', regex=False).tolist()
                        logger.info(f"Retrieved {len(symbols)} S&P 500 symbols")
                    except Exception as e:
                        logger.error(f"Error fetching S&P 500 symbols: {e}")
                        # Fallback to top components if fetching fails
                        symbols = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "NVDA", "BRK-B", "UNH", "JNJ"]
                        logger.warning(f"Using fallback list of {len(symbols)} S&P 500 components")
                
                elif exch in ["NASDAQ", "NYSE", "AMEX"]:
                    # Read symbols from CSV files in config directory
                    try:
                        # Construct the CSV file path
                        csv_path = os.path.join(
                            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                            "config", 
                            f"{exch}.csv"
                        )
                        logger.info(f"Reading {exch} symbols from {csv_path}")
                        
                        # Check if file exists
                        if os.path.exists(csv_path):
                            # Read the CSV file
                            df = pd.read_csv(csv_path)
                            
                            # Extract symbols column
                            if 'Symbol' in df.columns:
                                symbols = df['Symbol'].tolist()
                            elif 'symbol' in df.columns:
                                symbols = df['symbol'].tolist()
                            else:
                                # Try to use the first column
                                symbols = df.iloc[:, 0].tolist()
                                
                            logger.info(f"Retrieved {len(symbols)} {exch} symbols from CSV file")
                        else:
                            logger.error(f"CSV file for {exch} not found at {csv_path}")
                            raise FileNotFoundError(f"CSV file for {exch} not found at {csv_path}")
                    except Exception as e:
                        logger.error(f"Error reading {exch} symbols from CSV: {e}")
                        # Fallback to top components
                        if exch == "NASDAQ":
                            symbols = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "NVDA", "PYPL", "INTC", "CSCO"]
                        elif exch == "NYSE":
                            symbols = ["JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "AXP", "USB", "PNC"]
                        elif exch == "AMEX":
                            symbols = ["SPY", "GLD", "XLF", "EEM", "XLE", "VXX", "EFA", "XLV", "IWM", "QQQ"]
                        logger.warning(f"Using fallback list of {len(symbols)} {exch} components")
                
                # Store symbols in Redis
                redis_key = f"symbols_{exch.lower()}"
                self.redis.set(redis_key, json.dumps(symbols))
                logger.info(f"Stored {len(symbols)} symbols for {exch} in Redis")
                
                # Add to all symbols list
                all_symbols.extend(symbols)
            
            except Exception as e:
                logger.error(f"Error fetching symbols for {exch}: {e}")
        
        # Store all symbols in Redis
        if all_symbols:
            self.redis.set("symbols_all", json.dumps(all_symbols))
            logger.info(f"Stored {len(all_symbols)} symbols in Redis")
        
        # Now process all symbols to get ticker information
        self.process_stock_symbols(all_symbols)
        
        return all_symbols
    
    def process_stock_symbols(self, symbols, exchange=None):
        """Process stock symbols to get ticker information and store in database"""
        logger.info(f"Processing {len(symbols)} symbols for ticker information")
        
        # Process in batches to avoid rate limiting
        for i in range(0, len(symbols), BATCH_SIZE):
            batch = symbols[i:i+BATCH_SIZE]
            logger.info(f"Processing batch {i//BATCH_SIZE + 1}/{(len(symbols)-1)//BATCH_SIZE + 1} ({len(batch)} symbols)")
            
            for symbol in batch:
                try:
                    # Get stock info from yfinance
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    
                    # Store in database
                    self._store_stock_info(
                        symbol=symbol,
                        name=info.get('shortName', None),
                        exchange=exchange,
                        sector=info.get('sector', None),
                        industry=info.get('industry', None)
                    )
                except Exception as e:
                    logger.warning(f"Error getting info for {symbol}: {e}")
                    # Still store basic info
                    self._store_stock_info(
                        symbol=symbol,
                        name=None,
                        exchange=exchange,
                        sector=None,
                        industry=None
                    )
            
            # Sleep to avoid rate limiting
            time.sleep(1)
    
    def _store_stock_info(self, symbol, name=None, exchange=None, sector=None, industry=None):
        """Store stock information in database"""
        try:
            # Check if stock already exists
            stock = self.db.query(Stock).filter(Stock.symbol == symbol).first()
            
            if not stock:
                # Create new stock
                stock = Stock(
                    symbol=symbol,
                    name=name,
                    exchange=exchange,
                    sector=sector,
                    industry=industry
                )
                self.db.add(stock)
            else:
                # Update existing stock
                if name:
                    stock.name = name
                if exchange:
                    stock.exchange = exchange
                if sector:
                    stock.sector = sector
                if industry:
                    stock.industry = industry
                stock.updated_at = datetime.utcnow()
            
            self.db.commit()
            return stock
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error storing stock info for {symbol}: {e}")
            return None
    
    def fetch_stock_history(self, symbols, start_date=None, end_date=None, time_frame="daily"):
        """
        Fetch historical stock data for specified symbols
        
        Args:
            symbols: List of stock symbols or "all" for all symbols
            start_date: Start date for historical data (default: 1 year ago)
            end_date: End date for historical data (default: today)
            time_frame: Time frame for data (daily, weekly, monthly)
        
        Returns:
            Dictionary of stock data by symbol
        """
        # Set default dates if not provided
        if not end_date:
            end_date = datetime.now()
        elif isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        if not start_date:
            if time_frame == "daily":
                start_date = end_date - timedelta(days=365)  # 1 year of daily data
            elif time_frame == "weekly":
                start_date = end_date - timedelta(days=365 * 2)  # 2 years of weekly data
            elif time_frame == "monthly":
                start_date = end_date - timedelta(days=365 * 5)  # 5 years of monthly data
        elif isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        
        # Convert time_frame to yfinance interval
        interval = "1d"  # default daily
        if time_frame == "weekly":
            interval = "1wk"
        elif time_frame == "monthly":
            interval = "1mo"
        
        # Get symbols if "all" is specified
        if symbols == "all" or symbols == "ALL":
            symbols_json = self.redis.get("symbols_all")
            if not symbols_json:
                symbols = self.fetch_stock_symbols()
            else:
                symbols = json.loads(symbols_json)
        elif isinstance(symbols, str) and symbols.lower() in ["sp500", "nasdaq", "nyse", "amex"]:
            # Get symbols for specific exchange
            exchange = symbols.lower()
            symbols_json = self.redis.get(f"symbols_{exchange}")
            if not symbols_json:
                symbols = self.fetch_stock_symbols(exchange.upper())
            else:
                symbols = json.loads(symbols_json)
        
        # Fetch data in batches
        results = {}
        for i in range(0, len(symbols), BATCH_SIZE):
            batch = symbols[i:i+BATCH_SIZE]
            logger.info(f"Fetching historical data for batch {i//BATCH_SIZE + 1}/{(len(symbols)-1)//BATCH_SIZE + 1} ({len(batch)} symbols)")
            
            for attempt in range(RETRY_ATTEMPTS):
                try:
                    # Fetch data from yfinance
                    data = yf.download(
                        tickers=batch,
                        start=start_date,
                        end=end_date,
                        interval=interval,
                        group_by="ticker",
                        auto_adjust=True,
                        prepost=False,
                        threads=True
                    )
                    
                    # Process and store data
                    for symbol in batch:
                        if len(batch) == 1:
                            # For single symbol, data is not multi-level
                            symbol_data = data
                        else:
                            # For multiple symbols, data is multi-level
                            symbol_data = data[symbol]
                        
                        if not symbol_data.empty:
                            # Store data in database
                            self._store_stock_prices(symbol, symbol_data, time_frame)
                            results[symbol] = symbol_data
                    
                    # Break retry loop if successful
                    break
                
                except Exception as e:
                    logger.error(f"Error fetching data (attempt {attempt+1}/{RETRY_ATTEMPTS}): {e}")
                    if attempt < RETRY_ATTEMPTS - 1:
                        time.sleep(RETRY_DELAY)
            
            # Sleep to avoid rate limiting
            time.sleep(1)
        
        return results
    
    def _store_stock_prices(self, symbol, data, time_frame):
        """Store stock prices in database"""
        try:
            # Get stock ID
            stock = self.db.query(Stock).filter(Stock.symbol == symbol).first()
            if not stock:
                logger.warning(f"Stock {symbol} not found in database, creating it")
                stock = Stock(symbol=symbol)
                self.db.add(stock)
                self.db.commit()
            
            # Process each row in the dataframe
            for date, row in data.iterrows():
                # Skip rows with NaN values
                if row.isnull().any():
                    continue
                
                # Check if price already exists
                existing_price = self.db.query(StockPrice).filter(
                    StockPrice.stock_id == stock.id,
                    StockPrice.date == date,
                    StockPrice.time_frame == time_frame
                ).first()
                
                if existing_price:
                    # Update existing price
                    existing_price.open = row["Open"]
                    existing_price.high = row["High"]
                    existing_price.low = row["Low"]
                    existing_price.close = row["Close"]
                    existing_price.adjusted_close = row["Close"]  # Using Close as Adj Close since we use auto_adjust=True
                    existing_price.volume = int(row["Volume"])
                else:
                    # Create new price
                    price = StockPrice(
                        stock_id=stock.id,
                        date=date,
                        open=row["Open"],
                        high=row["High"],
                        low=row["Low"],
                        close=row["Close"],
                        adjusted_close=row["Close"],  # Using Close as Adj Close since we use auto_adjust=True
                        volume=int(row["Volume"]),
                        time_frame=time_frame
                    )
                    self.db.add(price)
            
            self.db.commit()
            logger.info(f"Stored {len(data)} prices for {symbol} ({time_frame})")
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error storing prices for {symbol}: {e}")