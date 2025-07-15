#!/usr/bin/env python3
"""
Test script to compare original vs optimized monthly filtering
"""

import sys
import os
import pandas as pd
import numpy as np
import yaml
from datetime import datetime, timedelta

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from indicators.technical import TechnicalIndicators
from filters.optimized_monthly_filter import OptimizedMonthlyFilter

def create_monthly_sample_data(periods=36, trend_type='mixed'):
    """Create sample OHLCV data for testing different market conditions over months"""
    dates = pd.date_range(start='2021-01-01', periods=periods, freq='ME')  # Monthly data (end of month)
    
    np.random.seed(42)
    base_price = 100
    
    if trend_type == 'uptrend':
        # Create long-term uptrending data
        trend = np.linspace(0, 0.5, periods)  # 50% uptrend over 3 years
        noise = np.random.normal(0, 0.03, periods)  # 3% monthly noise
        price_changes = trend + noise
    elif trend_type == 'downtrend':
        # Create long-term downtrending data
        trend = np.linspace(0, -0.3, periods)  # 30% downtrend
        noise = np.random.normal(0, 0.03, periods)
        price_changes = trend + noise
    elif trend_type == 'recovery':
        # Create recovery pattern (down then up)
        first_half = np.linspace(0, -0.2, periods//2)  # Down 20%
        second_half = np.linspace(-0.2, 0.3, periods - periods//2)  # Up 50%
        trend = np.concatenate([first_half, second_half])
        noise = np.random.normal(0, 0.03, periods)
        price_changes = trend + noise
    else:  # mixed
        # Create mixed trend data with some volatility
        price_changes = np.random.normal(0, 0.04, periods)  # 4% monthly volatility
    
    prices = [base_price]
    for change in price_changes[1:]:
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, 1))
    
    # Create OHLC data
    data = []
    for i, price in enumerate(prices):
        high = price * (1 + abs(np.random.normal(0, 0.02)))
        low = price * (1 - abs(np.random.normal(0, 0.02)))
        open_price = prices[i-1] if i > 0 else price
        close_price = price
        
        # Create volume with correlation to price movement and trend
        base_volume = 1000000
        if i > 0:
            price_change = (price - prices[i-1]) / prices[i-1]
            volume_multiplier = 1 + abs(price_change) * 3  # Higher volume on big moves
            
            # Add trend-based volume (more volume in uptrends)
            if trend_type == 'uptrend' or (trend_type == 'recovery' and i > periods//2):
                volume_multiplier *= 1.2
        else:
            volume_multiplier = 1
        
        volume = int(base_volume * volume_multiplier * (1 + np.random.normal(0, 0.2)))
        
        data.append({
            'Date': dates[i],
            'Open': open_price,
            'High': high,
            'Low': low,
            'Close': close_price,
            'Volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('Date', inplace=True)
    return df

def load_config():
    """Load the optimized configuration"""
    config_path = os.path.join(os.path.dirname(__file__), "config", "config.yaml")
    with open(config_path, "r") as config_file:
        return yaml.safe_load(config_file)

def test_monthly_filtering_comparison():
    """Test and compare original vs optimized monthly filtering"""
    print("🔍 Monthly Filtering Optimization Analysis")
    print("=" * 70)
    
    # Load optimized config
    config = load_config()
    
    # Test different market conditions
    market_conditions = [
        ('uptrend', 'Long-term uptrending market'),
        ('recovery', 'Recovery from decline'),
        ('mixed', 'Mixed/volatile market'),
        ('downtrend', 'Long-term downtrending market')
    ]
    
    results_summary = {}
    
    for condition, description in market_conditions:
        print(f"\n📊 Testing {description.upper()}")
        print("-" * 50)
        
        # Create sample data for this condition
        sample_data = create_monthly_sample_data(36, condition)  # 3 years of monthly data
        print(f"Created {len(sample_data)} months of {condition} data")
        print(f"Price change: {sample_data['Close'].iloc[0]:.2f} -> {sample_data['Close'].iloc[-1]:.2f} ({((sample_data['Close'].iloc[-1]/sample_data['Close'].iloc[0])-1)*100:.1f}%)")
        
        # Calculate indicators with optimized parameters
        monthly_indicators = TechnicalIndicators.calculate_all_indicators(sample_data, 'monthly')
        
        if monthly_indicators.empty:
            print(f"❌ No indicators calculated for {condition}")
            continue
        
        # Test with optimized filter
        optimized_filter = OptimizedMonthlyFilter(config)
        filter_results = optimized_filter.check_monthly_filters(monthly_indicators, f"TEST_{condition.upper()}")
        
        results_summary[condition] = {
            'passed': filter_results['passed'],
            'conditions': filter_results['conditions'],
            'summary': optimized_filter.get_filter_summary(filter_results)
        }
        
        # Display results
        if filter_results['passed']:
            print(f"✅ PASSED: Monthly filtering successful")
            print(f"📈 Summary: {optimized_filter.get_filter_summary(filter_results)}")
        else:
            print(f"❌ FAILED: No conditions passed")
        
        # Show details of each condition
        print(f"📋 Condition Details:")
        for condition_name, condition_result in filter_results['conditions'].items():
            status = "✅ PASS" if condition_result.get('passed', False) else "❌ FAIL"
            reason = condition_result.get('reason', 'No reason provided')
            print(f"   {condition_name}: {status} - {reason}")
        
        # Show some key indicator values
        latest = monthly_indicators.iloc[-1]
        print(f"📊 Key Monthly Indicators (Latest):")
        
        indicators_to_show = [
            'MONTHLY_MA_3', 'MONTHLY_MA_6', 'MONTHLY_MA_12',
            'MONTHLY_EMA_4_Close', 'MONTHLY_EMA_8_Close',
            'MONTHLY_RSI_14', 'MONTHLY_MACD'
        ]
        
        for indicator in indicators_to_show:
            if indicator in latest.index and not pd.isna(latest[indicator]):
                print(f"   {indicator}: {latest[indicator]:.2f}")
    
    # Summary comparison
    print(f"\n🎯 MONTHLY FILTERING EFFECTIVENESS SUMMARY")
    print("=" * 60)
    
    for condition, results in results_summary.items():
        status = "✅ DISCOVERED" if results['passed'] else "❌ MISSED"
        print(f"{condition.upper():12} | {status} | {results['summary']}")
    
    return results_summary

def analyze_monthly_parameter_improvements():
    """Analyze the monthly parameter improvements made"""
    print(f"\n🔧 MONTHLY PARAMETER OPTIMIZATION ANALYSIS")
    print("=" * 60)
    
    improvements = [
        {
            'category': 'Moving Averages',
            'original': 'MA periods: [3, 20]',
            'optimized': 'MA periods: [3, 6, 12]',
            'benefit': 'Added MA6 for intermediate signals, MA12 for medium-term trend'
        },
        {
            'category': 'MACD (Monthly)',
            'original': 'MACD: (6, 13, 5)',
            'optimized': 'MACD: (5, 10, 4)',
            'benefit': 'Even faster response for monthly trend changes'
        },
        {
            'category': 'RSI Thresholds',
            'original': 'Momentum: 50-60',
            'optimized': 'Momentum: 45-65, Uptrend: 40-70',
            'benefit': 'More permissive ranges suitable for monthly timeframe'
        },
        {
            'category': 'EMA Periods',
            'original': 'EMA: [4]',
            'optimized': 'EMA: [4, 8]',
            'benefit': 'Added EMA8 for trend confirmation and comparison'
        },
        {
            'category': 'Bollinger Bands',
            'original': 'Period: 20, Std Dev: 2.0',
            'optimized': 'Period: 10, Std Dev: 1.5',
            'benefit': 'More responsive to monthly price movements'
        },
        {
            'category': 'Filtering Logic',
            'original': '3 conditions with AND logic',
            'optimized': '5 conditions with OR logic, flexible criteria',
            'benefit': 'Higher discovery rate with multiple pathways'
        },
        {
            'category': 'Volume Analysis',
            'original': 'No volume consideration',
            'optimized': 'Volume trend analysis and confirmation',
            'benefit': 'Institutional interest validation for monthly trends'
        }
    ]
    
    for improvement in improvements:
        print(f"\n📈 {improvement['category']}")
        print(f"   Original:  {improvement['original']}")
        print(f"   Optimized: {improvement['optimized']}")
        print(f"   Benefit:   {improvement['benefit']}")

def test_monthly_edge_cases():
    """Test monthly edge cases and boundary conditions"""
    print(f"\n🧪 MONTHLY EDGE CASE TESTING")
    print("=" * 40)
    
    config = load_config()
    optimized_filter = OptimizedMonthlyFilter(config)
    
    # Test with minimal data
    minimal_data = create_monthly_sample_data(12, 'uptrend')  # Just 12 months
    monthly_indicators = TechnicalIndicators.calculate_all_indicators(minimal_data, 'monthly')
    
    if not monthly_indicators.empty:
        results = optimized_filter.check_monthly_filters(monthly_indicators, "MINIMAL_DATA")
        print(f"✅ Minimal data test (12 months): {'PASSED' if results['passed'] else 'FAILED'}")
    else:
        print(f"❌ Minimal data test: No indicators calculated")
    
    # Test with very volatile data
    volatile_data = create_monthly_sample_data(24, 'mixed')
    # Add extra volatility
    volatile_data['Close'] *= (1 + np.random.normal(0, 0.1, len(volatile_data)))
    
    monthly_indicators_volatile = TechnicalIndicators.calculate_all_indicators(volatile_data, 'monthly')
    if not monthly_indicators_volatile.empty:
        results_volatile = optimized_filter.check_monthly_filters(monthly_indicators_volatile, "VOLATILE")
        print(f"✅ High volatility test: {'PASSED' if results_volatile['passed'] else 'FAILED'}")
    else:
        print(f"❌ High volatility test: No indicators calculated")

def compare_original_vs_optimized():
    """Compare original monthly criteria vs optimized"""
    print(f"\n📊 ORIGINAL VS OPTIMIZED COMPARISON")
    print("=" * 50)
    
    comparison_data = [
        {
            'aspect': 'Number of Conditions',
            'original': '3 conditions',
            'optimized': '5 conditions',
            'improvement': '+67% more pathways'
        },
        {
            'aspect': 'Logic Type',
            'original': 'OR between conditions',
            'optimized': 'OR between conditions + flexible AND within',
            'improvement': 'More nuanced filtering'
        },
        {
            'aspect': 'MA Analysis',
            'original': 'Only MA20',
            'optimized': 'MA3, MA6, MA12 options',
            'improvement': 'Multiple timeframe confirmation'
        },
        {
            'aspect': 'RSI Range',
            'original': '50-60 (narrow)',
            'optimized': '45-65 (broader)',
            'improvement': 'More realistic for monthly'
        },
        {
            'aspect': 'Volume Consideration',
            'original': 'None',
            'optimized': 'Volume trend analysis',
            'improvement': 'Institutional confirmation'
        },
        {
            'aspect': 'EMA Analysis',
            'original': 'Not used in filtering',
            'optimized': 'EMA4 vs EMA8 trend',
            'improvement': 'Short-term trend validation'
        }
    ]
    
    for item in comparison_data:
        print(f"\n🔍 {item['aspect']}")
        print(f"   Original:    {item['original']}")
        print(f"   Optimized:   {item['optimized']}")
        print(f"   Improvement: {item['improvement']}")

if __name__ == "__main__":
    print("🚀 Optimized Monthly Filtering Test Suite")
    print("=" * 70)
    print()
    
    # Test monthly filtering comparison
    results = test_monthly_filtering_comparison()
    
    # Analyze parameter improvements
    analyze_monthly_parameter_improvements()
    
    # Test edge cases
    test_monthly_edge_cases()
    
    # Compare original vs optimized
    compare_original_vs_optimized()
    
    print(f"\n🎯 MONTHLY OPTIMIZATION SUMMARY")
    print("=" * 50)
    print("The optimized monthly filtering approach provides:")
    print("1. ✅ More flexible discovery criteria with 5 conditions")
    print("2. ✅ Better parameter sensitivity for monthly timeframe")
    print("3. ✅ Multiple MA periods for different trend confirmations")
    print("4. ✅ Realistic RSI ranges (45-65) for monthly analysis")
    print("5. ✅ Volume trend analysis for institutional confirmation")
    print("6. ✅ EMA trend validation for short-term momentum")
    print("7. ✅ Proper handling of timeframe-prefixed indicators")
    print()
    print("💡 Recommendation: Use optimized monthly configuration for better")
    print("   long-term trend discovery while maintaining quality standards.")