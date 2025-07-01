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
                    indicators = TechnicalIndicators.calculate_all_indicators(data)
                    
                    # Check if stock meets criteria
                    if self._meets_criteria(indicators, time_frame, symbol):
                        result = {
                            'symbol': symbol,
                            'indicators': indicators,
                            'data_points': len(data),
                            'last_updated': datetime.now().isoformat()
                        }
                        results[time_frame].append(result)
                        
                        # Store result in database and cache
                        self._store_filtered_result(symbol, indicators, time_frame)
                        
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
                data = data.resample('M').agg({
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
                time_frame=time_frame,
                rsi=indicators.get('rsi'),
                macd_signal=indicators.get('macd_signal'),
                bollinger_position=indicators.get('bollinger_position'),
                volume_sma_ratio=indicators.get('volume_sma_ratio'),
                price_sma_ratio=indicators.get('price_sma_ratio'),
                atr=indicators.get('atr'),
                obv=indicators.get('obv'),
                stochastic_k=indicators.get('stochastic_k'),
                stochastic_d=indicators.get('stochastic_d'),
                williams_r=indicators.get('williams_r'),
                roc=indicators.get('roc'),
                cci=indicators.get('cci'),
                adx=indicators.get('adx'),
                aroon_up=indicators.get('aroon_up'),
                aroon_down=indicators.get('aroon_down'),
                mfi=indicators.get('mfi'),
                trix=indicators.get('trix'),
                vortex_pos=indicators.get('vortex_pos'),
                vortex_neg=indicators.get('vortex_neg'),
                filtered_at=datetime.now()
            )
            
            # Check if record already exists for today
            existing = self.db.query(FilteredStock).filter(
                FilteredStock.stock_id == stock.id,
                FilteredStock.time_frame == time_frame,
                FilteredStock.filtered_at >= datetime.now().date()
            ).first()
            
            if existing:
                # Update existing record
                for key, value in indicators.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                existing.filtered_at = datetime.now()
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
                    FilteredStock.filtered_at >= cutoff_date
                ).all()
                
                results[time_frame] = []
                for fs in filtered_stocks:
                    stock_data = {
                        'symbol': fs.stock.symbol,
                        'indicators': {
                            'rsi': fs.rsi,
                            'macd_signal': fs.macd_signal,
                            'bollinger_position': fs.bollinger_position,
                            'volume_sma_ratio': fs.volume_sma_ratio,
                            'price_sma_ratio': fs.price_sma_ratio,
                            'atr': fs.atr,
                            'obv': fs.obv,
                            'stochastic_k': fs.stochastic_k,
                            'stochastic_d': fs.stochastic_d,
                            'williams_r': fs.williams_r,
                            'roc': fs.roc,
                            'cci': fs.cci,
                            'adx': fs.adx,
                            'aroon_up': fs.aroon_up,
                            'aroon_down': fs.aroon_down,
                            'mfi': fs.mfi,
                            'trix': fs.trix,
                            'vortex_pos': fs.vortex_pos,
                            'vortex_neg': fs.vortex_neg
                        },
                        'filtered_at': fs.filtered_at.isoformat()
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
            
            # Technical indicator criteria
            rsi = indicators.get('rsi', 50)
            macd_signal = indicators.get('macd_signal', 0)
            bollinger_position = indicators.get('bollinger_position', 0.5)
            volume_sma_ratio = indicators.get('volume_sma_ratio', 1.0)
            price_sma_ratio = indicators.get('price_sma_ratio', 1.0)
            
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
            
            # Additional criteria for different time frames
            if time_frame in ['weekly', 'monthly']:
                # More stringent criteria for longer time frames
                adx = indicators.get('adx', 0)
                if adx < 25:  # Strong trend required
                    logger.debug(f"{symbol}: ADX {adx} indicates weak trend for {time_frame}")
                    return False
            
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