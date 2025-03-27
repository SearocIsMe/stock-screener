"""
Data acquisition module for fetching stock data from yfinance API
"""
import os
import json
import logging
import time
import re
from src.utils.logging_config import configure_logging
from datetime import datetime, timedelta
import yaml
import requests

import yfinance as yf
import pandas as pd
import pandas_datareader as pdr
import akshare as ak
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
                
                elif exch in ["NASDAQ", "NYSE", "AMEX", "ACN"]:
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
                                symbols = df['Symbol'].astype(str).tolist()
                            elif 'symbol' in df.columns:
                                symbols = df['symbol'].astype(str).tolist()
                            else:
                                # Try to use the first column
                                symbols = df.iloc[:, 0].astype(str).tolist()
                                
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
                        elif exch == "ACN":
                            symbols = ["300281.SZ", "600061.SH", "836239.BJ", "302132.SZ", "830809.BJ"]
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
                    # Skip symbols containing '^' character (indices)
                    if '^' in symbol:
                        logger.info(f"Skipping index symbol: {symbol}")
                        continue
                    
                    # Check if it's a Chinese A stock (pattern: number.SH or number.SZ)
                    chinese_stock_pattern = r'^\d'
                    is_chinese_a_stock = bool(re.match(chinese_stock_pattern, symbol))
                    
                    if is_chinese_a_stock:
                        # Handle Chinese A stocks differently
                        logger.info(f"Processing Chinese A stock: {symbol}")
                        self._process_chinese_a_stock(symbol, exchange)
                    else:
                        # Get stock info from yfinance for non-Chinese stocks
                        ticker = yf.Ticker(symbol)
                        info = ticker.info
                        
                        # Store in database
                        self._store_stock_info(
                            symbol=symbol,
                            name=info.get('shortName', None),
                            exchange=exchange,
                            sector=info.get('sector', None),
                            industry=info.get('industry', None),
                            gross_margin=info.get('grossMargins', None),
                            roe=info.get('returnOnEquity', None),
                            rd_ratio=info.get('researchAndDevelopmentToRevenue', None)
                        )
                except Exception as e:
                    logger.warning(f"Error getting info for {symbol}: {e}")
                    # Still store basic info
                    self._store_stock_info(
                        symbol=symbol,
                        name=None,
                        exchange=exchange,
                        sector=None,
                        industry=None,
                        gross_margin=None,
                        roe=None,
                        rd_ratio=None
                    )
                    # Sleep to avoid rate limiting
                    time.sleep(5)
    
    def _process_chinese_a_stock(self, symbol, exchange=None):
        """Process Chinese A stock information using alternative methods"""
        try:
            stock_code = symbol
            
            # Calculate date range
            chinese_stock_pattern = r'^\d'
            
            # Check if it's a Chinese A stock
            is_chinese_a_stock = bool(re.match(chinese_stock_pattern, symbol))

            # Use akshare to fetch historical data for Chinese A stocks
            try:
                logger.info(f"Fetching historical data for Chinese A stock: {symbol} using akshare")
                # Calculate date range for historical data
                end_date = datetime.now()
                start_date = end_date - timedelta(days=365)  # 1 year of daily data
                
                # Use akshare to fetch historical data
                df = ak.stock_zh_a_hist(
                    symbol=stock_code, 
                    period="daily",
                    start_date=start_date.strftime('%Y%m%d'), 
                    end_date=end_date.strftime('%Y%m%d'),
                    adjust="qfq"  # qfq means forward adjusted price
                )
                
                # Rename columns to match yfinance format if needed
                if not df.empty:
                    # Get stock name from the data if available
                    stock_name = None
                    if 'name' in df.columns:
                        stock_name = df['name'].iloc[0]
                    
                    # Store the stock information
                    self._store_stock_info(
                        symbol=symbol,
                        name=stock_name,
                        exchange="ACN",
                        sector=f"Chinese A Stock",
                        industry=None,
                        gross_margin=None,
                        roe=None,
                        rd_ratio=None
                    )
                    logger.info(f"Successfully retrieved info for Chinese A stock: {symbol} using akshare")
                    return
            except Exception as e:
                logger.warning(f"Error using akshare for {symbol}: {e}")
            
            # Try to get basic information using requests to a public API
            try:
                # Method 1: Try to use a free API to get stock information
                # This is a fallback method that doesn't require additional libraries
                url = f"http://hq.sinajs.cn/list={market.lower()}{stock_code}"
                headers = {
                    'Referer': 'https://finance.sina.com.cn',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(url, headers=headers)
                
                if response.status_code == 200:
                    # Parse the response which is in the format: var hq_str_sh600000="STOCK NAME,..."
                    content = response.text
                    if 'hq_str_' in content and '=' in content and '"' in content:
                        data_str = content.split('=')[1].strip('";\n')
                        data_parts = data_str.split(',')
                        
                        if len(data_parts) > 0:
                            stock_name = data_parts[0]
                            
                            # Store the information
                            self._store_stock_info(
                                symbol=symbol,
                                name=stock_name,
                                exchange="ACN",
                                sector=f"Chinese A Stock",
                                industry=None,
                                gross_margin=None,
                                roe=None,
                                rd_ratio=None
                            )
                            logger.info(f"Successfully retrieved basic info for Chinese A stock: {symbol}")
                            return
            except Exception as e:
                logger.warning(f"Error using Sina API for {symbol}: {e}")
            
            # Method 2: If the first method fails, try another approach
            try:
                # Use a different API or method
                # For example, we could use a different endpoint or service
                # This is just a placeholder for an alternative method
                
                # For now, we'll just store basic information based on the symbol
                self._store_stock_info(
                    symbol=symbol,
                    name=f"A Stock {stock_code}",
                    exchange="ACN",
                    sector=f"Chinese {sector_code}",
                    industry=None,
                    gross_margin=None,
                    roe=None,
                    rd_ratio=None
                )
                logger.info(f"Stored basic info for Chinese A stock: {symbol}")
                return
            except Exception as e:
                logger.warning(f"Error using alternative method for {symbol}: {e}")
            
            # If all methods fail, store minimal information
            self._store_stock_info(
                symbol=symbol,
                name=None,
                exchange="ACN",
                sector=None,
                industry=None,
                gross_margin=None,
                roe=None,
                rd_ratio=None
            )
            
        except Exception as e:
            logger.error(f"Error processing Chinese A stock {symbol}: {e}")
            # Store minimal information
            self._store_stock_info(
                symbol=symbol,
                name=None,
                exchange=exchange,
                sector=None,
                industry=None,
                gross_margin=None,
                roe=None,
                rd_ratio=None
            )
    
    def _store_stock_info(self, symbol, name=None, exchange=None, sector=None, industry=None, gross_margin=None, roe=None, rd_ratio=None):
        """Store stock information in database"""
        try:
            # Check if symbol is NaN or None
            if pd.isna(symbol) or symbol is None:
                logger.warning("Skipping stock info storage: Symbol is NaN or None")
                return None
                
            # Ensure symbol is a string
            symbol = str(symbol)
            # Check if stock already exists
            stock = self.db.query(Stock).filter(Stock.symbol == symbol).first()
            
            if not stock:
                # Create new stock
                stock = Stock(
                    symbol=symbol,
                    name=name,
                    exchange=exchange,
                    sector=sector,
                    industry=industry,
                    gross_margin=gross_margin,
                    roe=roe,
                    rd_ratio=rd_ratio
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
                if gross_margin is not None:
                    stock.gross_margin = gross_margin
                if roe is not None:
                    stock.roe = roe
                if rd_ratio is not None:
                    stock.rd_ratio = rd_ratio
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
            time.sleep(3)
        
        return results
    
    def _store_stock_prices(self, symbol, data, time_frame):
        """Store stock prices in database"""
        try:
            # Get or create stock
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
                    
                # Handle different column name formats
                price_data = {}
                column_mappings = {
                    'open': ['Open', 'open'],
                    'high': ['High', 'high'],
                    'low': ['Low', 'low'],
                    'close': ['Close', 'close'],
                    'volume': ['Volume', 'volume']
                }
                
                # Try to find each required column
                for db_col, possible_cols in column_mappings.items():
                    for col in possible_cols:
                        if col in row:
                            price_data[db_col] = row[col]
                            break
                
                # Skip if we couldn't find all required columns
                if len(price_data) < 5:
                    logger.warning(f"Skipping row for {symbol} at {date}: missing required columns")
                    continue
                
                # Check if price already exists
                existing_price = self.db.query(StockPrice).filter(
                    StockPrice.stock_id == stock.id,
                    StockPrice.date == date,
                    StockPrice.time_frame == time_frame
                ).first()
                
                if existing_price:
                    # Update existing price
                    existing_price.open = price_data['open']
                    existing_price.high = price_data['high']
                    existing_price.low = price_data['low']
                    existing_price.close = price_data['close']
                    existing_price.adjusted_close = price_data['close']  # Using Close as Adj Close since we use auto_adjust=True
                    existing_price.volume = int(price_data['volume'])
                else:
                    # Create new price
                    price = StockPrice(
                        stock_id=stock.id,
                        date=date,
                        open=price_data['open'],
                        high=price_data['high'],
                        low=price_data['low'],
                        close=price_data['close'],
                        adjusted_close=price_data['close'],  # Using Close as Adj Close since we use auto_adjust=True
                        volume=int(price_data['volume']),
                        time_frame=time_frame
                    )
                    self.db.add(price)
            
            self.db.commit()
            logger.info(f"Successfully stored prices for {symbol} ({time_frame})")
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error storing prices for {symbol}: {e}")