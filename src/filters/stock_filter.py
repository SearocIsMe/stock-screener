"""
Stock filtering module for filtering stocks based on technical indicators
"""
import os
import json
import logging
from datetime import datetime, timedelta
import yaml
import pandas as pd
from sqlalchemy.orm import Session
from src.data.database import get_redis
from src.data.models import Stock, StockPrice, FilteredStock
from src.data.acquisition import DataAcquisition
from src.indicators.technical import TechnicalIndicators

# Configure logging
logging.basicConfig(level=logging.INFO)
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
        
        # Get symbols if "all" is specified
        if symbols == "all" or symbols == "ALL":
            symbols_json = self.redis.get("symbols_all")
            if not symbols_json:
                symbols = self.data_acquisition.fetch_stock_symbols()
            else:
                symbols = json.loads(symbols_json)
        elif isinstance(symbols, str) and symbols.lower() in ["sp500", "nasdaq", "nyse"]:
            # Get symbols for specific exchange
            exchange = symbols.lower()
            symbols_json = self.redis.get(f"symbols_{exchange}")
            if not symbols_json:
                symbols = self.data_acquisition.fetch_stock_symbols(exchange.upper())
            else:
                symbols = json.loads(symbols_json)
        
        # Process each symbol
        filtered_results = {}
        for symbol in symbols:
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
        """Get historical data for a symbol"""
        # Calculate date range
        end_date = datetime.now()
        if time_frame == "daily":
            start_date = end_date - timedelta(days=days)
        elif time_frame == "weekly":
            start_date = end_date - timedelta(days=days * 7)
        elif time_frame == "monthly":
            start_date = end_date - timedelta(days=days * 30)
        
        # Query database for historical data
        stock = self.db.query(Stock).filter(Stock.symbol == symbol).first()
        
        if not stock:
            logger.warning(f"Stock {symbol} not found in database")
            return pd.DataFrame()
        
        prices = self.db.query(StockPrice).filter(
            StockPrice.stock_id == stock.id,
            StockPrice.time_frame == time_frame,
            StockPrice.date >= start_date,
            StockPrice.date <= end_date
        ).order_by(StockPrice.date).all()
        
        if not prices:
            logger.warning(f"No historical prices for {symbol} ({time_frame})")
            # Fetch data if not available
            self.data_acquisition.fetch_stock_history([symbol], start_date, end_date, time_frame)
            
            # Try querying again
            prices = self.db.query(StockPrice).filter(
                StockPrice.stock_id == stock.id,
                StockPrice.time_frame == time_frame,
                StockPrice.date >= start_date,
                StockPrice.date <= end_date
            ).order_by(StockPrice.date).all()
            
            if not prices:
                return pd.DataFrame()
        
        # Convert to DataFrame
        data = pd.DataFrame([
            {
                'Date': price.date,
                'Open': price.open,
                'High': price.high,
                'Low': price.low,
                'Close': price.close,
                'Volume': price.volume
            }
            for price in prices
        ])
        
        # Set index
        data.set_index('Date', inplace=True)
        
        return data
    
    def _get_next_day_data(self, symbol, last_date, time_frame):
        """Get next day data for a symbol"""
        # Calculate next date
        if time_frame == "daily":
            next_date = last_date + timedelta(days=1)
        elif time_frame == "weekly":
            next_date = last_date + timedelta(days=7)
        elif time_frame == "monthly":
            next_date = last_date + timedelta(days=30)
        
        # Query database for next day data
        stock = self.db.query(Stock).filter(Stock.symbol == symbol).first()
        
        if not stock:
            logger.warning(f"Stock {symbol} not found in database")
            return pd.DataFrame()
        
        price = self.db.query(StockPrice).filter(
            StockPrice.stock_id == stock.id,
            StockPrice.time_frame == time_frame,
            StockPrice.date > last_date
        ).order_by(StockPrice.date).first()
        
        if not price:
            logger.warning(f"No next day price for {symbol} ({time_frame})")
            return pd.DataFrame()
        
        # Convert to DataFrame
        data = pd.DataFrame([
            {
                'Date': price.date,
                'Open': price.open,
                'High': price.high,
                'Low': price.low,
                'Close': price.close,
                'Volume': price.volume
            }
        ])
        
        # Set index
        data.set_index('Date', inplace=True)
        
        return data
    
    def _meets_criteria(self, indicators, time_frame):
        """Check if indicators meet filtering criteria"""
        if indicators.empty:
            return False
        
        # Get configuration for the specified time frame
        tf_config = {
            'bias': config['indicators']['bias'][time_frame],
            'rsi': config['indicators']['rsi'][time_frame],
            'macd': config['indicators']['macd'][time_frame]
        }
        
        # Check BIAS criteria
        bias_threshold = tf_config['bias']['threshold']
        bias_value = indicators['BIAS_13_Close'].iloc[-1]
        
        if not pd.isna(bias_value) and bias_value < bias_threshold:
            # Check RSI criteria
            rsi_oversold = tf_config['rsi']['oversold']
            rsi_value = indicators[f"RSI_{tf_config['rsi']['period']}"].iloc[-1]
            
            if not pd.isna(rsi_value) and rsi_value < rsi_oversold:
                # Check MACD criteria
                macd_value = indicators['MACD'].iloc[-1]
                macd_signal = indicators['MACD_Signal'].iloc[-1]
                
                if not pd.isna(macd_value) and not pd.isna(macd_signal) and macd_value < macd_signal:
                    return True
        
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
            
            # Check if record already exists
            existing_filter = self.db.query(FilteredStock).filter(
                FilteredStock.stock_id == stock.id,
                FilteredStock.filter_date == filter_date,
                FilteredStock.time_frame == time_frame
            ).first()
            
            if existing_filter:
                # Update existing record
                existing_filter.bias_value = indicators['BIAS_13_Close'].iloc[-1]
                existing_filter.rsi_value = indicators[f"RSI_{config['indicators']['rsi'][time_frame]['period']}"].iloc[-1]
                existing_filter.macd_value = indicators['MACD'].iloc[-1]
                existing_filter.macd_signal = indicators['MACD_Signal'].iloc[-1]
                existing_filter.macd_histogram = indicators['MACD_Histogram'].iloc[-1]
                filtered_stock = existing_filter
            else:
                # Create new record
                filtered_stock = FilteredStock(
                    stock_id=stock.id,
                    filter_date=filter_date,
                    time_frame=time_frame,
                    bias_value=indicators['BIAS_13_Close'].iloc[-1],
                    rsi_value=indicators[f"RSI_{config['indicators']['rsi'][time_frame]['period']}"].iloc[-1],
                    macd_value=indicators['MACD'].iloc[-1],
                    macd_signal=indicators['MACD_Signal'].iloc[-1],
                    macd_histogram=indicators['MACD_Histogram'].iloc[-1]
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
                    "bias": float(filtered_stock.bias_value)
                },
                "RSI": {
                    "value": float(filtered_stock.rsi_value),
                    "period": config['indicators']['rsi'][time_frame]['period']
                },
                "MACD": {
                    "value": float(filtered_stock.macd_value),
                    "signal": float(filtered_stock.macd_signal),
                    "histogram": float(filtered_stock.macd_histogram),
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