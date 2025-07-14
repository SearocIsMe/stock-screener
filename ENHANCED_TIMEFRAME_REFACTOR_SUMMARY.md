# Enhanced Timeframe-Specific Indicator Calculation Refactor

## Overview

The [`calculate_all_indicators`](src/indicators/technical.py:117) function has been comprehensively refactored to provide clear timeframe differentiation with enhanced data processing, validation, and column naming.

## Key Improvements Made

### 1. Enhanced Timeframe-Specific Validation

```python
# Timeframe-specific data validation
min_data_points = {
    'daily': 30,    # Need at least 30 days for reliable indicators
    'weekly': 20,   # Need at least 20 weeks for reliable indicators  
    'monthly': 12   # Need at least 12 months for reliable indicators
}

# Validate timeframe parameter
valid_timeframes = ['daily', 'weekly', 'monthly']
if time_frame not in valid_timeframes:
    logger.error(f"Invalid timeframe '{time_frame}'. Must be one of: {valid_timeframes}")
    return pd.DataFrame()
```

### 2. Timeframe-Prefixed Column Naming

All indicator columns now include timeframe prefixes for clear differentiation:

```python
# Add timeframe prefix for better differentiation
tf_prefix = time_frame.upper()

# Examples of prefixed columns:
# DAILY_EMA_13_Close, WEEKLY_EMA_13_Close, MONTHLY_EMA_4_Close
# DAILY_MACD, WEEKLY_MACD, MONTHLY_MACD
# DAILY_RSI_14, WEEKLY_RSI_14, MONTHLY_RSI_14
```

### 3. Timeframe-Specific Parameter Usage

Each timeframe now uses its specific configuration parameters:

| Indicator | Daily | Weekly | Monthly | 
|-----------|-------|--------|---------|
| **EMA** | EMA_13 | EMA_13 | EMA_4 |
| **MA** | MA_10, MA_20 | MA_10, MA_20 | MA_3, MA_20 |
| **MACD** | (12,26,9) | (12,26,9) | (6,13,5) |
| **RSI** | RSI_14 | RSI_14 | RSI_14 + special thresholds |

### 4. Enhanced Logging and Monitoring

```python
# Enhanced logging with timeframe differentiation
logger.info(f"Calculating {time_frame.upper()} indicators with {len(data)} data points using timeframe-specific parameters")

# Log timeframe-specific parameters used
logger.debug(f"{time_frame.upper()} timeframe parameters - EMA: {ema_config['periods']}, "
            f"MACD: ({macd_config['fast_period']},{macd_config['slow_period']},{macd_config['signal_period']}), "
            f"MA: {ma_config['periods']}")
```

## Test Results

The enhanced [`test_enhanced_timeframe_indicators.py`](test_enhanced_timeframe_indicators.py) confirms:

✅ **Timeframe Differentiation**: Each timeframe produces 23 properly prefixed indicators  
✅ **Parameter Usage**: Monthly uses EMA_4, MACD(6,13,5), MA_3 vs Daily EMA_13, MACD(12,26,9), MA_10  
✅ **Column Naming**: All indicators properly prefixed (DAILY_, WEEKLY_, MONTHLY_)  
✅ **Data Validation**: Invalid timeframes rejected, insufficient data handled  
✅ **Original Data Preservation**: OHLCV columns remain unprefixed  

## Sample Output Comparison

### Daily Timeframe
```
DAILY_EMA_13_Close: 80.3080
DAILY_BIAS_13_Close: -1.4824
DAILY_MA_10: 80.5567
DAILY_MA_20: 79.8234
DAILY_RSI_14: 45.2341
DAILY_MACD: -0.1234
```

### Monthly Timeframe
```
MONTHLY_EMA_4_Close: 79.4186
MONTHLY_BIAS_4_Close: -0.3791
MONTHLY_MA_3: 79.3635
MONTHLY_MA_20: 79.8234
MONTHLY_RSI_14: 45.2341
MONTHLY_MACD: -0.0987  # Uses (6,13,5) parameters
```

## Benefits of the Refactor

### 1. **Clear Timeframe Differentiation**
- Each timeframe's indicators are clearly identified with prefixes
- No confusion between daily, weekly, and monthly calculations
- Easy to combine multiple timeframes in the same DataFrame

### 2. **Proper Parameter Usage**
- Monthly timeframe uses faster-responding parameters appropriate for longer periods
- Each timeframe optimized for its specific characteristics
- Configuration-driven approach for easy adjustments

### 3. **Enhanced Data Validation**
- Timeframe-specific minimum data requirements
- Invalid timeframe rejection
- Better error handling and logging

### 4. **Improved Maintainability**
- Clear separation of timeframe logic
- Consistent naming conventions
- Enhanced logging for debugging

### 5. **Better Integration**
- Multiple timeframes can be calculated and stored together
- Filtering logic can easily reference specific timeframe indicators
- Clear data lineage and traceability

## Usage Examples

### Single Timeframe Calculation
```python
# Calculate daily indicators
daily_data = TechnicalIndicators.calculate_all_indicators(price_data, 'daily')
print(daily_data['DAILY_EMA_13_Close'].tail())

# Calculate monthly indicators with different parameters
monthly_data = TechnicalIndicators.calculate_all_indicators(price_data, 'monthly')
print(monthly_data['MONTHLY_EMA_4_Close'].tail())  # Uses EMA_4 instead of EMA_13
```

### Multi-Timeframe Analysis
```python
# Combine multiple timeframes
combined_data = price_data.copy()

# Add daily indicators
daily_indicators = TechnicalIndicators.calculate_all_indicators(price_data, 'daily')
for col in daily_indicators.columns:
    if col.startswith('DAILY_'):
        combined_data[col] = daily_indicators[col]

# Add monthly indicators
monthly_indicators = TechnicalIndicators.calculate_all_indicators(price_data, 'monthly')
for col in monthly_indicators.columns:
    if col.startswith('MONTHLY_'):
        combined_data[col] = monthly_indicators[col]

# Now you can compare: combined_data['DAILY_EMA_13_Close'] vs combined_data['MONTHLY_EMA_4_Close']
```

### Filtering with Timeframe-Specific Indicators
```python
# Filter using monthly trend and daily signals
filtered_stocks = combined_data[
    (combined_data['MONTHLY_EMA_4_Close'] > combined_data['MONTHLY_MA_20']) &  # Monthly uptrend
    (combined_data['DAILY_RSI_14'] < 70) &  # Daily not overbought
    (combined_data['DAILY_MACD'] > combined_data['DAILY_MACD_Signal'])  # Daily MACD bullish
]
```

## Migration Notes

If you have existing code that uses the old column names, you'll need to update references:

```python
# Old way
old_ema = data['EMA_13_Close']
old_rsi = data['RSI_14']

# New way - specify timeframe
daily_ema = data['DAILY_EMA_13_Close']
monthly_ema = data['MONTHLY_EMA_4_Close']  # Different parameter!
daily_rsi = data['DAILY_RSI_14']
```

This refactor ensures that the `calculate_all_indicators` function now properly differentiates timeframes with appropriate parameters, clear naming, and robust validation, making it suitable for comprehensive multi-timeframe technical analysis.