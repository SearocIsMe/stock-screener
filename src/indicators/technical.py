"""
Technical indicators module for calculating EMA, BIAS, RSI, and MACD
"""
import os
import logging
from src.utils.logging_config import configure_logging
import yaml
import numpy as np
import pandas as pd
import pandas_ta as ta

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)

# Load configuration
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "config.yaml")
with open(config_path, "r") as config_file:
    config = yaml.safe_load(config_file)

class TechnicalIndicators:
    """Technical indicators calculation class"""
    calucated_amount = 0

    def __init__(self):
        self.calucated_amount = 1
    
    @classmethod
    def calculate_all_indicators(cls, data, time_frame='daily'):
        """
        Calculate all technical indicators for the given data based on the specified timeframe
        using pandas-ta
        
        Args:
            data: DataFrame with price data (must have OHLC columns)
            time_frame: Time frame for indicators (daily, weekly, monthly)
        
        Returns:
            DataFrame with all indicators for the specified timeframe
        """
        if data.empty:
            logger.warning("Empty data provided, cannot calculate indicators")
            return pd.DataFrame()
        
        if len(data) < 30:  # Need at least 30 data points for reliable indicators
            logger.warning(f"Not enough data points for reliable indicators ({len(data)} < 30)")
            return pd.DataFrame()
        
        # Log the timeframe being used for calculations
        logger.debug(f"Calculating indicators for {time_frame} timeframe with {len(data)} data points")
        
        # Get configuration for the specified time frame
        ema_config = config['indicators']['ema'][time_frame]
        rsi_config = config['indicators']['rsi'][time_frame]
        macd_config = config['indicators']['macd'][time_frame]
        
        # Create a copy of the data to avoid modifying the original
        df = data.copy()
        
        # Calculate EMA for each period in the config
        for period in ema_config['periods']:
            # Calculate EMA using pandas-ta
            ema_col = f'EMA_{period}_Close'
            df[ema_col] = df.ta.ema(close='Close', length=period)
            
            # Calculate BIAS (Price - EMA) / EMA * 100
            bias_col = f'BIAS_{period}_Close'
            df[bias_col] = (df['Close'] - df[ema_col]) / df[ema_col] * 100
        
        # Calculate RSI
        rsi_period = rsi_config['period']
        df[f'RSI_{rsi_period}'] = df.ta.rsi(close='Close', length=rsi_period)
        
        # Calculate MACD
        macd = df.ta.macd(
            close='Close', 
            fast=macd_config['fast_period'],
            slow=macd_config['slow_period'],
            signal=macd_config['signal_period']
        )
        
        # MACD returns a DataFrame with columns: MACD_fast_slow_signal, MACDh_fast_slow_signal, MACDs_fast_slow_signal
        # Rename to match our expected column names
        df['MACD'] = macd[f'MACD_{macd_config["fast_period"]}_{macd_config["slow_period"]}_{macd_config["signal_period"]}']
        df['MACD_Signal'] = macd[f'MACDs_{macd_config["fast_period"]}_{macd_config["slow_period"]}_{macd_config["signal_period"]}']
        df['MACD_Histogram'] = macd[f'MACDh_{macd_config["fast_period"]}_{macd_config["slow_period"]}_{macd_config["signal_period"]}']
        
        # Log the calculated indicators
        if cls.calucated_amount > 100:
            logger.debug(f"{cls.calucated_amount} stocks are calculated indicators for {time_frame} timeframe: {', '.join(df.columns[df.columns.str.contains('EMA|BIAS|RSI|MACD')])}")
            cls.calucated_amount = 1
        else:  
            cls.calucated_amount += 1
        
        return df
    
    @classmethod
    def get_latest_indicators(cls, data, time_frame='daily'):
        """
        Get the most recent indicators from the calculated data
        
        Args:
            data: DataFrame with price and indicator data
            time_frame: Time frame for indicators (daily, weekly, monthly)
        
        Returns:
            DataFrame with the most recent indicators
        """
        if data.empty:
            logger.warning("Empty data provided, cannot get latest indicators")
            return pd.DataFrame()
        
        # Return only the last row (most recent indicators)
        return data.iloc[-1:].copy()