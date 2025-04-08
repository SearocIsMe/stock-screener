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
        
    @staticmethod
    def calculate_ema_slope(data, ema_period=13, window=3):
        """
        Calculate the slope of the EMA over a specified window
        
        Args:
            data: DataFrame with price data and EMA values
            ema_period: EMA period to use for slope calculation
            window: Number of periods to use for slope calculation
            
        Returns:
            DataFrame with EMA slope values in degrees
        """
        if data.empty or len(data) < window:
            return pd.DataFrame()
            
        # Ensure the EMA column exists
        ema_col = f'EMA_{ema_period}_Close'
        if ema_col not in data.columns:
            return pd.DataFrame()
            
        # Create a copy of the data
        df = data.copy()
        
        # Calculate the slope using numpy's polyfit
        # This calculates the slope of the line of best fit through the EMA values
        df[f'EMA_{ema_period}_Slope'] = np.nan
        
        # Use rolling window to calculate slope for each point
        for i in range(window - 1, len(df)):
            # Get the window of EMA values
            y = df[ema_col].iloc[i-(window-1):i+1].values
            x = np.arange(window)
            
            # Calculate the slope using polyfit
            slope, _ = np.polyfit(x, y, 1)
            
            # Convert slope to degrees (arctan of slope in radians, then convert to degrees)
            slope_degrees = np.degrees(np.arctan(slope))
            
            # Store the slope in degrees
            df[f'EMA_{ema_period}_Slope'].iloc[i] = slope_degrees
            
        return df
        
    @staticmethod
    def check_uptrend_duration(data, ema_period=13, min_slope=10, min_weeks=3):
        """
        Check if the EMA slope has been upward for a minimum number of consecutive periods
        
        Args:
            data: DataFrame with EMA slope values
            ema_period: EMA period used for slope calculation
            min_slope: Minimum slope in degrees to consider as upward
            min_weeks: Minimum number of consecutive periods with upward slope
            
        Returns:
            Tuple of (is_uptrend, duration)
        """
        if data.empty:
            return False, 0
            
        slope_col = f'EMA_{ema_period}_Slope'
        if slope_col not in data.columns:
            return False, 0
            
        # Get the most recent slope values
        recent_slopes = data[slope_col].dropna().tail(min_weeks * 2)  # Get more than we need
        
        if len(recent_slopes) < min_weeks:
            return False, 0
            
        # Count consecutive periods with upward slope
        consecutive_count = 0
        max_consecutive = 0
        
        for slope in recent_slopes:
            if slope > min_slope:  # Upward slope
                consecutive_count += 1
                max_consecutive = max(max_consecutive, consecutive_count)
            else:
                consecutive_count = 0
                
        # Check if we have enough consecutive periods
        is_uptrend = max_consecutive >= min_weeks
        
        return is_uptrend, max_consecutive
    
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
        
    @classmethod
    def calculate_trend_indicators(cls, data, time_frame='weekly', ema_period=13, min_slope=10, min_weeks=3):
        """
        Calculate trend indicators including EMA slope and uptrend duration
        
        Args:
            data: DataFrame with price data
            time_frame: Time frame for indicators (daily, weekly, monthly)
            ema_period: EMA period to use for slope calculation
            min_slope: Minimum slope in degrees to consider as upward
            min_weeks: Minimum number of consecutive periods with upward slope
            
        Returns:
            Tuple of (DataFrame with trend indicators, is_uptrend, uptrend_duration)
        """
        if data.empty or len(data) < min_weeks:
            logger.warning(f"Not enough data points for trend analysis ({len(data)} < {min_weeks})")
            return pd.DataFrame(), False, 0
            
        # Calculate all indicators first
        df = cls.calculate_all_indicators(data, time_frame)
        
        # Calculate EMA slope
        df = cls.calculate_ema_slope(df, ema_period, window=min_weeks)
        
        # Check uptrend duration
        is_uptrend, duration = cls.check_uptrend_duration(df, ema_period, min_slope, min_weeks)
        
        return df, is_uptrend, duration
        return data.iloc[-1:].copy()