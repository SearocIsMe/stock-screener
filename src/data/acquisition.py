"""
Unified data acquisition module with enhanced free alternatives
This module consolidates all data acquisition functionality with configurable fallbacks
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
REDIS_EXPIRATION = config["database"]["redis"]["expiration_days"] * 86400
BATCH_SIZE = config["data_fetching"]["yfinance"]["batch_size"]
RETRY_ATTEMPTS = config["data_fetching"]["yfinance"]["retry_attempts"]
RETRY_DELAY = config["data_fetching"]["yfinance"]["retry_delay"]
MAX_BACKOFF_TIME = 120
FMP_API_KEY = config.get("data_fetching", {}).get("fmp", {}).get("api_key", "dfiMAaPz1npS81CJctAuUwaajtCzBRsw")

class DataAcquisition:
    """Unified data acquisition class with enhanced free alternatives"""
    
    def __init__(self, db: Session):
        """Initialize data acquisition with database session"""
        self.db = db
        self.redis = get_redis()
        self.use_free_sources = True
        self.fmp_rate_limit_exceeded = False
        
    def _make_api_request(self, url, method="GET", params=None, headers=None, 
                         data=None, json_data=None, retry_count=RETRY_ATTEMPTS, 
                         handle_rate_limit=True, use_free_fallback=True):
        """
        Enhanced API request with free fallback options
        
        Args:
            url: API endpoint URL
            method: HTTP method
            params: URL parameters
            headers: HTTP headers
            data: Request body data
            json_data: JSON request body
            retry_count: Number of retry attempts
            handle_rate_limit: Whether to handle rate limiting
            use_free_fallback: Whether to use free alternatives on failure
            
        Returns:
            Response object or None if all attempts failed
        """
        # If FMP rate limit is exceeded and this is an FMP request, skip directly to free sources
        if self.fmp_rate_limit_exceeded and "financialmodelingprep.com" in url and use_free_fallback:
            logger.info("FMP rate limit exceeded, using free alternatives directly")
            return None
            
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
                    timeout=30
                )
                
                # Check for rate limit headers
                if 'X-Rate-Limit-Remaining' in response.headers:
                    remaining = int(response.headers['X-Rate-Limit-Remaining'])
                    logger.debug(f"Rate limit remaining: {remaining}")
                    
                    # Mark FMP as rate limited if very few requests remaining
                    if remaining < 5 and "financialmodelingprep.com" in url:
                        self.fmp_rate_limit_exceeded = True
                        logger.warning("FMP API approaching rate limit, consider switching to free sources")
                
                # Handle different response codes
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:  # Rate limited
                    if handle_rate_limit:
                        if "financialmodelingprep.com" in url:
                            self.fmp_rate_limit_exceeded = True
                            logger.warning("FMP API rate limited, marking for free source usage")
                        
                        retry_after = response.headers.get('Retry-After')
                        if retry_after:
                            wait_time = min(int(retry_after), MAX_BACKOFF_TIME)
                        else:
                            wait_time = min(backoff_time, MAX_BACKOFF_TIME)
                        
                        logger.warning(f"Rate limited, waiting {wait_time}s before retry {current_retry + 1}/{retry_count}")
                        time.sleep(wait_time)
                        backoff_time *= 2  # Exponential backoff
                    else:
                        logger.error(f"Rate limited and rate limit handling disabled: {response.status_code}")
                        return None
                elif response.status_code in [401, 403]:  # Authentication/authorization errors
                    logger.error(f"Authentication error: {response.status_code} - {response.text}")
                    if "financialmodelingprep.com" in url:
                        self.fmp_rate_limit_exceeded = True
                    return None
                elif response.status_code >= 500:  # Server errors
                    logger.warning(f"Server error {response.status_code}, retrying...")
                else:
                    logger.warning(f"Unexpected status code: {response.status_code}")
                    return response  # Return anyway, let caller handle
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout for {url}, retry {current_retry + 1}/{retry_count}")
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Connection error for {url}: {e}, retry {current_retry + 1}/{retry_count}")
            except Exception as e:
                logger.error(f"Unexpected error for {url}: {e}")
                return None
                
            current_retry += 1
            if current_retry <= retry_count:
                time.sleep(min(backoff_time, MAX_BACKOFF_TIME))
                backoff_time *= 2
        
        logger.error(f"All retries failed for {url}")
        return None

    def _store_stock_prices(self, symbol, data, time_frame):
        """Store stock prices in database"""
        try:
            if data.empty:
                logger.warning(f"No data to store for {symbol}")
                return
            
            # Get or create stock
            stock = self.db.query(Stock).filter(Stock.symbol == symbol).first()
            if not stock:
                stock = Stock(symbol=symbol)
                self.db.add(stock)
                self.db.commit()
                self.db.refresh(stock)
            
            # Get time frame enum
            time_frame_enum = TimeFrame.DAILY
            if time_frame.lower() in ['weekly', 'week']:
                time_frame_enum = TimeFrame.WEEKLY
            elif time_frame.lower() in ['monthly', 'month']:
                time_frame_enum = TimeFrame.MONTHLY
            
            stored_count = 0
            for date, row in data.iterrows():
                try:
                    # Convert date to datetime if it's not already
                    if isinstance(date, str):
                        price_date = datetime.strptime(date, '%Y-%m-%d').date()
                    elif hasattr(date, 'date'):
                        price_date = date.date()
                    else:
                        price_date = date
                    
                    # Check if price already exists
                    existing_price = self.db.query(StockPrice).filter(
                        StockPrice.stock_id == stock.id,
                        StockPrice.date == price_date,
                        StockPrice.time_frame == time_frame_enum
                    ).first()
                    
                    # Prepare price data
                    price_data = {
                        'open': float(row.get('Open', row.get('open', 0))),
                        'high': float(row.get('High', row.get('high', 0))),
                        'low': float(row.get('Low', row.get('low', 0))),
                        'close': float(row.get('Close', row.get('close', row.get('Adj Close', 0)))),
                        'volume': int(row.get('Volume', row.get('volume', 0)))
                    }
                    
                    if existing_price:
                        # Update existing price
                        try:
                            existing_price.open = price_data['open']
                            existing_price.high = price_data['high']
                            existing_price.low = price_data['low']
                            existing_price.close = price_data['close']
                            existing_price.volume = price_data['volume']
                            existing_price.updated_at = datetime.now()
                        except Exception as e:
                            logger.error(f"Error updating price for {symbol} on {price_date}: {e}")
                            continue
                    else:
                        # Create new price record
                        try:
                            new_price = StockPrice(
                                stock_id=stock.id,
                                date=price_date,
                                time_frame=time_frame_enum,
                                **price_data
                            )
                            try:
                                self.db.add(new_price)
                                stored_count += 1
                            except Exception as e:
                                logger.error(f"Error adding new price for {symbol}: {e}")
                                continue
                        except Exception as e:
                            logger.error(f"Error creating price record for {symbol}: {e}")
                            continue
                            
                except Exception as e:
                    logger.error(f"Error processing price data for {symbol} on {date}: {e}")
                    continue
            
            # Commit all changes
            self.db.commit()
            logger.info(f"Stored {stored_count} price records for {symbol}")
            
        except Exception as e:
            logger.error(f"Error storing stock prices for {symbol}: {e}")
            self.db.rollback()

    def _store_stock_info(self, symbol, name=None, exchange=None, sector=None, industry=None, 
                         market_cap=None, country=None):
        """Store stock information in database"""
        try:
            stock = self.db.query(Stock).filter(Stock.symbol == symbol).first()
            if not stock:
                stock = Stock(symbol=symbol)
                self.db.add(stock)
            
            # Update stock information
            if name:
                stock.name = name
            if exchange:
                stock.exchange = exchange
            if sector:
                stock.sector = sector
            if industry:
                stock.industry = industry
            if market_cap:
                stock.market_cap = market_cap
            if country:
                stock.country = country
            
            stock.updated_at = datetime.now()
            self.db.commit()
            logger.debug(f"Updated stock info for {symbol}")
            
        except Exception as e:
            logger.error(f"Error storing stock info for {symbol}: {e}")
            self.db.rollback()

    def get_fundamentals(self, ticker):
        """
        Get fundamental data with enhanced free alternatives
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            dict: Fundamental data or None if not available
        """
        try:
            # Check if free data config is available and enabled
            if (free_data_config and 
                free_data_config.get('enabled', True) and 
                'fundamentals' in free_data_config.get('free_data_sources', {}).get('priority', {})):
                
                priority_sources = free_data_config['free_data_sources']['priority']['fundamentals']
                logger.info(f"Using configured priority sources for {ticker} fundamentals: {priority_sources}")
                
                for source in priority_sources:
                    if source == 'fmp_api':
                        result = self._get_fmp_fundamentals(ticker)
                        if result:
                            logger.info(f"Successfully got fundamentals for {ticker} from FMP API")
                            return result
                    # Add other sources here as needed
                    
            else:
                # Fallback to FMP API
                logger.debug(f"Trying FMP API for fundamentals of {ticker}")
                try:
                    return self._get_fmp_fundamentals(ticker)
                except Exception as e:
                    logger.warning(f"FMP API failed for {ticker} fundamentals: {e}")
            
            logger.warning(f"No fundamental data available for {ticker}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting fundamentals for {ticker}: {e}")
            return None

    def _get_fmp_fundamentals(self, ticker):
        """Get fundamentals from FMP API"""
        try:
            url = f"https://financialmodelingprep.com/api/v3/key-metrics/{ticker}?period=quarter&apikey={FMP_API_KEY}"
            response = self._make_api_request(url, use_free_fallback=False)
            
            if response and response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    latest = data[0]
                    return {
                        'pe_ratio': latest.get('peRatio'),
                        'pb_ratio': latest.get('pbRatio'),
                        'debt_to_equity': latest.get('debtToEquity'),
                        'roe': latest.get('roe'),
                        'roa': latest.get('roa'),
                        'current_ratio': latest.get('currentRatio'),
                        'quick_ratio': latest.get('quickRatio'),
                        'gross_margin': latest.get('grossProfitMargin'),
                        'operating_margin': latest.get('operatingProfitMargin'),
                        'net_margin': latest.get('netProfitMargin')
                    }
            return None
        except Exception as e:
            logger.error(f"Error getting FMP fundamentals for {ticker}: {e}")
            return None

    def get_pb_ratio(self, ticker):
        """
        Get P/B ratio with free alternatives
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            float: P/B ratio or None if not available
        """
        try:
            fundamentals = self.get_fundamentals(ticker)
            if fundamentals and fundamentals.get('pb_ratio'):
                return float(fundamentals['pb_ratio'])
            
            # Try direct FMP API call for P/B ratio
            try:
                metrics_url = f"https://financialmodelingprep.com/api/v3/key-metrics/{ticker}?limit=1&apikey={FMP_API_KEY}"
                metrics_response = self._make_api_request(metrics_url)
                
                if metrics_response and metrics_response.status_code == 200:
                    metrics_data = metrics_response.json()
                    if metrics_data and len(metrics_data) > 0:
                        pb_ratio = metrics_data[0].get('pbRatio')
                        if pb_ratio:
                            return float(pb_ratio)
                        
                        # If P/B ratio not available, calculate from price and book value
                        price_url = f"https://financialmodelingprep.com/api/v3/quote-short/{ticker}?apikey={FMP_API_KEY}"
                        price_response = self._make_api_request(price_url)
                        
                        if price_response and price_response.status_code == 200:
                            price_data = price_response.json()
                            if price_data and len(price_data) > 0:
                                current_price = price_data[0].get('price')
                                book_value = metrics_data[0].get('bookValuePerShare')
                                
                                if current_price and book_value and book_value != 0:
                                    return float(current_price) / float(book_value)
            except Exception as e:
                logger.warning(f"Error getting P/B ratio from FMP for {ticker}: {e}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting P/B ratio for {ticker}: {e}")
            return None

    def get_realtime_pb(self, ticker):
        """
        Get real-time P/B ratio
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            float: Real-time P/B ratio or None if not available
        """
        try:
            return self.get_pb_ratio(ticker)
        except Exception as e:
            logger.error(f"Error getting real-time P/B for {ticker}: {e}")
            return None

    def get_stock_profile(self, ticker):
        """
        Get stock profile with enhanced free alternatives
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            dict: Stock profile data or None if not available
        """
        try:
            # Check if free data config is available and enabled
            if (free_data_config and 
                free_data_config.get('enabled', True) and 
                'stock_profiles' in free_data_config.get('free_data_sources', {}).get('priority', {})):
                
                priority_sources = free_data_config['free_data_sources']['priority']['stock_profiles']
                logger.info(f"Using configured priority sources for {ticker} profile: {priority_sources}")
                
                for source in priority_sources:
                    if source == 'fmp_api':
                        result = self._get_fmp_stock_profile(ticker)
                        if result:
                            logger.info(f"Successfully got profile for {ticker} from FMP API")
                            return result
                    # Add other sources here as needed
                    
            else:
                # Fallback to FMP API
                logger.debug(f"Trying FMP API for profile of {ticker}")
                try:
                    return self._get_fmp_stock_profile(ticker)
                except Exception as e:
                    logger.warning(f"FMP API failed for {ticker} profile: {e}")
            
            logger.warning(f"No profile data available for {ticker}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting stock profile for {ticker}: {e}")
            return None

    def _get_fmp_stock_profile(self, ticker):
        """Get stock profile from FMP API"""
        try:
            url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={FMP_API_KEY}"
            response = self._make_api_request(url, use_free_fallback=False)
            
            if response and response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    profile = data[0]
                    return {
                        'symbol': profile.get('symbol'),
                        'companyName': profile.get('companyName'),
                        'sector': profile.get('sector'),
                        'industry': profile.get('industry'),
                        'exchange': profile.get('exchangeShortName'),
                        'country': profile.get('country'),
                        'marketCap': profile.get('mktCap'),
                        'description': profile.get('description')
                    }
            return None
        except Exception as e:
            logger.error(f"Error getting FMP stock profile for {ticker}: {e}")
            return None

    def get_historical_data(self, ticker, from_date, to_date, interval='1day'):
        """
        Get historical data with enhanced free alternatives
        
        Args:
            ticker: Stock ticker symbol
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            interval: Data interval (1day, 1week, 1month)
            
        Returns:
            DataFrame: Historical price data
        """
        try:
            # Check if free data config is available and enabled
            if (free_data_config and 
                free_data_config.get('enabled', True) and 
                'historical_data' in free_data_config.get('free_data_sources', {}).get('priority', {})):
                
                priority_sources = free_data_config['free_data_sources']['priority']['historical_data']
                logger.info(f"Using configured priority sources for {ticker} historical data: {priority_sources}")
                
                for source in priority_sources:
                    if source == 'fmp_api':
                        result = self._get_fmp_historical_data(ticker, from_date, to_date, interval)
                        if result is not None and not result.empty:
                            logger.info(f"Successfully got historical data for {ticker} from FMP API")
                            return result
                    # Other sources would be handled by the stock filter's _get_enhanced_historical_data method
                    
            else:
                # Fallback to FMP API
                logger.debug(f"Trying FMP API for historical data of {ticker}")
                try:
                    return self._get_fmp_historical_data(ticker, from_date, to_date, interval)
                except Exception as e:
                    logger.warning(f"FMP API failed for {ticker} historical data: {e}")
            
            logger.warning(f"No historical data available for {ticker}")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting historical data for {ticker}: {e}")
            return pd.DataFrame()

    def _get_fmp_historical_data(self, ticker_str, from_date, to_date, interval):
        """Get historical data from FMP API"""
        try:
            # Map interval to FMP API parameter
            if interval == '1w':
                url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker_str}?from={from_date}&to={to_date}&apikey={FMP_API_KEY}&serietype=line"
                is_weekly = True
                is_monthly = False
            elif interval == '1m':
                url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker_str}?from={from_date}&to={to_date}&apikey={FMP_API_KEY}&serietype=line"
                is_weekly = False
                is_monthly = True
            else:  # Default to daily
                url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker_str}?from={from_date}&to={to_date}&apikey={FMP_API_KEY}"
                is_weekly = False
                is_monthly = False
            
            response = self._make_api_request(url, use_free_fallback=False)
            
            if response and response.status_code == 200:
                data = response.json()
                
                if 'historical' in data and data['historical']:
                    df = pd.DataFrame(data['historical'])
                    
                    # Process FMP data
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.set_index('date')
                    df = df.sort_index()
                    
                    # Rename columns to match yfinance format
                    column_mapping = {
                        'open': 'Open',
                        'high': 'High', 
                        'low': 'Low',
                        'close': 'Close',
                        'adjClose': 'Adj Close',
                        'volume': 'Volume'
                    }
                    df = df.rename(columns=column_mapping)
                    
                    # Ensure we have the required columns
                    required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                    for col in required_columns:
                        if col not in df.columns:
                            df[col] = 0
                    
                    # Ensure Adj Close exists (needed for resampling)
                    if 'Adj Close' not in df.columns:
                        if 'Close' in df.columns:
                            df['Adj Close'] = df['Close']
                        else:
                            df['Adj Close'] = 0
                    
                    # Convert weekly/monthly if needed
                    if is_weekly:
                        df = df.resample('W').agg({
                            'Open': 'first',
                            'High': 'max',
                            'Low': 'min',
                            'Close': 'last',
                            'Adj Close': 'last',
                            'Volume': 'sum'
                        }).dropna()
                    elif is_monthly:
                        df = df.resample('ME').agg({
                            'Open': 'first',
                            'High': 'max',
                            'Low': 'min',
                            'Close': 'last',
                            'Adj Close': 'last',
                            'Volume': 'sum'
                        }).dropna()
                    
                    logger.info(f"Successfully fetched {len(df)} records for {ticker_str} from FMP API")
                    return df
                else:
                    logger.warning(f"No historical data found for {ticker_str} in FMP response")
                    return pd.DataFrame()
            else:
                logger.warning(f"FMP API request failed for {ticker_str}: {response.status_code if response else 'No response'}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error getting FMP historical data for {ticker_str}: {e}")
            return pd.DataFrame()

    def fetch_stock_history(self, symbols, start_date=None, end_date=None, time_frame="daily", days=None):
        """
        Fetch historical stock data for multiple symbols
        
        Args:
            symbols: List of stock symbols
            start_date: Start date for data
            end_date: End date for data  
            time_frame: Time frame (daily, weekly, monthly)
            days: Number of days to fetch (alternative to start_date)
            
        Returns:
            dict: Symbol -> DataFrame mapping
        """
        results = {}
        
        # Calculate date range
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            if days:
                start_date = end_date - timedelta(days=days)
            else:
                start_date = end_date - timedelta(days=365)
        
        # Convert to string format
        start_str = start_date.strftime('%Y-%m-%d') if hasattr(start_date, 'strftime') else str(start_date)
        end_str = end_date.strftime('%Y-%m-%d') if hasattr(end_date, 'strftime') else str(end_date)
        
        # Map time frame to interval
        interval_map = {
            'daily': '1day',
            'weekly': '1week', 
            'monthly': '1month'
        }
        interval = interval_map.get(time_frame.lower(), '1day')
        
        for symbol in symbols:
            try:
                data = self.get_historical_data(symbol, start_str, end_str, interval)
                if not data.empty:
                    results[symbol] = data
                    # Store in database
                    self._store_stock_prices(symbol, data, time_frame)
                else:
                    logger.warning(f"No data fetched for {symbol}")
                    
            except Exception as e:
                logger.error(f"Error fetching history for {symbol}: {e}")
                
        return results

    def fetch_stock_symbols(self, exchange=None):
        """
        Fetch available stock symbols
        
        Args:
            exchange: Exchange to fetch symbols from
            
        Returns:
            list: List of stock symbols
        """
        symbols = []
        
        try:
            if exchange and exchange.upper() in ['SSE', 'SZSE']:
                # Chinese exchanges
                logger.info(f"Fetching Chinese stock symbols from {exchange}")
                try:
                    if exchange.upper() == 'SSE':
                        # Shanghai Stock Exchange
                        stock_list = ak.stock_info_sh_name_code()
                    else:
                        # Shenzhen Stock Exchange  
                        stock_list = ak.stock_info_sz_name_code()
                    
                    if not stock_list.empty:
                        symbols = stock_list['证券代码'].tolist()
                        logger.info(f"Fetched {len(symbols)} symbols from {exchange}")
                except Exception as e:
                    logger.error(f"Error fetching Chinese symbols from {exchange}: {e}")
            else:
                # US exchanges - try to get from S&P 500 list
                try:
                    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
                    response = self._make_api_request(url)
                    if response and response.status_code == 200:
                        tables = pd.read_html(response.text)
                        if tables:
                            sp500_table = tables[0]
                            symbols = sp500_table['Symbol'].tolist()
                            logger.info(f"Fetched {len(symbols)} S&P 500 symbols")
                except Exception as e:
                    logger.warning(f"Error fetching S&P 500 symbols: {e}")
                    
                # Fallback to FMP API for exchange symbols
                if not symbols and exchange:
                    try:
                        url = f"https://financialmodelingprep.com/api/v3/symbol/{exchange}?apikey={FMP_API_KEY}"
                        response = self._make_api_request(url)
                        if response and response.status_code == 200:
                            data = response.json()
                            symbols = [item['symbol'] for item in data if 'symbol' in item]
                            logger.info(f"Fetched {len(symbols)} symbols from {exchange} via FMP")
                    except Exception as e:
                        logger.error(f"Error fetching symbols from FMP for {exchange}: {e}")
                        
        except Exception as e:
            logger.error(f"Error in fetch_stock_symbols: {e}")
            
        return symbols

    def get_batch_profiles(self, symbols):
        """Get stock profiles for multiple symbols"""
        try:
            symbols_str = ','.join(symbols[:100])  # FMP API limit
            profile_url = f"https://financialmodelingprep.com/api/v3/profile/{symbols_str}?apikey={FMP_API_KEY}"
            response = self._make_api_request(profile_url, use_free_fallback=False)
            
            if response and response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"Error getting batch profiles: {e}")
            return []

    def get_batch_key_metrics(self, symbols, period="annual"):
        """Get key metrics for multiple symbols"""
        try:
            symbols_str = ','.join(symbols[:100])  # FMP API limit
            metrics_url = f"https://financialmodelingprep.com/api/v3/key-metrics/{symbols_str}?period={period}&apikey={FMP_API_KEY}"
            response = self._make_api_request(metrics_url, use_free_fallback=False)
            
            if response and response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"Error getting batch key metrics: {e}")
            return []

    def get_batch_ratios(self, symbols):
        """Get financial ratios for multiple symbols"""
        try:
            symbols_str = ','.join(symbols[:100])  # FMP API limit
            ratios_url = f"https://financialmodelingprep.com/api/v3/ratios-ttm/{symbols_str}?apikey={FMP_API_KEY}"
            response = self._make_api_request(ratios_url, use_free_fallback=False)
            
            if response and response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"Error getting batch ratios: {e}")
            return []

    def _process_stock_symbols(self, symbols, exchange=None):
        """Process and validate stock symbols"""
        processed_symbols = []
        
        for symbol in symbols:
            try:
                # Clean and validate symbol
                clean_symbol = symbol.strip().upper()
                if clean_symbol and len(clean_symbol) <= 10:  # Reasonable symbol length
                    processed_symbols.append(clean_symbol)
            except Exception as e:
                logger.warning(f"Error processing symbol {symbol}: {e}")
                
        return processed_symbols

    def _process_chinese_a_stock(self, symbol, exchange=None):
        """Process Chinese A-share stock data"""
        try:
            logger.info(f"Processing Chinese A stock data for {symbol}")
            
            # Use akshare to get Chinese stock data
            try:
                stock_data = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date="20200101", adjust="")
                if not stock_data.empty:
                    # Convert to standard format
                    stock_data = stock_data.rename(columns={
                        '开盘': 'Open',
                        '最高': 'High',
                        '最低': 'Low',
                        '收盘': 'Close',
                        '成交量': 'Volume'
                    })
                    stock_data['Adj Close'] = stock_data['Close']
                    return stock_data
            except Exception as e:
                logger.error(f"Error fetching Chinese stock data for {symbol}: {e}")
                
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error processing Chinese A stock {symbol}: {e}")
            return pd.DataFrame()

    def _fetch_chinese_stock_prices(self, symbol, full_symbol):
        """Fetch Chinese stock price data"""
        try:
            return self._process_chinese_a_stock(symbol)
        except Exception as e:
            logger.error(f"Error fetching Chinese stock prices for {symbol}: {e}")
            return pd.DataFrame()