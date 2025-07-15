"""
Optimized monthly filtering implementation with improved logic and flexibility
"""
import logging
import pandas as pd
import numpy as np
from src.indicators.technical import TechnicalIndicators
from src.utils.logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

class OptimizedMonthlyFilter:
    """
    Optimized monthly filter with more flexible criteria and better stock discovery
    """
    
    def __init__(self, config):
        """Initialize with configuration"""
        self.config = config
        
    def check_monthly_filters(self, indicators, symbol):
        """
        Check optimized monthly filtering criteria using OR logic between conditions
        
        Args:
            indicators: DataFrame with calculated indicators (with MONTHLY_ prefix)
            symbol: Stock symbol for logging
            
        Returns:
            dict: Results of each condition check
        """
        if indicators.empty or len(indicators) == 0:
            logger.debug(f"{symbol}: No indicators data available for monthly filtering")
            return {'passed': False, 'conditions': {}}
        
        results = {
            'passed': False,
            'conditions': {},
            'details': {}
        }
        
        # Check each condition (OR logic - any one passing is sufficient)
        conditions = [
            ('condition_1', self._check_condition_1),
            ('condition_2', self._check_condition_2), 
            ('condition_3', self._check_condition_3),
            ('condition_4', self._check_condition_4),
            ('condition_5', self._check_condition_5)
        ]
        
        for condition_name, condition_func in conditions:
            try:
                condition_result = condition_func(indicators, symbol)
                results['conditions'][condition_name] = condition_result
                
                if condition_result['passed']:
                    results['passed'] = True
                    logger.info(f"{symbol}: Passed monthly {condition_name} - {condition_result['reason']}")
                    
            except Exception as e:
                logger.error(f"Error checking {condition_name} for {symbol}: {e}")
                results['conditions'][condition_name] = {'passed': False, 'reason': f'Error: {str(e)}'}
        
        return results
    
    def _check_condition_1(self, indicators, symbol):
        """
        Condition 1: Trend Confirmation (ENHANCED)
        - 3 consecutive green candles OR above MA6 OR above MA12
        - More flexible than original (only MA20)
        """
        latest = indicators.iloc[-1]
        reasons = []
        
        # Check 3 consecutive green candles
        if TechnicalIndicators.check_three_consecutive_green_candles(indicators):
            reasons.append("3 consecutive green candles")
            return {'passed': True, 'reason': '; '.join(reasons)}
        
        # Check if above MA6 (short-term trend)
        close_price = latest.get('Close', None)
        ma6 = latest.get('MONTHLY_MA_6', None)
        
        if close_price and ma6 and not (pd.isna(close_price) or pd.isna(ma6)):
            if close_price > ma6:
                reasons.append(f"Above MA6 ({close_price:.2f} > {ma6:.2f})")
                return {'passed': True, 'reason': '; '.join(reasons)}
        
        # Check if above MA12 (medium-term trend)
        ma12 = latest.get('MONTHLY_MA_12', None)
        if close_price and ma12 and not (pd.isna(close_price) or pd.isna(ma12)):
            if close_price > ma12:
                reasons.append(f"Above MA12 ({close_price:.2f} > {ma12:.2f})")
                return {'passed': True, 'reason': '; '.join(reasons)}
        
        # Check if above MA3 (very short-term)
        ma3 = latest.get('MONTHLY_MA_3', None)
        if close_price and ma3 and not (pd.isna(close_price) or pd.isna(ma3)):
            if close_price > ma3:
                reasons.append(f"Above MA3 ({close_price:.2f} > {ma3:.2f})")
                return {'passed': True, 'reason': '; '.join(reasons)}
        
        return {'passed': False, 'reason': 'No trend confirmation signals'}
    
    def _check_condition_2(self, indicators, symbol):
        """
        Condition 2: Bollinger Pattern (KEPT - already good)
        - Bollinger squeeze -> expansion
        """
        if TechnicalIndicators.check_bollinger_squeeze_expansion(indicators):
            return {'passed': True, 'reason': 'Bollinger squeeze expansion'}
        
        return {'passed': False, 'reason': 'No Bollinger squeeze expansion'}
    
    def _check_condition_3(self, indicators, symbol):
        """
        Condition 3: RSI Momentum (RELAXED)
        - RSI moving from 45 towards 65 (was 50-60)
        - More permissive range for monthly timeframe
        """
        latest = indicators.iloc[-1]
        
        # Check RSI in relaxed range
        rsi = latest.get('MONTHLY_RSI_14', None)
        if not rsi or pd.isna(rsi):
            return {'passed': False, 'reason': 'Missing RSI data'}
        
        # Check if RSI is in momentum building range (45-65)
        if 45 <= rsi <= 65:
            # Check if RSI is trending upward
            if len(indicators) >= 3:
                recent_rsi = indicators['MONTHLY_RSI_14'].tail(3).dropna()
                if len(recent_rsi) >= 2:
                    if recent_rsi.iloc[-1] > recent_rsi.iloc[-2]:
                        return {'passed': True, 'reason': f'RSI momentum building ({rsi:.1f}, trending up)'}
            
            return {'passed': True, 'reason': f'RSI in momentum range ({rsi:.1f})'}
        
        return {'passed': False, 'reason': f'RSI outside momentum range ({rsi:.1f} not in 45-65)'}
    
    def _check_condition_4(self, indicators, symbol):
        """
        Condition 4: Volume and Price Action (NEW)
        - Price above MA3 AND volume increasing
        - MACD improving AND RSI > 40
        """
        latest = indicators.iloc[-1]
        reasons = []
        
        # Check price above MA3
        close_price = latest.get('Close', None)
        ma3 = latest.get('MONTHLY_MA_3', None)
        
        if not (close_price and ma3 and not (pd.isna(close_price) or pd.isna(ma3))):
            return {'passed': False, 'reason': 'Missing price or MA3 data'}
        
        if close_price <= ma3:
            return {'passed': False, 'reason': f'Price({close_price:.2f}) not above MA3({ma3:.2f})'}
        
        reasons.append(f"Price({close_price:.2f}) > MA3({ma3:.2f})")
        
        # Check volume increasing (simplified - compare recent vs historical average)
        if len(indicators) >= 6:
            recent_volume = indicators['Volume'].tail(3).mean()
            historical_volume = indicators['Volume'].tail(12).mean()
            
            if recent_volume > historical_volume:
                reasons.append(f"Volume increasing (recent: {recent_volume:.0f} vs avg: {historical_volume:.0f})")
            else:
                return {'passed': False, 'reason': 'Volume not increasing'}
        
        # Check MACD improving
        macd = latest.get('MONTHLY_MACD', None)
        macd_signal = latest.get('MONTHLY_MACD_Signal', None)
        
        if macd and macd_signal and not (pd.isna(macd) or pd.isna(macd_signal)):
            if macd > macd_signal:
                reasons.append("MACD above signal")
            else:
                # Check if MACD is improving (getting closer to signal)
                if len(indicators) >= 2:
                    prev_macd = indicators['MONTHLY_MACD'].iloc[-2]
                    prev_signal = indicators['MONTHLY_MACD_Signal'].iloc[-2]
                    
                    if not (pd.isna(prev_macd) or pd.isna(prev_signal)):
                        current_diff = macd - macd_signal
                        prev_diff = prev_macd - prev_signal
                        
                        if current_diff > prev_diff:
                            reasons.append("MACD improving")
                        else:
                            return {'passed': False, 'reason': 'MACD not improving'}
        
        # Check RSI > 40
        rsi = latest.get('MONTHLY_RSI_14', None)
        if rsi and not pd.isna(rsi):
            if rsi > 40:
                reasons.append(f"RSI({rsi:.1f}) > 40")
            else:
                return {'passed': False, 'reason': f'RSI({rsi:.1f}) <= 40'}
        
        return {'passed': True, 'reason': '; '.join(reasons)}
    
    def _check_condition_5(self, indicators, symbol):
        """
        Condition 5: EMA Trend and Momentum (NEW)
        - EMA4 > EMA8 (short-term uptrend)
        - Price within 10% of EMA4 (not extended)
        - Volume above 6-month average
        """
        latest = indicators.iloc[-1]
        reasons = []
        
        # Check EMA trend
        ema4 = latest.get('MONTHLY_EMA_4_Close', None)
        ema8 = latest.get('MONTHLY_EMA_8_Close', None)
        
        if not (ema4 and ema8 and not (pd.isna(ema4) or pd.isna(ema8))):
            return {'passed': False, 'reason': 'Missing EMA data'}
        
        if ema4 <= ema8:
            return {'passed': False, 'reason': f'EMA4({ema4:.2f}) not > EMA8({ema8:.2f})'}
        
        reasons.append(f"EMA4({ema4:.2f}) > EMA8({ema8:.2f})")
        
        # Check price within 10% of EMA4
        close_price = latest.get('Close', None)
        if close_price and not pd.isna(close_price):
            price_ema_diff = abs(close_price - ema4) / ema4
            if price_ema_diff > 0.10:
                return {'passed': False, 'reason': f'Price({close_price:.2f}) too far from EMA4({ema4:.2f})'}
            
            reasons.append(f"Price near EMA4 (diff: {price_ema_diff:.1%})")
        
        # Check volume above 6-month average
        if len(indicators) >= 6:
            recent_volume = indicators['Volume'].tail(2).mean()
            avg_volume = indicators['Volume'].tail(6).mean()
            
            if recent_volume > avg_volume:
                reasons.append(f"Volume above average (recent: {recent_volume:.0f} vs avg: {avg_volume:.0f})")
            else:
                return {'passed': False, 'reason': 'Volume below average'}
        
        return {'passed': True, 'reason': '; '.join(reasons)}

    def get_filter_summary(self, results):
        """
        Get a summary of filter results for reporting
        
        Args:
            results: Results from check_monthly_filters
            
        Returns:
            str: Summary string
        """
        if not results['passed']:
            return "Failed all monthly conditions"
        
        passed_conditions = [condition for condition, result in results['conditions'].items() 
                           if result.get('passed', False)]
        
        return f"Passed: {', '.join(passed_conditions)}"