"""
Trend strategy module for filtering stocks based on technical and fundamental criteria
"""
import logging
import os
import yaml
import json
import pandas as pd
import numpy as np
from datetime import datetime
from sqlalchemy.orm import Session
from src.utils.logging_config import configure_logging
from src.data.models import Stock
from src.data.acquisition import DataAcquisition
from src.data.database import get_redis
from src.indicators.technical import TechnicalIndicators

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)

# Load configuration
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "config.yaml")
with open(config_path, "r") as config_file:
    config = yaml.safe_load(config_file)

class TrendStrategy:
    """
    Trend strategy class for implementing a buy-first, sell-later strategy
    based on technical and fundamental criteria
    """
    
    def __init__(self, db: Session):
        """Initialize trend strategy with database session"""
        self.db = db
        self.data_acquisition = DataAcquisition(db)
        self.redis = get_redis()
        
    def analyze_stocks(self, symbols, custom_thresholds=None):
        """
        Analyze stocks based on the trend strategy criteria
        
        Args:
            symbols: List of stock symbols, exchange names, or "all" for all symbols
            custom_thresholds: Custom thresholds for fundamental criteria
            
        Returns:
            Dictionary of analysis results by symbol
        """
        # Process symbols to get actual stock symbols
        all_stock_symbols = self._process_symbols(symbols)
        
        # Analyze each stock
        results = {}
        for symbol in all_stock_symbols:
            try:
                # Analyze individual stock
                result = self._analyze_stock(symbol, custom_thresholds)
                results[symbol] = result
            except Exception as e:
                logger.error(f"Error analyzing stock {symbol}: {e}")
                results[symbol] = self._create_error_response(symbol, f"Error analyzing stock: {str(e)}")
                
        return results
        
    def _process_symbols(self, symbols):
        """Process symbols to get actual stock symbols"""
        # Set default value
        if not symbols:
            symbols = "all"
            
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
            
            # Case 2: Symbol is an exchange name (SP500, NASDAQ, NYSE, AMEX, ACN)
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
        
        logger.info(f"Processing {len(all_stock_symbols)} stock symbols for trend analysis")
        
        return all_stock_symbols
        
    def _analyze_stock(self, symbol, custom_thresholds=None):
        """
        Analyze a single stock based on the trend strategy criteria
        
        Args:
            symbol: Stock symbol to analyze
            custom_thresholds: Custom thresholds for fundamental criteria
            
        Returns:
            Dictionary with analysis results
        """
        try:
            # Get stock from database
            stock = self.db.query(Stock).filter(Stock.symbol == symbol).first()
            
            if not stock:
                logger.warning(f"Stock {symbol} not found in database")
                return self._create_error_response(symbol, "Stock not found in database")
            
            # Get thresholds
            thresholds = self._get_thresholds(custom_thresholds)
            
            # Get historical data for weekly timeframe (for trend analysis)
            weekly_data = self._get_historical_data(symbol, "weekly", days=90)
            
            if weekly_data.empty:
                logger.warning(f"No weekly historical data for {symbol}")
                return self._create_error_response(symbol, "No weekly historical data available")
            
            # Get historical data for daily timeframe (for BIAS check)
            daily_data = self._get_historical_data(symbol, "daily", days=30)
            
            if daily_data.empty:
                logger.warning(f"No daily historical data for {symbol}")
                return self._create_error_response(symbol, "No daily historical data available")
            
            # Analyze technical conditions
            technical_result = self._analyze_technical_conditions(weekly_data, daily_data, thresholds)
            
            # Analyze fundamental conditions
            fundamental_result = self._analyze_fundamental_conditions(stock, thresholds)
            
            # Determine verdict
            verdict, reason = self._determine_verdict(technical_result, fundamental_result)
            
            # Create response
            response = {
                "stock": {
                    "symbol": symbol,
                    "name": stock.name if stock.name else symbol
                },
                "trend_status": {
                    "ema_slope": technical_result["ema_slope_status"],
                    "ema_slope_value": technical_result["ema_slope_value"],
                    "ema_slope_duration": technical_result["ema_slope_duration"],
                    "meets_trend_criteria": technical_result["meets_criteria"]
                },
                "fundamentals": {
                    "pb_ratio": {
                        "value": stock.pb_ratio,
                        "threshold": thresholds["pb_ratio_max"],
                        "meets_criteria": fundamental_result["pb_criteria"]
                    },
                    "pe_ratio": {
                        "value": stock.pe_ratio,
                        "threshold": thresholds["pe_ratio_min"],
                        "meets_criteria": fundamental_result["pe_criteria"]
                    },
                    "roe": {
                        "value": stock.roe,
                        "threshold": thresholds["roe_min"],
                        "meets_criteria": fundamental_result["roe_criteria"]
                    },
                    "gross_margin": {
                        "value": stock.gross_margin,
                        "threshold": thresholds["gross_margin_min"],
                        "meets_criteria": fundamental_result["gross_margin_criteria"]
                    },
                    "dividend_yield": {
                        "value": stock.dividend_yield,
                        "threshold": thresholds["dividend_yield_min"],
                        "meets_criteria": fundamental_result["dividend_yield_criteria"]
                    },
                    "meets_fundamental_criteria": fundamental_result["meets_criteria"]
                },
                "verdict": {
                    "action": verdict,
                    "reason": reason
                },
                "analysis_time": datetime.now().isoformat()
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Error analyzing stock {symbol}: {e}")
            return self._create_error_response(symbol, f"Error analyzing stock: {str(e)}")
    
    def _get_historical_data(self, symbol, time_frame, days=90):
        """Get historical data for a symbol"""
        try:
            # Use the data acquisition module to get historical data with the days parameter
            data = self.data_acquisition.fetch_stock_history(
                symbols=[symbol],
                time_frame=time_frame,
                days=days
            )
            
            # Return the data for the symbol
            return data.get(symbol, pd.DataFrame())
            
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            return pd.DataFrame()
    
    def _get_thresholds(self, custom_thresholds=None):
        """Get thresholds for fundamental criteria"""
        # Default thresholds based on requirements
        default_thresholds = {
            "pb_ratio_max": 10.0,  # P/B < 10
            "pe_ratio_min": 10.0,  # P/E > 10
            "roe_min": 0.10,       # ROE > 10%
            "gross_margin_min": 0.30,  # Gross Margin > 30%
            "dividend_yield_min": 0.03,  # Dividend Yield > 3%
            "ema_slope_min": 10.0,  # EMA slope > 10 degrees
            "ema_slope_weeks": 3,   # For at least 3 consecutive weeks
            "ema_period": 13,       # 13-week EMA
            "bias_threshold": config['indicators']['bias']['daily']['threshold']  # From config
        }
        
        # Override with custom thresholds if provided
        if custom_thresholds:
            for key, value in custom_thresholds.items():
                if key in default_thresholds and value is not None:
                    default_thresholds[key] = value
        
        return default_thresholds
    
    def _analyze_technical_conditions(self, weekly_data, daily_data, thresholds):
        """
        Analyze technical conditions:
        1. Weekly EMA(13) slope must be upward (>10 degrees) for at least 3 consecutive weeks
        2. Daily BIAS must be less than the threshold
        """
        result = {
            "meets_criteria": False,
            "ema_slope_status": "Flat",
            "ema_slope_value": None,
            "ema_slope_duration": 0,
            "bias_value": None,
            "bias_meets_criteria": False
        }
        
        # Calculate trend indicators for weekly data
        weekly_indicators, is_uptrend, uptrend_duration = TechnicalIndicators.calculate_trend_indicators(
            weekly_data,
            time_frame="weekly",
            ema_period=thresholds["ema_period"],
            min_slope=thresholds["ema_slope_min"],
            min_weeks=thresholds["ema_slope_weeks"]
        )
        
        # Get the latest EMA slope value
        if not weekly_indicators.empty and f'EMA_{thresholds["ema_period"]}_Slope' in weekly_indicators.columns:
            latest_slope = weekly_indicators[f'EMA_{thresholds["ema_period"]}_Slope'].iloc[-1]
            result["ema_slope_value"] = latest_slope
            
            # Determine slope status
            if latest_slope > thresholds["ema_slope_min"]:
                result["ema_slope_status"] = f"Up ({uptrend_duration} weeks)"
            elif latest_slope < -thresholds["ema_slope_min"]:
                result["ema_slope_status"] = f"Down ({uptrend_duration} weeks)"
            else:
                result["ema_slope_status"] = "Flat"
                
            result["ema_slope_duration"] = uptrend_duration
        
        # Calculate indicators for daily data
        daily_indicators = TechnicalIndicators.calculate_all_indicators(daily_data, time_frame="daily")
        
        # Check BIAS criteria
        if not daily_indicators.empty:
            # Find BIAS column
            bias_columns = [col for col in daily_indicators.columns if col.startswith('BIAS_')]
            if bias_columns:
                bias_column = bias_columns[0]
                latest_bias = daily_indicators[bias_column].iloc[-1]
                result["bias_value"] = latest_bias
                result["bias_meets_criteria"] = latest_bias <= thresholds["bias_threshold"]
        
        # Stock meets technical criteria if both conditions are met
        result["meets_criteria"] = is_uptrend and result["bias_meets_criteria"]
        
        return result
    
    def _analyze_fundamental_conditions(self, stock, thresholds):
        """
        Analyze fundamental conditions:
        1. P/B < 10 and not negative
        2. P/E > 10
        3. ROE > 10%
        4. Gross Margin > 30%
        5. Dividend Yield > 3%
        """
        result = {
            "meets_criteria": False,
            "pb_criteria": False,
            "pe_criteria": False,
            "roe_criteria": False,
            "gross_margin_criteria": False,
            "dividend_yield_criteria": False
        }
        
        # Check P/B ratio
        if stock.pb_ratio is not None:
            result["pb_criteria"] = 0 < stock.pb_ratio < thresholds["pb_ratio_max"]
        
        # Check P/E ratio
        if stock.pe_ratio is not None:
            result["pe_criteria"] = stock.pe_ratio > thresholds["pe_ratio_min"]
        
        # Check ROE
        if stock.roe is not None:
            result["roe_criteria"] = stock.roe > thresholds["roe_min"]
        
        # Check Gross Margin
        if stock.gross_margin is not None:
            result["gross_margin_criteria"] = stock.gross_margin > thresholds["gross_margin_min"]
        
        # Check Dividend Yield
        if stock.dividend_yield is not None:
            result["dividend_yield_criteria"] = stock.dividend_yield > thresholds["dividend_yield_min"]
        
        # Stock meets fundamental criteria if all conditions are met
        result["meets_criteria"] = (
            result["pb_criteria"] and
            result["pe_criteria"] and
            result["roe_criteria"] and
            result["gross_margin_criteria"] and
            result["dividend_yield_criteria"]
        )
        
        return result
    
    def _determine_verdict(self, technical_result, fundamental_result):
        """
        Determine verdict based on technical and fundamental criteria:
        - Buy: All conditions are met
        - Sell: EMA slope becomes flat from up
        - Reject: Any condition is not met
        """
        # Check if all conditions are met for a buy signal
        if technical_result["meets_criteria"] and fundamental_result["meets_criteria"]:
            return "Buy", "All technical and fundamental criteria are met"
        
        # Check for sell signal (EMA slope becomes flat from up)
        if technical_result["ema_slope_status"] == "Flat" and technical_result["ema_slope_duration"] > 0:
            return "Sell", "EMA slope has flattened from upward trend"
        
        # Determine rejection reason
        if not technical_result["meets_criteria"]:
            if not technical_result.get("bias_meets_criteria", False):
                return "Reject", "Daily BIAS does not meet criteria"
            else:
                return "Reject", "Weekly EMA slope does not meet uptrend criteria"
        
        if not fundamental_result["meets_criteria"]:
            # Identify which fundamental criteria failed
            failed_criteria = []
            if not fundamental_result["pb_criteria"]:
                failed_criteria.append("P/B ratio")
            if not fundamental_result["pe_criteria"]:
                failed_criteria.append("P/E ratio")
            if not fundamental_result["roe_criteria"]:
                failed_criteria.append("ROE")
            if not fundamental_result["gross_margin_criteria"]:
                failed_criteria.append("Gross Margin")
            if not fundamental_result["dividend_yield_criteria"]:
                failed_criteria.append("Dividend Yield")
            
            return "Reject", f"Fundamental criteria not met: {', '.join(failed_criteria)}"
        
        return "Reject", "Unknown reason"
    
    def _create_error_response(self, symbol, error_message):
        """Create error response"""
        return {
            "stock": {
                "symbol": symbol,
                "name": symbol
            },
            "error": error_message,
            "analysis_time": datetime.now().isoformat()
        }