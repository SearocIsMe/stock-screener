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
        using pandas-ta with timeframe-specific configurations and column naming
        
        Args:
            data: DataFrame with price data (must have OHLC columns)
            time_frame: Time frame for indicators (daily, weekly, monthly)
        
        Returns:
            DataFrame with all indicators for the specified timeframe with timeframe-prefixed columns
        """
        if data.empty:
            logger.warning("Empty data provided, cannot calculate indicators")
            return pd.DataFrame()
        
        # Timeframe-specific data validation
        min_data_points = {
            'daily': 30,    # Need at least 30 days for reliable indicators
            'weekly': 20,   # Need at least 20 weeks for reliable indicators
            'monthly': 12   # Need at least 12 months for reliable indicators
        }
        
        required_points = min_data_points.get(time_frame, 30)
        if len(data) < required_points:
            logger.warning(f"Not enough data points for reliable {time_frame} indicators ({len(data)} < {required_points})")
            return pd.DataFrame()
        
        # Validate timeframe parameter
        valid_timeframes = ['daily', 'weekly', 'monthly']
        if time_frame not in valid_timeframes:
            logger.error(f"Invalid timeframe '{time_frame}'. Must be one of: {valid_timeframes}")
            return pd.DataFrame()
        
        # Log the timeframe being used for calculations
        logger.info(f"Calculating {time_frame.upper()} indicators with {len(data)} data points using timeframe-specific parameters")
        
        # Get configuration for the specified time frame
        ema_config = config['indicators']['ema'][time_frame]
        rsi_config = config['indicators']['rsi'][time_frame]
        macd_config = config['indicators']['macd'][time_frame]
        ma_config = config['indicators']['ma'][time_frame]
        bollinger_config = config['indicators']['bollinger'][time_frame]
        dmi_config = config['indicators']['dmi'][time_frame]
        atr_config = config['indicators']['atr'][time_frame]
        stochastic_config = config['indicators']['stochastic'][time_frame]
        williams_r_config = config['indicators']['williams_r'][time_frame]
        
        # Create a copy of the data to avoid modifying the original
        df = data.copy()
        
        # Add timeframe prefix for better differentiation
        tf_prefix = time_frame.upper()
        
        # Calculate EMA for each period in the config with timeframe prefix
        for period in ema_config['periods']:
            # Calculate EMA using pandas-ta
            ema_col = f'{tf_prefix}_EMA_{period}_Close'
            df[ema_col] = df.ta.ema(close='Close', length=period)
            
            # Calculate BIAS (Price - EMA) / EMA * 100
            bias_col = f'{tf_prefix}_BIAS_{period}_Close'
            df[bias_col] = (df['Close'] - df[ema_col]) / df[ema_col] * 100
        
        # Calculate Simple Moving Averages (MA) with timeframe prefix
        for period in ma_config['periods']:
            ma_col = f'{tf_prefix}_MA_{period}'
            df[ma_col] = df.ta.sma(close='Close', length=period)
        
        # Calculate RSI with timeframe prefix
        rsi_period = rsi_config['period']
        rsi_result = df.ta.rsi(close='Close', length=rsi_period)
        
        # Handle case where RSI returns DataFrame instead of Series
        if isinstance(rsi_result, pd.DataFrame):
            # Take the first column if it's a DataFrame
            rsi_col = rsi_result.columns[0] if len(rsi_result.columns) > 0 else None
            if rsi_col:
                df[f'{tf_prefix}_RSI_{rsi_period}'] = rsi_result[rsi_col]
            else:
                df[f'{tf_prefix}_RSI_{rsi_period}'] = pd.Series([np.nan] * len(df), index=df.index)
        else:
            df[f'{tf_prefix}_RSI_{rsi_period}'] = rsi_result
        
        # Calculate MACD with timeframe-specific parameters and prefix
        macd = df.ta.macd(
            close='Close',
            fast=macd_config['fast_period'],
            slow=macd_config['slow_period'],
            signal=macd_config['signal_period']
        )
        
        # MACD returns a DataFrame with columns: MACD_fast_slow_signal, MACDh_fast_slow_signal, MACDs_fast_slow_signal
        # Rename to match our expected column names with timeframe prefix
        if macd is not None and not macd.empty:
            df[f'{tf_prefix}_MACD'] = macd[f'MACD_{macd_config["fast_period"]}_{macd_config["slow_period"]}_{macd_config["signal_period"]}']
            df[f'{tf_prefix}_MACD_Signal'] = macd[f'MACDs_{macd_config["fast_period"]}_{macd_config["slow_period"]}_{macd_config["signal_period"]}']
            df[f'{tf_prefix}_MACD_Histogram'] = macd[f'MACDh_{macd_config["fast_period"]}_{macd_config["slow_period"]}_{macd_config["signal_period"]}']
        
        # Calculate Bollinger Bands with timeframe prefix
        bb_period = bollinger_config['period']
        bb_std = bollinger_config['std_dev']
        bb = df.ta.bbands(close='Close', length=bb_period, std=bb_std)
        if bb is not None and not bb.empty:
            # Handle both integer and decimal standard deviations in column naming
            bb_std_str = f"{bb_std:.1f}" if bb_std != int(bb_std) else str(int(bb_std))
            
            # Try different column naming patterns
            possible_columns = [
                f'BBL_{bb_period}_{bb_std_str}.0',
                f'BBL_{bb_period}_{bb_std}',
                f'BBL_{bb_period}_{int(bb_std)}.0' if bb_std == int(bb_std) else f'BBL_{bb_period}_{bb_std:.1f}',
            ]
            
            bb_lower_col = None
            bb_middle_col = None
            bb_upper_col = None
            
            # Find the correct column names
            for col_pattern in possible_columns:
                if col_pattern in bb.columns:
                    bb_lower_col = col_pattern
                    bb_middle_col = col_pattern.replace('BBL_', 'BBM_')
                    bb_upper_col = col_pattern.replace('BBL_', 'BBU_')
                    break
            
            # If standard patterns don't work, search for any BB columns
            if bb_lower_col is None:
                bb_cols = [col for col in bb.columns if 'BBL_' in col]
                if bb_cols:
                    bb_lower_col = bb_cols[0]
                    bb_middle_col = bb_lower_col.replace('BBL_', 'BBM_')
                    bb_upper_col = bb_lower_col.replace('BBL_', 'BBU_')
            
            if bb_lower_col and bb_lower_col in bb.columns:
                df[f'{tf_prefix}_BB_Lower'] = bb[bb_lower_col]
                df[f'{tf_prefix}_BB_Middle'] = bb[bb_middle_col]
                df[f'{tf_prefix}_BB_Upper'] = bb[bb_upper_col]
                df[f'{tf_prefix}_BB_Width'] = df[f'{tf_prefix}_BB_Upper'] - df[f'{tf_prefix}_BB_Lower']
                df[f'{tf_prefix}_BB_Position'] = (df['Close'] - df[f'{tf_prefix}_BB_Lower']) / (df[f'{tf_prefix}_BB_Upper'] - df[f'{tf_prefix}_BB_Lower'])
            else:
                logger.warning(f"Could not find Bollinger Bands columns for {tf_prefix}. Available columns: {bb.columns.tolist()}")
        
        # Calculate OBV (On-Balance Volume) with timeframe prefix
        df[f'{tf_prefix}_OBV'] = df.ta.obv(close='Close', volume='Volume')
        
        # Calculate DMI (Directional Movement Index) with timeframe prefix
        dmi_period = dmi_config['period']
        dmi = df.ta.dm(high='High', low='Low', close='Close', length=dmi_period)
        if dmi is not None and not dmi.empty:
            df[f'{tf_prefix}_DMP'] = dmi[f'DMP_{dmi_period}']  # Positive Directional Movement
            df[f'{tf_prefix}_DMN'] = dmi[f'DMN_{dmi_period}']  # Negative Directional Movement
        
        # Calculate ADX (Average Directional Index) with timeframe prefix
        adx = df.ta.adx(high='High', low='Low', close='Close', length=dmi_period)
        if adx is not None and not adx.empty:
            df[f'{tf_prefix}_ADX'] = adx[f'ADX_{dmi_period}']
            df[f'{tf_prefix}_DI_Plus'] = adx[f'DMP_{dmi_period}']
            df[f'{tf_prefix}_DI_Minus'] = adx[f'DMN_{dmi_period}']
        
        # Calculate additional indicators for comprehensive analysis with timeframe-specific periods and prefixes
        # Use timeframe-specific configurations for each indicator
        
        # ATR with timeframe-specific period and prefix
        atr_period = atr_config['period']
        df[f'{tf_prefix}_ATR'] = df.ta.atr(high='High', low='Low', close='Close', length=atr_period)
        
        # Stochastic with timeframe-specific periods and prefix
        stoch_k = stochastic_config['k_period']
        stoch_d = stochastic_config['d_period']
        stoch_smooth = stochastic_config['smooth_k']
        stoch_result = df.ta.stoch(high='High', low='Low', close='Close', k=stoch_k, d=stoch_d, smooth_k=stoch_smooth)
        if stoch_result is not None and not stoch_result.empty:
            df[f'{tf_prefix}_Stochastic_K'] = stoch_result[f'STOCHk_{stoch_k}_{stoch_d}_{stoch_smooth}']
            df[f'{tf_prefix}_Stochastic_D'] = stoch_result[f'STOCHd_{stoch_k}_{stoch_d}_{stoch_smooth}']
        
        # Williams %R with timeframe-specific period and prefix
        williams_period = williams_r_config['period']
        df[f'{tf_prefix}_Williams_R'] = df.ta.willr(high='High', low='Low', close='Close', length=williams_period)
        
        # Log the calculated indicators with timeframe differentiation
        indicator_columns = [col for col in df.columns if col.startswith(tf_prefix)]
        
        if cls.calucated_amount > 100:
            logger.info(f"Calculated {len(indicator_columns)} {time_frame.upper()} indicators for {cls.calucated_amount} stocks")
            logger.debug(f"{time_frame.upper()} indicators: {', '.join(indicator_columns[:10])}{'...' if len(indicator_columns) > 10 else ''}")
            cls.calucated_amount = 1
        else:
            cls.calucated_amount += 1
        
        # Add summary of timeframe-specific parameters used
        logger.debug(f"{time_frame.upper()} timeframe parameters - EMA: {ema_config['periods']}, "
                    f"MACD: ({macd_config['fast_period']},{macd_config['slow_period']},{macd_config['signal_period']}), "
                    f"MA: {ma_config['periods']}")
        
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
    
    @staticmethod
    def check_macd_golden_cross(data, lookback_periods=3, timeframe_prefix=None):
        """
        Check if MACD just formed a golden cross (MACD line crosses above signal line)
        
        Args:
            data: DataFrame with MACD and MACD_Signal columns
            lookback_periods: Number of periods to look back for recent golden cross
            timeframe_prefix: Optional timeframe prefix (e.g., 'WEEKLY_', 'MONTHLY_')
            
        Returns:
            bool: True if golden cross occurred recently
        """
        if data.empty or len(data) < lookback_periods + 1:
            return False
        
        # Determine column names based on timeframe prefix
        if timeframe_prefix:
            macd_col = f'{timeframe_prefix}MACD'
            signal_col = f'{timeframe_prefix}MACD_Signal'
        else:
            # Try to find MACD columns with any timeframe prefix
            macd_cols = [col for col in data.columns if col.endswith('_MACD') or col == 'MACD']
            signal_cols = [col for col in data.columns if col.endswith('_MACD_Signal') or col == 'MACD_Signal']
            
            if not macd_cols or not signal_cols:
                return False
            
            macd_col = macd_cols[0]
            signal_col = signal_cols[0]
        
        if macd_col not in data.columns or signal_col not in data.columns:
            return False
        
        # Check recent periods for golden cross
        recent_data = data.tail(lookback_periods + 1)
        
        for i in range(1, len(recent_data)):
            prev_macd = recent_data[macd_col].iloc[i-1]
            prev_signal = recent_data[signal_col].iloc[i-1]
            curr_macd = recent_data[macd_col].iloc[i]
            curr_signal = recent_data[signal_col].iloc[i]
            
            # Check if MACD crossed above signal line
            if (prev_macd <= prev_signal and curr_macd > curr_signal and
                not pd.isna(prev_macd) and not pd.isna(prev_signal) and
                not pd.isna(curr_macd) and not pd.isna(curr_signal)):
                return True
        
        return False
    
    @staticmethod
    def check_macd_near_golden_cross(data, threshold=0.1, timeframe_prefix=None):
        """
        Check if MACD is approaching golden cross (MACD line close to signal line from below)
        
        Args:
            data: DataFrame with MACD and MACD_Signal columns
            threshold: Threshold for "close" (as percentage of signal line)
            timeframe_prefix: Optional timeframe prefix (e.g., 'WEEKLY_', 'MONTHLY_')
            
        Returns:
            bool: True if MACD is approaching golden cross
        """
        if data.empty:
            return False
        
        # Determine column names based on timeframe prefix
        if timeframe_prefix:
            macd_col = f'{timeframe_prefix}MACD'
            signal_col = f'{timeframe_prefix}MACD_Signal'
        else:
            # Try to find MACD columns with any timeframe prefix
            macd_cols = [col for col in data.columns if col.endswith('_MACD') or col == 'MACD']
            signal_cols = [col for col in data.columns if col.endswith('_MACD_Signal') or col == 'MACD_Signal']
            
            if not macd_cols or not signal_cols:
                return False
            
            macd_col = macd_cols[0]
            signal_col = signal_cols[0]
        
        if macd_col not in data.columns or signal_col not in data.columns:
            return False
        
        latest = data.iloc[-1]
        macd = latest[macd_col]
        signal = latest[signal_col]
        
        if pd.isna(macd) or pd.isna(signal) or signal == 0:
            return False
        
        # Check if MACD is below but close to signal line
        if macd < signal:
            diff_pct = abs(macd - signal) / abs(signal)
            return diff_pct <= threshold
        
        return False
    
    @staticmethod
    def check_three_consecutive_green_candles(data):
        """
        Check if there are 3 consecutive green (bullish) candles
        
        Args:
            data: DataFrame with Open and Close columns
            
        Returns:
            bool: True if last 3 candles are green
        """
        if data.empty or len(data) < 3:
            return False
        
        if 'Open' not in data.columns or 'Close' not in data.columns:
            return False
        
        # Check last 3 candles
        recent_data = data.tail(3)
        
        for _, row in recent_data.iterrows():
            if pd.isna(row['Open']) or pd.isna(row['Close']) or row['Close'] <= row['Open']:
                return False
        
        return True
    
    @staticmethod
    def check_bollinger_squeeze_expansion(data, squeeze_threshold=0.1, expansion_threshold=0.2, timeframe_prefix=None):
        """
        Check if Bollinger Bands had a squeeze and then expanded upward
        
        Args:
            data: DataFrame with Bollinger Bands columns
            squeeze_threshold: Threshold for identifying squeeze (BB_Width relative to price)
            expansion_threshold: Threshold for identifying expansion
            timeframe_prefix: Optional timeframe prefix (e.g., 'WEEKLY_', 'MONTHLY_')
            
        Returns:
            bool: True if squeeze followed by upward expansion occurred
        """
        if data.empty or len(data) < 10:
            return False
        
        # Determine column names based on timeframe prefix
        if timeframe_prefix:
            bb_width_col = f'{timeframe_prefix}BB_Width'
            bb_upper_col = f'{timeframe_prefix}BB_Upper'
            bb_middle_col = f'{timeframe_prefix}BB_Middle'
        else:
            # Try to find BB columns with any timeframe prefix
            bb_width_cols = [col for col in data.columns if col.endswith('_BB_Width') or col == 'BB_Width']
            bb_upper_cols = [col for col in data.columns if col.endswith('_BB_Upper') or col == 'BB_Upper']
            bb_middle_cols = [col for col in data.columns if col.endswith('_BB_Middle') or col == 'BB_Middle']
            
            if not bb_width_cols or not bb_upper_cols or not bb_middle_cols:
                return False
            
            bb_width_col = bb_width_cols[0]
            bb_upper_col = bb_upper_cols[0]
            bb_middle_col = bb_middle_cols[0]
        
        required_cols = [bb_width_col, 'Close', bb_upper_col, bb_middle_col]
        if not all(col in data.columns for col in required_cols):
            return False
        
        recent_data = data.tail(10)
        
        # Find squeeze periods (low BB_Width relative to price)
        recent_data = recent_data.copy()
        recent_data['BB_Width_Pct'] = recent_data[bb_width_col] / recent_data['Close']
        
        # Look for squeeze followed by expansion
        squeeze_found = False
        for i in range(len(recent_data) - 3):
            # Check for squeeze
            if recent_data['BB_Width_Pct'].iloc[i] < squeeze_threshold:
                squeeze_found = True
                
                # Check for subsequent expansion with upward breakout
                for j in range(i + 1, min(i + 4, len(recent_data))):
                    if (recent_data['BB_Width_Pct'].iloc[j] > expansion_threshold and
                        recent_data['Close'].iloc[j] > recent_data[bb_middle_col].iloc[j]):
                        return True
        
        return False
    
    @staticmethod
    def check_rsi_momentum_50_to_60(data, rsi_period=14, timeframe_prefix=None):
        """
        Check if RSI is moving from 50 towards 60 (upward momentum)
        
        Args:
            data: DataFrame with RSI column
            rsi_period: RSI period to check
            timeframe_prefix: Optional timeframe prefix (e.g., 'WEEKLY_', 'MONTHLY_')
            
        Returns:
            bool: True if RSI shows upward momentum from 50 towards 60
        """
        if data.empty or len(data) < 3:
            return False
        
        # Determine column name based on timeframe prefix
        if timeframe_prefix:
            rsi_col = f'{timeframe_prefix}RSI_{rsi_period}'
        else:
            # Try to find RSI column with any timeframe prefix
            rsi_cols = [col for col in data.columns if col.endswith(f'_RSI_{rsi_period}') or col == f'RSI_{rsi_period}']
            if not rsi_cols:
                return False
            rsi_col = rsi_cols[0]
        
        if rsi_col not in data.columns:
            return False
        
        recent_rsi = data[rsi_col].tail(3).dropna()
        if len(recent_rsi) < 3:
            return False
        
        # Check if RSI is in the 50-60 range and trending upward
        latest_rsi = recent_rsi.iloc[-1]
        prev_rsi = recent_rsi.iloc[-2]
        
        return (50 <= latest_rsi <= 60 and
                latest_rsi > prev_rsi and
                prev_rsi >= 50)
    
    @staticmethod
    def check_volume_increase_yoy(data, current_period_weeks=4):
        """
        Check if recent volume shows year-over-year increase
        
        Args:
            data: DataFrame with Volume column and datetime index
            current_period_weeks: Number of recent weeks to compare
            
        Returns:
            bool: True if recent volume is higher than same period last year
        """
        if data.empty or len(data) < 52:  # Need at least 1 year of weekly data
            return False
        
        if 'Volume' not in data.columns:
            return False
        
        try:
            # Get recent volume average
            recent_volume = data['Volume'].tail(current_period_weeks).mean()
            
            # Get volume from same period last year (52 weeks ago)
            year_ago_start = -(52 + current_period_weeks)
            year_ago_end = -52
            
            if len(data) < abs(year_ago_start):
                return False
            
            year_ago_volume = data['Volume'].iloc[year_ago_start:year_ago_end].mean()
            
            # Check for None or NaN values before comparison
            if (recent_volume is None or year_ago_volume is None or
                pd.isna(recent_volume) or pd.isna(year_ago_volume) or
                year_ago_volume == 0):
                return False
            
            return recent_volume > year_ago_volume
            
        except Exception as e:
            logger.error(f"Error in volume YoY check: {e}")
            return False
    
    @staticmethod
    def check_volume_breakout(data, volume_threshold=1.5, price_breakout=True):
        """
        Check if there's a volume breakout with price breakout
        
        Args:
            data: DataFrame with Volume and price columns
            volume_threshold: Volume multiplier for breakout detection
            price_breakout: Whether to also check for price breakout
            
        Returns:
            bool: True if volume breakout occurred
        """
        if data.empty or len(data) < 20:
            return False
        
        if 'Volume' not in data.columns:
            return False
        
        try:
            # Calculate average volume over last 20 periods
            avg_volume = data['Volume'].tail(20).mean()
            latest_volume = data['Volume'].iloc[-1]
            
            # Check for None or NaN values before comparison
            if (avg_volume is None or latest_volume is None or
                pd.isna(avg_volume) or pd.isna(latest_volume) or
                avg_volume == 0):
                return False
            
            volume_breakout_detected = latest_volume > (avg_volume * volume_threshold)
            
            if not price_breakout:
                return volume_breakout_detected
            
            # Also check for price breakout (above recent high)
            if 'High' in data.columns and 'Close' in data.columns:
                recent_high = data['High'].tail(10).max()
                latest_close = data['Close'].iloc[-1]
                
                if (recent_high is not None and latest_close is not None and
                    not pd.isna(recent_high) and not pd.isna(latest_close)):
                    price_breakout_detected = latest_close > recent_high
                    return volume_breakout_detected and price_breakout_detected
            
            return volume_breakout_detected
            
        except Exception as e:
            logger.error(f"Error in volume breakout check: {e}")
            return False
    
    @staticmethod
    def check_dmi_positive_turn(data, dmi_period=14, timeframe_prefix=None):
        """
        Check if DMI shows positive turn (DI+ crossing above DI-)
        
        Args:
            data: DataFrame with DMI columns
            dmi_period: DMI period
            timeframe_prefix: Optional timeframe prefix (e.g., 'WEEKLY_', 'MONTHLY_')
            
        Returns:
            bool: True if positive DMI turn occurred recently
        """
        if data.empty or len(data) < 3:
            return False
        
        # Determine column names based on timeframe prefix
        if timeframe_prefix:
            di_plus_col = f'{timeframe_prefix}DI_Plus'
            di_minus_col = f'{timeframe_prefix}DI_Minus'
        else:
            # Try to find DMI columns with any timeframe prefix
            di_plus_cols = [col for col in data.columns if col.endswith('_DI_Plus') or col == 'DI_Plus']
            di_minus_cols = [col for col in data.columns if col.endswith('_DI_Minus') or col == 'DI_Minus']
            
            if not di_plus_cols or not di_minus_cols:
                return False
            
            di_plus_col = di_plus_cols[0]
            di_minus_col = di_minus_cols[0]
        
        if di_plus_col not in data.columns or di_minus_col not in data.columns:
            return False
        
        recent_data = data.tail(3)
        
        for i in range(1, len(recent_data)):
            prev_plus = recent_data[di_plus_col].iloc[i-1]
            prev_minus = recent_data[di_minus_col].iloc[i-1]
            curr_plus = recent_data[di_plus_col].iloc[i]
            curr_minus = recent_data[di_minus_col].iloc[i]
            
            # Check if DI+ crossed above DI-
            if (prev_plus <= prev_minus and curr_plus > curr_minus and
                not pd.isna(prev_plus) and not pd.isna(prev_minus) and
                not pd.isna(curr_plus) and not pd.isna(curr_minus)):
                return True
        
        return False
    
    @staticmethod
    def check_bollinger_breakout(data, breakout_type='middle', timeframe_prefix=None):
        """
        Check if price broke out above Bollinger Band middle or upper band
        
        Args:
            data: DataFrame with Bollinger Bands columns
            breakout_type: 'middle' or 'upper' band breakout
            timeframe_prefix: Optional timeframe prefix (e.g., 'WEEKLY_', 'MONTHLY_')
            
        Returns:
            bool: True if breakout occurred
        """
        if data.empty or len(data) < 2:
            return False
        
        # Determine column names based on timeframe prefix
        if timeframe_prefix:
            bb_middle_col = f'{timeframe_prefix}BB_Middle'
            bb_upper_col = f'{timeframe_prefix}BB_Upper'
        else:
            # Try to find BB columns with any timeframe prefix
            bb_middle_cols = [col for col in data.columns if col.endswith('_BB_Middle') or col == 'BB_Middle']
            bb_upper_cols = [col for col in data.columns if col.endswith('_BB_Upper') or col == 'BB_Upper']
            
            if not bb_middle_cols:
                return False
            
            bb_middle_col = bb_middle_cols[0]
            bb_upper_col = bb_upper_cols[0] if bb_upper_cols else None
        
        required_cols = ['Close', bb_middle_col]
        if breakout_type == 'upper':
            if bb_upper_col is None:
                return False
            required_cols.append(bb_upper_col)
        
        if not all(col in data.columns for col in required_cols):
            return False
        
        latest = data.iloc[-1]
        previous = data.iloc[-2]
        
        if breakout_type == 'middle':
            return (previous['Close'] <= previous[bb_middle_col] and
                    latest['Close'] > latest[bb_middle_col])
        else:  # upper
            return (previous['Close'] <= previous[bb_upper_col] and
                    latest['Close'] > latest[bb_upper_col])
    
    @staticmethod
    def check_obv_uptrend(data, periods=5, timeframe_prefix=None):
        """
        Check if OBV is in uptrend
        
        Args:
            data: DataFrame with OBV column
            periods: Number of periods to check for uptrend
            timeframe_prefix: Optional timeframe prefix (e.g., 'WEEKLY_', 'MONTHLY_')
            
        Returns:
            bool: True if OBV is trending upward
        """
        if data.empty or len(data) < periods:
            return False
        
        # Determine column name based on timeframe prefix
        if timeframe_prefix:
            obv_col = f'{timeframe_prefix}OBV'
        else:
            # Try to find OBV column with any timeframe prefix
            obv_cols = [col for col in data.columns if col.endswith('_OBV') or col == 'OBV']
            if not obv_cols:
                return False
            obv_col = obv_cols[0]
        
        if obv_col not in data.columns:
            return False
        
        recent_obv = data[obv_col].tail(periods).dropna()
        if len(recent_obv) < periods:
            return False
        
        # Check if OBV is generally trending upward
        first_value = recent_obv.iloc[0]
        last_value = recent_obv.iloc[-1]
        
        return last_value > first_value