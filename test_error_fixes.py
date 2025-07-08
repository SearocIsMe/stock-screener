#!/usr/bin/env python3
"""
Test script to verify the error fixes for stock filtering
"""
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.filters.stock_filter import StockFilter
from src.indicators.technical import TechnicalIndicators
from src.data.database import SessionLocal

def create_test_data():
    """Create test data that might trigger the original errors"""
    # Create minimal data that could cause "out-of-bounds" errors
    dates = pd.date_range(start='2023-01-01', periods=5, freq='D')
    
    # Test case 1: Very limited data (could cause out-of-bounds)
    limited_data = pd.DataFrame({
        'Open': [100, 101, 102, 103, 104],
        'High': [105, 106, 107, 108, 109],
        'Low': [95, 96, 97, 98, 99],
        'Close': [102, 103, 104, 105, 106],
        'Volume': [1000, 1100, 1200, 1300, 1400],
        'Adj Close': [102, 103, 104, 105, 106]
    }, index=dates)
    
    # Test case 2: Data with None/NaN values (could cause arithmetic errors)
    nan_data = pd.DataFrame({
        'Open': [100, None, 102, 103, 104],
        'High': [105, 106, None, 108, 109],
        'Low': [95, 96, 97, None, 99],
        'Close': [102, 103, 104, 105, None],
        'Volume': [1000, None, 1200, 1300, 1400],
        'Adj Close': [102, 103, 104, 105, 106]
    }, index=dates)
    
    # Test case 3: Empty DataFrame
    empty_data = pd.DataFrame()
    
    return limited_data, nan_data, empty_data

def test_technical_indicators():
    """Test technical indicators with problematic data"""
    print("Testing Technical Indicators...")
    
    limited_data, nan_data, empty_data = create_test_data()
    
    # Test with limited data
    try:
        indicators_limited = TechnicalIndicators.calculate_all_indicators(limited_data, 'weekly')
        print(f"✅ Limited data test passed: {len(indicators_limited)} indicators calculated")
    except Exception as e:
        print(f"❌ Limited data test failed: {e}")
    
    # Test with NaN data
    try:
        indicators_nan = TechnicalIndicators.calculate_all_indicators(nan_data, 'weekly')
        print(f"✅ NaN data test passed: {len(indicators_nan)} indicators calculated")
    except Exception as e:
        print(f"❌ NaN data test failed: {e}")
    
    # Test with empty data
    try:
        indicators_empty = TechnicalIndicators.calculate_all_indicators(empty_data, 'weekly')
        print(f"✅ Empty data test passed: {len(indicators_empty)} indicators calculated")
    except Exception as e:
        print(f"❌ Empty data test failed: {e}")
    
    # Test specific methods that were causing errors
    if not limited_data.empty:
        try:
            # Test volume increase YoY (might fail with limited data)
            result = TechnicalIndicators.check_volume_increase_yoy(limited_data)
            print(f"✅ Volume YoY test passed: {result}")
        except Exception as e:
            print(f"❌ Volume YoY test failed: {e}")
        
        try:
            # Test volume breakout
            result = TechnicalIndicators.check_volume_breakout(limited_data)
            print(f"✅ Volume breakout test passed: {result}")
        except Exception as e:
            print(f"❌ Volume breakout test failed: {e}")

def test_stock_filter_methods():
    """Test stock filter methods with problematic data"""
    print("\nTesting Stock Filter Methods...")
    
    # Create a mock database session (we'll skip actual DB operations)
    try:
        db = SessionLocal()
        stock_filter = StockFilter(db)
        
        limited_data, nan_data, empty_data = create_test_data()
        
        # Test with limited indicators
        try:
            indicators_limited = TechnicalIndicators.calculate_all_indicators(limited_data, 'weekly')
            
            # Test weekly combination methods
            result1 = stock_filter._check_weekly_combination_1(indicators_limited, "TEST")
            print(f"✅ Weekly combination 1 test passed: {result1}")
            
            result2 = stock_filter._check_weekly_combination_2(indicators_limited, "TEST")
            print(f"✅ Weekly combination 2 test passed: {result2}")
            
            result3 = stock_filter._check_weekly_combination_3(indicators_limited, "TEST")
            print(f"✅ Weekly combination 3 test passed: {result3}")
            
        except Exception as e:
            print(f"❌ Weekly combination tests failed: {e}")
        
        # Test with empty indicators
        try:
            result1 = stock_filter._check_weekly_combination_1(empty_data, "TEST")
            print(f"✅ Empty data weekly combination 1 test passed: {result1}")
            
            result2 = stock_filter._check_weekly_combination_2(empty_data, "TEST")
            print(f"✅ Empty data weekly combination 2 test passed: {result2}")
            
        except Exception as e:
            print(f"❌ Empty data weekly combination tests failed: {e}")
        
        # Test extract latest indicators
        try:
            if not limited_data.empty:
                indicators = TechnicalIndicators.calculate_all_indicators(limited_data, 'weekly')
                latest = stock_filter._extract_latest_indicators(indicators, 'weekly')
                print(f"✅ Extract latest indicators test passed: {len(latest)} indicators extracted")
            
            # Test with empty indicators
            latest_empty = stock_filter._extract_latest_indicators(empty_data, 'weekly')
            print(f"✅ Extract latest indicators (empty) test passed: {len(latest_empty)} indicators extracted")
            
        except Exception as e:
            print(f"❌ Extract latest indicators test failed: {e}")
        
        db.close()
        
    except Exception as e:
        print(f"❌ Database connection failed, skipping stock filter tests: {e}")

def main():
    """Run all tests"""
    print("🧪 Testing Error Fixes for Stock Filter")
    print("=" * 50)
    
    test_technical_indicators()
    test_stock_filter_methods()
    
    print("\n" + "=" * 50)
    print("✅ All tests completed! Check the results above.")
    print("\nThe fixes should prevent:")
    print("1. 'single positional indexer is out-of-bounds' errors")
    print("2. 'unsupported operand type(s) for -: 'float' and 'NoneType'' errors")

if __name__ == "__main__":
    main()