"""
Free alternative data sources to replace paid APIs
This module provides free alternatives to Financial Modeling Prep API
"""
import os
import json
import logging
import time
import random
from datetime import datetime, timedelta
import requests
import pandas as pd
import yfinance as yf
from typing import Dict, List, Optional, Union
import pandas_datareader.data as web
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)

class FreeDataSources:
    """Free data sources for stock information and historical data"""
    
    def __init__(self):
        """Initialize free data sources"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def make_robust_request(self, url: str, method: str = "GET", params: dict = None, 
                           headers: dict = None, max_retries: int = 3, 
                           backoff_factor: float = 1.0) -> Optional[requests.Response]:
        """
        Make robust HTTP requests with retry logic and rate limiting
        
        Args:
            url: Request URL
            method: HTTP method
            params: URL parameters
            headers: Additional headers
            max_retries: Maximum retry attempts
            backoff_factor: Backoff multiplier for retries
            
        Returns:
            Response object or None if failed
        """
        if headers:
            session_headers = self.session.headers.copy()
            session_headers.update(headers)
        else:
            session_headers = self.session.headers
            
        for attempt in range(max_retries + 1):
            try:
                # Add random delay to avoid being blocked
                time.sleep(random.uniform(0.5, 1.5))
                
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    headers=session_headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:  # Rate limited
                    wait_time = backoff_factor * (2 ** attempt) + random.uniform(1, 3)
                    logger.warning(f"Rate limited. Waiting {wait_time:.2f} seconds...")
                    time.sleep(wait_time)
                elif response.status_code >= 500:  # Server error
                    wait_time = backoff_factor * (2 ** attempt)
                    logger.warning(f"Server error {response.status_code}. Retrying in {wait_time:.2f} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Request failed with status {response.status_code}: {response.text}")
                    return None
                    
            except requests.exceptions.RequestException as e:
                wait_time = backoff_factor * (2 ** attempt)
                logger.warning(f"Request exception: {e}. Retrying in {wait_time:.2f} seconds...")
                if attempt < max_retries:
                    time.sleep(wait_time)
                    
        logger.error(f"All retry attempts failed for {url}")
        return None

    def get_historical_data_yfinance(self, ticker: str, start_date: str, end_date: str,
                                   interval: str = '1d') -> pd.DataFrame:
        """
        Get historical data using yfinance with rate limiting and retry logic
        
        Args:
            ticker: Stock symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            interval: Data interval (1d, 1wk, 1mo)
            
        Returns:
            DataFrame with historical price data
        """
        max_retries = 3
        base_delay = 2.0
        
        for attempt in range(max_retries + 1):
            try:
                # Add delay between requests to avoid rate limiting
                if attempt > 0:
                    delay = base_delay * (2 ** (attempt - 1)) + random.uniform(1, 3)
                    logger.info(f"Rate limit retry {attempt}/{max_retries} for {ticker}, waiting {delay:.2f}s")
                    time.sleep(delay)
                else:
                    # Always add a small delay to be respectful
                    time.sleep(random.uniform(0.5, 1.5))
                
                # Map interval formats
                yf_interval = interval
                if interval == '1day':
                    yf_interval = '1d'
                elif interval == '1week':
                    yf_interval = '1wk'
                elif interval == '1month':
                    yf_interval = '1mo'
                    
                # Create yfinance ticker object
                stock = yf.Ticker(ticker)
                
                # Download historical data with error handling for rate limits
                hist_data = stock.history(
                    start=start_date,
                    end=end_date,
                    interval=yf_interval,
                    auto_adjust=True,  # Automatically adjust for splits and dividends
                    prepost=False,
                    timeout=15  # Increased timeout
                )
                
                if hist_data.empty:
                    logger.warning(f"No historical data found for {ticker}")
                    return pd.DataFrame()
                    
                # Rename columns to match our schema
                hist_data = hist_data.rename(columns={
                    'Open': 'open',
                    'High': 'high',
                    'Low': 'low',
                    'Close': 'close',
                    'Volume': 'volume'
                })
                
                # Add adjusted_close (same as close when auto_adjust=True)
                hist_data['adjusted_close'] = hist_data['close']
                
                # Sort by date (newest first)
                hist_data = hist_data.sort_index(ascending=False)
                
                logger.info(f"Successfully fetched {len(hist_data)} records for {ticker}")
                return hist_data
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # Check if it's a rate limiting error
                if any(phrase in error_msg for phrase in ['rate limit', 'too many requests', '429', 'throttle']):
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt) + random.uniform(2, 5)
                        logger.warning(f"Rate limited for {ticker}, attempt {attempt + 1}/{max_retries + 1}, retrying in {delay:.2f}s")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"Rate limit exceeded for {ticker} after {max_retries} retries: {e}")
                        return pd.DataFrame()
                
                # Check if it's a timeout or connection error
                elif any(phrase in error_msg for phrase in ['timeout', 'connection', 'network']):
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"Connection error for {ticker}, attempt {attempt + 1}/{max_retries + 1}, retrying in {delay:.2f}s")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"Connection failed for {ticker} after {max_retries} retries: {e}")
                        return pd.DataFrame()
                
                # For other errors, don't retry
                else:
                    logger.error(f"Error fetching historical data for {ticker} using yfinance: {e}")
                    return pd.DataFrame()
        
        logger.error(f"All retry attempts failed for {ticker}")
        return pd.DataFrame()

    def get_historical_data_pandas_datareader(self, ticker: str, start_date: str,
                                            end_date: str) -> pd.DataFrame:
        """
        Get historical data using pandas-datareader with enhanced timeout handling and retry logic
        
        Args:
            ticker: Stock symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            DataFrame with historical price data
        """
        # Configuration for stooq retry mechanism
        max_retry_duration = 3600  # 1 hour in seconds
        retry_start_time = time.time()
        base_delay = 5.0
        max_delay = 300.0  # 5 minutes max delay
        
        # Track stooq availability
        stooq_available = True
        fallback_sources = ['yahoo']  # Fallback sources when stooq is down
        
        try:
            # Primary attempt with stooq
            sources_to_try = ['stooq'] if stooq_available else fallback_sources
            
            while time.time() - retry_start_time < max_retry_duration:
                for source in sources_to_try:
                    try:
                        logger.info(f"Trying to fetch {ticker} data from {source}")
                        
                        # Set timeout for the request
                        import socket
                        original_timeout = socket.getdefaulttimeout()
                        socket.setdefaulttimeout(30)  # 30 second timeout
                        
                        try:
                            # Fetch data from the source
                            data = web.DataReader(
                                ticker,
                                source,
                                start=pd.to_datetime(start_date),
                                end=pd.to_datetime(end_date)
                            )
                        finally:
                            # Restore original timeout
                            socket.setdefaulttimeout(original_timeout)
                        
                        if not data.empty:
                            # Standardize column names
                            data.columns = [col.lower() for col in data.columns]
                            
                            # Ensure we have the required columns
                            required_cols = ['open', 'high', 'low', 'close', 'volume']
                            for col in required_cols:
                                if col not in data.columns:
                                    if col == 'volume':
                                        data[col] = 0  # Set volume to 0 if not available
                                    elif col in ['open', 'high', 'low'] and 'close' in data.columns:
                                        data[col] = data['close']  # Use close price as fallback
                                        
                            # Add adjusted_close
                            data['adjusted_close'] = data['close']
                            
                            # Sort by date (newest first)
                            data = data.sort_index(ascending=False)
                            
                            logger.info(f"Successfully fetched {len(data)} records for {ticker} from {source}")
                            
                            # If stooq worked, mark it as available
                            if source == 'stooq' and not stooq_available:
                                stooq_available = True
                                logger.info(f"Stooq connection restored for {ticker}")
                            
                            return data
                            
                    except Exception as source_error:
                        error_msg = str(source_error).lower()
                        
                        # Check if it's a stooq-specific timeout or connection error
                        if source == 'stooq' and any(phrase in error_msg for phrase in
                                                   ['timeout', 'connection', 'network', 'unreachable', 'refused']):
                            
                            if stooq_available:
                                logger.warning(f"Stooq connection issue for {ticker}: {source_error}")
                                logger.info(f"Marking stooq as unavailable, switching to fallback sources")
                                stooq_available = False
                                sources_to_try = fallback_sources
                                continue  # Try fallback sources immediately
                            else:
                                # Calculate retry delay with exponential backoff
                                elapsed_time = time.time() - retry_start_time
                                remaining_time = max_retry_duration - elapsed_time
                                
                                if remaining_time > 0:
                                    # Exponential backoff with jitter
                                    retry_count = int(elapsed_time / 60)  # Rough retry count based on elapsed time
                                    delay = min(base_delay * (2 ** min(retry_count, 6)), max_delay)
                                    delay += random.uniform(0, delay * 0.1)  # Add jitter
                                    
                                    if delay < remaining_time:
                                        logger.info(f"Stooq still unavailable for {ticker}, retrying in {delay:.1f}s "
                                                  f"(remaining retry time: {remaining_time/60:.1f} minutes)")
                                        time.sleep(delay)
                                        sources_to_try = ['stooq']  # Try stooq again
                                        break  # Break from source loop to retry stooq
                                    else:
                                        logger.warning(f"Not enough time remaining to retry stooq for {ticker}")
                                        break
                                else:
                                    logger.warning(f"Retry time limit exceeded for stooq connection to {ticker}")
                                    break
                        else:
                            logger.warning(f"Failed to fetch {ticker} from {source}: {source_error}")
                            continue
                
                # If we've tried all sources in this iteration and none worked,
                # and we're not retrying stooq, break the retry loop
                if stooq_available or 'stooq' not in sources_to_try:
                    break
                    
            # Final attempt with all available fallback sources if stooq failed
            if not stooq_available:
                logger.info(f"Final attempt for {ticker} using all fallback sources")
                for source in fallback_sources:
                    try:
                        logger.info(f"Final attempt: trying {source} for {ticker}")
                        
                        import socket
                        original_timeout = socket.getdefaulttimeout()
                        socket.setdefaulttimeout(30)
                        
                        try:
                            data = web.DataReader(
                                ticker,
                                source,
                                start=pd.to_datetime(start_date),
                                end=pd.to_datetime(end_date)
                            )
                        finally:
                            socket.setdefaulttimeout(original_timeout)
                        
                        if not data.empty:
                            # Process data same as above
                            data.columns = [col.lower() for col in data.columns]
                            required_cols = ['open', 'high', 'low', 'close', 'volume']
                            for col in required_cols:
                                if col not in data.columns:
                                    if col == 'volume':
                                        data[col] = 0
                                    elif col in ['open', 'high', 'low'] and 'close' in data.columns:
                                        data[col] = data['close']
                            data['adjusted_close'] = data['close']
                            data = data.sort_index(ascending=False)
                            
                            logger.info(f"Successfully fetched {len(data)} records for {ticker} from fallback {source}")
                            return data
                            
                    except Exception as fallback_error:
                        logger.warning(f"Fallback source {source} failed for {ticker}: {fallback_error}")
                        continue
                        
            logger.warning(f"All data sources failed for {ticker} after retry period")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error in pandas-datareader for {ticker}: {e}")
            return pd.DataFrame()

    def get_stock_fundamentals_yahoo(self, ticker: str) -> Dict:
        """
        Get fundamental data from Yahoo Finance (free)
        
        Args:
            ticker: Stock symbol
            
        Returns:
            Dictionary with fundamental metrics
        """
        try:
            stock = yf.Ticker(ticker)
            
            # Get stock info
            info = stock.info
            
            if not info:
                logger.warning(f"No fundamental data found for {ticker}")
                return {'pb': None, 'pe': None, 'roe': None, 'dy': None, 'gm': None}
                
            # Extract fundamental metrics
            fundamentals = {
                'pb': info.get('priceToBook'),
                'pe': info.get('trailingPE') or info.get('forwardPE'),
                'roe': info.get('returnOnEquity'),
                'dy': info.get('dividendYield'),
                'gm': info.get('grossMargins')
            }
            
            # Convert percentages to proper format
            if fundamentals['roe'] is not None:
                fundamentals['roe'] = fundamentals['roe'] * 100  # Convert to percentage
            if fundamentals['dy'] is not None:
                fundamentals['dy'] = fundamentals['dy'] * 100  # Convert to percentage
            if fundamentals['gm'] is not None:
                fundamentals['gm'] = fundamentals['gm'] * 100  # Convert to percentage
                
            # Round values
            return {k: round(v, 2) if v is not None else None for k, v in fundamentals.items()}
            
        except Exception as e:
            logger.error(f"Error getting fundamentals for {ticker} from Yahoo: {e}")
            return {'pb': None, 'pe': None, 'roe': None, 'dy': None, 'gm': None}

    def get_stock_profile_yahoo(self, ticker: str) -> Dict:
        """
        Get stock profile from Yahoo Finance (free)
        
        Args:
            ticker: Stock symbol
            
        Returns:
            Dictionary with stock profile information
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            if not info:
                return {}
                
            profile = {
                'name': info.get('longName') or info.get('shortName'),
                'exchange': info.get('exchange'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'description': info.get('longBusinessSummary'),
                'website': info.get('website'),
                'market_cap': info.get('marketCap'),
                'price': info.get('currentPrice') or info.get('regularMarketPrice'),
                'last_div': info.get('lastDividendValue')
            }
            
            return profile
            
        except Exception as e:
            logger.error(f"Error getting profile for {ticker} from Yahoo: {e}")
            return {}

    def get_batch_fundamentals_yahoo(self, tickers: List[str]) -> Dict[str, Dict]:
        """
        Get fundamentals for multiple tickers using Yahoo Finance
        
        Args:
            tickers: List of stock symbols
            
        Returns:
            Dictionary of fundamentals by ticker
        """
        results = {}
        
        for ticker in tickers:
            try:
                # Add delay to avoid rate limiting
                time.sleep(random.uniform(0.1, 0.5))
                
                fundamentals = self.get_stock_fundamentals_yahoo(ticker)
                results[ticker] = fundamentals
                
            except Exception as e:
                logger.error(f"Error getting fundamentals for {ticker}: {e}")
                results[ticker] = {'pb': None, 'pe': None, 'roe': None, 'dy': None, 'gm': None}
                
        return results

    def get_batch_profiles_yahoo(self, tickers: List[str]) -> Dict[str, Dict]:
        """
        Get profiles for multiple tickers using Yahoo Finance
        
        Args:
            tickers: List of stock symbols
            
        Returns:
            Dictionary of profiles by ticker
        """
        results = {}
        
        for ticker in tickers:
            try:
                # Add delay to avoid rate limiting
                time.sleep(random.uniform(0.1, 0.5))
                
                profile = self.get_stock_profile_yahoo(ticker)
                results[ticker] = profile
                
            except Exception as e:
                logger.error(f"Error getting profile for {ticker}: {e}")
                results[ticker] = {}
                
        return results

    def get_sp500_symbols_free(self) -> List[str]:
        """
        Get S&P 500 symbols from Wikipedia (free)
        
        Returns:
            List of S&P 500 stock symbols
        """
        try:
            url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
            response = self.make_robust_request(url)
            
            if response:
                # Parse the HTML table
                tables = pd.read_html(response.text)
                sp500_table = tables[0]  # First table contains the S&P 500 companies
                
                # Extract symbols and clean them
                symbols = sp500_table['Symbol'].str.replace('.', '-', regex=False).tolist()
                
                logger.info(f"Successfully fetched {len(symbols)} S&P 500 symbols")
                return symbols
            else:
                # Fallback list of major S&P 500 companies
                fallback_symbols = [
                    "AAPL", "MSFT", "AMZN", "GOOGL", "GOOG", "META", "TSLA", "BRK-B", 
                    "UNH", "JNJ", "XOM", "JPM", "V", "PG", "MA", "CVX", "HD", "PFE", 
                    "ABBV", "BAC", "KO", "AVGO", "PEP", "TMO", "COST", "WMT", "DIS", 
                    "ABT", "DHR", "VZ", "ADBE", "CRM", "NFLX", "CMCSA", "NKE", "ACN", 
                    "TXN", "RTX", "QCOM", "NEE", "PM", "HON", "UPS", "T", "SPGI", 
                    "LOW", "ORCL", "IBM", "GS", "CAT"
                ]
                logger.warning(f"Using fallback S&P 500 symbols ({len(fallback_symbols)} symbols)")
                return fallback_symbols
                
        except Exception as e:
            logger.error(f"Error fetching S&P 500 symbols: {e}")
            return []

    def get_nasdaq_symbols_free(self) -> List[str]:
        """
        Get NASDAQ symbols from free sources
        
        Returns:
            List of NASDAQ stock symbols
        """
        try:
            # Try to get from NASDAQ's official API (free but limited)
            url = "https://api.nasdaq.com/api/screener/stocks"
            params = {
                'tableonly': 'true',
                'limit': '5000',
                'exchange': 'NASDAQ'
            }
            
            response = self.make_robust_request(url, params=params)
            
            if response:
                data = response.json()
                if 'data' in data and 'table' in data['data'] and 'rows' in data['data']['table']:
                    symbols = [row['symbol'] for row in data['data']['table']['rows']]
                    logger.info(f"Successfully fetched {len(symbols)} NASDAQ symbols")
                    return symbols
                    
        except Exception as e:
            logger.warning(f"Error fetching NASDAQ symbols from API: {e}")
            
        # Fallback to major NASDAQ companies
        fallback_symbols = [
            "AAPL", "MSFT", "AMZN", "GOOGL", "GOOG", "META", "TSLA", "NVDA", 
            "PYPL", "INTC", "CSCO", "CMCSA", "ADBE", "NFLX", "PEP", "COST", 
            "AVGO", "TXN", "QCOM", "SBUX", "INTU", "ISRG", "BKNG", "GILD", 
            "MDLZ", "AMD", "REGN", "ATVI", "FISV", "CSX", "VRTX", "ILMN", 
            "LRCX", "ADI", "KLAC", "MELI", "DXCM", "BIIB", "MRNA", "DOCU"
        ]
        logger.warning(f"Using fallback NASDAQ symbols ({len(fallback_symbols)} symbols)")
        return fallback_symbols

# Global instance for easy access
free_data_sources = FreeDataSources()