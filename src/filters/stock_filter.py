"""
Stock filtering module for filtering stocks based on technical indicators
Enhanced with free data sources and improved historical data handling
"""
import os
import json
import logging
import re
import time
from src.utils.logging_config import configure_logging
from datetime import datetime, timedelta
import akshare as ak
import yfinance as yf
import yaml
import pandas as pd
import requests
from sqlalchemy.orm import Session
from src.data.database import get_redis
from src.data.models import Stock, StockPrice, FilteredStock
from src.data.acquisition import DataAcquisition
from src.data.free_data_sources import FreeDataSources
from src.indicators.technical import TechnicalIndicators

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

class StockFilter:
    """Stock filtering class"""
    
    def __init__(self, db: Session):
        """Initialize stock filter with database session"""
        self.db = db
        self.redis = get_redis()
        self.data_acquisition = DataAcquisition(db)
        self.free_data_sources = FreeDataSources()
        self.custom_financial_thresholds = None
        
        # Enhanced configuration for better data collection
        self.min_data_points = {
            'daily': 60,    # 2 months minimum for daily
            'weekly': 52,   # 1 year minimum for weekly
            'monthly': 24   # 2 years minimum for monthly
        }
        
        # Data collection periods (in days)
        self.data_periods = {
            'daily': 365,     # 1 year for daily
            'weekly': 365 * 3, # 3 years for weekly
            'monthly': 365 * 5 # 5 years for monthly
        }
    
    def filter_stocks(self, symbols=None, time_frames=None, custom_financial_thresholds=None):
        """
        Filter stocks based on technical indicators
        
        Args:
            symbols: List of stock symbols or "all" for all symbols
            time_frames: List of time frames to filter (daily, weekly, monthly)
        
        Returns:
            Dictionary of filtered stocks by symbol
        """
        # Set custom financial thresholds if provided
        if custom_financial_thresholds:
            self.set_custom_financial_thresholds(custom_financial_thresholds)
        
        # Set default values
        if not symbols:
            symbols = "all"
        
        if not time_frames:
            time_frames = ["daily", "weekly", "monthly"]
        
        # Convert single string to list for consistent processing
        if isinstance(symbols, str):
            symbols = [symbols]
        
        # Process symbols to get actual stock symbols
        all_stock_symbols = []
        
        # Iterate through each element in the symbols list
        for symbol in symbols:
            # Ensure symbol is a string (important for Chinese stock symbols which might be numerical)
            symbol_str = str(symbol)
            symbol_upper = symbol_str.upper()
            
            # Case 1: Symbol is "ALL" - get all symbols
            if symbol_upper == "ALL":
                symbols_json = self.redis.get("symbols_all")
                if symbols_json:
                    all_stock_symbols.extend(json.loads(symbols_json))
                else:
                    all_stock_symbols.extend(self.data_acquisition.fetch_stock_symbols())
            
            # Case 2: Symbol is an exchange name (SP500, NASDAQ, NYSE, AMEX)
            elif symbol_upper in ["SP500", "NASDAQ", "NYSE", "AMEX", "ACN"]:
                exchange_lower = symbol_upper.lower()
                symbols_json = self.redis.get(f"symbols_{exchange_lower}")
                if symbols_json:
                    all_stock_symbols.extend(json.loads(symbols_json))
                else:
                    all_stock_symbols.extend(self.data_acquisition.fetch_stock_symbols(symbol_upper))
            
            # Case 3: Symbol is an actual stock symbol
            else:
                all_stock_symbols.append(symbol)
        
        # Remove duplicates while preserving order
        all_stock_symbols = list(dict.fromkeys(all_stock_symbols))
        
        logger.info(f"Processing {len(all_stock_symbols)} stock symbols for filtering")
        
        # Process each stock symbol
        filtered_results = {}
        for symbol in all_stock_symbols:
            try:
                # Filter stock for each time frame
                if '^' in symbol:
                    logger.info(f"skip this {symbol} for processing")
                    continue

                symbol_results = {}
                
                for time_frame in time_frames:
                    # Get enhanced historical data with sufficient data points
                    historical_data = self._get_enhanced_historical_data(symbol, time_frame)
                    
                    if historical_data.empty:
                        logger.warning(f"No historical data for {symbol} ({time_frame})")
                        continue
                    
                    # Check if we have enough data points
                    min_required = self.min_data_points.get(time_frame, 30)
                    if len(historical_data) < min_required:
                        logger.warning(f"Insufficient data for {symbol} ({time_frame}): {len(historical_data)} < {min_required}")
                        continue
                    
                    # Calculate all indicators using the timeframe-specific data
                    indicators_df = TechnicalIndicators.calculate_all_indicators(historical_data, time_frame)
                    
                    if indicators_df.empty:
                        logger.warning(f"Failed to calculate indicators for {symbol} ({time_frame})")
                        continue
                        
                    latest_indicators = TechnicalIndicators.get_latest_indicators(indicators_df, time_frame)
                    
                    # Apply filtering criteria
                    if self._meets_criteria(latest_indicators, time_frame, symbol, stock=self.db.query(Stock).filter(Stock.symbol == symbol).first()):
                        # Store filtered result
                        result = self._store_filtered_result(symbol, latest_indicators, time_frame)
                        
                        if result:
                            # Add to time frame results
                            symbol_results[time_frame] = result
                
                # If any time frame results exist, add to filtered results
                if symbol_results:
                    filtered_results[symbol] = symbol_results
                    
                    # Add metaData and FinancialMetrics at the same level as timeframes
                    stock = self.db.query(Stock).filter(Stock.symbol == symbol).first()
                    if stock:
                        # Add metaData
                        filtered_results[symbol]["metaData"] = {
                            "stock": symbol,
                            "filterTime": datetime.now().isoformat()
                        }
                        
                        # Add FinancialMetrics
                        filtered_results[symbol]["FinancialMetrics"] = {
                            "gross_margin": float(stock.gross_margin) if stock.gross_margin is not None else None,
                            "roe": float(stock.roe) if stock.roe is not None else None,
                            "rd_ratio": float(stock.rd_ratio) if stock.rd_ratio is not None else None,
                            "thresholds": self._get_financial_thresholds()
                        }
            
            except Exception as e:
                logger.error(f"Error filtering {symbol}: {e}")
        
        return filtered_results

    def _get_financial_thresholds(self):
        """Get financial thresholds from custom thresholds or config"""
        if self.custom_financial_thresholds:
            return {
                "gross_margin": float(self.custom_financial_thresholds.get('gross_margin_threshold', 
                                    config.get('financial_metrics', {}).get('gross_margin_threshold', 0.3))),
                "roe": float(self.custom_financial_thresholds.get('roe_threshold', 
                           config.get('financial_metrics', {}).get('roe_threshold', 0.05))),
                "rd_ratio": float(self.custom_financial_thresholds.get('rd_ratio_threshold', 
                                config.get('financial_metrics', {}).get('rd_ratio_threshold', 0.7)))
            }
        else:
            return {
                "gross_margin": float(config.get('financial_metrics', {}).get('gross_margin_threshold', 0.3)),
                "roe": float(config.get('financial_metrics', {}).get('roe_threshold', 0.05)),
                "rd_ratio": float(config.get('financial_metrics', {}).get('rd_ratio_threshold', 0.7))
            }
    
    def set_custom_financial_thresholds(self, thresholds):
        """Set custom financial thresholds"""
        self.custom_financial_thresholds = thresholds
        logger.info(f"Set custom financial thresholds: {thresholds}")
        
    def _get_enhanced_historical_data(self, symbol, time_frame):
        """
        Enhanced historical data fetching with configurable free sources and sufficient data points
        
        Args:
            symbol: Stock symbol
            time_frame: Time frame (daily, weekly, monthly)
            
        Returns:
            DataFrame with sufficient historical data
        """
        try:
            # Calculate required data period
            days_needed = self.data_periods.get(time_frame, 365)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_needed)
            
            # Format dates
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            # Check if it's a Chinese A stock
            chinese_stock_pattern = r'^\d'
            is_chinese_stock = bool(re.match(chinese_stock_pattern, symbol))
            
            if is_chinese_stock:
                return self._get_chinese_stock_data(symbol, time_frame, start_date, end_date)
            
            # For non-Chinese stocks, use configured data sources
            logger.debug(f"Fetching enhanced historical data for {symbol} ({time_frame})")
            
            # Get priority list from configuration
            if (free_data_config.get('free_data_sources', {}).get('enabled', False) and
                'priority' in free_data_config['free_data_sources'] and
                'historical_data' in free_data_config['free_data_sources']['priority']):
                
                priority_sources = free_data_config['free_data_sources']['priority']['historical_data']
                logger.info(f"Using configured priority sources for {symbol}: {priority_sources}")
                
                # Try each source in priority order
                for source in priority_sources:
                    data = None
                    
                    if source == 'yfinance':
                        data = self._get_yfinance_data(symbol, time_frame, start_str, end_str)
                        source_name = 'yfinance'
                    elif source == 'pandas_datareader':
                        data = self._get_pandas_datareader_data(symbol, start_str, end_str, time_frame)
                        source_name = 'pandas-datareader'
                    elif source == 'fmp_api':
                        data = self.data_acquisition.get_historical_data(symbol, start_str, end_str, f'1{time_frame[0]}')
                        if not data.empty:
                            data = self._convert_to_yfinance_format(data)
                        source_name = 'FMP API'
                    else:
                        logger.warning(f"Unknown data source configured: {source}")
                        continue
                    
                    # Check if we got sufficient data
                    if not data.empty and len(data) >= self.min_data_points.get(time_frame, 30):
                        logger.info(f"Successfully got {len(data)} records for {symbol} from {source_name}")
                        return data
                    elif not data.empty:
                        logger.warning(f"Got {len(data)} records for {symbol} from {source_name}, but need at least {self.min_data_points.get(time_frame, 30)}")
                    else:
                        logger.warning(f"No data returned for {symbol} from {source_name}")
            else:
                # Fallback to original hardcoded order if config is not available
                logger.warning("Free data config not available or disabled, using fallback order")
                
                # Method 1: Try yfinance first (most reliable)
                yf_data = self._get_yfinance_data(symbol, time_frame, start_str, end_str)
                if not yf_data.empty and len(yf_data) >= self.min_data_points.get(time_frame, 30):
                    logger.info(f"Successfully got {len(yf_data)} records for {symbol} from yfinance")
                    return yf_data
                
                # Method 2: Try pandas-datareader
                pdr_data = self._get_pandas_datareader_data(symbol, start_str, end_str, time_frame)
                if not pdr_data.empty and len(pdr_data) >= self.min_data_points.get(time_frame, 30):
                    logger.info(f"Successfully got {len(pdr_data)} records for {symbol} from pandas-datareader")
                    return pdr_data
                
                # Method 3: Try enhanced data acquisition (with FMP fallback)
                enhanced_data = self.data_acquisition.get_historical_data(symbol, start_str, end_str, f'1{time_frame[0]}')
                if not enhanced_data.empty and len(enhanced_data) >= self.min_data_points.get(time_frame, 30):
                    logger.info(f"Successfully got {len(enhanced_data)} records for {symbol} from enhanced acquisition")
                    return self._convert_to_yfinance_format(enhanced_data)
            
            # If we still don't have enough data, try extending the date range
            if days_needed < 365 * 10:  # Don't go beyond 10 years
                logger.info(f"Extending date range for {symbol} to get more data")
                return self._get_enhanced_historical_data_extended(symbol, time_frame, days_needed * 2)
            
            logger.warning(f"Could not get sufficient historical data for {symbol} ({time_frame})")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting enhanced historical data for {symbol}: {e}")
            return pd.DataFrame()

    def _get_enhanced_historical_data_extended(self, symbol, time_frame, days_needed):
        """Get historical data with extended date range"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_needed)
            
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            # Try yfinance with extended range
            yf_data = self._get_yfinance_data(symbol, time_frame, start_str, end_str)
            if not yf_data.empty:
                logger.info(f"Got {len(yf_data)} records for {symbol} with extended range")
                return yf_data
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting extended historical data for {symbol}: {e}")
            return pd.DataFrame()

    def _get_yfinance_data(self, symbol, time_frame, start_str, end_str):
        """Get data from yfinance with proper interval mapping"""
        try:
            # Map time frame to yfinance interval
            interval_map = {
                'daily': '1d',
                'weekly': '1wk',
                'monthly': '1mo'
            }
            
            interval = interval_map.get(time_frame, '1d')
            
            # Use free_data_sources for consistent handling
            data = self.free_data_sources.get_historical_data_yfinance(symbol, start_str, end_str, interval)
            
            if not data.empty:
                # Ensure proper column names for yfinance format
                if 'open' in data.columns:
                    data = data.rename(columns={
                        'open': 'Open',
                        'high': 'High',
                        'low': 'Low',
                        'close': 'Close',
                        'volume': 'Volume'
                    })
                
                return data
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting yfinance data for {symbol}: {e}")
            return pd.DataFrame()

    def _get_pandas_datareader_data(self, symbol, start_str, end_str, time_frame):
        """Get data from pandas-datareader and resample if needed"""
        try:
            data = self.free_data_sources.get_historical_data_pandas_datareader(symbol, start_str, end_str)
            
            if not data.empty:
                # Convert to yfinance format
                if 'open' in data.columns:
                    data = data.rename(columns={
                        'open': 'Open',
                        'high': 'High',
                        'low': 'Low',
                        'close': 'Close',
                        'volume': 'Volume'
                    })
                
                # Resample if needed for weekly/monthly
                if time_frame == 'weekly':
                    data = data.resample('W').agg({
                        'Open': 'first',
                        'High': 'max',
                        'Low': 'min',
                        'Close': 'last',
                        'Volume': 'sum'
                    }).dropna()
                elif time_frame == 'monthly':
                    data = data.resample('ME').agg({
                        'Open': 'first',
                        'High': 'max',
                        'Low': 'min',
                        'Close': 'last',
                        'Volume': 'sum'
                    }).dropna()
                
                return data
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting pandas-datareader data for {symbol}: {e}")
            return pd.DataFrame()

    def _get_chinese_stock_data(self, symbol, time_frame, start_date, end_date):
        """Get Chinese stock data using akshare"""
        try:
            logger.info(f"Fetching Chinese A stock data for {symbol}")
            
            # Map time frame to akshare period
            period_map = {
                'daily': 'daily',
                'weekly': 'weekly',
                'monthly': 'monthly'
            }
            
            period = period_map.get(time_frame, 'daily')
            
            # Format dates for akshare
            start_date_ak = start_date.strftime('%Y%m%d')
            end_date_ak = end_date.strftime('%Y%m%d')
            
            # Fetch data using akshare
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period=period,
                start_date=start_date_ak,
                end_date=end_date_ak,
                adjust="qfq"  # Forward adjusted
            )
            
            if not df.empty:
                # Rename columns to match yfinance format
                df = df.rename(columns={
                    '日期': 'Date',
                    '开盘': 'Open',
                    '收盘': 'Close',
                    '最高': 'High',
                    '最低': 'Low',
                    '成交量': 'Volume'
                })
                
                # Set date as index
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
                
                # Sort by date (newest first for consistency)
                df = df.sort_index(ascending=True)  # Keep chronological order for indicators
                
                logger.info(f"Successfully got {len(df)} Chinese stock records for {symbol}")
                return df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting Chinese stock data for {symbol}: {e}")
            return pd.DataFrame()

    def _convert_to_yfinance_format(self, data):
        """Convert data to yfinance format"""
        try:
            if data.empty:
                return data
            
            # Rename columns if needed
            column_mapping = {
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume',
                'adjusted_close': 'Adj Close'
            }
            
            # Apply mapping for existing columns
            for old_col, new_col in column_mapping.items():
                if old_col in data.columns and new_col not in data.columns:
                    data = data.rename(columns={old_col: new_col})
            
            return data
            
        except Exception as e:
            logger.error(f"Error converting data format: {e}")
            return data
        
    def _store_filtered_result(self, symbol, indicators, time_frame):
        """Store filtered result in database and Redis"""
        try:
            # Get stock
            stock = self.db.query(Stock).filter(Stock.symbol == symbol).first()
            
            if not stock:
                # Create the stock if it doesn't exist
                logger.warning(f"Stock {symbol} not found in database, creating it")
                stock = Stock(symbol=symbol)
                self.db.add(stock)
                self.db.commit()
                logger.info(f"Created new stock record for {symbol}")
            
            # Create filtered stock record
            filter_date = indicators.index[-1]
            
            # Get configuration for the specified time frame
            ema_config = config['indicators']['ema'][time_frame]
            rsi_config = config['indicators']['rsi'][time_frame]
            
            # Find BIAS column - use the first EMA period from config
            bias_column = None
            if 'periods' in ema_config and len(ema_config['periods']) > 0:
                # Try to find any BIAS column if the expected one doesn't exist
                bias_columns = [col for col in indicators.columns if col.startswith('BIAS_')]
                if bias_columns:
                    bias_column = bias_columns[0]
                else:
                    ema_period = ema_config['periods'][0]
                    bias_column = f"BIAS_{ema_period}_Close"
            
            # Find RSI column
            rsi_column = f"RSI_{rsi_config['period']}"
            
            # Check if record already exists
            existing_filter = self.db.query(FilteredStock).filter(
                FilteredStock.stock_id == stock.id,
                FilteredStock.filter_date == filter_date,
                FilteredStock.time_frame == time_frame
            ).first()
            
            # Get values from indicators (with safety checks)
            # Try to find any RSI column if the expected one doesn't exist
            if rsi_column not in indicators.columns:
                rsi_columns = [col for col in indicators.columns if col.startswith('RSI_')]
                if rsi_columns:
                    rsi_column = rsi_columns[0]
            
            bias_value = indicators[bias_column].iloc[-1] if bias_column and bias_column in indicators.columns else None
            rsi_value = indicators[rsi_column].iloc[-1] if rsi_column in indicators.columns else None
            macd_value = indicators['MACD'].iloc[-1] if 'MACD' in indicators.columns else None
            macd_signal = indicators['MACD_Signal'].iloc[-1] if 'MACD_Signal' in indicators.columns else None
            macd_histogram = indicators['MACD_Histogram'].iloc[-1] if 'MACD_Histogram' in indicators.columns else None
            
            if existing_filter:
                # Update existing record
                existing_filter.bias_value = bias_value
                existing_filter.rsi_value = rsi_value
                existing_filter.macd_value = macd_value
                existing_filter.macd_signal = macd_signal
                existing_filter.macd_histogram = macd_histogram
                filtered_stock = existing_filter
            else:
                # Create new record
                filtered_stock = FilteredStock(
                    stock_id=stock.id,
                    filter_date=filter_date,
                    time_frame=time_frame,
                    bias_value=bias_value,
                    rsi_value=rsi_value,
                    macd_value=macd_value,
                    macd_signal=macd_signal,
                    macd_histogram=macd_histogram,
                    gross_margin=stock.gross_margin,
                    roe=stock.roe,
                    rd_ratio=stock.rd_ratio
                )
                self.db.add(filtered_stock)
            
            self.db.commit()
            
            # Store in Redis
            redis_key = f"filtered_stock_{symbol}"
            
            # Get existing data from Redis
            existing_data = self.redis.get(redis_key)
            if existing_data:
                filtered_data = json.loads(existing_data)
                
                # Check if FinancialMetrics exists at the outer level
                if "FinancialMetrics" not in filtered_data:
                    # Add FinancialMetrics to the outer level
                    filtered_data["FinancialMetrics"] = {
                        "gross_margin": float(stock.gross_margin) if stock.gross_margin is not None else None,
                        "roe": float(stock.roe) if stock.roe is not None else None,
                        "rd_ratio": float(stock.rd_ratio) if stock.rd_ratio is not None else None,
                        "thresholds": {
                            "gross_margin": float(config.get('financial_metrics', {}).get('gross_margin_threshold', 0.3)),
                            "roe": float(config.get('financial_metrics', {}).get('roe_threshold', 0.15)),
                            "rd_ratio": float(config.get('financial_metrics', {}).get('rd_ratio_threshold', 0.7))
                        }
                    }
                    
                    # Remove FinancialMetrics from time frames if they exist
                    for tf in filtered_data:
                        if tf != "metaData" and tf != "FinancialMetrics" and "FinancialMetrics" in filtered_data[tf]:
                            del filtered_data[tf]["FinancialMetrics"]
            else:
                filtered_data = {
                    "metaData": {
                        "stock": symbol,
                        "filterTime": datetime.now().isoformat()
                    },
                    "FinancialMetrics": {
                        "gross_margin": float(stock.gross_margin) if stock.gross_margin is not None else None,
                        "roe": float(stock.roe) if stock.roe is not None else None,
                        "rd_ratio": float(stock.rd_ratio) if stock.rd_ratio is not None else None,
                        "thresholds": self._get_financial_thresholds()
                    }
                }
            
            # Add time frame data
            filtered_data[time_frame] = {
                "BIAS": {
                    "bias": float(filtered_stock.bias_value) if filtered_stock.bias_value is not None else None
                },
                "RSI": {
                    "value": float(filtered_stock.rsi_value) if filtered_stock.rsi_value is not None else None,
                    "period": rsi_config['period']
                },
                "MACD": {
                    "value": float(filtered_stock.macd_value) if filtered_stock.macd_value is not None else None,
                    "signal": float(filtered_stock.macd_signal) if filtered_stock.macd_signal is not None else None,
                    "histogram": float(filtered_stock.macd_histogram) if filtered_stock.macd_histogram is not None else None,
                    "fast_period": config['indicators']['macd'][time_frame]['fast_period'],
                    "slow_period": config['indicators']['macd'][time_frame]['slow_period'],
                    "signal_period": config['indicators']['macd'][time_frame]['signal_period']
                }
            }
            
            # Store in Redis with expiration
            expiration = config["database"]["redis"]["expiration_days"] * 86400  # Convert days to seconds
            self.redis.set(redis_key, json.dumps(filtered_data), ex=expiration)
            
            return filtered_data[time_frame]
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error storing filtered result for {symbol}: {e}")
            return None
    
    def get_filtered_stocks(self, time_frames=None, recent_days=1):
        """
        Get filtered stocks from Redis
        
        Args:
            time_frames: List of time frames to filter (daily, weekly, monthly)
            recent_days: Number of recent days to retrieve (0 for today)
        
        Returns:
            Dictionary of filtered stocks
        """
        if not time_frames:
            time_frames = ["daily", "weekly", "monthly"]
        
        # Get all filtered stock keys from Redis
        filtered_keys = self.redis.keys("filtered_stock_*")
        
        # Get current date
        current_date = datetime.now()
        
        # Calculate filter date
        if recent_days > 0:
            filter_date = current_date - timedelta(days=recent_days)
        else:
            filter_date = current_date
        
        # Get filtered stocks
        filtered_stocks = {}
        
        for key in filtered_keys:
            try:
                # Get data from Redis
                data = self.redis.get(key)
                if not data:
                    continue
                
                stock_data = json.loads(data)

                # Check if this is old format data (FinancialMetrics in time frames)
                if "FinancialMetrics" not in stock_data:
                    # Try to find financial metrics in any time frame
                    financial_metrics = None
                    for tf in time_frames:
                        if tf in stock_data and "FinancialMetrics" in stock_data[tf]:
                            financial_metrics = stock_data[tf]["FinancialMetrics"]
                            break
                    
                    # If found, add to outer level and remove from time frames
                    if financial_metrics:
                        stock_data["FinancialMetrics"] = financial_metrics
                        
                        # Remove from time frames
                        for tf in time_frames:
                            if tf in stock_data and tf != "metaData" and tf != "FinancialMetrics" and "FinancialMetrics" in stock_data[tf]:
                                del stock_data[tf]["FinancialMetrics"]
                
                # Check if any of the requested time frames exist
                has_time_frame = False
                for tf in time_frames:
                    if tf in stock_data:
                        has_time_frame = True
                        break
                
                if has_time_frame:
                    # Extract symbol from key
                    symbol = key.decode('utf-8').replace('filtered_stock_', '')
                    filtered_stocks[symbol] = stock_data
            
            except Exception as e:
                logger.error(f"Error processing filtered stock data: {e}")
                continue
                
        return filtered_stocks

    def _meets_criteria(self, indicators, time_frame, symbol, stock=None):
        """Check if stock meets filtering criteria"""
        try:
            # Get configuration for the specified time frame
            ema_config = config['indicators']['ema'][time_frame]
            rsi_config = config['indicators']['rsi'][time_frame]
            macd_config = config['indicators']['macd'][time_frame]
            
            # Find BIAS column - use the first EMA period from config
            bias_column = None
            if 'periods' in ema_config and len(ema_config['periods']) > 0:
                # Try to find any BIAS column if the expected one doesn't exist
                bias_columns = [col for col in indicators.columns if col.startswith('BIAS_')]
                if bias_columns:
                    bias_column = bias_columns[0]
                else:
                    ema_period = ema_config['periods'][0]
                    bias_column = f"BIAS_{ema_period}_Close"
            
            # Find RSI column
            rsi_column = f"RSI_{rsi_config['period']}"
            
            # Check if required columns exist
            if bias_column and bias_column not in indicators.columns:
                logger.warning(f"BIAS column {bias_column} not found for {symbol}")
                return False
            
            if rsi_column not in indicators.columns:
                # Try to find any RSI column
                rsi_columns = [col for col in indicators.columns if col.startswith('RSI_')]
                if rsi_columns:
                    rsi_column = rsi_columns[0]
                else:
                    logger.warning(f"RSI column not found for {symbol}")
                    return False
            
            if 'MACD' not in indicators.columns or 'MACD_Signal' not in indicators.columns:
                logger.warning(f"MACD columns not found for {symbol}")
                return False
            
            # Get values
            bias_value = indicators[bias_column].iloc[-1] if bias_column else None
            rsi_value = indicators[rsi_column].iloc[-1]
            macd_value = indicators['MACD'].iloc[-1]
            macd_signal = indicators['MACD_Signal'].iloc[-1]
            macd_histogram = indicators['MACD_Histogram'].iloc[-1] if 'MACD_Histogram' in indicators.columns else None
            
            # Check criteria
            # 1. BIAS criteria
            bias_criteria = False
            if bias_value is not None:
                # Get BIAS threshold from config - filter stocks with BIAS below this threshold
                bias_threshold = config['indicators']['bias'][time_frame]['threshold']
                bias_criteria = bias_value <= bias_threshold
            
            # 2. RSI criteria
            rsi_lower = rsi_config.get('lower', 30)
            rsi_upper = rsi_config.get('upper', 70)
            rsi_criteria = rsi_lower <= rsi_value <= rsi_upper
            
            # 3. MACD criteria - check if MACD is about to cross above signal line
            macd_criteria = False
            if macd_histogram is not None:
                # MACD histogram is positive and increasing
                macd_criteria = macd_histogram > 0 and macd_value > macd_signal
            else:
                # Alternative: MACD is above signal line
                macd_criteria = macd_value > macd_signal

            # Combine criteria based on configuration
            # Default: All criteria must be met
            criteria_mode = config.get('filtering', {}).get('criteria_mode', 'all')
            
            if criteria_mode == 'all':
                # All criteria must be met
                meets_criteria = (not bias_column or bias_criteria) and rsi_criteria and macd_criteria
            elif criteria_mode == 'any':
                # Any criteria can be met
                meets_criteria = (bias_column and bias_criteria) or rsi_criteria or macd_criteria
            elif criteria_mode == 'majority':
                # Majority of criteria must be met (at least 2 out of 3)
                criteria_count = sum([
                    1 if bias_column and bias_criteria else 0,
                    1 if rsi_criteria else 0,
                    1 if macd_criteria else 0
                ])
                meets_criteria = criteria_count >= 2
            else:
                # Default to all
                meets_criteria = (not bias_column or bias_criteria) and rsi_criteria and macd_criteria

            # Check financial metrics if stock is provided and financial filtering is enabled
            if stock and config.get('financial_metrics', {}).get('enable_financial_filtering', True):
                # Get financial thresholds
                thresholds = self._get_financial_thresholds()
                
                # Check gross margin
                gross_margin_criteria = True
                if stock.gross_margin is not None and thresholds["gross_margin"] is not None:
                    gross_margin_criteria = float(stock.gross_margin) >= thresholds["gross_margin"]
                
                # Check ROE
                roe_criteria = True
                if stock.roe is not None and thresholds["roe"] is not None:
                    roe_criteria = float(stock.roe) >= thresholds["roe"]
                
                # Check R&D ratio
                rd_ratio_criteria = True
                if stock.rd_ratio is not None and thresholds["rd_ratio"] is not None:
                    rd_ratio_criteria = float(stock.rd_ratio) >= thresholds["rd_ratio"]
                
                # Combine financial criteria
                financial_criteria = gross_margin_criteria and roe_criteria and rd_ratio_criteria
                
                # Combine with technical criteria
                meets_criteria = meets_criteria and financial_criteria
                
                logger.debug(f"Financial criteria for {symbol}: gross_margin={gross_margin_criteria}, roe={roe_criteria}, rd_ratio={rd_ratio_criteria}")
                
            return meets_criteria
        
        except Exception as e:
            logger.error(f"Error checking criteria for {symbol}: {e}")
            return False
