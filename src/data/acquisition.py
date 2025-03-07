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
import yfinance as yf
import pandas as pd
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
            exchange: Exchange to fetch symbols from (SP500, NASDAQ, NYSE)
                     If None, fetch from all exchanges
        
        Returns:
            List of stock symbols
        """
        exchanges = [exchange] if exchange else config["exchanges"]
        all_symbols = []
        
        for exch in exchanges:
            logger.info(f"Fetching stock symbols from {exch}")
            
            try:
                if exch == "SP500":
                    # Fetch S&P 500 symbols
                    sp500 = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
                    symbols = sp500["Symbol"].tolist()
                    
                    # Store stock info in database
                    for i, row in sp500.iterrows():
                        symbol = row["Symbol"]
                        self._store_stock_info(
                            symbol=symbol,
                            name=row["Security"],
                            exchange="SP500",
                            sector=row["GICS Sector"],
                            industry=row["GICS Sub-Industry"]
                        )
                
                elif exch == "NASDAQ":
                    # Fetch NASDAQ symbols
                    try:
                        # Try to get the Nasdaq-100 list
                        tables = pd.read_html("https://en.wikipedia.org/wiki/Nasdaq-100")
                        
                        # Find the table with company listings by looking for tables with 'Ticker' or 'Symbol' column
                        nasdaq = None
                        ticker_col = None
                        company_col = None
                        industry_col = None
                        
                        for table in tables:
                            if 'Ticker' in table.columns:
                                nasdaq = table
                                ticker_col = 'Ticker'
                                company_col = 'Company' if 'Company' in table.columns else 'Name'
                                industry_col = 'Industry' if 'Industry' in table.columns else 'Sector'
                                break
                            elif 'Symbol' in table.columns:
                                nasdaq = table
                                ticker_col = 'Symbol'
                                company_col = 'Company' if 'Company' in table.columns else 'Name'
                                industry_col = 'Industry' if 'Industry' in table.columns else 'Sector'
                                break
                        
                        if nasdaq is not None:
                            symbols = nasdaq[ticker_col].tolist()
                            
                            # Store stock info in database
                            for i, row in nasdaq.iterrows():
                                symbol = row[ticker_col]
                                self._store_stock_info(
                                    symbol=symbol,
                                    name=row[company_col] if company_col in nasdaq.columns else None,
                                    exchange="NASDAQ",
                                    sector=None,
                                    industry=row[industry_col] if industry_col in nasdaq.columns else None
                                )
                        else:
                            # Fallback to a default list of major NASDAQ stocks
                            symbols = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "NVDA", "PYPL", "INTC", "CSCO", "CMCSA", "PEP", "ADBE", "NFLX", "AVGO"]
                            logger.warning(f"Could not find NASDAQ symbols table, using fallback list of {len(symbols)} major stocks")
                            
                            # Store basic info for these symbols
                            for symbol in symbols:
                                self._store_stock_info(
                                    symbol=symbol,
                                    name=None,
                                    exchange="NASDAQ",
                                    sector=None,
                                    industry=None
                                )
                    except Exception as e:
                        # Fallback to a default list of major NASDAQ stocks
                        symbols = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "NVDA", "PYPL", "INTC", "CSCO", "CMCSA", "PEP", "ADBE", "NFLX", "AVGO"]
                        logger.warning(f"Error fetching NASDAQ symbols: {e}. Using fallback list of {len(symbols)} major stocks")
                        
                        # Store basic info for these symbols
                        for symbol in symbols:
                            self._store_stock_info(
                                symbol=symbol,
                                name=None,
                                exchange="NASDAQ",
                                sector=None,
                                industry=None
                            )
                
                elif exch == "NYSE":
                    # For NYSE, we'll use a different approach since there's no simple Wikipedia table
                    # This is a simplified approach - in production, you might want to use a more reliable source
                    try:
                        # Try to get NYSE symbols
                        tables = pd.read_html("https://en.wikipedia.org/wiki/List_of_NYSE_symbols")
                        
                        # Find the table with symbol listings
                        nyse_table = None
                        symbol_col = None
                        
                        for table in tables:
                            if 'Symbol' in table.columns:
                                nyse_table = table
                                symbol_col = 'Symbol'
                                break
                            elif 'Ticker' in table.columns:
                                nyse_table = table
                                symbol_col = 'Ticker'
                                break
                        
                        if nyse_table is not None:
                            nyse_symbols = nyse_table[symbol_col].tolist()
                            
                            # Store stock info in database
                            for symbol in nyse_symbols:
                                self._store_stock_info(
                                    symbol=symbol,
                                    name=None,
                                    exchange="NYSE",
                                    sector=None,
                                    industry=None
                                )
                            
                            symbols = nyse_symbols
                        else:
                            # Fallback to a default list of major NYSE stocks
                            symbols = ["JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "AXP", "USB", "PNC", "COF", "BK", "STT", "SCHW", "DFS"]
                            logger.warning(f"Could not find NYSE symbols table, using fallback list of {len(symbols)} major stocks")
                            
                            # Store basic info for these symbols
                            for symbol in symbols:
                                self._store_stock_info(
                                    symbol=symbol,
                                    name=None,
                                    exchange="NYSE",
                                    sector=None,
                                    industry=None
                                )
                    except Exception as e:
                        # Fallback to a default list of major NYSE stocks
                        symbols = ["JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "AXP", "USB", "PNC", "COF", "BK", "STT", "SCHW", "DFS"]
                        logger.warning(f"Error fetching NYSE symbols: {e}. Using fallback list of {len(symbols)} major stocks")
                        
                        # Store basic info for these symbols
                        for symbol in symbols:
                            self._store_stock_info(
                                symbol=symbol,
                                name=None,
                                exchange="NYSE",
                                sector=None,
                                industry=None
                            )
                
                # Store symbols in Redis
                redis_key = f"symbols_{exch.lower()}"
                self.redis.set(redis_key, json.dumps(symbols))
                logger.info(f"Stored {len(symbols)} symbols for {exch} in Redis")
                
                all_symbols.extend(symbols)
            
            except Exception as e:
                logger.error(f"Error fetching symbols for {exch}: {e}")
        
        # Store all symbols in Redis
        if all_symbols:
            self.redis.set("symbols_all", json.dumps(all_symbols))
            logger.info(f"Stored {len(all_symbols)} symbols in Redis")
        
        return all_symbols
    
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
        elif isinstance(symbols, str) and symbols.lower() in ["sp500", "nasdaq", "nyse"]:
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