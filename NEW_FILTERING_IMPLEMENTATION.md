# New Weekly and Monthly Filtering Criteria Implementation

## Overview

This document describes the implementation of enhanced weekly and monthly filtering criteria for the stock screener, as requested. The new filtering logic provides more sophisticated and targeted screening for different timeframes.

## Changes Made

### 1. Configuration Updates (`config/config.yaml`)

Added new configuration sections:

- **Moving Averages (MA)**: Added MA10 and MA20 for trend analysis
- **Bollinger Bands**: Configuration for squeeze and breakout detection
- **DMI (Directional Movement Index)**: For trend direction analysis
- **Filtering Criteria**: Detailed configuration for weekly and monthly combinations/conditions

### 2. Enhanced Technical Indicators (`src/indicators/technical.py`)

Added comprehensive technical indicators:

- **Simple Moving Averages (MA10, MA20)**
- **Bollinger Bands** with position calculation
- **On-Balance Volume (OBV)**
- **DMI and ADX** for trend analysis
- **Additional indicators**: ATR, Stochastic, Williams %R

Added specialized helper methods:
- `check_macd_golden_cross()` - Detects recent MACD golden cross
- `check_macd_near_golden_cross()` - Detects approaching golden cross
- `check_three_consecutive_green_candles()` - Monthly bullish pattern
- `check_bollinger_squeeze_expansion()` - Bollinger squeeze breakout
- `check_rsi_momentum_50_to_60()` - RSI momentum analysis
- `check_volume_increase_yoy()` - Year-over-year volume comparison
- `check_volume_breakout()` - Volume breakout detection
- `check_dmi_positive_turn()` - DMI trend reversal
- `check_bollinger_breakout()` - Bollinger band breakouts
- `check_obv_uptrend()` - OBV trend analysis

### 3. Enhanced Stock Filter (`src/filters/stock_filter.py`)

Modified the `_meets_criteria()` method to route weekly and monthly timeframes to specialized checking methods:

#### Weekly Filtering (Any of 3 combinations):

**Combination 1: Double MA + MACD Golden Cross**
- MA10 > MA20 (bullish alignment)
- MACD just formed golden cross
- Volume increased year-over-year

**Combination 2: Trend + Volume Breakout**
- MA10 > MA20 (bullish alignment)
- Weekly volume breakout
- MACD approaching golden cross
- DMI positive turn (DI+ > DI-)

**Combination 3: Bollinger + OBV**
- Bollinger band breakout (middle or upper)
- OBV in uptrend

#### Monthly Filtering (Any of 3 conditions):

**Condition 1: Bullish Pattern or Trend**
- 3 consecutive green monthly candles OR
- Price above 20-month MA

**Condition 2: Bollinger Squeeze Expansion**
- Bollinger bands squeeze then expand upward

**Condition 3: RSI Momentum**
- RSI moving from 50 towards 60

## Implementation Details

### Weekly Criteria Logic

```python
def _check_weekly_criteria(self, indicators, symbol):
    # Check any of the 3 combinations
    combination_1 = self._check_weekly_combination_1(indicators, symbol)
    combination_2 = self._check_weekly_combination_2(indicators, symbol)
    combination_3 = self._check_weekly_combination_3(indicators, symbol)
    
    return combination_1 or combination_2 or combination_3
```

### Monthly Criteria Logic

```python
def _check_monthly_criteria(self, indicators, symbol):
    # Check any of the 3 conditions
    condition_1 = self._check_monthly_condition_1(indicators, symbol)
    condition_2 = self._check_monthly_condition_2(indicators, symbol)
    condition_3 = self._check_monthly_condition_3(indicators, symbol)
    
    return condition_1 or condition_2 or condition_3
```

## Usage Examples

### Basic Usage

```python
from src.filters.stock_filter import StockFilter

# Initialize filter
stock_filter = StockFilter(db_session)

# Filter with new criteria
results = stock_filter.filter_stocks(
    symbols=['AAPL', 'MSFT', 'GOOGL'],
    time_frames=['weekly', 'monthly']
)

# Access results
weekly_stocks = results['weekly']
monthly_stocks = results['monthly']
```

### Custom Configuration

The filtering criteria can be customized by modifying the `config/config.yaml` file:

```yaml
filtering_criteria:
  weekly:
    combination_1:
      ma10_above_ma20: true
      macd_golden_cross: true
      volume_increase: true
  monthly:
    condition_1:
      three_green_candles: true
      above_ma20: true
```

## Testing

Two test scripts have been created:

1. **`test_new_filtering.py`** - Tests technical indicator calculations
2. **`example_new_filtering.py`** - Demonstrates the complete filtering workflow

Run tests:
```bash
python test_new_filtering.py
python example_new_filtering.py
```

## Benefits

1. **More Sophisticated Screening**: Multiple criteria combinations provide better signal quality
2. **Timeframe-Specific Logic**: Different strategies for weekly vs monthly analysis
3. **Flexible Configuration**: Easy to modify criteria through config files
4. **Comprehensive Indicators**: Full suite of technical indicators available
5. **Robust Implementation**: Error handling and logging throughout

## Technical Indicators Added

| Indicator | Purpose | Timeframes |
|-----------|---------|------------|
| MA10/MA20 | Trend direction | All |
| Bollinger Bands | Volatility and breakouts | All |
| OBV | Volume trend | All |
| DMI/ADX | Trend strength | All |
| Enhanced MACD | Momentum signals | All |
| RSI Momentum | Overbought/oversold with momentum | All |

## Configuration Structure

```yaml
indicators:
  ma:
    weekly:
      periods: [10, 20]
  bollinger:
    weekly:
      period: 20
      std_dev: 2
  dmi:
    weekly:
      period: 14

filtering_criteria:
  weekly:
    combination_1: {...}
    combination_2: {...}
    combination_3: {...}
  monthly:
    condition_1: {...}
    condition_2: {...}
    condition_3: {...}
```

## Future Enhancements

1. **Backtesting**: Add historical performance analysis
2. **Machine Learning**: Integrate ML models for pattern recognition
3. **Real-time Alerts**: Add notification system for criteria matches
4. **Custom Combinations**: Allow users to create custom filtering combinations
5. **Performance Metrics**: Add success rate tracking for each combination

## Conclusion

The new weekly and monthly filtering criteria provide a sophisticated, multi-layered approach to stock screening. The implementation is flexible, well-tested, and ready for production use. The modular design allows for easy extension and customization of filtering logic.