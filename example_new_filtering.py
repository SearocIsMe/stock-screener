#!/usr/bin/env python3
"""
Example script demonstrating the new weekly and monthly filtering criteria
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import our modules
from src.filters.stock_filter import StockFilter
from src.data.database import get_db_session
from src.indicators.technical import TechnicalIndicators

def demonstrate_new_filtering():
    """Demonstrate the new weekly and monthly filtering criteria"""
    print("=== Demonstrating New Weekly and Monthly Filtering Criteria ===\n")
    
    try:
        # Get database session
        db = next(get_db_session())
        
        # Initialize stock filter
        stock_filter = StockFilter(db)
        
        print("1. Testing with sample symbols...")
        
        # Test with a few sample symbols
        test_symbols = ['AAPL', 'MSFT', 'GOOGL']
        
        # Test weekly filtering
        print("\n--- Weekly Filtering Results ---")
        weekly_results = stock_filter.filter_stocks(
            symbols=test_symbols, 
            time_frames=['weekly']
        )
        
        if weekly_results.get('weekly'):
            print(f"Found {len(weekly_results['weekly'])} stocks passing weekly criteria:")
            for stock in weekly_results['weekly']:
                print(f"  - {stock['symbol']}: {stock['data_points']} data points")
                print(f"    Latest indicators: RSI={stock['indicators'].get('rsi', 'N/A'):.2f}, "
                      f"MACD={stock['indicators'].get('macd', 'N/A'):.4f}")
        else:
            print("No stocks passed weekly filtering criteria")
        
        # Test monthly filtering
        print("\n--- Monthly Filtering Results ---")
        monthly_results = stock_filter.filter_stocks(
            symbols=test_symbols, 
            time_frames=['monthly']
        )
        
        if monthly_results.get('monthly'):
            print(f"Found {len(monthly_results['monthly'])} stocks passing monthly criteria:")
            for stock in monthly_results['monthly']:
                print(f"  - {stock['symbol']}: {stock['data_points']} data points")
                print(f"    Latest indicators: RSI={stock['indicators'].get('rsi', 'N/A'):.2f}, "
                      f"Close=${stock['indicators'].get('close_price', 'N/A'):.2f}")
        else:
            print("No stocks passed monthly filtering criteria")
        
        # Test both timeframes together
        print("\n--- Combined Weekly and Monthly Filtering ---")
        combined_results = stock_filter.filter_stocks(
            symbols=test_symbols, 
            time_frames=['weekly', 'monthly']
        )
        
        print("Summary of results:")
        for timeframe, results in combined_results.items():
            print(f"  {timeframe.capitalize()}: {len(results)} stocks passed")
        
        db.close()
        
    except Exception as e:
        print(f"Error during filtering demonstration: {e}")
        import traceback
        traceback.print_exc()

def explain_filtering_criteria():
    """Explain the new filtering criteria"""
    print("\n=== New Filtering Criteria Explanation ===\n")
    
    print("WEEKLY FILTERING (Any of 3 combinations):")
    print("1. Double MA + MACD Golden Cross:")
    print("   - MA10 > MA20 (bullish trend)")
    print("   - MACD just formed golden cross")
    print("   - Volume increased year-over-year")
    print()
    
    print("2. Trend + Volume Breakout:")
    print("   - MA10 > MA20 (bullish trend)")
    print("   - Weekly volume breakout")
    print("   - MACD approaching golden cross")
    print("   - DMI positive turn (DI+ > DI-)")
    print()
    
    print("3. Bollinger + OBV:")
    print("   - Bollinger band breakout (middle or upper)")
    print("   - OBV in uptrend")
    print()
    
    print("MONTHLY FILTERING (Any of 3 conditions):")
    print("1. Bullish Candles or Trend:")
    print("   - 3 consecutive green monthly candles OR")
    print("   - Price above 20-month MA")
    print()
    
    print("2. Bollinger Squeeze Expansion:")
    print("   - Bollinger bands squeeze then expand upward")
    print()
    
    print("3. RSI Momentum:")
    print("   - RSI moving from 50 towards 60")
    print()

def show_configuration():
    """Show the configuration for the new filtering criteria"""
    print("\n=== Configuration Details ===\n")
    
    try:
        import yaml
        config_path = os.path.join(os.path.dirname(__file__), "config", "config.yaml")
        with open(config_path, "r") as config_file:
            config = yaml.safe_load(config_file)
        
        print("Technical Indicators Configuration:")
        print(f"- MA periods: {config['indicators']['ma']}")
        print(f"- Bollinger Bands: {config['indicators']['bollinger']}")
        print(f"- DMI periods: {config['indicators']['dmi']}")
        
        if 'filtering_criteria' in config:
            print(f"\nFiltering Criteria:")
            print(f"- Weekly combinations: {list(config['filtering_criteria']['weekly'].keys())}")
            print(f"- Monthly conditions: {list(config['filtering_criteria']['monthly'].keys())}")
        
    except Exception as e:
        print(f"Error loading configuration: {e}")

if __name__ == "__main__":
    # Explain the criteria first
    explain_filtering_criteria()
    
    # Show configuration
    show_configuration()
    
    # Demonstrate the filtering
    demonstrate_new_filtering()
    
    print("\n=== Demo Complete ===")
    print("The new weekly and monthly filtering criteria have been successfully implemented!")
    print("You can now use these enhanced filters in your stock screening process.")