#!/usr/bin/env python3
"""
Test script to verify yfinance fix
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.data.free_data_sources import FreeDataSources
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_yfinance_fix():
    """Test that yfinance works without the threads parameter error"""
    
    print("🧪 Testing yfinance fix...")
    
    # Initialize free data sources
    free_sources = FreeDataSources()
    
    # Test with a common stock symbol
    test_symbol = "AAPL"
    start_date = "2024-01-01"
    end_date = "2024-12-31"
    
    print(f"📊 Testing yfinance data fetch for {test_symbol}...")
    
    # Test yfinance
    yf_data = free_sources.get_historical_data_yfinance(
        ticker=test_symbol,
        start_date=start_date,
        end_date=end_date,
        interval="1day"
    )
    
    if not yf_data.empty:
        print(f"✅ yfinance SUCCESS: Got {len(yf_data)} records for {test_symbol}")
        print(f"   Date range: {yf_data.index[-1]} to {yf_data.index[0]}")
        print(f"   Columns: {list(yf_data.columns)}")
    else:
        print(f"⚠️  yfinance returned empty data for {test_symbol}")
    
    # Test pandas-datareader as fallback
    print(f"📊 Testing pandas-datareader fallback for {test_symbol}...")
    
    pdr_data = free_sources.get_historical_data_pandas_datareader(
        ticker=test_symbol,
        start_date=start_date,
        end_date=end_date
    )
    
    if not pdr_data.empty:
        print(f"✅ pandas-datareader SUCCESS: Got {len(pdr_data)} records for {test_symbol}")
        print(f"   Date range: {pdr_data.index[-1]} to {pdr_data.index[0]}")
        print(f"   Columns: {list(pdr_data.columns)}")
    else:
        print(f"⚠️  pandas-datareader returned empty data for {test_symbol}")
    
    # Test with the problematic symbol from logs
    print(f"\n📊 Testing with ECL (from error logs)...")
    
    ecl_data = free_sources.get_historical_data_yfinance(
        ticker="ECL",
        start_date=start_date,
        end_date=end_date,
        interval="1day"
    )
    
    if not ecl_data.empty:
        print(f"✅ yfinance SUCCESS for ECL: Got {len(ecl_data)} records")
    else:
        print(f"⚠️  yfinance failed for ECL, testing fallback...")
        
        ecl_fallback = free_sources.get_historical_data_pandas_datareader(
            ticker="ECL",
            start_date=start_date,
            end_date=end_date
        )
        
        if not ecl_fallback.empty:
            print(f"✅ pandas-datareader SUCCESS for ECL: Got {len(ecl_fallback)} records")
        else:
            print(f"❌ Both sources failed for ECL")

if __name__ == "__main__":
    test_yfinance_fix()