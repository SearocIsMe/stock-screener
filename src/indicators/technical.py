"""
Technical indicators module for calculating EMA, BIAS, RSI, and MACD
"""
import os
import logging
import yaml
import numpy as np
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "config.yaml")
with open(config_path, "r") as config_file:
    config = yaml.safe_load(config_file)

class TechnicalIndicators:
    """Technical indicators calculation class"""
    
    @staticmethod
    def calculate_ema(data, period=13, price_col='Close'):
        """
        Calculate Exponential Moving Average (EMA)
        
        Args:
            data: DataFrame with price data
            period: EMA period
            price_col: Column name for price data
        
        Returns:
            Series with EMA values
        """
        if len(data) < period:
            logger.warning(f"Not enough data to calculate EMA ({len(data)} < {period})")
            return pd.Series(np.nan, index=data.index)
        
        return data[price_col].ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_bias(data, ema, price_col='Close'):
        """
        Calculate BIAS indicator
        BIAS = (Price - EMA) / EMA * 100
        
        Args:
            data: DataFrame with price data
            ema: Series with EMA values
            price_col: Column name for price data
        
        Returns:
            Series with BIAS values
        """
        if ema.isnull().all():
            logger.warning("EMA values are all NaN, cannot calculate BIAS")
            return pd.Series(np.nan, index=data.index)
        
        return (data[price_col] - ema) / ema * 100
    
    @staticmethod
    def calculate_rsi(data, period=14, price_col='Close'):
        """
        Calculate Relative Strength Index (RSI)
        
        Args:
            data: DataFrame with price data
            period: RSI period
            price_col: Column name for price data
        
        Returns:
            Series with RSI values
        """
        if len(data) < period + 1:
            logger.warning(f"Not enough data to calculate RSI ({len(data)} < {period + 1})")
            return pd.Series(np.nan, index=data.index)
        
        # Calculate price changes
        delta = data[price_col].diff()
        
        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Calculate average gain and loss
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_macd(data, fast_period=12, slow_period=26, signal_period=9, price_col='Close'):
        """
        Calculate Moving Average Convergence Divergence (MACD)
        
        Args:
            data: DataFrame with price data
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            signal_period: Signal EMA period
            price_col: Column name for price data
        
        Returns:
            DataFrame with MACD, Signal, and Histogram values
        """
        if len(data) < slow_period:
            logger.warning(f"Not enough data to calculate MACD ({len(data)} < {slow_period})")
            return pd.DataFrame(
                {
                    'MACD': np.nan,
                    'Signal': np.nan,
                    'Histogram': np.nan
                },
                index=data.index
            )
        
        # Calculate fast and slow EMAs
        fast_ema = data[price_col].ewm(span=fast_period, adjust=False).mean()
        slow_ema = data[price_col].ewm(span=slow_period, adjust=False).mean()
        
        # Calculate MACD line
        macd_line = fast_ema - slow_ema
        
        # Calculate signal line
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        
        # Calculate histogram
        histogram = macd_line - signal_line
        
        return pd.DataFrame(
            {
                'MACD': macd_line,
                'Signal': signal_line,
                'Histogram': histogram
            },
            index=data.index
        )
    
    @classmethod
    def calculate_all_indicators(cls, data, time_frame='daily'):
        """
        Calculate all technical indicators for the given data
        
        Args:
            data: DataFrame with price data (must have OHLC columns)
            time_frame: Time frame for indicators (daily, weekly, monthly)
        
        Returns:
            DataFrame with all indicators
        """
        if data.empty:
            logger.warning("Empty data provided, cannot calculate indicators")
            return pd.DataFrame()
        
        # Get configuration for the specified time frame
        tf_config = {
            'ema': config['indicators']['ema'][time_frame],
            'bias': config['indicators']['bias'][time_frame],
            'rsi': config['indicators']['rsi'][time_frame],
            'macd': config['indicators']['macd'][time_frame]
        }
        
        # Create result DataFrame
        result = data.copy()
        
        # Calculate EMA for each price column (OHLC)
        for price_col in ['Open', 'High', 'Low', 'Close']:
            for period in tf_config['ema']['periods']:
                ema_col = f'EMA_{period}_{price_col}'
                result[ema_col] = cls.calculate_ema(data, period, price_col)
                
                # Calculate BIAS for each EMA
                bias_col = f'BIAS_{period}_{price_col}'
                result[bias_col] = cls.calculate_bias(data, result[ema_col], price_col)
        
        # Calculate RSI
        rsi_period = tf_config['rsi']['period']
        result[f'RSI_{rsi_period}'] = cls.calculate_rsi(data, rsi_period)
        
        # Calculate MACD
        macd_config = tf_config['macd']
        macd_data = cls.calculate_macd(
            data,
            fast_period=macd_config['fast_period'],
            slow_period=macd_config['slow_period'],
            signal_period=macd_config['signal_period']
        )
        
        result['MACD'] = macd_data['MACD']
        result['MACD_Signal'] = macd_data['Signal']
        result['MACD_Histogram'] = macd_data['Histogram']
        
        return result
    
    @classmethod
    def calculate_next_day_indicators(cls, historical_data, next_day_data, time_frame='daily'):
        """
        Calculate indicators for the next day using historical data
        
        Args:
            historical_data: DataFrame with historical price data
            next_day_data: DataFrame with next day's price data
            time_frame: Time frame for indicators (daily, weekly, monthly)
        
        Returns:
            DataFrame with indicators for the next day
        """
        if historical_data.empty or next_day_data.empty:
            logger.warning("Empty data provided, cannot calculate next day indicators")
            return pd.DataFrame()
        
        # Combine historical and next day data
        combined_data = pd.concat([historical_data, next_day_data])
        
        # Calculate indicators for the combined data
        indicators = cls.calculate_all_indicators(combined_data, time_frame)
        
        # Return only the indicators for the next day
        return indicators.iloc[-1:]