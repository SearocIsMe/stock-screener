#!/usr/bin/env python3
"""
Example script demonstrating free alternatives to paid APIs
This script shows how to use the enhanced data acquisition with free data sources
"""
import sys
import os
import logging
from datetime import datetime, timedelta

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.logging_config import configure_logging
from src.data.free_data_sources import free_data_sources
from src.data.database import get_db_session
from src.data.acquisition import DataAcquisition

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)

def demonstrate_free_historical_data():
    """Demonstrate free historical data fetching"""
    print("\n" + "="*60)
    print("DEMONSTRATING FREE HISTORICAL DATA SOURCES")
    print("="*60)
    
    # Test symbols
    symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"]
    
    # Date range
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    for symbol in symbols:
        print(f"\n--- Testing {symbol} ---")
        
        # Method 1: yfinance
        print("1. Trying yfinance...")
        try:
            yf_data = free_data_sources.get_historical_data_yfinance(
                symbol, start_date, end_date, '1d'
            )
            if not yf_data.empty:
                print(f"   ✓ Success: Got {len(yf_data)} records from yfinance")
                print(f"   Latest close: ${yf_data.iloc[0]['close']:.2f}")
            else:
                print("   ✗ No data from yfinance")
        except Exception as e:
            print(f"   ✗ Error with yfinance: {e}")
        
        # Method 2: pandas-datareader
        print("2. Trying pandas-datareader...")
        try:
            pdr_data = free_data_sources.get_historical_data_pandas_datareader(
                symbol, start_date, end_date
            )
            if not pdr_data.empty:
                print(f"   ✓ Success: Got {len(pdr_data)} records from pandas-datareader")
                print(f"   Latest close: ${pdr_data.iloc[0]['close']:.2f}")
            else:
                print("   ✗ No data from pandas-datareader")
        except Exception as e:
            print(f"   ✗ Error with pandas-datareader: {e}")

def demonstrate_free_fundamentals():
    """Demonstrate free fundamental data fetching"""
    print("\n" + "="*60)
    print("DEMONSTRATING FREE FUNDAMENTAL DATA SOURCES")
    print("="*60)
    
    # Test symbols
    symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"]
    
    for symbol in symbols:
        print(f"\n--- Testing {symbol} Fundamentals ---")
        
        try:
            fundamentals = free_data_sources.get_stock_fundamentals_yahoo(symbol)
            
            print("Yahoo Finance Fundamentals:")
            for key, value in fundamentals.items():
                if value is not None:
                    if key in ['roe', 'dy', 'gm']:
                        print(f"   {key.upper()}: {value:.2f}%")
                    else:
                        print(f"   {key.upper()}: {value:.2f}")
                else:
                    print(f"   {key.upper()}: N/A")
                    
        except Exception as e:
            print(f"   ✗ Error getting fundamentals: {e}")

def demonstrate_free_profiles():
    """Demonstrate free stock profile fetching"""
    print("\n" + "="*60)
    print("DEMONSTRATING FREE STOCK PROFILE DATA")
    print("="*60)
    
    # Test symbols
    symbols = ["AAPL", "MSFT", "GOOGL"]
    
    for symbol in symbols:
        print(f"\n--- Testing {symbol} Profile ---")
        
        try:
            profile = free_data_sources.get_stock_profile_yahoo(symbol)
            
            if profile:
                print("Yahoo Finance Profile:")
                print(f"   Name: {profile.get('name', 'N/A')}")
                print(f"   Sector: {profile.get('sector', 'N/A')}")
                print(f"   Industry: {profile.get('industry', 'N/A')}")
                print(f"   Exchange: {profile.get('exchange', 'N/A')}")
                
                market_cap = profile.get('market_cap')
                if market_cap:
                    print(f"   Market Cap: ${market_cap:,.0f}")
                    
                price = profile.get('price')
                if price:
                    print(f"   Current Price: ${price:.2f}")
            else:
                print("   ✗ No profile data available")
                
        except Exception as e:
            print(f"   ✗ Error getting profile: {e}")

def demonstrate_enhanced_acquisition():
    """Demonstrate the enhanced data acquisition class"""
    print("\n" + "="*60)
    print("DEMONSTRATING ENHANCED DATA ACQUISITION")
    print("="*60)
    
    try:
        # Get database session
        db = next(get_db_session())
        
        # Create enhanced data acquisition instance
        data_acq = DataAcquisition(db)
        
        # Test symbols
        symbols = ["AAPL", "MSFT"]
        
        for symbol in symbols:
            print(f"\n--- Testing Enhanced Methods for {symbol} ---")
            
            # Test enhanced fundamentals
            print("1. Enhanced Fundamentals:")
            fundamentals = data_acq.get_fundamentals(symbol)
            for key, value in fundamentals.items():
                if value is not None:
                    if key in ['roe', 'dy', 'gm']:
                        print(f"   {key.upper()}: {value:.2f}%")
                    else:
                        print(f"   {key.upper()}: {value:.2f}")
                else:
                    print(f"   {key.upper()}: N/A")
            
            # Test enhanced profile
            print("2. Enhanced Profile:")
            profile = data_acq.get_stock_profile(symbol)
            if profile:
                print(f"   Name: {profile.get('name', 'N/A')}")
                print(f"   Sector: {profile.get('sector', 'N/A')}")
                print(f"   Industry: {profile.get('industry', 'N/A')}")
            else:
                print("   No profile data available")
            
            # Test enhanced historical data
            print("3. Enhanced Historical Data:")
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            
            hist_data = data_acq.get_historical_data(symbol, start_date, end_date, '1day')
            if not hist_data.empty:
                print(f"   ✓ Got {len(hist_data)} records")
                print(f"   Latest close: ${hist_data.iloc[0]['close']:.2f}")
            else:
                print("   ✗ No historical data")
        
        db.close()
        
    except Exception as e:
        print(f"Error in enhanced acquisition demo: {e}")

def demonstrate_rate_limit_handling():
    """Demonstrate rate limit handling"""
    print("\n" + "="*60)
    print("DEMONSTRATING RATE LIMIT HANDLING")
    print("="*60)
    
    try:
        # Get database session
        db = next(get_db_session())
        
        # Create data acquisition instance
        data_acq = DataAcquisition(db)
        
        # Simulate rate limit exceeded
        print("1. Simulating FMP rate limit exceeded...")
        data_acq.fmp_rate_limit_exceeded = True
        
        # Test that it falls back to free sources
        symbol = "AAPL"
        print(f"2. Testing fallback for {symbol}...")
        
        fundamentals = data_acq.get_fundamentals(symbol)
        if any(v is not None for v in fundamentals.values()):
            print("   ✓ Successfully got data using free alternatives")
            for key, value in fundamentals.items():
                if value is not None:
                    if key in ['roe', 'dy', 'gm']:
                        print(f"   {key.upper()}: {value:.2f}%")
                    else:
                        print(f"   {key.upper()}: {value:.2f}")
        else:
            print("   ✗ No data available from free sources")
        
        db.close()
        
    except Exception as e:
        print(f"Error in rate limit demo: {e}")

def main():
    """Main demonstration function"""
    print("FREE DATA SOURCES DEMONSTRATION")
    print("This script demonstrates free alternatives to paid APIs")
    print("for stock data acquisition to solve rate limit problems.")
    
    try:
        # Run demonstrations
        demonstrate_free_historical_data()
        demonstrate_free_fundamentals()
        demonstrate_free_profiles()
        demonstrate_enhanced_acquisition()
        demonstrate_rate_limit_handling()
        
        print("\n" + "="*60)
        print("SUMMARY OF FREE ALTERNATIVES")
        print("="*60)
        print("1. Historical Data:")
        print("   - yfinance: Completely free, very reliable")
        print("   - pandas-datareader: Multiple free sources (Stooq, Yahoo)")
        print("   - No API keys required!")
        print()
        print("2. Fundamental Data:")
        print("   - Yahoo Finance: Free P/E, P/B, ROE, Dividend Yield, Gross Margin")
        print("   - No API keys required!")
        print()
        print("3. Stock Profiles:")
        print("   - Yahoo Finance: Free company info, sector, industry")
        print("   - No API keys required!")
        print()
        print("4. Rate Limit Solutions:")
        print("   - Automatic fallback to free sources")
        print("   - Smart retry logic with backoff")
        print("   - No more API rate limit errors!")
        print()
        print("✓ All solutions are completely FREE and require no API keys!")
        
    except Exception as e:
        logger.error(f"Error in main demonstration: {e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()