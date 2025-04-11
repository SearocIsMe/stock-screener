"""
Data acquisition module for fetching stock data from Financial Modeling Prep API
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
FMP_API_KEY = config.get("data_fetching", {}).get("fmp", {}).get("api_key", "dfiMAaPz1npS81CJctAuUwaajtCzBRsw")  # Default key from sample

class DataAcquisition:
    """Data acquisition class for fetching stock data"""
    
    def __init__(self, db: Session):
        """Initialize data acquisition with database session"""
        self.db = db
        self.redis = get_redis()
        
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
                
                # Create price data dictionary
                price_data = {
                    'open': row.get('open', None),
                    'high': row.get('high', None),
                    'low': row.get('low', None),
                    'close': row.get('close', None),
                    'volume': row.get('volume', 0)
                }
                
                # Check for essential columns (open, high, low, close)
                essential_columns = ['open', 'high', 'low', 'close']
                missing_essential = [col for col in essential_columns if col not in price_data or price_data[col] is None]
                
                # If any essential column is missing, try to fill with available data
                if missing_essential:
                    # If we have close but missing others, use close for all
                    if 'close' in price_data and price_data['close'] is not None:
                        close_value = price_data['close']
                        for col in missing_essential:
                            if col != 'close':
                                price_data[col] = close_value
                    # If we have open but missing others, use open for all
                    elif 'open' in price_data and price_data['open'] is not None:
                        open_value = price_data['open']
                        for col in missing_essential:
                            price_data[col] = open_value
                    else:
                        # Still missing essential columns
                        logger.warning(f"Skipping row for {symbol} at {date}: missing essential price columns")
                        continue
                
                # Volume is optional, set to 0 if missing
                if 'volume' not in price_data or price_data['volume'] is None:
                    price_data['volume'] = 0
                
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
                    # Set adjusted_close (when auto_adjust=True, Close is already adjusted)
                    existing_price.adjusted_close = price_data['close']
                    
                    # Convert volume to int, with fallback to 0 if conversion fails
                    try:
                        vol_value = price_data['volume']
                        if pd.isna(vol_value) or vol_value is None:
                            existing_price.volume = 0
                        else:
                            existing_price.volume = int(float(vol_value))
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Volume conversion error for {symbol} at {date}: {e}, using 0")
                        existing_price.volume = 0
                else:
                    # Create new price with proper error handling
                    try:
                        # Get adjusted close (same as close when auto_adjust=True)
                        adjusted_close = price_data.get('close', 0)
                        
                        # Get volume with proper conversion
                        volume = 0
                        if 'volume' in price_data and not pd.isna(price_data['volume']):
                            try:
                                volume = int(float(price_data['volume']))
                            except (ValueError, TypeError):
                                volume = 0
                        
                        # Create the price record
                        price = StockPrice(
                            stock_id=stock.id,
                            date=date,
                            open=price_data.get('open', 0),
                            high=price_data.get('high', 0),
                            low=price_data.get('low', 0),
                            close=price_data.get('close', 0),
                            adjusted_close=adjusted_close,
                            volume=volume,
                            time_frame=time_frame
                        )
                        self.db.add(price)
                    except Exception as e:
                        logger.warning(f"Error creating price record for {symbol} at {date}: {e}")
                        continue
            
            self.db.commit()
            logger.info(f"Successfully stored prices for {symbol} ({time_frame})")
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error storing prices for {symbol}: {e}")
            
    def _store_stock_info(self, symbol, name=None, exchange=None, sector=None, industry=None, 
                         gross_margin=None, roe=None, rd_ratio=None, pe_ratio=None, pb_ratio=None, 
                         dividend_yield=None):
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
                    rd_ratio=rd_ratio,
                    pe_ratio=pe_ratio,
                    pb_ratio=pb_ratio,
                    dividend_yield=dividend_yield
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
                if pe_ratio is not None:
                    stock.pe_ratio = pe_ratio
                if pb_ratio is not None:
                    stock.pb_ratio = pb_ratio
                if dividend_yield is not None:
                    stock.dividend_yield = dividend_yield
                stock.updated_at = datetime.utcnow()
            
            self.db.commit()
            return stock
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error storing stock info for {symbol}: {e}")
            return None
            
    def get_fundamentals(self, ticker):
        """
        Get fundamental data for a stock from FMP API
        
        Args:
            ticker: Stock symbol
            
        Returns:
            Dictionary with pb, pe, roe, dy, gm (or None if unavailable)
        """
        results = {'pb': None, 'pe': None, 'roe': None, 'dy': None, 'gm': None}
        
        try:
            # Get P/B and P/E from Key Metrics endpoint
            metric_url = f"https://financialmodelingprep.com/api/v3/key-metrics/{ticker}?period=annual&apikey={FMP_API_KEY}"
            metric_response = requests.get(metric_url)
            
            if metric_response.status_code == 200:
                metric_data = metric_response.json()
                if metric_data:
                    results['pe'] = metric_data[0].get('peRatioTTM')
                    results['pb'] = metric_data[0].get('pbRatio')
            
            # Get ROE and Gross Margin from Ratios endpoint
            ratios_url = f"https://financialmodelingprep.com/api/v3/ratios-ttm/{ticker}?apikey={FMP_API_KEY}"
            ratios_response = requests.get(ratios_url)
            
            if ratios_response.status_code == 200:
                ratios_data = ratios_response.json()
                if ratios_data:
                    roe_value = ratios_data[0].get('returnOnEquityTTM')
                    if roe_value is not None:
                        results['roe'] = roe_value * 100  # Convert to %
                    
                    gm_value = ratios_data[0].get('grossProfitMarginTTM')
                    if gm_value is not None:
                        results['gm'] = gm_value * 100  # Convert to %
            
            # Get Dividend Yield from Profile endpoint
            profile_url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={FMP_API_KEY}"
            profile_response = requests.get(profile_url)
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                if profile_data:
                    last_div = profile_data[0].get('lastDiv')
                    price = profile_data[0].get('price')
                    
                    if last_div is not None and price is not None and price > 0:
                        results['dy'] = (last_div / price) * 100  # Convert to %
            
            # If P/B is still None, try to calculate it
            if results['pb'] is None:
                results['pb'] = self.get_pb_ratio(ticker)
            
            # Round values for readability
            return {k: round(v, 2) if v is not None else None for k, v in results.items()}
            
        except Exception as e:
            logger.error(f"Error getting fundamentals for {ticker}: {e}")
            return results

    def get_pb_ratio(self, ticker):
        """
        Get P/B ratio for a stock from FMP API
        
        Args:
            ticker: Stock symbol
            
        Returns:
            P/B ratio or None if unavailable
        """
        try:
            # Try quarterly metrics first (more up-to-date)
            url = f"https://financialmodelingprep.com/api/v3/key-metrics/{ticker}?period=quarter&apikey={FMP_API_KEY}"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    # Prefer pbRatio (more frequently updated) over priceToBookRatio
                    return data[0].get('pbRatio')
            
            # If that fails, try to calculate it manually
            return self.get_realtime_pb(ticker)
            
        except Exception as e:
            logger.error(f"Error getting P/B ratio for {ticker}: {e}")
            return None

    def get_realtime_pb(self, ticker):
        """
        Calculate real-time P/B ratio using latest book value and current price
        
        Args:
            ticker: Stock symbol
            
        Returns:
            P/B ratio or None if unavailable
        """
        try:
            # Get latest book value per share
            metrics_url = f"https://financialmodelingprep.com/api/v3/key-metrics/{ticker}?limit=1&apikey={FMP_API_KEY}"
            metrics_response = requests.get(metrics_url)
            
            if metrics_response.status_code == 200:
                metrics_data = metrics_response.json()
                if metrics_data and len(metrics_data) > 0:
                    bvps = metrics_data[0].get('bookValuePerShare')
                    
                    # Get real-time price
                    price_url = f"https://financialmodelingprep.com/api/v3/quote-short/{ticker}?apikey={FMP_API_KEY}"
                    price_response = requests.get(price_url)
                    
                    if price_response.status_code == 200:
                        price_data = price_response.json()
                        if price_data and len(price_data) > 0:
                            price = price_data[0].get('price')
                            
                            if bvps is not None and price is not None and bvps > 0:
                                return round(price / bvps, 2)
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculating real-time P/B ratio for {ticker}: {e}")
            return None
            
    def get_stock_profile(self, ticker):
        """
        Get stock profile information from FMP API
        
        Args:
            ticker: Stock symbol
            
        Returns:
            Dictionary with stock profile information
        """
        try:
            profile_url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={FMP_API_KEY}"
            response = requests.get(profile_url)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    profile = data[0]
                    return {
                        'name': profile.get('companyName'),
                        'exchange': profile.get('exchangeShortName'),
                        'sector': profile.get('sector'),
                        'industry': profile.get('industry'),
                        'description': profile.get('description'),
                        'website': profile.get('website'),
                        'market_cap': profile.get('mktCap'),
                        'price': profile.get('price')
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting stock profile for {ticker}: {e}")
            return None

    def get_historical_data(self, ticker, from_date, to_date, interval='1day'):
        """
        Get historical price data from FMP API
        
        Args:
            ticker: Stock symbol
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            interval: Time interval (1day, 1week, 1month)
            
        Returns:
            DataFrame with historical price data
        """
        try:
            # Map interval to FMP API parameter
            if interval == '1week':
                url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}?from={from_date}&to={to_date}&apikey={FMP_API_KEY}&serietype=line"
                is_weekly = True
                is_monthly = False
            elif interval == '1month':
                url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}?from={from_date}&to={to_date}&apikey={FMP_API_KEY}&serietype=line"
                is_weekly = False
                is_monthly = True
            else:  # Default to daily
                url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}?from={from_date}&to={to_date}&apikey={FMP_API_KEY}"
                is_weekly = False
                is_monthly = False
            
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'historical' in data and data['historical']:
                    # Convert to DataFrame
                    df = pd.DataFrame(data['historical'])
                    
                    # Log the actual columns for debugging
                    logger.debug(f"Original columns for {ticker}: {df.columns.tolist()}")
                    
                    # Check if expected columns exist and create them if they don't
                    expected_columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'adjClose']
                    for col in expected_columns:
                        if col not in df.columns:
                            if col == 'adjClose':
                                # If adjClose is missing, use close
                                if 'close' in df.columns:
                                    df['adjClose'] = df['close']
                                else:
                                    df['adjClose'] = 0
                            elif col == 'volume':
                                # If volume is missing, use 0
                                df['volume'] = 0
                            elif col in ['open', 'high', 'low', 'close']:
                                # For OHLC, try to fill with available data
                                if 'close' in df.columns:
                                    df[col] = df['close']
                                else:
                                    df[col] = 0
                            elif col != 'date':  # Skip date as it's required
                                df[col] = 0
                    
                    # Rename columns to match our expected format
                    df = df.rename(columns={
                        'date': 'date',
                        'open': 'open',
                        'high': 'high',
                        'low': 'low',
                        'close': 'close',
                        'volume': 'volume',
                        'adjClose': 'adjusted_close'
                    })
                    
                    # Convert date to datetime
                    df['date'] = pd.to_datetime(df['date'])
                    
                    # Set date as index
                    df.set_index('date', inplace=True)
                    
                    # Sort by date (newest first)
                    df = df.sort_index(ascending=False)
                    
                    # Verify all required columns exist before resampling
                    required_columns = ['open', 'high', 'low', 'close', 'adjusted_close', 'volume']
                    missing_columns = [col for col in required_columns if col not in df.columns]
                    
                    if missing_columns:
                        logger.warning(f"Missing columns for {ticker}: {missing_columns}. Creating them with default values.")
                        for col in missing_columns:
                            if col == 'adjusted_close' and 'close' in df.columns:
                                df['adjusted_close'] = df['close']
                            else:
                                df[col] = 0
                    
                    # For weekly or monthly data, we need to resample
                    if is_weekly:
                        try:
                            # Resample to weekly frequency
                            df = df.resample('W').agg({
                                'open': 'first',
                                'high': 'max',
                                'low': 'min',
                                'close': 'last',
                                'adjusted_close': 'last',
                                'volume': 'sum'
                            })
                        except Exception as e:
                            logger.error(f"Error resampling weekly data for {ticker}: {e}")
                            # Return the daily data if resampling fails
                    elif is_monthly:
                        try:
                            # Resample to monthly frequency
                            df = df.resample('M').agg({
                                'open': 'first',
                                'high': 'max',
                                'low': 'min',
                                'close': 'last',
                                'adjusted_close': 'last',
                                'volume': 'sum'
                            })
                        except Exception as e:
                            logger.error(f"Error resampling monthly data for {ticker}: {e}")
                            # Return the daily data if resampling fails
                    
                    return df
            
            # If we get here, something went wrong
            logger.warning(f"No historical data found for {ticker}")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting historical data for {ticker}: {e}")
            return pd.DataFrame()
            
    def fetch_stock_history(self, symbols, start_date=None, end_date=None, time_frame="daily", days=None):
        """
        Fetch historical stock data for specified symbols
        
        Args:
            symbols: List of stock symbols or "all" for all symbols
            start_date: Start date for historical data (default: 1 year ago)
            end_date: End date for historical data (default: today)
            time_frame: Time frame for data (daily, weekly, monthly)
            days: Number of days of historical data to fetch (overrides start_date if provided)
        
        Returns:
            Dictionary of stock data by symbol
        """
        # Set default dates if not provided
        if not end_date:
            end_date = datetime.now()
        elif isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        # If days parameter is provided, calculate start_date based on days
        if days is not None:
            start_date = end_date - timedelta(days=days)
        elif not start_date:
            # Default time ranges if neither start_date nor days is provided
            if time_frame == "daily":
                start_date = end_date - timedelta(days=365)  # 1 year of daily data
            elif time_frame == "weekly":
                start_date = end_date - timedelta(days=365 * 2)  # 2 years of weekly data
            elif time_frame == "monthly":
                start_date = end_date - timedelta(days=365 * 5)  # 5 years of monthly data
        elif isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        
        # Convert time_frame to FMP interval
        interval = "1day"  # default daily
        if time_frame == "weekly":
            interval = "1week"
        elif time_frame == "monthly":
            interval = "1month"
        
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
        elif isinstance(symbols, str):
            # Single symbol as string
            symbols = [symbols]
        
        # Fetch data in batches
        results = {}
        for i in range(0, len(symbols), BATCH_SIZE):
            batch = symbols[i:i+BATCH_SIZE]
            logger.info(f"Fetching historical data for batch {i//BATCH_SIZE + 1}/{(len(symbols)-1)//BATCH_SIZE + 1} ({len(batch)} symbols)")
            
            for symbol in batch:
                for attempt in range(RETRY_ATTEMPTS):
                    try:
                        # Format dates for FMP API
                        start_str = start_date.strftime('%Y-%m-%d')
                        end_str = end_date.strftime('%Y-%m-%d')
                        
                        # Fetch data from FMP API
                        historical_data = self.get_historical_data(symbol, start_str, end_str, interval)
                        
                        if historical_data.empty:
                            logger.warning(f"No historical data found for {symbol}")
                            results[symbol] = pd.DataFrame()
                            break
                        
                        # Store data in database
                        self._store_stock_prices(symbol, historical_data, time_frame)
                        results[symbol] = historical_data
                        
                        # Break retry loop if successful
                        break
                    
                    except Exception as e:
                        logger.error(f"Error fetching data for {symbol} (attempt {attempt+1}/{RETRY_ATTEMPTS}): {e}")
                        if attempt < RETRY_ATTEMPTS - 1:
                            time.sleep(RETRY_DELAY)
                
                # Sleep to avoid rate limiting
                time.sleep(1)
        
        return results
        
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
        self._process_stock_symbols(all_symbols)
        
        return all_symbols
    
    def _process_stock_symbols(self, symbols, exchange=None):
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
                        # Get stock info from FMP API for non-Chinese stocks
                        fundamentals = self.get_fundamentals(symbol)
                        profile = self.get_stock_profile(symbol)
                        
                        if not profile:
                            logger.warning(f"[ERROR] No profile data found for {symbol}")
                            continue
                        
                        # Store in database
                        self._store_stock_info(
                            symbol=symbol,
                            name=profile.get('name', None),
                            exchange=profile.get('exchange', exchange),
                            sector=profile.get('sector', None),
                            industry=profile.get('industry', None),
                            gross_margin=fundamentals.get('gm', None),
                            roe=fundamentals.get('roe', None),
                            rd_ratio=None,  # Not available in FMP API
                            pe_ratio=fundamentals.get('pe', None),
                            pb_ratio=fundamentals.get('pb', None),
                            dividend_yield=fundamentals.get('dy', None)
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
                        rd_ratio=None,
                        pe_ratio=None,
                        pb_ratio=None,
                        dividend_yield=None
                    )
                    # Sleep to avoid rate limiting
                    time.sleep(5)
    
    def _process_chinese_a_stock(self, symbol, exchange=None):
        """Process Chinese A stock information using alternative methods"""
        try:
            # For Chinese A stocks, we'll just store minimal information
            # as FMP API doesn't support Chinese A stocks well
            self._store_stock_info(
                symbol=symbol,
                name=None,
                exchange="ACN",
                sector=f"Chinese A Stock",
                industry=None,
                gross_margin=None,
                roe=None,
                rd_ratio=None,
                pe_ratio=None,
                pb_ratio=None,
                dividend_yield=None
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
                rd_ratio=None,
                pe_ratio=None,
                pb_ratio=None,
                dividend_yield=None
            )
