# Stock Filter Error Fixes Summary

## Issues Fixed

### 1. "single positional indexer is out-of-bounds" Errors

**Location**: Lines 740, 778 in [`src/filters/stock_filter.py`](src/filters/stock_filter.py)

**Root Cause**: The methods `_check_weekly_combination_1()` and `_check_weekly_combination_2()` were trying to access `indicators.iloc[-1]` without checking if the DataFrame was empty or had sufficient data.

**Fix Applied**:
- Added empty DataFrame checks before accessing `indicators.iloc[-1]`
- Added similar checks to `_check_weekly_combination_3()` and monthly condition methods
- Now returns `False` gracefully when insufficient data is available

**Code Changes**:
```python
# Before (causing error)
latest = indicators.iloc[-1]

# After (safe)
if indicators.empty or len(indicators) == 0:
    logger.debug(f"{symbol}: No indicators data available for weekly combination 1")
    return False

latest = indicators.iloc[-1]
```

### 2. "unsupported operand type(s) for -: 'float' and 'NoneType'" Error

**Location**: Line 183 in [`src/filters/stock_filter.py`](src/filters/stock_filter.py) and various methods in [`src/indicators/technical.py`](src/indicators/technical.py)

**Root Cause**: Arithmetic operations were being performed on `None` values returned from data calculations, particularly in volume-related calculations.

**Fix Applied**:
- Added comprehensive `None` and `NaN` value checks before arithmetic operations
- Enhanced error handling in [`TechnicalIndicators.check_volume_increase_yoy()`](src/indicators/technical.py:438)
- Enhanced error handling in [`TechnicalIndicators.check_volume_breakout()`](src/indicators/technical.py:473)
- Added safety checks in [`_extract_latest_indicators()`](src/filters/stock_filter.py:925)

**Code Changes**:
```python
# Before (causing error)
if pd.isna(recent_volume) or pd.isna(year_ago_volume) or year_ago_volume == 0:
    return False

# After (safe)
if (recent_volume is None or year_ago_volume is None or 
    pd.isna(recent_volume) or pd.isna(year_ago_volume) or 
    year_ago_volume == 0):
    return False
```

### 3. Additional Safety Improvements

**Enhanced Data Validation**:
- Added checks for empty indicators DataFrame in main filtering loop
- Added validation for latest indicators extraction
- Improved error handling with try-catch blocks and proper logging

**Methods Enhanced**:
- [`_check_weekly_combination_1()`](src/filters/stock_filter.py:710)
- [`_check_weekly_combination_2()`](src/filters/stock_filter.py:743)
- [`_check_weekly_combination_3()`](src/filters/stock_filter.py:801)
- [`_check_monthly_condition_1()`](src/filters/stock_filter.py:863)
- [`_check_monthly_condition_2()`](src/filters/stock_filter.py:897)
- [`_check_monthly_condition_3()`](src/filters/stock_filter.py:906)
- [`_extract_latest_indicators()`](src/filters/stock_filter.py:925)
- [`TechnicalIndicators.check_volume_increase_yoy()`](src/indicators/technical.py:438)
- [`TechnicalIndicators.check_volume_breakout()`](src/indicators/technical.py:473)

## Test Results

The fixes were validated using [`test_error_fixes.py`](test_error_fixes.py) which tests:

1. **Technical Indicators with problematic data**:
   - Limited data (5 data points)
   - Data with NaN/None values
   - Empty DataFrames

2. **Stock Filter Methods**:
   - Weekly combination checks with insufficient data
   - Monthly condition checks with empty data
   - Latest indicators extraction with various data conditions

**All tests passed successfully** without throwing the original errors.

## Error Prevention

The fixes now prevent:

1. **IndexError**: `single positional indexer is out-of-bounds`
   - Occurs when trying to access `DataFrame.iloc[-1]` on empty DataFrames
   - Now handled with proper empty checks

2. **TypeError**: `unsupported operand type(s) for -: 'float' and 'NoneType'`
   - Occurs when performing arithmetic on None values
   - Now handled with comprehensive None/NaN checks

3. **General robustness improvements**:
   - Better error logging for debugging
   - Graceful degradation when data is insufficient
   - Consistent return values (False) when conditions cannot be evaluated

## Impact

These fixes ensure that the stock filtering system:
- Continues to operate even with problematic or insufficient data
- Provides clear logging for debugging purposes
- Maintains data integrity and prevents crashes
- Handles edge cases gracefully

The system will now skip stocks with insufficient data rather than crashing, allowing the filtering process to continue for other stocks in the list.