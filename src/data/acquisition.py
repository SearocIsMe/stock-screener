"""
Data acquisition module for fetching stock data with free alternatives
Enhanced with multiple free data sources to avoid API rate limits
"""
import os
import json
import logging
import time
import re
import random
from src.utils.logging_config import configure_logging
from datetime import datetime, timedelta
import yaml
import requests
import pandas as pd
import akshare as ak
from sqlalchemy.orm import Session
from .database import get_redis
from .models import Stock, StockPrice, TimeFrame
from .free_data_sources import free_data_sources

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)

# Load configuration
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "config.yaml")
with open(config_path, "r") as config_file:
    config = yaml.safe_load(config_file)

# Load free data configuration
free_data_config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "free_data_config.yaml")
with open(free_data_config_path, "r") as free_config_file:
    free_data_config = yaml.safe_load(free_config_file)

# Constants
REDIS_EXPIRATION = config["database"]["redis"]["expiration_days"] * 86400  # Convert days to seconds
BATCH_SIZE = config["data_fetching"]["yfinance"]["batch_size"]
RETRY_ATTEMPTS = config["data_fetching"]["yfinance"]["retry_attempts"]
RETRY_DELAY = config["data_fetching"]["yfinance"]["retry_delay"]
MAX_BACKOFF_TIME = 120  # Maximum backoff time in seconds
FMP_API_KEY = config.get("data_fetching", {}).get("fmp", {}).get("api_key", "dfiMAaPz1npS81CJctAuUwaajtCzBRsw")  # Default key from sample

class DataAcquisition:
    """Data acquisition class for fetching stock data with free alternatives"""
    
    def __init__(self, db: Session):
        """Initialize data acquisition with database session"""
        self.db = db
        self.redis = get_redis()
        self.use_free_sources = True  # Flag to enable free sources
        self.fmp_rate_limit_exceeded = False  # Track FMP rate limit status
        
    def _make_api_request(self, url, method="GET", params=None, headers=None, data=None, json_data=None,
                          retry_count=RETRY_ATTEMPTS, handle_rate_limit=True):
        """
        Make an API request with robust error handling and free fallback options
        
        Args:
            url: API endpoint URL
            method: HTTP method (GET, POST, etc.)
            params: URL parameters
            headers: HTTP headers
            data: Request body data
            json_data: JSON request body
            retry_count: Number of retry attempts
            handle_rate_limit: Whether to handle rate limiting
            
        Returns:
            Response object or None if all retries failed
        """
        # If FMP rate limit is exceeded and this is an FMP request, log and continue
        if self.fmp_rate_limit_exceeded and "financialmodelingprep.com" in url:
            logger.info("FMP rate limit exceeded, consider using free alternatives")
        headers = headers or {}
        current_retry = 0
        backoff_time = RETRY_DELAY
        
        while current_retry <= retry_count:
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    params=params,
                    headers=headers,
                    data=data,
                    json=json_data,
                    timeout=30  # Set a reasonable timeout
                )
                
                # Check for rate limit headers
                if 'X-Rate-Limit-Remaining' in response.headers:
                    remaining = int(response.headers['X-Rate-Limit-Remaining'])
                    logger.debug(f"Rate limit remaining: {remaining}")
                    
                    # Mark FMP as rate limited if very few requests remaining
                    if remaining < 5 and "financialmodelingprep.com" in url:
                        self.fmp_rate_limit_exceeded = True
                        logger.warning("FMP API approaching rate limit, consider switching to free sources")
                
                if 'X-Rate-Limit-Reset' in response.headers:
                    reset_time = int(response.headers['X-Rate-Limit-Reset'])
                    logger.debug(f"Rate limit resets in: {reset_time} seconds")
                
                # Handle different status codes
                if response.status_code == 200:
                    # Success
                    return response
                elif response.status_code == 429:
                    # Rate limit exceeded - mark FMP as rate limited
                    if "financialmodelingprep.com" in url:
                        self.fmp_rate_limit_exceeded = True
                        logger.warning("FMP API rate limit exceeded, consider using free alternatives")
                    
                    if not handle_rate_limit:
                        logger.error(f"Rate limit exceeded for {url}")
                        return None
                    
                    # Get retry-after header if available
                    retry_after = int(response.headers.get('Retry-After', backoff_time))
                    
                    # Use the larger of retry_after or our calculated backoff
                    wait_time = max(retry_after, backoff_time)
                    
                    # Add some jitter to avoid thundering herd
                    wait_time = min(wait_time + random.uniform(0.1, 1.0), MAX_BACKOFF_TIME)
                    
                    logger.warning(f"Rate limit exceeded. Waiting {wait_time:.2f} seconds before retry. "
                                  f"Consider using free data sources to avoid rate limits.")
                    time.sleep(wait_time)
                    
                    # Increase backoff for next attempt
                    backoff_time = min(backoff_time * 2, MAX_BACKOFF_TIME)
                elif response.status_code == 401:
                    logger.error(f"Authentication error: Invalid API key for {url}")
                    if "financialmodelingprep.com" in url:
                        self.fmp_rate_limit_exceeded = True
                        logger.info("Consider using free data sources as alternatives")
                    return None
                elif response.status_code == 403:
                    logger.error(f"Authorization error: Forbidden access to {url}")
                    if "financialmodelingprep.com" in url:
                        self.fmp_rate_limit_exceeded = True
                        logger.info("Consider using free data sources as alternatives")
                    return None
                elif response.status_code == 404:
                    logger.warning(f"Resource not found: {url}")
                    return None
                elif response.status_code >= 500:
                    # Server error, retry with backoff
                    logger.warning(f"Server error {response.status_code} for {url}. Retrying in {backoff_time} seconds.")
                    time.sleep(backoff_time)
                    backoff_time = min(backoff_time * 2, MAX_BACKOFF_TIME)
                else:
                    # Other error codes
                    logger.error(f"API request failed with status code {response.status_code}: {response.text}")
                    return None
                
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout for {url}. Retrying in {backoff_time} seconds.")
                time.sleep(backoff_time)
                backoff_time = min(backoff_time * 2, MAX_BACKOFF_TIME)
            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection error for {url}. Retrying in {backoff_time} seconds.")
                time.sleep(backoff_time)
                backoff_time = min(backoff_time * 2, MAX_BACKOFF_TIME)
            except Exception as e:
                logger.error(f"Unexpected error making request to {url}: {e}")
                return None
            
            current_retry += 1
        
        logger.error(f"All retry attempts failed for {url}")
        return None
        self.rate_limit_remaining = None
        self.rate_limit_reset = None
        
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
        Get fundamental data with free alternatives to avoid rate limits
        
        Args:
            ticker: Stock symbol
            
        Returns:
            Dictionary with pb, pe, roe, dy, gm (or None if unavailable)
        """
        if not isinstance(ticker, str):
            logger.error(f"Invalid ticker format: {ticker}")
            return {'pb': None, 'pe': None, 'roe': None, 'dy': None, 'gm': None}
        
        try:
            # Method 1: Try Yahoo Finance first (free and reliable)
            logger.debug(f"Trying Yahoo Finance for fundamentals of {ticker}")
            yahoo_fundamentals = free_data_sources.get_stock_fundamentals_yahoo(ticker)
            
            # Check if we got meaningful data from Yahoo
            if any(v is not None for v in yahoo_fundamentals.values()):
                logger.info(f"Successfully got fundamentals for {ticker} from Yahoo Finance")
                return yahoo_fundamentals
            
            # Method 2: Try FMP API only if not rate limited
            if not self.fmp_rate_limit_exceeded:
                logger.debug(f"Trying FMP API for fundamentals of {ticker}")
                try:
                    # Get data from batch methods
                    profiles = self.get_batch_profiles([ticker])
                    key_metrics = self.get_batch_key_metrics([ticker])
                    ratios = self.get_batch_ratios([ticker])
                    
                    # Initialize results
                    results = {'pb': None, 'pe': None, 'roe': None, 'dy': None, 'gm': None}
                    
                    # Extract metrics
                    if ticker in key_metrics:
                        results['pe'] = key_metrics[ticker].get('pe')
                        results['pb'] = key_metrics[ticker].get('pb')
                    
                    # Extract ratios
                    if ticker in ratios:
                        results['roe'] = ratios[ticker].get('roe')
                        results['gm'] = ratios[ticker].get('gm')
                    
                    # Calculate dividend yield
                    if ticker in profiles:
                        last_div = profiles[ticker].get('last_div')
                        price = profiles[ticker].get('price')
                        
                        if last_div is not None and price is not None and price > 0:
                            results['dy'] = (last_div / price) * 100  # Convert to %
                    
                    # If P/B is still None, try to calculate it
                    if results['pb'] is None:
                        results['pb'] = self.get_pb_ratio(ticker)
                    
                    # Round values for readability
                    fmp_results = {k: round(v, 2) if v is not None else None for k, v in results.items()}
                    
                    if any(v is not None for v in fmp_results.values()):
                        logger.info(f"Successfully got fundamentals for {ticker} from FMP API")
                        return fmp_results
                        
                except Exception as e:
                    logger.error(f"Error getting FMP fundamentals for {ticker}: {e}")
            
            # If both methods failed, return Yahoo results (even if all None)
            logger.warning(f"Limited fundamental data available for {ticker}")
            return yahoo_fundamentals
            
        except Exception as e:
            logger.error(f"Error getting enhanced fundamentals for {ticker}: {e}")
            return {'pb': None, 'pe': None, 'roe': None, 'dy': None, 'gm': None}

    def get_pb_ratio(self, ticker):
        """
        Get P/B ratio with free alternatives
        
        Args:
            ticker: Stock symbol
            
        Returns:
            P/B ratio or None if unavailable
        """
        try:
            # Method 1: Try Yahoo Finance first
            yahoo_fundamentals = free_data_sources.get_stock_fundamentals_yahoo(ticker)
            if yahoo_fundamentals.get('pb') is not None:
                logger.debug(f"Got P/B ratio for {ticker} from Yahoo Finance")
                return yahoo_fundamentals['pb']
            
            # Method 2: Try FMP API if not rate limited
            if not self.fmp_rate_limit_exceeded:
                # Try quarterly metrics first (more up-to-date)
                url = f"https://financialmodelingprep.com/api/v3/key-metrics/{ticker}?period=quarter&apikey={FMP_API_KEY}"
                response = self._make_api_request(url)
                
                if response and response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        # Prefer pbRatio (more frequently updated) over priceToBookRatio
                        pb_ratio = data[0].get('pbRatio')
                        if pb_ratio is not None:
                            logger.debug(f"Got P/B ratio for {ticker} from FMP API")
                            return pb_ratio
                
                # If that fails, try to calculate it manually
                return self.get_realtime_pb(ticker)
            
            return None
            
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
            metrics_response = self._make_api_request(metrics_url)
            
            if metrics_response and metrics_response.status_code == 200:
                metrics_data = metrics_response.json()
                if metrics_data and len(metrics_data) > 0:
                    bvps = metrics_data[0].get('bookValuePerShare')
                    
                    # Get real-time price
                    price_url = f"https://financialmodelingprep.com/api/v3/quote-short/{ticker}?apikey={FMP_API_KEY}"
                    price_response = self._make_api_request(price_url)
                    
                    if price_response and price_response.status_code == 200:
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
        Get stock profile information with free alternatives
        
        Args:
            ticker: Stock symbol
            
        Returns:
            Dictionary with stock profile information
        """
        if not isinstance(ticker, str):
            logger.error(f"Invalid ticker format: {ticker}")
            return None
        
        try:
            # Method 1: Try Yahoo Finance first
            logger.debug(f"Trying Yahoo Finance for profile of {ticker}")
            yahoo_profile = free_data_sources.get_stock_profile_yahoo(ticker)
            
            if yahoo_profile and yahoo_profile.get('name'):
                logger.info(f"Successfully got profile for {ticker} from Yahoo Finance")
                return yahoo_profile
            
            # Method 2: Try FMP API only if not rate limited
            if not self.fmp_rate_limit_exceeded:
                logger.debug(f"Trying FMP API for profile of {ticker}")
                try:
                    profiles = self.get_batch_profiles([ticker])
                    
                    if ticker in profiles and profiles[ticker]:
                        logger.info(f"Successfully got profile for {ticker} from FMP API")
                        return profiles[ticker]
                        
                except Exception as e:
                    logger.error(f"Error getting FMP profile for {ticker}: {e}")
            
            # Return Yahoo profile even if incomplete
            return yahoo_profile if yahoo_profile else None
            
        except Exception as e:
            logger.error(f"Error getting enhanced profile for {ticker}: {e}")
            return None

    def get_historical_data(self, ticker, from_date, to_date, interval='1day'):
        """
        Get historical price data with free alternatives to avoid rate limits
        
        Args:
            ticker: Stock symbol
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            interval: Time interval (1day, 1week, 1month)
            
        Returns:
            DataFrame with historical price data
        """
        try:
            # Ensure ticker is a string
            ticker_str = str(ticker)
            
            # Check if this is a Chinese A stock (6 digits, starting with 6, 0, or 3)
            is_chinese_stock = False
            if len(ticker_str) == 6 and (ticker_str.startswith('6') or ticker_str.startswith('0') or ticker_str.startswith('3') or ticker_str.startswith('4') or ticker_str.startswith('8')):
                is_chinese_stock = True
                logger.debug(f"Detected Chinese A stock: {ticker_str}")
                
                # Use akshare to fetch Chinese stock data
                try:
                    # Convert date strings to the format required by akshare (YYYYMMDD)
                    from_date_ak = datetime.strptime(from_date, '%Y-%m-%d').strftime('%Y%m%d')
                    to_date_ak = datetime.strptime(to_date, '%Y-%m-%d').strftime('%Y%m%d')
                    
                    # Determine period based on interval
                    period = "daily"
                    if interval == '1week':
                        period = "weekly"
                    elif interval == '1month':
                        period = "monthly"
                    
                    # Fetch data using akshare
                    stock_data = ak.stock_zh_a_hist(symbol=ticker_str, period=period,
                                                   start_date=from_date_ak, end_date=to_date_ak,
                                                   adjust="qfq")  # qfq = forward adjusted
                    
                    if not stock_data.empty:
                        # Rename columns to match our database schema
                        stock_data = stock_data.rename(columns={
                            '日期': 'date',
                            '开盘': 'open',
                            '收盘': 'close',
                            '最高': 'high',
                            '最低': 'low',
                            '成交量': 'volume',
                            '涨跌幅': 'change_pct',
                            '换手率': 'turnover_rate'
                        })
                        
                        # Convert date column to datetime
                        stock_data['date'] = pd.to_datetime(stock_data['date'])
                        
                        # Set date as index
                        stock_data = stock_data.set_index('date')
                        
                        # Add adjusted_close column (same as close for qfq adjusted data)
                        stock_data['adjusted_close'] = stock_data['close']
                        
                        # Sort by date (newest first)
                        stock_data = stock_data.sort_index(ascending=False)
                        
                        return stock_data
                    else:
                        logger.warning(f"No data found for Chinese stock {ticker_str} using akshare")
                        # Fall back to FMP API if akshare fails
                        is_chinese_stock = False
                
                except Exception as ak_err:
                    logger.error(f"Error fetching Chinese stock data for {ticker_str} using akshare: {ak_err}")
                    # Fall back to FMP API if akshare fails
                    is_chinese_stock = False
            
            # For non-Chinese stocks, try multiple free sources before FMP API
            if not is_chinese_stock:
                # Method 1: Try yfinance first (most reliable and free)
                logger.info(f"Trying yfinance for {ticker_str}")
                yf_data = free_data_sources.get_historical_data_yfinance(
                    ticker_str, from_date, to_date, interval
                )
                
                if not yf_data.empty:
                    logger.info(f"Successfully fetched {ticker_str} data using yfinance")
                    return yf_data
                
                # Method 2: Try pandas-datareader as fallback
                logger.info(f"Trying pandas-datareader for {ticker_str}")
                pdr_data = free_data_sources.get_historical_data_pandas_datareader(
                    ticker_str, from_date, to_date
                )
                
                if not pdr_data.empty:
                    logger.info(f"Successfully fetched {ticker_str} data using pandas-datareader")
                    return pdr_data
                
                # Method 3: Try FMP API only if not rate limited
                if not self.fmp_rate_limit_exceeded:
                    logger.info(f"Trying FMP API for {ticker_str}")
                    # Map interval to FMP API parameter
                    if interval == '1week':
                        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker_str}?from={from_date}&to={to_date}&apikey={FMP_API_KEY}&serietype=line"
                        is_weekly = True
                        is_monthly = False
                    elif interval == '1month':
                        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker_str}?from={from_date}&to={to_date}&apikey={FMP_API_KEY}&serietype=line"
                        is_weekly = False
                        is_monthly = True
                    else:  # Default to daily
                        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker_str}?from={from_date}&to={to_date}&apikey={FMP_API_KEY}"
                        is_weekly = False
                        is_monthly = False
                    
                    response = self._make_api_request(url)
                else:
                    logger.warning(f"FMP API rate limited, skipping for {ticker_str}")
                    response = None
            
            if response and response.status_code == 200:
                data = response.json()
                
                if 'historical' in data and data['historical']:
                    # Convert to DataFrame
                    df = pd.DataFrame(data['historical'])
                    
                    # Log the actual columns for debugging
                    logger.debug(f"Original columns for {ticker_str}: {df.columns.tolist()}")
                    
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
                        logger.warning(f"Missing columns for {ticker_str}: {missing_columns}. Creating them with default values.")
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
                            logger.error(f"Error resampling weekly data for {ticker_str}: {e}")
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
                            logger.error(f"Error resampling monthly data for {ticker_str}: {e}")
                            # Return the daily data if resampling fails
                    
                    return df
            
            # If we get here, something went wrong
            logger.warning(f"No historical data found for {ticker_str}")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting historical data for {ticker_str}: {e}")
            return pd.DataFrame()
            
    def fetch_stock_history(self, symbols, start_date=None, end_date=None, time_frame="daily", days=None):
        """
        Fetch historical stock data for specified symbols
        
        Args:
            symbols: List of stock symbols, market name (e.g., "NASDAQ"), or "all" for all symbols
                    If a list is provided, each element is treated as an individual stock symbol
                    If a string is provided, it's checked against known markets (SP500, NASDAQ, NYSE, AMEX)
                    and expanded to all symbols in that market if it matches
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
                try:
                    # Format dates for FMP API
                    start_str = start_date.strftime('%Y-%m-%d')
                    end_str = end_date.strftime('%Y-%m-%d')
                    
                    # Fetch data from FMP API
                    historical_data = self.get_historical_data(symbol, start_str, end_str, interval)
                    
                    if historical_data.empty:
                        logger.warning(f"No historical data found for {symbol}")
                        results[symbol] = pd.DataFrame()
                    else:
                        # Store data in database
                        self._store_stock_prices(symbol, historical_data, time_frame)
                        results[symbol] = historical_data
                
                except Exception as e:
                    logger.error(f"Error fetching data for {symbol}: {e}")
                    # Continue with next symbol
                
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
                        # Use requests with our robust handler
                        wiki_response = self._make_api_request('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
                        if wiki_response and wiki_response.status_code == 200:
                            sp500_df = pd.read_html(wiki_response.text)[0]
                            symbols = sp500_df['Symbol'].str.replace('.', '-', regex=False).tolist()
                        else:
                            raise Exception("Failed to fetch S&P 500 companies from Wikipedia")
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
    
    def get_batch_profiles(self, symbols):
        """
        Get stock profiles for multiple symbols in a single API call
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dictionary of profiles by symbol
        """
        if not symbols:
            return {}
            
        try:
            # Join symbols with commas for batch request
            symbols_str = ','.join(symbols)
            profile_url = f"https://financialmodelingprep.com/api/v3/profile/{symbols_str}?apikey={FMP_API_KEY}"
            response = self._make_api_request(profile_url)
            
            if response and response.status_code == 200:
                profiles_data = response.json()
                
                # Create a dictionary of profiles by symbol
                profiles = {}
                for profile in profiles_data:
                    symbol = profile.get('symbol')
                    if symbol:
                        profiles[symbol] = {
                            'name': profile.get('companyName'),
                            'exchange': profile.get('exchangeShortName'),
                            'sector': profile.get('sector'),
                            'industry': profile.get('industry'),
                            'description': profile.get('description'),
                            'website': profile.get('website'),
                            'market_cap': profile.get('mktCap'),
                            'price': profile.get('price'),
                            'last_div': profile.get('lastDiv')
                        }
                
                return profiles
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting batch profiles: {e}")
            return {}
    
    def get_batch_key_metrics(self, symbols, period="annual"):
        """
        Get key metrics for multiple symbols in a single API call
        
        Args:
            symbols: List of stock symbols
            period: Period for metrics (annual, quarter)
            
        Returns:
            Dictionary of key metrics by symbol
        """
        if not symbols:
            return {}
            
        try:
            # Join symbols with commas for batch request
            symbols_str = ','.join(symbols)
            metrics_url = f"https://financialmodelingprep.com/api/v3/key-metrics/{symbols_str}?period={period}&apikey={FMP_API_KEY}"
            response = self._make_api_request(metrics_url)
            
            if response and response.status_code == 200:
                metrics_data = response.json()
                
                # Create a dictionary of metrics by symbol
                metrics = {}
                for metric in metrics_data:
                    symbol = metric.get('symbol')
                    if symbol:
                        metrics[symbol] = {
                            'pe': metric.get('peRatioTTM'),
                            'pb': metric.get('pbRatio')
                        }
                
                return metrics
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting batch key metrics: {e}")
            return {}
    
    def get_batch_ratios(self, symbols):
        """
        Get financial ratios for multiple symbols in a single API call
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dictionary of ratios by symbol
        """
        if not symbols:
            return {}
            
        try:
            # Join symbols with commas for batch request
            symbols_str = ','.join(symbols)
            ratios_url = f"https://financialmodelingprep.com/api/v3/ratios-ttm/{symbols_str}?apikey={FMP_API_KEY}"
            response = self._make_api_request(ratios_url)
            
            if response and response.status_code == 200:
                ratios_data = response.json()
                
                # Create a dictionary of ratios by symbol
                ratios = {}
                for ratio in ratios_data:
                    symbol = ratio.get('symbol')
                    if symbol:
                        roe_value = ratio.get('returnOnEquityTTM')
                        gm_value = ratio.get('grossProfitMarginTTM')
                        
                        ratios[symbol] = {
                            'roe': roe_value * 100 if roe_value is not None else None,  # Convert to %
                            'gm': gm_value * 100 if gm_value is not None else None  # Convert to %
                        }
                
                return ratios
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting batch ratios: {e}")
            return {}
    
    def _process_stock_symbols(self, symbols, exchange=None):
        """Process stock symbols to get ticker information and store in database"""
        logger.info(f"Processing {len(symbols)} symbols for ticker information")
        
        # Filter out indices and separate Chinese A stocks
        filtered_symbols = []
        chinese_stocks = []
        
        for symbol in symbols:
            # Skip symbols containing '^' character (indices)
            if '^' in symbol:
                logger.info(f"Skipping index symbol: {symbol}")
                continue
                
            # Check if it's a Chinese A stock (pattern: number.SH or number.SZ)
            chinese_stock_pattern = r'^\d'
            is_chinese_a_stock = bool(re.match(chinese_stock_pattern, symbol))
            
            if is_chinese_a_stock:
                chinese_stocks.append(symbol)
            else:
                filtered_symbols.append(symbol)
        
        # Process Chinese A stocks separately (they don't work well with FMP API)
        for symbol in chinese_stocks:
            logger.info(f"Processing Chinese A stock: {symbol}")
            self._process_chinese_a_stock(symbol, exchange)
        
        # Process regular stocks in batches
        for i in range(0, len(filtered_symbols), BATCH_SIZE):
            batch = filtered_symbols[i:i+BATCH_SIZE]
            logger.info(f"Processing batch {i//BATCH_SIZE + 1}/{(len(filtered_symbols)-1)//BATCH_SIZE + 1} ({len(batch)} symbols)")
            
            try:
                # Get batch data from FMP API
                profiles = self.get_batch_profiles(batch)
                key_metrics = self.get_batch_key_metrics(batch)
                ratios = self.get_batch_ratios(batch)
                
                # Process each symbol in the batch
                for symbol in batch:
                    try:
                        profile = profiles.get(symbol, {})
                        metrics = key_metrics.get(symbol, {})
                        ratio = ratios.get(symbol, {})
                        
                        # Combine data from different endpoints
                        fundamentals = {
                            'pe': metrics.get('pe'),
                            'pb': metrics.get('pb'),
                            'roe': ratio.get('roe'),
                            'gm': ratio.get('gm'),
                            'dy': None
                        }
                        
                        # Calculate dividend yield if possible
                        last_div = profile.get('last_div')
                        price = profile.get('price')
                        if last_div is not None and price is not None and price > 0:
                            fundamentals['dy'] = (last_div / price) * 100  # Convert to %
                        
                        # Skip if no profile data found
                        if not profile:
                            logger.warning(f"[ERROR] No profile data found for {symbol}")
                            continue
                        
                        # Store in database
                        self._store_stock_info(
                            symbol=symbol,
                            name=profile.get('name'),
                            exchange=profile.get('exchange', exchange),
                            sector=profile.get('sector'),
                            industry=profile.get('industry'),
                            gross_margin=fundamentals.get('gm'),
                            roe=fundamentals.get('roe'),
                            rd_ratio=None,  # Not available in FMP API
                            pe_ratio=fundamentals.get('pe'),
                            pb_ratio=fundamentals.get('pb'),
                            dividend_yield=fundamentals.get('dy')
                        )
                    except Exception as e:
                        logger.warning(f"Error processing data for {symbol}: {e}")
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
            
            except Exception as e:
                logger.error(f"Error processing batch: {e}")
                # Store basic info for all symbols in the batch
                for symbol in batch:
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

    
    def _process_chinese_a_stock(self, symbol, exchange=None):
        """
        Process Chinese A stock information using akshare library
        
        Args:
            symbol: Stock symbol (e.g., '600000' for Shanghai or '000001' for Shenzhen)
            exchange: Exchange code (optional)
            
        Returns:
            Stock object if successful, None otherwise
        """
        try:
            logger.info(f"Fetching Chinese A stock data for {symbol} using akshare")
            
            # Determine the full symbol with exchange prefix if needed
            # Ensure symbol is a string
            symbol_str = str(symbol)
            if len(symbol_str) == 6:
                if symbol_str.startswith('6'):
                    full_symbol = f"sh{symbol_str}"  # Shanghai
                elif symbol_str.startswith('0') or symbol_str.startswith('3'):
                    full_symbol = f"sz{symbol_str}"  # Shenzhen
                else:
                    full_symbol = symbol
            else:
                full_symbol = symbol
                
            # Fetch stock profile information
            try:
                # Get stock information
                stock_info = ak.stock_individual_info_em(symbol=symbol)
                
                if not stock_info.empty:
                    # Extract company name
                    company_name = None
                    for _, row in stock_info.iterrows():
                        if row[0] == "股票简称" or row[0] == "名称":  # Stock name
                            company_name = row[1]
                            break
                    
                    # Extract industry information
                    industry = None
                    sector = None
                    for _, row in stock_info.iterrows():
                        if row[0] == "所属行业":  # Industry
                            industry = row[1]
                            break
                    
                    # Get financial metrics
                    try:
                        # Fetch financial indicators
                        financial_data = ak.stock_financial_analysis_indicator(symbol=symbol)
                        
                        # Extract latest metrics
                        if not financial_data.empty:
                            latest_data = financial_data.iloc[0]
                            
                            # Extract ROE (Return on Equity)
                            roe = None
                            if "净资产收益率(%)" in latest_data:
                                roe = latest_data["净资产收益率(%)"]
                            elif "加权净资产收益率(%)" in latest_data:
                                roe = latest_data["加权净资产收益率(%)"]
                                
                            # Extract Gross Margin
                            gross_margin = None
                            if "销售毛利率(%)" in latest_data:
                                gross_margin = latest_data["销售毛利率(%)"]
                                
                            # Get P/E and P/B ratios from real-time quotes
                            quote_data = ak.stock_zh_a_spot_em()
                            stock_quote = quote_data[quote_data['代码'] == symbol]
                            
                            pe_ratio = None
                            pb_ratio = None
                            dividend_yield = None
                            
                            if not stock_quote.empty:
                                if '市盈率-动态' in stock_quote.columns:
                                    pe_ratio = stock_quote['市盈率-动态'].values[0]
                                if '市净率' in stock_quote.columns:
                                    pb_ratio = stock_quote['市净率'].values[0]
                                if '涨跌幅' in stock_quote.columns and '现价' in stock_quote.columns:
                                    # Calculate dividend yield if available
                                    try:
                                        dividend_data = ak.stock_history_dividend_detail(symbol=symbol, indicator="分红")
                                        if not dividend_data.empty and '分红金额' in dividend_data.columns:
                                            latest_dividend = dividend_data['分红金额'].iloc[0]
                                            current_price = stock_quote['现价'].values[0]
                                            if latest_dividend > 0 and current_price > 0:
                                                dividend_yield = (latest_dividend / current_price) * 100
                                    except Exception as div_err:
                                        logger.debug(f"Could not fetch dividend data for {symbol}: {div_err}")
                        
                    except Exception as fin_err:
                        logger.warning(f"Error fetching financial metrics for {symbol}: {fin_err}")
                        roe = None
                        gross_margin = None
                        pe_ratio = None
                        pb_ratio = None
                        dividend_yield = None
                    
                    # Store stock information
                    stock = self._store_stock_info(
                        symbol=symbol,
                        name=company_name,
                        exchange="ACN",  # Chinese A stock
                        sector=sector,
                        industry=industry,
                        gross_margin=gross_margin,
                        roe=roe,
                        rd_ratio=None,  # R&D ratio not readily available
                        pe_ratio=pe_ratio,
                        pb_ratio=pb_ratio,
                        dividend_yield=dividend_yield
                    )
                    
                    # Fetch historical price data
                    self._fetch_chinese_stock_prices(symbol, full_symbol)
                    
                    return stock
                    
            except Exception as info_err:
                logger.warning(f"Error fetching stock info for {symbol}: {info_err}")
            
            # If we reach here, we couldn't get detailed information
            # Store minimal information
            stock = self._store_stock_info(
                symbol=symbol,
                name=None,
                exchange="ACN",
                sector="Chinese A Stock",
                industry=None,
                gross_margin=None,
                roe=None,
                rd_ratio=None,
                pe_ratio=None,
                pb_ratio=None,
                dividend_yield=None
            )
            
            # Still try to fetch price data with minimal info
            symbol_str = str(symbol)  # Ensure symbol is a string
            self._fetch_chinese_stock_prices(symbol_str, full_symbol if 'full_symbol' in locals() else f"sh{symbol_str}" if symbol_str.startswith('6') else f"sz{symbol_str}")
            
            return stock
            
        except Exception as e:
            logger.error(f"Error processing Chinese A stock {symbol}: {e}")
            # Store minimal information as fallback
            return self._store_stock_info(
                symbol=symbol,
                name=None,
                exchange=exchange or "ACN",
                sector=None,
                industry=None,
                gross_margin=None,
                roe=None,
                rd_ratio=None,
                pe_ratio=None,
                pb_ratio=None,
                dividend_yield=None
            )
    
    def _fetch_chinese_stock_prices(self, symbol, full_symbol):
        """
        Fetch historical price data for Chinese A stocks using akshare
        
        Args:
            symbol: Stock symbol without exchange prefix (e.g., '600000')
            full_symbol: Stock symbol with exchange prefix (e.g., 'sh600000')
        """
        try:
            # Ensure symbols are strings
            symbol_str = str(symbol)
            full_symbol_str = str(full_symbol)
            
            # Get daily price data for the past year
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
            
            # Fetch daily K-line data
            daily_data = ak.stock_zh_a_hist(symbol=symbol_str, period="daily",
                                           start_date=start_date, end_date=end_date,
                                           adjust="qfq")  # qfq = forward adjusted
            
            if not daily_data.empty:
                # Rename columns to match our database schema
                daily_data = daily_data.rename(columns={
                    '日期': 'date',
                    '开盘': 'open',
                    '收盘': 'close',
                    '最高': 'high',
                    '最低': 'low',
                    '成交量': 'volume'
                })
                
                # Convert date column to datetime
                daily_data['date'] = pd.to_datetime(daily_data['date'])
                
                # Set date as index
                daily_data = daily_data.set_index('date')
                
                # Store daily data
                self._store_stock_prices(symbol_str, daily_data, TimeFrame.DAILY)
                
                # Create weekly data by resampling
                weekly_data = daily_data.resample('W').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                })
                
                # Store weekly data
                self._store_stock_prices(symbol_str, weekly_data, TimeFrame.WEEKLY)
                
                # Create monthly data by resampling
                monthly_data = daily_data.resample('M').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                })
                
                # Store monthly data
                self._store_stock_prices(symbol_str, monthly_data, TimeFrame.MONTHLY)
                
                logger.info(f"Successfully fetched and stored price data for Chinese A stock {symbol_str}")
            else:
                logger.warning(f"No price data found for Chinese A stock {symbol_str}")
                
        except Exception as e:
            logger.error(f"Error fetching price data for Chinese A stock {symbol_str}: {e}")
