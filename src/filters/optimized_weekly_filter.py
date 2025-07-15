"""
Optimized weekly filtering implementation with improved logic and flexibility
"""
import logging
import pandas as pd
import numpy as np
from src.indicators.technical import TechnicalIndicators
from src.utils.logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

class OptimizedWeeklyFilter:
    """
    Optimized weekly filter with more flexible criteria and better stock discovery
    """
    
    def __init__(self, config):
        """Initialize with configuration"""
        self.config = config
        
    def check_weekly_filters(self, indicators, symbol):
        """
        Check optimized weekly filtering criteria using OR logic between combinations
        
        Args:
            indicators: DataFrame with calculated indicators (with WEEKLY_ prefix)
            symbol: Stock symbol for logging
            
        Returns:
            dict: Results of each combination check
        """
        if indicators.empty or len(indicators) == 0:
            logger.debug(f"{symbol}: No indicators data available for weekly filtering")
            return {'passed': False, 'combinations': {}}
        
        results = {
            'passed': False,
            'combinations': {},
            'details': {}
        }
        
        # Check each combination (OR logic - any one passing is sufficient)
        combinations = [
            ('combination_1', self._check_combination_1),
            ('combination_2', self._check_combination_2), 
            ('combination_3', self._check_combination_3),
            ('combination_4', self._check_combination_4)
        ]
        
        for combo_name, combo_func in combinations:
            try:
                combo_result = combo_func(indicators, symbol)
                results['combinations'][combo_name] = combo_result
                
                if combo_result['passed']:
                    results['passed'] = True
                    logger.info(f"{symbol}: Passed weekly {combo_name} - {combo_result['reason']}")
                    
            except Exception as e:
                logger.error(f"Error checking {combo_name} for {symbol}: {e}")
                results['combinations'][combo_name] = {'passed': False, 'reason': f'Error: {str(e)}'}
        
        return results
    
    def _check_combination_1(self, indicators, symbol):
        """
        Combination 1: Basic Trend + Volume (SIMPLIFIED)
        - MA bullish alignment (MA8 > MA13 OR MA13 > MA20)
        - Volume condition (volume increase YoY OR volume breakout)
        """
        latest = indicators.iloc[-1]
        reasons = []
        
        # Check MA bullish alignment (more flexible)
        ma8 = latest.get('WEEKLY_MA_8', None)
        ma13 = latest.get('WEEKLY_MA_13', None) 
        ma20 = latest.get('WEEKLY_MA_20', None)
        
        ma_bullish = False
        if ma8 and ma13 and not (pd.isna(ma8) or pd.isna(ma13)):
            if ma8 > ma13:
                ma_bullish = True
                reasons.append(f"MA8({ma8:.2f}) > MA13({ma13:.2f})")
        
        if not ma_bullish and ma13 and ma20 and not (pd.isna(ma13) or pd.isna(ma20)):
            if ma13 > ma20:
                ma_bullish = True
                reasons.append(f"MA13({ma13:.2f}) > MA20({ma20:.2f})")
        
        if not ma_bullish:
            return {'passed': False, 'reason': 'No bullish MA alignment'}
        
        # Check volume condition (OR logic)
        volume_ok = False
        
        # Check volume increase YoY
        if TechnicalIndicators.check_volume_increase_yoy(indicators, current_period_weeks=4):
            volume_ok = True
            reasons.append("Volume increase YoY")
        
        # Check volume breakout
        if not volume_ok and TechnicalIndicators.check_volume_breakout(indicators, volume_threshold=1.5):
            volume_ok = True
            reasons.append("Volume breakout")
        
        if not volume_ok:
            return {'passed': False, 'reason': 'No volume support'}
        
        return {'passed': True, 'reason': '; '.join(reasons)}
    
    def _check_combination_2(self, indicators, symbol):
        """
        Combination 2: MACD Momentum (SIMPLIFIED)
        - MACD bullish (golden cross OR near golden cross)
        - Price above MA (above MA8 OR MA13)
        """
        latest = indicators.iloc[-1]
        reasons = []
        
        # Check MACD bullish condition (OR logic)
        macd_bullish = False
        
        if TechnicalIndicators.check_macd_golden_cross(indicators, lookback_periods=5):
            macd_bullish = True
            reasons.append("MACD golden cross")
        
        if not macd_bullish and TechnicalIndicators.check_macd_near_golden_cross(indicators, threshold=0.15):
            macd_bullish = True
            reasons.append("MACD near golden cross")
        
        if not macd_bullish:
            return {'passed': False, 'reason': 'No MACD bullish signal'}
        
        # Check price above MA (OR logic)
        price = latest.get('Close', None)
        ma8 = latest.get('WEEKLY_MA_8', None)
        ma13 = latest.get('WEEKLY_MA_13', None)
        
        price_above_ma = False
        if price and ma8 and not (pd.isna(price) or pd.isna(ma8)):
            if price > ma8:
                price_above_ma = True
                reasons.append(f"Price({price:.2f}) > MA8({ma8:.2f})")
        
        if not price_above_ma and price and ma13 and not (pd.isna(price) or pd.isna(ma13)):
            if price > ma13:
                price_above_ma = True
                reasons.append(f"Price({price:.2f}) > MA13({ma13:.2f})")
        
        if not price_above_ma:
            return {'passed': False, 'reason': 'Price not above key MAs'}
        
        return {'passed': True, 'reason': '; '.join(reasons)}
    
    def _check_combination_3(self, indicators, symbol):
        """
        Combination 3: Bollinger + Momentum (SIMPLIFIED)
        - Bollinger expansion (breakout OR squeeze expansion)
        - Momentum positive (RSI > 45 OR DMI positive)
        """
        latest = indicators.iloc[-1]
        reasons = []
        
        # Check Bollinger expansion (OR logic)
        bollinger_ok = False
        
        if TechnicalIndicators.check_bollinger_breakout(indicators, 'middle'):
            bollinger_ok = True
            reasons.append("Bollinger middle breakout")
        
        if not bollinger_ok and TechnicalIndicators.check_bollinger_breakout(indicators, 'upper'):
            bollinger_ok = True
            reasons.append("Bollinger upper breakout")
        
        if not bollinger_ok and TechnicalIndicators.check_bollinger_squeeze_expansion(indicators):
            bollinger_ok = True
            reasons.append("Bollinger squeeze expansion")
        
        if not bollinger_ok:
            return {'passed': False, 'reason': 'No Bollinger expansion signal'}
        
        # Check momentum positive (OR logic)
        momentum_ok = False
        
        # Check RSI > 45
        rsi = latest.get('WEEKLY_RSI_14', None)
        if rsi and not pd.isna(rsi) and rsi > 45:
            momentum_ok = True
            reasons.append(f"RSI({rsi:.1f}) > 45")
        
        # Check DMI positive
        if not momentum_ok and TechnicalIndicators.check_dmi_positive_turn(indicators):
            momentum_ok = True
            reasons.append("DMI positive turn")
        
        if not momentum_ok:
            return {'passed': False, 'reason': 'No positive momentum'}
        
        return {'passed': True, 'reason': '; '.join(reasons)}
    
    def _check_combination_4(self, indicators, symbol):
        """
        Combination 4: Early Stage Discovery (NEW)
        - Early uptrend (EMA13 > EMA21 AND price near EMA13)
        - Volume support (volume above average)
        - RSI healthy (RSI between 35-65, not overbought/oversold)
        """
        latest = indicators.iloc[-1]
        reasons = []
        
        # Check early uptrend
        ema13 = latest.get('WEEKLY_EMA_13_Close', None)
        ema21 = latest.get('WEEKLY_EMA_21_Close', None)
        price = latest.get('Close', None)
        
        if not (ema13 and ema21 and price and not any(pd.isna(x) for x in [ema13, ema21, price])):
            return {'passed': False, 'reason': 'Missing EMA or price data'}
        
        if ema13 <= ema21:
            return {'passed': False, 'reason': f'EMA13({ema13:.2f}) not > EMA21({ema21:.2f})'}
        
        # Check if price is near EMA13 (within 5%)
        price_ema_diff = abs(price - ema13) / ema13
        if price_ema_diff > 0.05:
            return {'passed': False, 'reason': f'Price({price:.2f}) too far from EMA13({ema13:.2f})'}
        
        reasons.append(f"EMA13({ema13:.2f}) > EMA21({ema21:.2f}), price near EMA13")
        
        # Check volume support (simplified - just check if recent volume is above average)
        if len(indicators) >= 10:
            recent_volume = indicators['Volume'].tail(3).mean()
            avg_volume = indicators['Volume'].tail(20).mean()
            
            if recent_volume > avg_volume:
                reasons.append(f"Volume support (recent: {recent_volume:.0f} vs avg: {avg_volume:.0f})")
            else:
                return {'passed': False, 'reason': 'Insufficient volume support'}
        
        # Check RSI healthy (35-65 range)
        rsi = latest.get('WEEKLY_RSI_14', None)
        if rsi and not pd.isna(rsi):
            if 35 <= rsi <= 65:
                reasons.append(f"Healthy RSI({rsi:.1f})")
            else:
                return {'passed': False, 'reason': f'RSI({rsi:.1f}) outside healthy range (35-65)'}
        else:
            return {'passed': False, 'reason': 'Missing RSI data'}
        
        return {'passed': True, 'reason': '; '.join(reasons)}

    def get_filter_summary(self, results):
        """
        Get a summary of filter results for reporting
        
        Args:
            results: Results from check_weekly_filters
            
        Returns:
            str: Summary string
        """
        if not results['passed']:
            return "Failed all weekly combinations"
        
        passed_combinations = [combo for combo, result in results['combinations'].items() 
                             if result.get('passed', False)]
        
        return f"Passed: {', '.join(passed_combinations)}"