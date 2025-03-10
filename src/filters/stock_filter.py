"""
Stock filtering module for filtering stocks based on technical indicators
"""
import os
import json
import logging
from src.utils.logging_config import configure_logging
from datetime import datetime, timedelta
import yfinance as yf
import yaml
import pandas as pd
from sqlalchemy.orm import Session
from src.data.database import get_redis
from src.data.models import Stock, StockPrice, FilteredStock
from src.data.acquisition import DataAcquisition
from src.indicators.technical import TechnicalIndicators

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)

# Load configuration
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "config.yaml")
with open(config_path, "r") as config_file:
    config = yaml.safe_load(config_file)

class StockFilter:
    """Stock filtering class"""
    
    def __init__(self, db: Session):
        """Initialize stock filter with database session"""
        self.db = db
        self.redis = get_redis()
        self.data_acquisition = DataAcquisition(db)
    
    def filter_stocks(self, symbols=None, time_frames=None):
        """
        Filter stocks based on technical indicators
        
        Args:
            symbols: List of stock symbols or "all" for all symbols
            time_frames: List of time frames to filter (daily, weekly, monthly)
        
        Returns:
            Dictionary of filtered stocks by symbol
        """
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
            symbol_upper = symbol.upper()
            
            # Case 1: Symbol is "ALL" - get all symbols
            if symbol_upper == "ALL":
                symbols_json = self.redis.get("symbols_all")
                if symbols_json:
                    all_stock_symbols.extend(json.loads(symbols_json))
                else:
                    all_stock_symbols.extend(self.data_acquisition.fetch_stock_symbols())
            
            # Case 2: Symbol is an exchange name (SP500, NASDAQ, NYSE, AMEX)
            elif symbol_upper in ["SP500", "NASDAQ", "NYSE", "AMEX"]:
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
                symbol_results = {}
                
                for time_frame in time_frames:
                    # Get historical data
                    historical_data = self._get_historical_data(symbol, time_frame)
                    
                    if historical_data.empty:
                        logger.warning(f"No historical data for {symbol} ({time_frame})")
                        continue
                    
                    # Get next day data (for BIAS calculation)
                    next_day_data = self._get_next_day_data(symbol, historical_data.index[-1], time_frame)
                    
                    if next_day_data.empty:
                        logger.warning(f"No next day data for {symbol} ({time_frame})")
                        continue
                    
                    # Calculate indicators
                    indicators = TechnicalIndicators.calculate_all_indicators(historical_data, time_frame)
                    next_day_indicators = TechnicalIndicators.calculate_next_day_indicators(
                        historical_data, next_day_data, time_frame
                    )
                    
                    # Apply filtering criteria
                    if self._meets_criteria(next_day_indicators, time_frame):
                        # Store filtered result
                        result = self._store_filtered_result(symbol, next_day_indicators, time_frame)
                        
                        if result:
                            # Add to time frame results
                            symbol_results[time_frame] = result
                
                # If any time frame results exist, add to filtered results
                if symbol_results:
                    filtered_results[symbol] = symbol_results
            
            except Exception as e:
                logger.error(f"Error filtering {symbol}: {e}")
        
        return filtered_results
    
    def _get_historical_data(self, symbol, time_frame, days=100):
        """Get historical data for a symbol directly from yfinance"""
        # Calculate date range
        end_date = datetime.now()
        
        # Set interval and start date based on time frame
        if time_frame == "daily":
            start_date = end_date - timedelta(days=days)
            interval = "1d"
        elif time_frame == "weekly":
            start_date = end_date - timedelta(days=days * 7)
            interval = "1wk"
        elif time_frame == "monthly":
            start_date = end_date - timedelta(days=days * 30)
            interval = "1mo"
        else:
            logger.error(f"Invalid time frame: {time_frame}")
            return pd.DataFrame()
        
        try:
            # Fetch data directly from yfinance
            ticker = yf.Ticker(symbol)
            data = ticker.history(
                start=start_date,
                end=end_date,
                interval=interval
            )
            
            if data.empty:
                logger.warning(f"No historical data for {symbol} ({time_frame})")
            
            return data
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return pd.DataFrame()
    
    def _get_next_day_data(self, symbol, last_date, time_frame):
        """Get next day data for a symbol directly from yfinance"""
        # Calculate next date
        if time_frame == "daily":
            next_date = last_date + timedelta(days=1)
            interval = "1d"
        elif time_frame == "weekly":
            next_date = last_date + timedelta(days=7)
            interval = "1wk"
        elif time_frame == "monthly":
            next_date = last_date + timedelta(days=30)
            interval = "1mo"
        else:
            logger.error(f"Invalid time frame: {time_frame}")
            return pd.DataFrame()
        
        try:
            # Fetch data directly from yfinance
            ticker = yf.Ticker(symbol)
            data = ticker.history(
                start=last_date + timedelta(days=1),
                end=next_date + timedelta(days=1),  # Add an extra day to ensure we get at least one data point
                interval=interval
            )
            return data.head(1)  # Return only the first row
        except Exception as e:
            logger.error(f"Error fetching next day data for {symbol}: {e}")
            return pd.DataFrame()
    
    def _meets_criteria(self, indicators, time_frame):
        """Check if indicators meet filtering criteria"""
        if indicators.empty:
            logger.warning("Empty indicators DataFrame, cannot apply filtering criteria")
            return False
        
        try:
            # Get configuration for the specified time frame
            ema_config = config['indicators']['ema'][time_frame]
            bias_config = config['indicators']['bias'][time_frame]
            rsi_config = config['indicators']['rsi'][time_frame]
            macd_config = config['indicators']['macd'][time_frame]
            
            # Find BIAS column - use the first EMA period from config
            if 'periods' in ema_config and len(ema_config['periods']) > 0:
                ema_period = ema_config['periods'][0]
                bias_column = f"BIAS_{ema_period}_Close"
                
                # Check if the BIAS column exists in the indicators DataFrame
                if bias_column not in indicators.columns:
                    logger.warning(f"BIAS column '{bias_column}' not found in indicators")
                    return False
                
                # Get BIAS value and threshold
                bias_value = indicators[bias_column].iloc[-1]
                bias_threshold = bias_config['threshold']
                
                # Check BIAS criteria
                if pd.isna(bias_value) or bias_value >= bias_threshold:
                    return False
                
                # Check RSI criteria
                rsi_period = rsi_config['period']
                rsi_column = f"RSI_{rsi_period}"
                
                if rsi_column not in indicators.columns:
                    logger.warning(f"RSI column '{rsi_column}' not found in indicators")
                    return False
                
                rsi_value = indicators[rsi_column].iloc[-1]
                rsi_oversold = rsi_config['oversold']
                
                if pd.isna(rsi_value) or rsi_value >= rsi_oversold:
                    return False
                
                # Check MACD criteria
                if 'MACD' not in indicators.columns or 'MACD_Signal' not in indicators.columns:
                    logger.warning("MACD or MACD_Signal column not found in indicators")
                    return False
                
                macd_value = indicators['MACD'].iloc[-1]
                macd_signal = indicators['MACD_Signal'].iloc[-1]
                
                if pd.isna(macd_value) or pd.isna(macd_signal) or macd_value >= macd_signal:
                    return False
                
                # All criteria met
                return True
            else:
                logger.warning(f"No EMA periods defined for {time_frame} timeframe")
                return False
        
        except Exception as e:
            logger.error(f"Error in _meets_criteria: {e}")
            return False
    
    def _store_filtered_result(self, symbol, indicators, time_frame):
        """Store filtered result in database and Redis"""
        try:
            # Get stock
            stock = self.db.query(Stock).filter(Stock.symbol == symbol).first()
            
            if not stock:
                logger.warning(f"Stock {symbol} not found in database")
                return None
            
            # Create filtered stock record
            filter_date = indicators.index[-1]
            
            # Get configuration for the specified time frame
            ema_config = config['indicators']['ema'][time_frame]
            rsi_config = config['indicators']['rsi'][time_frame]
            
            # Find BIAS column - use the first EMA period from config
            bias_column = None
            if 'periods' in ema_config and len(ema_config['periods']) > 0:
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
                    macd_histogram=macd_histogram
                )
                self.db.add(filtered_stock)
            
            self.db.commit()
            
            # Store in Redis
            redis_key = f"filtered_stock_{symbol}"
            
            # Get existing data from Redis
            existing_data = self.redis.get(redis_key)
            if existing_data:
                filtered_data = json.loads(existing_data)
            else:
                filtered_data = {
                    "metaData": {
                        "stock": symbol,
                        "filterTime": datetime.now().isoformat()
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
                
                # Check if stock has all required time frames
                has_all_time_frames = all(tf in stock_data for tf in time_frames)
                
                if has_all_time_frames:
                    # Get symbol from key
                    symbol = key.split("_")[-1]
                    
                    # Add to filtered stocks
                    filtered_stocks[symbol] = {
                        "metaData": stock_data["metaData"],
                        **{tf: stock_data[tf] for tf in time_frames}
                    }
            
            except Exception as e:
                logger.error(f"Error getting filtered stock {key}: {e}")
        
        return filtered_stocks