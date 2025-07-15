"""
Unified stock filtering module with enhanced free data sources and improved data handling
This module consolidates all stock filtering functionality with configurable data sources
"""
import os
import json
import logging
import re
import time
from datetime import datetime, timedelta
import yaml
import pandas as pd
from sqlalchemy.orm import Session

from src.utils.logging_config import configure_logging
from src.data.database import get_redis
from src.data.models import Stock, StockPrice, FilteredStock
from src.data.acquisition import DataAcquisition
from src.data.free_data_sources import FreeDataSources
from src.indicators.technical import TechnicalIndicators

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)

# Load configurations
def load_config():
    """Load configuration files"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "config.yaml")
    free_data_config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "free_data_config.yaml")
    
    with open(config_path, "r") as config_file:
        config = yaml.safe_load(config_file)
    
    with open(free_data_config_path, "r") as free_config_file:
        free_data_config = yaml.safe_load(free_config_file)
    
    return config, free_data_config

config, free_data_config = load_config()

class StockFilter:
    """Unified stock filtering class with enhanced free data sources and improved data handling"""
    
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
            'day': 60,      # Alternative naming
            'weekly': 12,   # 3 months minimum for weekly
            'week': 12,     # Alternative naming
            'monthly': 6,   # 6 months minimum for monthly
            'month': 6      # Alternative naming
        }
        
        # Data period requirements (days to fetch)
        self.data_periods = {
            'daily': 365,   # 1 year for daily analysis
            'day': 365,     # Alternative naming
            'weekly': 730,  # 2 years for weekly analysis
            'week': 730,    # Alternative naming
            'monthly': 1095, # 3 years for monthly analysis
            'month': 1095   # Alternative naming
        }

    def filter_stocks(self, symbols=None, time_frames=None, custom_financial_thresholds=None):
        """
        Filter stocks based on technical indicators and financial metrics
        
        Args:
            symbols: List of stock symbols to filter (optional)
            time_frames: List of time frames to analyze (optional)
            custom_financial_thresholds: Custom financial thresholds (optional)
            
        Returns:
            dict: Filtered results by time frame
        """
        if custom_financial_thresholds:
            self.set_custom_financial_thresholds(custom_financial_thresholds)
        
        # Default time frames if not specified
        if time_frames is None:
            time_frames = ['daily', 'weekly', 'monthly']
        
        # Get symbols from database if not provided
        if symbols is None:
            symbols = [stock.symbol for stock in self.db.query(Stock).all()]
        
        # Preprocess symbols - check if any are exchange names that need expansion
        processed_symbols = []
        
        # Load exchange definitions from config
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'config.yaml')
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        exchange_names = config.get('exchanges', [])
        
        for symbol in symbols:
            if symbol in exchange_names:
                logger.info(f"Expanding exchange symbol: {symbol}")
                
                if symbol == 'SP500':
                    # Use free data sources to get SP500 symbols
                    free_sources = FreeDataSources()
                    sp500_symbols = free_sources.get_sp500_symbols_free()
                    processed_symbols.extend(sp500_symbols)
                    logger.info(f"Added {len(sp500_symbols)} SP500 symbols")
                    
                elif symbol in ['NASDAQ', 'NYSE', 'AMEX', 'ACN']:
                    # Read from CSV files in config directory
                    csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', f'{symbol}.csv')
                    if os.path.exists(csv_path):
                        try:
                            df = pd.read_csv(csv_path)
                            # Assume the first column contains symbols, or look for 'Symbol' column
                            if 'Symbol' in df.columns:
                                exchange_symbols = df['Symbol'].dropna().tolist()
                            else:
                                exchange_symbols = df.iloc[:, 0].dropna().tolist()
                            
                            processed_symbols.extend(exchange_symbols)
                            logger.info(f"Added {len(exchange_symbols)} {symbol} symbols from CSV")
                        except Exception as e:
                            logger.error(f"Error reading {symbol} CSV file: {e}")
                    else:
                        logger.warning(f"CSV file not found for exchange: {symbol}")
                        
            else:
                # Regular symbol, add as-is
                processed_symbols.append(symbol)
        
        # Remove duplicates while preserving order
        symbols = list(dict.fromkeys(processed_symbols))
        logger.info(f"Total symbols to process after expansion: {len(symbols)}")
        
        results = {}
        
        for time_frame in time_frames:
            logger.info(f"Filtering stocks for {time_frame} time frame")
            results[time_frame] = []
            
            for symbol in symbols:
                try:
                    # Get enhanced historical data
                    data = self._get_enhanced_historical_data(symbol, time_frame)
                    
                    if data.empty or len(data) < self.min_data_points.get(time_frame, 30):
                        logger.warning(f"Insufficient data for {symbol} in {time_frame} timeframe: {len(data)} points")
                        continue
                    
                    # Calculate technical indicators
                    indicators = TechnicalIndicators.calculate_all_indicators(data, time_frame)
                    
                    # Check if indicators calculation was successful
                    if indicators.empty or len(indicators) == 0:
                        logger.warning(f"Failed to calculate indicators for {symbol} in {time_frame} timeframe")
                        continue
                    
                    # Check if stock meets criteria
                    if self._meets_criteria(indicators, time_frame, symbol):
                        # Extract latest indicator values for JSON serialization
                        latest_indicators = self._extract_latest_indicators(indicators, time_frame)
                        
                        # Validate that latest_indicators is not None or empty
                        if not latest_indicators:
                            logger.warning(f"Failed to extract latest indicators for {symbol} in {time_frame} timeframe")
                            continue
                        
                        result = {
                            'symbol': symbol,
                            'indicators': latest_indicators,
                            'data_points': len(data),
                            'last_updated': datetime.now().isoformat()
                        }
                        results[time_frame].append(result)
                        
                        # Store result in database and cache
                        self._store_filtered_result(symbol, latest_indicators, time_frame)
                        
                        logger.info(f"✅ {symbol} passed {time_frame} filter")
                    else:
                        logger.debug(f"❌ {symbol} did not pass {time_frame} filter")
                        
                except Exception as e:
                    logger.error(f"Error filtering {symbol} for {time_frame}: {e}")
                    continue
        
        return results

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
            
            # Convert to string format
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            # Check if free data config is available and enabled
            if (free_data_config and 
                free_data_config.get('enabled', True) and 
                'historical_data' in free_data_config.get('free_data_sources', {}).get('priority', {})):
                
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
                        data = self.data_acquisition._get_fmp_historical_data(symbol, start_str, end_str, f'1{time_frame[0]}')
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
                
                # Method 3: Try FMP API as last resort
                fmp_data = self.data_acquisition._get_fmp_historical_data(symbol, start_str, end_str, f'1{time_frame[0]}')
                if not fmp_data.empty:
                    fmp_data = self._convert_to_yfinance_format(fmp_data)
                    if len(fmp_data) >= self.min_data_points.get(time_frame, 30):
                        logger.info(f"Successfully got {len(fmp_data)} records for {symbol} from FMP API")
                        return fmp_data
            
            # If still no sufficient data, try extended date range
            logger.warning(f"Insufficient data for {symbol}, trying extended date range")
            return self._get_enhanced_historical_data_extended(symbol, time_frame, days_needed * 2)
            
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
            
            # Try all sources with extended range
            for source_method in [self._get_yfinance_data, self._get_pandas_datareader_data]:
                try:
                    if source_method == self._get_yfinance_data:
                        data = source_method(symbol, time_frame, start_str, end_str)
                    else:
                        data = source_method(symbol, start_str, end_str, time_frame)
                    
                    if not data.empty:
                        return data
                except Exception as e:
                    logger.warning(f"Extended range attempt failed: {e}")
                    continue
            
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error in extended historical data fetch: {e}")
            return pd.DataFrame()

    def _get_yfinance_data(self, symbol, time_frame, start_str, end_str):
        """Get data from yfinance with proper interval mapping"""
        try:
            # Map time frame to yfinance interval
            interval_map = {
                'daily': '1d', 'day': '1d',
                'weekly': '1wk', 'week': '1wk', 
                'monthly': '1mo', 'month': '1mo'
            }
            interval = interval_map.get(time_frame.lower(), '1d')
            
            return self.free_data_sources.get_historical_data_yfinance(
                symbol, start_str, end_str, interval
            )
        except Exception as e:
            logger.error(f"Error getting yfinance data for {symbol}: {e}")
            return pd.DataFrame()

    def _get_pandas_datareader_data(self, symbol, start_str, end_str, time_frame):
        """Get data from pandas-datareader and resample if needed"""
        try:
            # Get daily data first
            data = self.free_data_sources.get_historical_data_pandas_datareader(
                symbol, start_str, end_str
            )
            
            if data.empty:
                return data
            
            # Resample for weekly/monthly if needed
            if time_frame.lower() in ['weekly', 'week']:
                data = data.resample('W').agg({
                    'Open': 'first',
                    'High': 'max',
                    'Low': 'min',
                    'Close': 'last',
                    'Adj Close': 'last',
                    'Volume': 'sum'
                }).dropna()
            elif time_frame.lower() in ['monthly', 'month']:
                data = data.resample('ME').agg({
                    'Open': 'first',
                    'High': 'max',
                    'Low': 'min',
                    'Close': 'last',
                    'Adj Close': 'last',
                    'Volume': 'sum'
                }).dropna()
            
            return data
        except Exception as e:
            logger.error(f"Error getting pandas-datareader data for {symbol}: {e}")
            return pd.DataFrame()

    def _convert_to_yfinance_format(self, data):
        """Convert data to yfinance format"""
        try:
            if data.empty:
                return data
            
            # Ensure we have the required columns
            required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in required_columns:
                if col not in data.columns:
                    data[col] = 0
            
            # Add Adj Close if not present
            if 'Adj Close' not in data.columns:
                data['Adj Close'] = data['Close']
            
            return data
        except Exception as e:
            logger.error(f"Error converting data format: {e}")
            return pd.DataFrame()

    def _get_financial_thresholds(self):
        """Get financial thresholds from config or custom settings"""
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

    def _store_filtered_result(self, symbol, indicators, time_frame):
        """Store filtered result in database and Redis"""
        try:
            # Get or create stock
            stock = self.db.query(Stock).filter(Stock.symbol == symbol).first()
            if not stock:
                stock = Stock(symbol=symbol)
                self.db.add(stock)
                self.db.commit()
                self.db.refresh(stock)
            
            # Create filtered stock record
            filtered_stock = FilteredStock(
                stock_id=stock.id,
                filter_date=datetime.now(),
                time_frame=time_frame,
                bias_value=indicators.get('bias_value'),
                rsi_value=indicators.get('rsi_value'),
                macd_value=indicators.get('macd_value'),
                macd_signal=indicators.get('macd_signal'),
                macd_histogram=indicators.get('macd_histogram'),
                gross_margin=indicators.get('gross_margin'),
                roe=indicators.get('roe'),
                rd_ratio=indicators.get('rd_ratio')
            )
            
            # Check if record already exists for today
            existing = self.db.query(FilteredStock).filter(
                FilteredStock.stock_id == stock.id,
                FilteredStock.time_frame == time_frame,
                FilteredStock.filter_date >= datetime.now().date()
            ).first()
            
            if existing:
                # Update existing record
                existing.bias_value = indicators.get('bias_value')
                existing.rsi_value = indicators.get('rsi_value')
                existing.macd_value = indicators.get('macd_value')
                existing.macd_signal = indicators.get('macd_signal')
                existing.macd_histogram = indicators.get('macd_histogram')
                existing.gross_margin = indicators.get('gross_margin')
                existing.roe = indicators.get('roe')
                existing.rd_ratio = indicators.get('rd_ratio')
                existing.filter_date = datetime.now()
            else:
                # Add new record
                self.db.add(filtered_stock)
            
            self.db.commit()
            
            # Store in Redis cache
            redis_key = f"filtered_stock:{symbol}:{time_frame}"
            redis_data = {
                'symbol': symbol,
                'time_frame': time_frame,
                'indicators': indicators,
                'filtered_at': datetime.now().isoformat()
            }
            
            if self.redis:
                self.redis.setex(redis_key, 86400, json.dumps(redis_data))  # 24 hour expiry
            
            logger.debug(f"Stored filtered result for {symbol} ({time_frame})")
            
        except Exception as e:
            logger.error(f"Error storing filtered result for {symbol}: {e}")
            self.db.rollback()

    def get_filtered_stocks(self, time_frames=None, recent_days=1):
        """
        Get recently filtered stocks from database
        
        Args:
            time_frames: List of time frames to retrieve
            recent_days: Number of recent days to look back
            
        Returns:
            dict: Filtered stocks by time frame
        """
        if time_frames is None:
            time_frames = ['daily', 'weekly', 'monthly']
        
        results = {}
        cutoff_date = datetime.now() - timedelta(days=recent_days)
        
        for time_frame in time_frames:
            try:
                filtered_stocks = self.db.query(FilteredStock).join(Stock).filter(
                    FilteredStock.time_frame == time_frame,
                    FilteredStock.filter_date >= cutoff_date
                ).all()
                
                results[time_frame] = []
                for fs in filtered_stocks:
                    stock_data = {
                        'symbol': fs.stock.symbol,
                        'indicators': {
                            'bias_value': fs.bias_value,
                            'rsi_value': fs.rsi_value,
                            'macd_value': fs.macd_value,
                            'macd_signal': fs.macd_signal,
                            'macd_histogram': fs.macd_histogram,
                            'gross_margin': fs.gross_margin,
                            'roe': fs.roe,
                            'rd_ratio': fs.rd_ratio
                        },
                        'filtered_at': fs.created_at.isoformat() if fs.created_at else None
                    }
                    results[time_frame].append(stock_data)
                
                logger.info(f"Retrieved {len(results[time_frame])} filtered stocks for {time_frame}")
                
            except Exception as e:
                logger.error(f"Error retrieving filtered stocks for {time_frame}: {e}")
                results[time_frame] = []
        
        return results

    def _meets_criteria(self, indicators, time_frame, symbol, stock=None):
        """Check if stock meets filtering criteria"""
        try:
            # Get financial thresholds
            thresholds = self._get_financial_thresholds()
 
            
            # Additional criteria for different time frames
            if time_frame == 'weekly':
                return self._check_weekly_criteria(indicators, symbol)
            elif time_frame == 'monthly':
                return self._check_monthly_criteria(indicators, symbol)
            else:
                # Extract latest indicator values from DataFrame
                if indicators.empty:
                    logger.warning(f"No indicators available for {symbol}")
                    return False
                
                # Get the most recent row (latest date)
                latest = indicators.iloc[-1]
                
                # Get configuration for the time frame
                rsi_config = config['indicators']['rsi'][time_frame]
                macd_config = config['indicators']['macd'][time_frame]
                
                # Extract technical indicator values from the latest row
                rsi_col = f'RSI_{rsi_config["period"]}'
                macd_signal_col = 'MACD_Signal'
                macd_col = 'MACD'
                
                # Get RSI value
                rsi = latest.get(rsi_col, None)
                if rsi is None or pd.isna(rsi):
                    logger.debug(f"{symbol}: RSI not available")
                    return False
                
                # Get MACD signal value
                macd_signal = latest.get(macd_signal_col, None)
                if macd_signal is None or pd.isna(macd_signal):
                    logger.debug(f"{symbol}: MACD signal not available")
                    return False
                
                # Get MACD value for additional checks
                macd = latest.get(macd_col, None)
                if macd is None or pd.isna(macd):
                    logger.debug(f"{symbol}: MACD not available")
                    return False
                
                # Calculate volume ratio (current volume vs recent average)
                volume_sma_ratio = 1.0  # Default if not calculated
                if 'Volume' in indicators.columns and len(indicators) >= 20:
                    # Calculate 20-period volume SMA
                    volume_sma = indicators['Volume'].rolling(window=20).mean().iloc[-1]
                    current_volume = latest['Volume']
                    if not pd.isna(volume_sma) and not pd.isna(current_volume) and volume_sma > 0:
                        volume_sma_ratio = current_volume / volume_sma
                
                # Calculate price vs EMA ratio
                price_sma_ratio = 1.0   # Default if not calculated
                ema_config = config['indicators']['ema'][time_frame]
                if ema_config['periods']:
                    ema_period = ema_config['periods'][0]  # Use first EMA period
                    ema_col = f'EMA_{ema_period}_Close'
                    if ema_col in latest.index and 'Close' in latest.index:
                        if not pd.isna(latest[ema_col]) and not pd.isna(latest['Close']) and latest[ema_col] > 0:
                            price_sma_ratio = latest['Close'] / latest[ema_col]
                
                # Calculate Bollinger Bands position if we have enough data
                bollinger_position = 0.5  # Default middle position
                if 'Close' in indicators.columns and len(indicators) >= 20:
                    # Calculate 20-period Bollinger Bands
                    close_prices = indicators['Close']
                    bb_period = 20
                    bb_std = 2
                    
                    sma_20 = close_prices.rolling(window=bb_period).mean()
                    std_20 = close_prices.rolling(window=bb_period).std()
                    
                    upper_band = sma_20 + (std_20 * bb_std)
                    lower_band = sma_20 - (std_20 * bb_std)
                    
                    # Get latest values
                    latest_close = latest['Close']
                    latest_upper = upper_band.iloc[-1]
                    latest_lower = lower_band.iloc[-1]
                    latest_middle = sma_20.iloc[-1]
                    
                    if not pd.isna(latest_upper) and not pd.isna(latest_lower) and latest_upper != latest_lower:
                        # Position between 0 (at lower band) and 1 (at upper band)
                        bollinger_position = (latest_close - latest_lower) / (latest_upper - latest_lower)
                        bollinger_position = max(0, min(1, bollinger_position))  # Clamp between 0 and 1
                
                # RSI criteria (not oversold, not overbought)
                if rsi < 30 or rsi > 70:
                    logger.debug(f"{symbol}: RSI {rsi} outside acceptable range")
                    return False
                
                # MACD signal (positive momentum)
                if macd_signal <= 0:
                    logger.debug(f"{symbol}: MACD signal {macd_signal} not positive")
                    return False
                
                # Bollinger Bands position (not at extremes)
                if bollinger_position < 0.2 or bollinger_position > 0.8:
                    logger.debug(f"{symbol}: Bollinger position {bollinger_position} at extremes")
                    return False
                
                # Volume criteria (above average)
                if volume_sma_ratio < 1.2:
                    logger.debug(f"{symbol}: Volume ratio {volume_sma_ratio} below threshold")
                    return False
                
                # Price trend (above moving average)
                if price_sma_ratio < 1.0:
                    logger.debug(f"{symbol}: Price ratio {price_sma_ratio} below moving average")
                    return False

                # For daily timeframe, keep existing logic
                # More stringent criteria for longer time frames
                # Try to get ADX if available (would need to be calculated separately)
                adx = None
                if 'ADX' in latest.index:
                    adx = latest.get('ADX', None)
                    if adx is not None and not pd.isna(adx) and adx < 25:
                        logger.debug(f"{symbol}: ADX {adx} indicates weak trend for {time_frame}")
                        return False
                else:
                    # If ADX is not available, we can skip this check or use alternative trend indicators
                    logger.debug(f"{symbol}: ADX not available for {time_frame} trend analysis")
            
            # Get financial data if available
            if stock:
                try:
                    fundamentals = self.data_acquisition.get_fundamentals(stock.symbol)
                    if fundamentals:
                        # Check financial criteria
                        gross_margin = fundamentals.get('gross_margin')
                        roe = fundamentals.get('roe')
                        
                        if gross_margin is not None and gross_margin < thresholds['gross_margin']:
                            logger.debug(f"{symbol}: Gross margin {gross_margin} below threshold")
                            return False
                        
                        if roe is not None and roe < thresholds['roe']:
                            logger.debug(f"{symbol}: ROE {roe} below threshold")
                            return False
                except Exception as e:
                    logger.warning(f"Could not get fundamentals for {symbol}: {e}")
            
            logger.debug(f"{symbol}: Passed all criteria for {time_frame}")
            return True
            
        except Exception as e:
            logger.error(f"Error checking criteria for {symbol}: {e}")
            return False

    def _check_weekly_criteria(self, indicators, symbol):
        """
        Check weekly filtering criteria - any of the 3 combinations
        
        Weekly Combinations:
        1. Weekly Double MA + MACD Golden Cross: MA10 > MA20 + MACD golden cross + volume increase YoY
        2. Monthly trend up + Weekly volume breakout: MA10 > MA20 + volume breakout + MACD near golden cross + DMI positive turn
        3. Monthly RSI + Bollinger squeeze breakout: Bollinger breakout + OBV uptrend
        """
        try:
            # Check Combination 1: Weekly Double MA + MACD Golden Cross
            combination_1 = self._check_weekly_combination_1(indicators, symbol)
            if combination_1:
                logger.debug(f"{symbol}: Passed weekly combination 1 (MA + MACD golden cross)")
                return True
            
            # Check Combination 2: Monthly trend up + Weekly volume breakout
            combination_2 = self._check_weekly_combination_2(indicators, symbol)
            if combination_2:
                logger.debug(f"{symbol}: Passed weekly combination 2 (trend + volume breakout)")
                return True
            
            # Check Combination 3: Monthly RSI + Bollinger squeeze breakout
            combination_3 = self._check_weekly_combination_3(indicators, symbol)
            if combination_3:
                logger.debug(f"{symbol}: Passed weekly combination 3 (Bollinger + OBV)")
                return True
            
            logger.debug(f"{symbol}: Did not pass any weekly combinations")
            return False
            
        except Exception as e:
            logger.error(f"Error checking weekly criteria for {symbol}: {e}")
            return False

    def _check_weekly_combination_1(self, indicators, symbol):
        """Weekly Combination 1: MA10 > MA20 + MACD golden cross + volume increase YoY"""
        try:
            # Check if indicators DataFrame is empty or has insufficient data
            if indicators.empty or len(indicators) == 0:
                logger.debug(f"{symbol}: No indicators data available for weekly combination 1")
                return False
            
            latest = indicators.iloc[-1]
            
            # Check MA10 > MA20 (bullish alignment)
            ma10 = latest.get('MA_10', None)
            ma20 = latest.get('MA_20', None)
            
            if ma10 is None or ma20 is None or pd.isna(ma10) or pd.isna(ma20):
                logger.debug(f"{symbol}: MA10 or MA20 not available")
                return False
            
            if ma10 <= ma20:
                logger.debug(f"{symbol}: MA10 ({ma10:.2f}) not above MA20 ({ma20:.2f})")
                return False
            
            # Check MACD golden cross
            if not TechnicalIndicators.check_macd_golden_cross(indicators):
                logger.debug(f"{symbol}: No recent MACD golden cross")
                return False
            
            # Check volume increase YoY
            if not TechnicalIndicators.check_volume_increase_yoy(indicators):
                logger.debug(f"{symbol}: No volume increase YoY")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error in weekly combination 1 for {symbol}: {e}")
            return False

    def _check_weekly_combination_2(self, indicators, symbol):
        """Weekly Combination 2: MA10 > MA20 + volume breakout + MACD near golden cross + DMI positive turn"""
        try:
            # Check if indicators DataFrame is empty or has insufficient data
            if indicators.empty or len(indicators) == 0:
                logger.debug(f"{symbol}: No indicators data available for weekly combination 2")
                return False
            
            latest = indicators.iloc[-1]
            
            # Check MA10 > MA20 (bullish alignment)
            ma10 = latest.get('MA_10', None)
            ma20 = latest.get('MA_20', None)
            
            if ma10 is None or ma20 is None or pd.isna(ma10) or pd.isna(ma20):
                logger.debug(f"{symbol}: MA10 or MA20 not available")
                return False
            
            if ma10 <= ma20:
                logger.debug(f"{symbol}: MA10 ({ma10:.2f}) not above MA20 ({ma20:.2f})")
                return False
            
            # Check volume breakout
            if not TechnicalIndicators.check_volume_breakout(indicators):
                logger.debug(f"{symbol}: No volume breakout")
                return False
            
            # Check MACD near golden cross
            if not TechnicalIndicators.check_macd_near_golden_cross(indicators):
                logger.debug(f"{symbol}: MACD not near golden cross")
                return False
            
            # Check DMI positive turn
            if not TechnicalIndicators.check_dmi_positive_turn(indicators):
                logger.debug(f"{symbol}: No DMI positive turn")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error in weekly combination 2 for {symbol}: {e}")
            return False

    def _check_weekly_combination_3(self, indicators, symbol):
        """Weekly Combination 3: Bollinger breakout + OBV uptrend"""
        try:
            # Check if indicators DataFrame is empty or has insufficient data
            if indicators.empty or len(indicators) == 0:
                logger.debug(f"{symbol}: No indicators data available for weekly combination 3")
                return False
            
            # Check Bollinger breakout (middle or upper band)
            bollinger_middle_breakout = TechnicalIndicators.check_bollinger_breakout(indicators, 'middle')
            bollinger_upper_breakout = TechnicalIndicators.check_bollinger_breakout(indicators, 'upper')
            
            if not (bollinger_middle_breakout or bollinger_upper_breakout):
                logger.debug(f"{symbol}: No Bollinger band breakout")
                return False
            
            # Check OBV uptrend
            if not TechnicalIndicators.check_obv_uptrend(indicators):
                logger.debug(f"{symbol}: OBV not in uptrend")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error in weekly combination 3 for {symbol}: {e}")
            return False

    def _check_monthly_criteria(self, indicators, symbol):
        """
        Check monthly filtering criteria - any of the 3 conditions
        
        Monthly Conditions:
        1. 3 consecutive green candles OR above 20MA
        2. Bollinger squeeze -> expansion
        3. RSI moving from 50 towards 60
        """
        try:
            # Check Condition 1: 3 consecutive green candles OR above 20MA
            condition_1 = self._check_monthly_condition_1(indicators, symbol)
            if condition_1:
                logger.debug(f"{symbol}: Passed monthly condition 1 (green candles or above MA20)")
                return True
            
            # Check Condition 2: Bollinger squeeze -> expansion
            condition_2 = self._check_monthly_condition_2(indicators, symbol)
            if condition_2:
                logger.debug(f"{symbol}: Passed monthly condition 2 (Bollinger squeeze expansion)")
                return True
            
            # Check Condition 3: RSI momentum 50 to 60
            condition_3 = self._check_monthly_condition_3(indicators, symbol)
            if condition_3:
                logger.debug(f"{symbol}: Passed monthly condition 3 (RSI momentum)")
                return True
            
            logger.debug(f"{symbol}: Did not pass any monthly conditions")
            return False
            
        except Exception as e:
            logger.error(f"Error checking monthly criteria for {symbol}: {e}")
            return False

    def _check_monthly_condition_1(self, indicators, symbol):
        """Monthly Condition 1: 3 consecutive green candles OR above 20MA"""
        try:
            # Check if indicators DataFrame is empty or has insufficient data
            if indicators.empty or len(indicators) == 0:
                logger.debug(f"{symbol}: No indicators data available for monthly condition 1")
                return False
            
            # Check 3 consecutive green candles
            three_green = TechnicalIndicators.check_three_consecutive_green_candles(indicators)
            if three_green:
                logger.debug(f"{symbol}: Has 3 consecutive green candles")
                return True
            
            # Check if above 20MA
            latest = indicators.iloc[-1]
            close_price = latest.get('Close', None)
            ma20 = latest.get('MA_20', None)
            
            if close_price is not None and ma20 is not None and not pd.isna(close_price) and not pd.isna(ma20):
                if close_price > ma20:
                    logger.debug(f"{symbol}: Above 20MA ({close_price:.2f} > {ma20:.2f})")
                    return True
                else:
                    logger.debug(f"{symbol}: Below 20MA ({close_price:.2f} <= {ma20:.2f})")
            else:
                logger.debug(f"{symbol}: Close price or MA20 not available")
            
            return False
            
        except Exception as e:
            logger.error(f"Error in monthly condition 1 for {symbol}: {e}")
            return False

    def _check_monthly_condition_2(self, indicators, symbol):
        """Monthly Condition 2: Bollinger squeeze -> expansion"""
        try:
            # Check if indicators DataFrame is empty or has insufficient data
            if indicators.empty or len(indicators) == 0:
                logger.debug(f"{symbol}: No indicators data available for monthly condition 2")
                return False
            
            return TechnicalIndicators.check_bollinger_squeeze_expansion(indicators)
            
        except Exception as e:
            logger.error(f"Error in monthly condition 2 for {symbol}: {e}")
            return False

    def _check_monthly_condition_3(self, indicators, symbol):
        """Monthly Condition 3: RSI moving from 50 towards 60"""
        try:
            # Check if indicators DataFrame is empty or has insufficient data
            if indicators.empty or len(indicators) == 0:
                logger.debug(f"{symbol}: No indicators data available for monthly condition 3")
                return False
            
            return TechnicalIndicators.check_rsi_momentum_50_to_60(indicators)
            
        except Exception as e:
            logger.error(f"Error in monthly condition 3 for {symbol}: {e}")
            return False

    def _extract_latest_indicators(self, indicators, time_frame):
        """
        Extract latest indicator values and convert to JSON-serializable format
        
        Args:
            indicators: DataFrame with calculated indicators
            time_frame: Time frame for indicators (daily, weekly, monthly)
            
        Returns:
            dict: JSON-serializable dictionary of latest indicator values
        """
        if indicators.empty or len(indicators) == 0:
            logger.warning("Empty indicators DataFrame provided to _extract_latest_indicators")
            return {}
        
        try:
            # Get the latest row
            latest = indicators.iloc[-1]
            
            # Get configuration for the time frame
            rsi_config = config['indicators']['rsi'][time_frame]
            macd_config = config['indicators']['macd'][time_frame]
            ema_config = config['indicators']['ema'][time_frame]
            
            # Extract key indicators with safe value handling
            close_val = latest.get('Close', 0)
            volume_val = latest.get('Volume', 0)
            
            result = {
                'close_price': float(close_val) if close_val is not None and not pd.isna(close_val) else 0.0,
                'volume': int(volume_val) if volume_val is not None and not pd.isna(volume_val) else 0,
                'date': latest.name.isoformat() if hasattr(latest.name, 'isoformat') else str(latest.name)
            }
            
            # RSI
            rsi_col = f'RSI_{rsi_config["period"]}'
            if rsi_col in latest.index:
                rsi_val = latest[rsi_col]
                if rsi_val is not None and not pd.isna(rsi_val):
                    result['rsi'] = float(rsi_val)
            
            # MACD
            if 'MACD' in latest.index:
                macd_val = latest['MACD']
                if macd_val is not None and not pd.isna(macd_val):
                    result['macd'] = float(macd_val)
                    
            if 'MACD_Signal' in latest.index:
                macd_signal_val = latest['MACD_Signal']
                if macd_signal_val is not None and not pd.isna(macd_signal_val):
                    result['macd_signal'] = float(macd_signal_val)
                    
            if 'MACD_Histogram' in latest.index:
                macd_hist_val = latest['MACD_Histogram']
                if macd_hist_val is not None and not pd.isna(macd_hist_val):
                    result['macd_histogram'] = float(macd_hist_val)
            
            # EMA and BIAS for each configured period
            for period in ema_config['periods']:
                ema_col = f'EMA_{period}_Close'
                bias_col = f'BIAS_{period}_Close'
                
                if ema_col in latest.index:
                    ema_val = latest[ema_col]
                    if ema_val is not None and not pd.isna(ema_val):
                        result[f'ema_{period}'] = float(ema_val)
                
                if bias_col in latest.index:
                    bias_val = latest[bias_col]
                    if bias_val is not None and not pd.isna(bias_val):
                        result[f'bias_{period}'] = float(bias_val)
            
            # Calculate additional ratios
            if 'Close' in latest.index and ema_config['periods']:
                close_val = latest['Close']
                ema_period = ema_config['periods'][0]
                ema_col = f'EMA_{ema_period}_Close'
                if (ema_col in latest.index and close_val is not None and
                    not pd.isna(close_val) and not pd.isna(latest[ema_col]) and
                    latest[ema_col] is not None and latest[ema_col] > 0):
                    result['price_ema_ratio'] = float(close_val / latest[ema_col])
            
            # Volume ratio if we have enough data
            if 'Volume' in indicators.columns and len(indicators) >= 20:
                volume_sma = indicators['Volume'].rolling(window=20).mean().iloc[-1]
                volume_val = latest.get('Volume', 0)
                if (volume_sma is not None and not pd.isna(volume_sma) and volume_sma > 0 and
                    volume_val is not None and not pd.isna(volume_val)):
                    result['volume_sma_ratio'] = float(volume_val / volume_sma)
            
            # Bollinger Bands position if calculated
            if 'Close' in indicators.columns and len(indicators) >= 20:
                close_prices = indicators['Close']
                sma_20 = close_prices.rolling(window=20).mean().iloc[-1]
                std_20 = close_prices.rolling(window=20).std().iloc[-1]
                close_val = latest.get('Close', 0)
                
                if (sma_20 is not None and std_20 is not None and close_val is not None and
                    not pd.isna(sma_20) and not pd.isna(std_20) and not pd.isna(close_val) and
                    std_20 > 0):
                    upper_band = sma_20 + (std_20 * 2)
                    lower_band = sma_20 - (std_20 * 2)
                    
                    if upper_band != lower_band:
                        bollinger_position = (close_val - lower_band) / (upper_band - lower_band)
                        result['bollinger_position'] = float(max(0, min(1, bollinger_position)))
                        result['bollinger_upper'] = float(upper_band)
                        result['bollinger_lower'] = float(lower_band)
                        result['bollinger_middle'] = float(sma_20)
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting latest indicators: {e}")
            return {}