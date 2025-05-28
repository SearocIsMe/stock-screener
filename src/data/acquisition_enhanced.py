"""
Enhanced data acquisition module with free alternatives to paid APIs
This module provides fallback mechanisms using free data sources
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

# Constants
REDIS_EXPIRATION = config["database"]["redis"]["expiration_days"] * 86400
BATCH_SIZE = config["data_fetching"]["yfinance"]["batch_size"]
RETRY_ATTEMPTS = config["data_fetching"]["yfinance"]["retry_attempts"]
RETRY_DELAY = config["data_fetching"]["yfinance"]["retry_delay"]
MAX_BACKOFF_TIME = 120
FMP_API_KEY = config.get("data_fetching", {}).get("fmp", {}).get("api_key", "dfiMAaPz1npS81CJctAuUwaajtCzBRsw")

class EnhancedDataAcquisition:
    """Enhanced data acquisition class with free alternatives"""
    
    def __init__(self, db: Session):
        """Initialize enhanced data acquisition with database session"""
        self.db = db
        self.redis = get_redis()
        self.use_free_sources = True  # Flag to enable free sources
        self.fmp_rate_limit_exceeded = False  # Track FMP rate limit status
        
    def _make_api_request_enhanced(self, url, method="GET", params=None, headers=None, 
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
                        logger.warning("FMP API approaching rate limit, switching to free sources")
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:
                    # Rate limit exceeded - mark FMP as rate limited
                    if "financialmodelingprep.com" in url:
                        self.fmp_rate_limit_exceeded = True
                        logger.warning("FMP API rate limit exceeded, switching to free sources")
                    
                    if not handle_rate_limit or not use_free_fallback:
                        logger.error(f"Rate limit exceeded for {url}")
                        return None
                    
                    # For rate limits, immediately try free alternatives instead of waiting
                    logger.info("Rate limit hit, switching to free data sources")
                    return None
                    
                elif response.status_code in [401, 403]:
                    logger.error(f"Authentication/Authorization error for {url}")
                    if "financialmodelingprep.com" in url:
                        self.fmp_rate_limit_exceeded = True
                    return None
                elif response.status_code == 404:
                    logger.warning(f"Resource not found: {url}")
                    return None
                elif response.status_code >= 500:
                    logger.warning(f"Server error {response.status_code} for {url}. Retrying in {backoff_time} seconds.")
                    time.sleep(backoff_time)
                    backoff_time = min(backoff_time * 2, MAX_BACKOFF_TIME)
                else:
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

    def get_historical_data_enhanced(self, ticker, from_date, to_date, interval='1day'):
        """
        Enhanced historical data fetching with free alternatives
        
        Args:
            ticker: Stock symbol
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            interval: Time interval (1day, 1week, 1month)
            
        Returns:
            DataFrame with historical price data
        """
        try:
            ticker_str = str(ticker)
            
            # Check if this is a Chinese A stock
            is_chinese_stock = False
            if len(ticker_str) == 6 and (ticker_str.startswith('6') or ticker_str.startswith('0') or 
                                       ticker_str.startswith('3') or ticker_str.startswith('4') or 
                                       ticker_str.startswith('8')):
                is_chinese_stock = True
                logger.debug(f"Detected Chinese A stock: {ticker_str}")
                
                # Use akshare for Chinese stocks (already free)
                try:
                    from_date_ak = datetime.strptime(from_date, '%Y-%m-%d').strftime('%Y%m%d')
                    to_date_ak = datetime.strptime(to_date, '%Y-%m-%d').strftime('%Y%m%d')
                    
                    period = "daily"
                    if interval == '1week':
                        period = "weekly"
                    elif interval == '1month':
                        period = "monthly"
                    
                    stock_data = ak.stock_zh_a_hist(symbol=ticker_str, period=period,
                                                  start_date=from_date_ak, end_date=to_date_ak,
                                                  adjust="qfq")
                    
                    if not stock_data.empty:
                        # Process Chinese stock data
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
                        
                        stock_data['date'] = pd.to_datetime(stock_data['date'])
                        stock_data = stock_data.set_index('date')
                        stock_data['adjusted_close'] = stock_data['close']
                        stock_data = stock_data.sort_index(ascending=False)
                        
                        return stock_data
                        
                except Exception as ak_err:
                    logger.error(f"Error fetching Chinese stock data for {ticker_str} using akshare: {ak_err}")
                    return pd.DataFrame()
            
            # For non-Chinese stocks, try multiple free sources
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
                    fmp_data = self._get_fmp_historical_data(ticker_str, from_date, to_date, interval)
                    
                    if not fmp_data.empty:
                        logger.info(f"Successfully fetched {ticker_str} data using FMP API")
                        return fmp_data
                
                logger.warning(f"All data sources failed for {ticker_str}")
                return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting enhanced historical data for {ticker_str}: {e}")
            return pd.DataFrame()

    def _get_fmp_historical_data(self, ticker_str, from_date, to_date, interval):
        """Get historical data from FMP API (original implementation)"""
        try:
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
            
            response = self._make_api_request_enhanced(url, use_free_fallback=False)
            
            if response and response.status_code == 200:
                data = response.json()
                
                if 'historical' in data and data['historical']:
                    df = pd.DataFrame(data['historical'])
                    
                    # Process FMP data (same as original implementation)
                    expected_columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'adjClose']
                    for col in expected_columns:
                        if col not in df.columns:
                            if col == 'adjClose':
                                if 'close' in df.columns:
                                    df['adjClose'] = df['close']
                                else:
                                    df['adjClose'] = 0
                            elif col == 'volume':
                                df['volume'] = 0
                            elif col in ['open', 'high', 'low', 'close']:
                                if 'close' in df.columns:
                                    df[col] = df['close']
                                else:
                                    df[col] = 0
                            elif col != 'date':
                                df[col] = 0
                    
                    df = df.rename(columns={
                        'date': 'date',
                        'open': 'open',
                        'high': 'high',
                        'low': 'low',
                        'close': 'close',
                        'volume': 'volume',
                        'adjClose': 'adjusted_close'
                    })
                    
                    df['date'] = pd.to_datetime(df['date'])
                    df.set_index('date', inplace=True)
                    df = df.sort_index(ascending=False)
                    
                    # Handle resampling for weekly/monthly data
                    if is_weekly:
                        try:
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
                    elif is_monthly:
                        try:
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
                    
                    return df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error fetching FMP historical data for {ticker_str}: {e}")
            return pd.DataFrame()

    def get_fundamentals_enhanced(self, ticker):
        """
        Enhanced fundamentals fetching with free alternatives
        
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
                fmp_fundamentals = self._get_fmp_fundamentals(ticker)
                
                if any(v is not None for v in fmp_fundamentals.values()):
                    logger.info(f"Successfully got fundamentals for {ticker} from FMP API")
                    return fmp_fundamentals
            
            # If both methods failed, return Yahoo results (even if all None)
            logger.warning(f"Limited fundamental data available for {ticker}")
            return yahoo_fundamentals
            
        except Exception as e:
            logger.error(f"Error getting enhanced fundamentals for {ticker}: {e}")
            return {'pb': None, 'pe': None, 'roe': None, 'dy': None, 'gm': None}

    def _get_fmp_fundamentals(self, ticker):
        """Get fundamentals from FMP API (original implementation)"""
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
                    results['dy'] = (last_div / price) * 100
            
            # If P/B is still None, try to calculate it
            if results['pb'] is None:
                results['pb'] = self.get_pb_ratio(ticker)
            
            # Round values for readability
            return {k: round(v, 2) if v is not None else None for k, v in results.items()}
            
        except Exception as e:
            logger.error(f"Error getting FMP fundamentals for {ticker}: {e}")
            return {'pb': None, 'pe': None, 'roe': None, 'dy': None, 'gm': None}

    def get_stock_profile_enhanced(self, ticker):
        """
        Enhanced stock profile fetching with free alternatives
        
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
                fmp_profiles = self.get_batch_profiles([ticker])
                
                if ticker in fmp_profiles and fmp_profiles[ticker]:
                    logger.info(f"Successfully got profile for {ticker} from FMP API")
                    return fmp_profiles[ticker]
            
            # Return Yahoo profile even if incomplete
            return yahoo_profile if yahoo_profile else None
            
        except Exception as e:
            logger.error(f"Error getting enhanced profile for {ticker}: {e}")
            return None

    def get_batch_profiles(self, symbols):
        """Get stock profiles for multiple symbols (original FMP implementation)"""
        if not symbols:
            return {}
            
        try:
            symbols_str = ','.join(symbols)
            profile_url = f"https://financialmodelingprep.com/api/v3/profile/{symbols_str}?apikey={FMP_API_KEY}"
            response = self._make_api_request_enhanced(profile_url, use_free_fallback=False)
            
            if response and response.status_code == 200:
                profiles_data = response.json()
                
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
        """Get key metrics for multiple symbols (original FMP implementation)"""
        if not symbols:
            return {}
            
        try:
            symbols_str = ','.join(symbols)
            metrics_url = f"https://financialmodelingprep.com/api/v3/key-metrics/{symbols_str}?period={period}&apikey={FMP_API_KEY}"
            response = self._make_api_request_enhanced(metrics_url, use_free_fallback=False)
            
            if response and response.status_code == 200:
                metrics_data = response.json()
                
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
        """Get financial ratios for multiple symbols (original FMP implementation)"""
        if not symbols:
            return {}
            
        try:
            symbols_str = ','.join(symbols)
            ratios_url = f"https://financialmodelingprep.com/api/v3/ratios-ttm/{symbols_str}?apikey={FMP_API_KEY}"
            response = self._make_api_request_enhanced(ratios_url, use_free_fallback=False)
            
            if response and response.status_code == 200:
                ratios_data = response.json()
                
                ratios = {}
                for ratio in ratios_data:
                    symbol = ratio.get('symbol')
                    if symbol:
                        roe_value = ratio.get('returnOnEquityTTM')
                        gm_value = ratio.get('grossProfitMarginTTM')
                        
                        ratios[symbol] = {
                            'roe': roe_value * 100 if roe_value is not None else None,
                            'gm': gm_value * 100 if gm_value is not None else None
                        }
                
                return ratios
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting batch ratios: {e}")
            return {}

    def get_pb_ratio(self, ticker):
        """Get P/B ratio with free alternatives"""
        try:
            # Try Yahoo Finance first
            yahoo_fundamentals = free_data_sources.get_stock_fundamentals_yahoo(ticker)
            if yahoo_fundamentals.get('pb') is not None:
                return yahoo_fundamentals['pb']
            
            # Try FMP API if not rate limited
            if not self.fmp_rate_limit_exceeded:
                url = f"https://financialmodelingprep.com/api/v3/key-metrics/{ticker}?period=quarter&apikey={FMP_API_KEY}"
                response = self._make_api_request_enhanced(url, use_free_fallback=False)
                
                if response and response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        return data[0].get('pbRatio')
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting P/B ratio for {ticker}: {e}")
            return None

    # Include other methods from original class with enhanced error handling
    def _store_stock_prices(self, symbol, data, time_frame):
        """Store stock prices in database (same as original)"""
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
                        adjusted_close = price_data.get('close', 0)
                        
                        volume = 0
                        if 'volume' in price_data and not pd.isna(price_data['volume']):
                            try:
                                volume = int(float(price_data['volume']))
                            except (ValueError, TypeError):
                                volume = 0
                        
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
        """Store stock information in database (same as original)"""
        try:
            if pd.isna(symbol) or symbol is None:
                logger.warning("Skipping stock info storage: Symbol is NaN or None")
                return None
                
            symbol = str(symbol)
            stock = self.db.query(Stock).filter(Stock.symbol == symbol).first()
            
            if not stock:
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