#!/usr/bin/env python3
"""
Test script for the new weekly and monthly filtering criteria
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.indicators.technical import TechnicalIndicators

def create_test_data():
    """Create sample test data for testing"""
    dates = pd.date_range(start='2023-01-01', end='2024-12-31', freq='W')
    np.random.seed(42)
    
    # Create sample OHLCV data
    data = pd.DataFrame({
        'Open': np.random.uniform(100, 200, len(dates)),
        'High': np.random.uniform(150, 250, len(dates)),
        'Low': np.random.uniform(50, 150, len(dates)),
        'Close': np.random.uniform(100, 200, len(dates)),
        'Volume': np.random.uniform(1000000, 10000000, len(dates))
    }, index=dates)
    
    # Ensure High >= max(Open, Close) and Low <= min(Open, Close)
    data['High'] = np.maximum(data['High'], np.maximum(data['Open'], data['Close']))
    data['Low'] = np.minimum(data['Low'], np.minimum(data['Open'], data['Close']))
    
    return data

def test_technical_indicators():
    """Test the enhanced technical indicators"""
    print("Testing enhanced technical indicators...")
    
    # Create test data
    data = create_test_data()
    print(f"Created test data with {len(data)} weekly data points")
    
    # Calculate indicators
    indicators = TechnicalIndicators.calculate_all_indicators(data, 'weekly')
    print(f"Calculated indicators: {list(indicators.columns)}")
    
    # Test specific indicator functions
    print("\nTesting specific indicator functions:")
    
    # Test MACD golden cross
    macd_golden = TechnicalIndicators.check_macd_golden_cross(indicators)
    print(f"MACD Golden Cross: {macd_golden}")
    
    # Test MACD near golden cross
    macd_near = TechnicalIndicators.check_macd_near_golden_cross(indicators)
    print(f"MACD Near Golden Cross: {macd_near}")
    
    # Test three consecutive green candles
    three_green = TechnicalIndicators.check_three_consecutive_green_candles(indicators)
    print(f"Three Consecutive Green Candles: {three_green}")
    
    # Test Bollinger squeeze expansion
    bb_squeeze = TechnicalIndicators.check_bollinger_squeeze_expansion(indicators)
    print(f"Bollinger Squeeze Expansion: {bb_squeeze}")
    
    # Test RSI momentum
    rsi_momentum = TechnicalIndicators.check_rsi_momentum_50_to_60(indicators)
    print(f"RSI Momentum 50-60: {rsi_momentum}")
    
    # Test volume increase YoY
    volume_yoy = TechnicalIndicators.check_volume_increase_yoy(indicators)
    print(f"Volume Increase YoY: {volume_yoy}")
    
    # Test volume breakout
    volume_breakout = TechnicalIndicators.check_volume_breakout(indicators)
    print(f"Volume Breakout: {volume_breakout}")
    
    # Test DMI positive turn
    dmi_positive = TechnicalIndicators.check_dmi_positive_turn(indicators)
    print(f"DMI Positive Turn: {dmi_positive}")
    
    # Test Bollinger breakout
    bb_breakout_middle = TechnicalIndicators.check_bollinger_breakout(indicators, 'middle')
    bb_breakout_upper = TechnicalIndicators.check_bollinger_breakout(indicators, 'upper')
    print(f"Bollinger Breakout (Middle): {bb_breakout_middle}")
    print(f"Bollinger Breakout (Upper): {bb_breakout_upper}")
    
    # Test OBV uptrend
    obv_uptrend = TechnicalIndicators.check_obv_uptrend(indicators)
    print(f"OBV Uptrend: {obv_uptrend}")
    
    print("\nTest completed successfully!")
    return indicators

def test_config_loading():
    """Test configuration loading"""
    print("\nTesting configuration loading...")
    
    try:
        import yaml
        config_path = os.path.join(os.path.dirname(__file__), "config", "config.yaml")
        with open(config_path, "r") as config_file:
            config = yaml.safe_load(config_file)
        
        print("Configuration loaded successfully!")
        print(f"Available timeframes for MA: {list(config['indicators']['ma'].keys())}")
        print(f"Available timeframes for Bollinger: {list(config['indicators']['bollinger'].keys())}")
        print(f"Available timeframes for DMI: {list(config['indicators']['dmi'].keys())}")
        
        # Check filtering criteria
        if 'filtering_criteria' in config:
            print(f"Weekly combinations: {list(config['filtering_criteria']['weekly'].keys())}")
            print(f"Monthly conditions: {list(config['filtering_criteria']['monthly'].keys())}")
        
        return True
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return False

if __name__ == "__main__":
    print("=== Testing New Weekly and Monthly Filtering Criteria ===")
    
    # Test configuration loading
    config_ok = test_config_loading()
    
    if config_ok:
        # Test technical indicators
        try:
            indicators = test_technical_indicators()
            print(f"\nFinal indicators shape: {indicators.shape}")
            print("All tests completed successfully!")
        except Exception as e:
            print(f"Error in technical indicators test: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("Configuration test failed, skipping technical indicators test")