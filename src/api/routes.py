"""
API routes for the stock screener application
"""
import logging, sys
import os
from src.utils.logging_config import configure_logging
import pandas as pd
from typing import List, Optional, Dict, Any, Union, Tuple
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from src.data.database import get_db
from src.data.acquisition import DataAcquisition
from src.filters.stock_filter import StockFilter

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Request and response models
class TimeRange(BaseModel):
    """Time range model"""
    start: Optional[str] = None
    end: Optional[str] = None

class FetchStockHistoryRequest(BaseModel):
    """Fetch stock history request model"""
    symbols: List[str] = Field(..., description="List of stock symbols or 'all' for all stocks")
    timeRange: Optional[TimeRange] = Field(None, description="Time range for historical data")

class TriggerFetchFilteringRequest(BaseModel):
    """Trigger fetch and filtering request model"""
    symbols: List[str] = Field(..., description="List of stock symbols or 'all' for all stocks")
    timeFrame: List[str] = Field(..., description="List of time frames (daily, weekly, monthly)")
    financialFilters: Optional[Dict[str, float]] = Field(
        None, 
        description="Financial metrics filters (optional)",
        example={
            "gross_margin_threshold": 0.3,  # 毛利率 (Gross Profit Margin)
            "roe_threshold": 0.15,  # 净资产收益率 (Return on Equity)
            "rd_ratio_threshold": 0.1  # 研发比率 (R&D Ratio)
        }
    )

class RetrieveFilteredStocksRequest(BaseModel):
    """Retrieve filtered stocks request model"""
    timeFrame: List[str] = Field(..., description="List of time frames (daily, weekly, monthly)")
    recentDay: int = Field(1, description="Number of recent days to retrieve (0 for today)")

class ApiResponse(BaseModel):
    """API response model"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class StockAllocation(BaseModel):
    """Stock allocation model for performance retreat"""
    symbol: str = Field(..., description="Stock symbol")
    percentage: float = Field(..., description="Percentage allocation in the portfolio (0-100)")

class PerformanceRetreatRequest(BaseModel):
    """Performance retreat request model"""
    stocks: List[StockAllocation] = Field(..., description="List of stocks with their percentage allocation")
    total_money: float = Field(..., description="Total money in USD for the portfolio")
    start_date: str = Field(..., description="Start date (date B) for mid-price calculation (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date (date A) for open price calculation (YYYY-MM-DD, defaults to current day)")

class StockPerformance(BaseModel):
    """Stock performance model"""
    symbol: str = Field(..., description="Stock symbol")
    shares: float = Field(..., description="Number of shares")
    initial_price: float = Field(..., description="Initial price (mid-price at start date)")
    final_price: float = Field(..., description="Final price (open price at end date)")
    initial_value: float = Field(..., description="Initial value in USD")
    final_value: float = Field(..., description="Final value in USD")
    gain_loss: float = Field(..., description="Money gained or lost in USD")
    gain_loss_percentage: float = Field(..., description="Percentage gain or loss")
    contribution_percentage: float = Field(..., description="Percentage contribution to total gain/loss")

class DailyPerformance(BaseModel):
    """Daily performance model"""
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    price: float = Field(..., description="Price on this date")
    value: float = Field(..., description="Value in USD on this date")
    gain_loss: float = Field(..., description="Money gained or lost since start date in USD")
    gain_loss_percentage: float = Field(..., description="Percentage gain or loss since start date")

class StockDetailedPerformance(StockPerformance):
    """Stock detailed performance model"""
    daily_performance: List[DailyPerformance] = Field(..., description="Daily performance details")

class PerformanceRetreatResponse(BaseModel):
    """Performance retreat response model"""
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    initial_total_value: float = Field(..., description="Initial total value in USD")
    final_total_value: float = Field(..., description="Final total value in USD")
    total_gain_loss: float = Field(..., description="Total money gained or lost in USD")
    total_gain_loss_percentage: float = Field(..., description="Total percentage gain or loss")
    stock_performances: List[StockPerformance] = Field(..., description="Performance for each stock")
    detailed_performances: List[StockDetailedPerformance] = Field(..., description="Detailed performance for each stock")

class PerformanceRetreatApiResponse(ApiResponse):
    """Performance retreat API response model"""
    data: Optional[PerformanceRetreatResponse] = None

@router.post("/trigger_fetch_filtering", response_model=ApiResponse)
async def trigger_fetch_filtering(
    request: TriggerFetchFilteringRequest,
    db: Session = Depends(get_db)
):
    """
    Trigger fetching and filtering of stocks
    
    This endpoint will:
    1. Fetch stock data if not already in Redis
    2. Calculate indicators for each stock
    3. Filter stocks based on indicators
    4. Store filtered results in Redis
    
    Args:
        request: Request with symbols and time frames
        db: Database session
    
    Returns:
        API response with filtered stocks
    """
    try:
        # Validate time frames
        valid_time_frames = ["daily", "weekly", "monthly"]
        for tf in request.timeFrame:
            if tf not in valid_time_frames:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid time frame: {tf}. Must be one of {valid_time_frames}"
                )
        
        # Initialize stock filter
        stock_filter = StockFilter(db)
        
        # Apply custom financial filters if provided
        custom_financial_filters = {}
        if request.financialFilters:
            custom_financial_filters = request.financialFilters
            logger.info(f"Using custom financial filters: {custom_financial_filters}")
            
            # Update config with custom thresholds
            import yaml
            with open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "config.yaml"), "r") as config_file:
                config = yaml.safe_load(config_file)
            
            for key, value in custom_financial_filters.items():
                if key in config.get('financial_metrics', {}):
                    config['financial_metrics'][key] = value
        
        # Filter stocks
        filtered_stocks = stock_filter.filter_stocks(
            symbols=request.symbols,
            time_frames=request.timeFrame
        )
        
        return ApiResponse(
            success=True,
            message=f"Successfully filtered {len(filtered_stocks)} stocks",
            data={"filtered_stocks": filtered_stocks}
        )
    
    except Exception as e:
        logger.error(f"Error in trigger_fetch_filtering: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error filtering stocks: {str(e)}"
        )

@router.post("/retrieve_filtered_stocks", response_model=ApiResponse)
async def retrieve_filtered_stocks(
    request: RetrieveFilteredStocksRequest,
    db: Session = Depends(get_db)
):
    """
    Retrieve filtered stocks from Redis
    
    This endpoint will:
    1. Scan Redis for filtered stocks
    2. Filter by time frame
    3. Return filtered stocks
    
    Args:
        request: Request with time frames and recent days
        db: Database session
    
    Returns:
        API response with filtered stocks
    """
    try:
        # Validate time frames
        valid_time_frames = ["daily", "weekly", "monthly"]
        for tf in request.timeFrame:
            if tf not in valid_time_frames:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid time frame: {tf}. Must be one of {valid_time_frames}"
                )
        
        # Initialize stock filter
        stock_filter = StockFilter(db)
        
        # Get filtered stocks
        filtered_stocks = stock_filter.get_filtered_stocks(
            time_frames=request.timeFrame,
            recent_days=request.recentDay
        )
        
        return ApiResponse(
            success=True,
            message=f"Successfully retrieved {len(filtered_stocks)} filtered stocks",
            data={"filtered_stocks": filtered_stocks}
        )
    
    except Exception as e:
        logger.error(f"Error in retrieve_filtered_stocks: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving filtered stocks: {str(e)}"
        )

@router.post("/fetch_stock_history", response_model=ApiResponse)
async def fetch_stock_history(
    request: FetchStockHistoryRequest,
    db: Session = Depends(get_db)
):
    """
    Fetch stock history
    
    This endpoint will:
    1. Fetch stock history for specified symbols
    2. Store in database
    
    Args:
        request: Request with symbols and time range
        db: Database session
    
    Returns:
        API response with success message
    """
    try:
        # Initialize data acquisition
        data_acquisition = DataAcquisition(db)
        
        # Get time range
        start_date = None
        end_date = None
        
        if request.timeRange:
            start_date = request.timeRange.start
            end_date = request.timeRange.end
        
        # Fetch stock history for each time frame
        time_frames = ["daily", "weekly", "monthly"]
        results = {}
        
        for time_frame in time_frames:
            # Fetch stock history
            history = data_acquisition.fetch_stock_history(
                symbols=request.symbols,
                start_date=start_date,
                end_date=end_date,
                time_frame=time_frame
            )
            
            # Count symbols with data
            symbols_with_data = sum(1 for data in history.values() if not data.empty)
            
            results[time_frame] = {
                "symbols_requested": len(request.symbols) if isinstance(request.symbols, list) else "all",
                "symbols_with_data": symbols_with_data
            }
        
        return ApiResponse(
            success=True,
            message="Successfully fetched stock history",
            data={"results": results}
        )
    
    except Exception as e:
        logger.error(f"Error in fetch_stock_history: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching stock history: {str(e)}"
        )

@router.post("/performance_retreat", response_model=PerformanceRetreatApiResponse)
async def performance_retreat(
    request: PerformanceRetreatRequest,
    db: Session = Depends(get_db)
):
    """
    Calculate performance metrics for a portfolio of stocks
    
    This endpoint will:
    1. Calculate the performance of each stock in the portfolio from start_date to end_date
    2. Calculate the total portfolio performance
    3. Return detailed performance metrics
    
    Args:
        request: Request with stocks, allocation percentages, total money, and date range
        db: Database session
    
    Returns:
        API response with performance metrics
    """
    try:
        # Validate input
        total_percentage = sum(stock.percentage for stock in request.stocks)
        if not (99.0 <= total_percentage <= 101.0):  # Allow for small rounding errors
            raise HTTPException(
                status_code=400,
                detail=f"Total percentage allocation must be 100%, got {total_percentage}%"
            )
        
        # Parse dates
        from datetime import datetime, timedelta
        
        try:
            start_date = datetime.fromisoformat(request.start_date)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid start_date format: {request.start_date}. Use YYYY-MM-DD format."
            )
        
        if request.end_date:
            try:
                end_date = datetime.fromisoformat(request.end_date)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid end_date format: {request.end_date}. Use YYYY-MM-DD format."
                )
        else:
            end_date = datetime.now()
        
        # Initialize data acquisition
        data_acquisition = DataAcquisition(db)
        
        # Calculate performance for each stock
        stock_performances = []
        detailed_performances = []
        initial_total_value = 0
        final_total_value = 0
        
        for stock_allocation in request.stocks:
            symbol = stock_allocation.symbol
            percentage = stock_allocation.percentage
            allocation_amount = request.total_money * (percentage / 100)
            
            # Fetch historical data for the stock
            history = data_acquisition.fetch_stock_history(
                symbols=[symbol],
                start_date=start_date,
                end_date=end_date,
                time_frame="daily"
            )
            
            if not symbol in history or history[symbol].empty:
                logger.warning(f"No historical data found for {symbol}")
                continue
            
            stock_data = history[symbol]
            
            # Get data for start date
            start_data = stock_data.loc[stock_data.index >= start_date].iloc[0] if not stock_data.empty else None
            if start_data is None:
                logger.warning(f"No data found for {symbol} at start date {start_date}")
                continue
                
            # Handle different column name formats (single symbol vs multiple symbols)
            if 'High' in start_data:
                initial_price = (start_data['High'] + start_data['Low']) / 2
            elif ('high' in start_data) and ('low' in start_data):
                initial_price = (start_data['high'] + start_data['low']) / 2
            else:
                # Try to find columns case-insensitively
                columns = [col.lower() if isinstance(col, str) else str(col).lower() for col in start_data.index]
                high_idx = next((i for i, col in enumerate(columns) if 'high' in col), None)
                low_idx = next((i for i, col in enumerate(columns) if 'low' in col), None)
                
                if high_idx is not None and low_idx is not None:
                    initial_price = (start_data.iloc[high_idx] + start_data.iloc[low_idx]) / 2
                else:
                    # Fallback to close price if high/low not available
                    if 'Close' in start_data:
                        initial_price = start_data['Close']
                    elif 'close' in start_data:
                        initial_price = start_data['close']
                    else:
                        close_idx = next((i for i, col in enumerate(columns) if 'close' in col), None)
                        if close_idx is not None:
                            initial_price = start_data.iloc[close_idx]
                        else:
                            logger.warning(f"Could not find price data for {symbol} at start date")
                            continue
            
            shares = allocation_amount / initial_price
            initial_value = shares * initial_price
            
            # Get data for end date
            end_data = stock_data.loc[stock_data.index <= end_date].iloc[-1] if not stock_data.empty else None
            if end_data is None:
                logger.warning(f"No data found for {symbol} at end date {end_date}")
                continue
                
            # Handle different column name formats for final price
            if 'Open' in end_data:
                final_price = end_data['Open']
            elif 'open' in end_data:
                final_price = end_data['open']
            else:
                # Try to find columns case-insensitively
                columns = [col.lower() if isinstance(col, str) else str(col).lower() for col in end_data.index]
                open_idx = next((i for i, col in enumerate(columns) if 'open' in col), None)
                
                if open_idx is not None:
                    final_price = end_data.iloc[open_idx]
                else:
                    # Fallback to close price if open not available
                    if 'Close' in end_data:
                        final_price = end_data['Close']
                    elif 'close' in end_data:
                        final_price = end_data['close']
                    else:
                        close_idx = next((i for i, col in enumerate(columns) if 'close' in col), None)
                        if close_idx is not None:
                            final_price = end_data.iloc[close_idx]
                        else:
                            logger.warning(f"Could not find price data for {symbol} at end date")
                            continue
            
            final_value = shares * final_price
            
            # Calculate gain/loss
            gain_loss = final_value - initial_value
            gain_loss_percentage = (gain_loss / initial_value) * 100 if initial_value > 0 else 0
            
            # Add to totals
            initial_total_value += initial_value
            final_total_value += final_value
            
            # Create daily performance data
            daily_performances = []
            for date, row in stock_data.iterrows():
                if start_date <= date <= end_date:
                    # Handle different column name formats for daily price
                    if 'Open' in row:
                        daily_price = row['Open']
                    elif 'open' in row:
                        daily_price = row['open']
                    else:
                        # Try to find columns case-insensitively
                        if isinstance(row, pd.Series):
                            columns = [col.lower() if isinstance(col, str) else str(col).lower() for col in row.index]
                            open_idx = next((i for i, col in enumerate(columns) if 'open' in col), None)
                            
                            if open_idx is not None:
                                daily_price = row.iloc[open_idx]
                            else:
                                # Fallback to close price if open not available
                                close_idx = next((i for i, col in enumerate(columns) if 'close' in col), None)
                                daily_price = row.iloc[close_idx] if close_idx is not None else None
                        else:
                            daily_price = None
                            
                    daily_value = shares * daily_price
                    daily_gain_loss = daily_value - initial_value
                    daily_gain_loss_percentage = (daily_gain_loss / initial_value) * 100 if initial_value > 0 else 0
                    
                    daily_performances.append(DailyPerformance(
                        date=date.strftime("%Y-%m-%d"),
                        price=daily_price,
                        value=daily_value,
                        gain_loss=daily_gain_loss,
                        gain_loss_percentage=daily_gain_loss_percentage
                    ))
            
            # Add stock performance
            stock_performance = StockPerformance(
                symbol=symbol,
                shares=shares,
                initial_price=initial_price,
                final_price=final_price,
                initial_value=initial_value,
                final_value=final_value,
                gain_loss=gain_loss,
                gain_loss_percentage=gain_loss_percentage,
                contribution_percentage=0  # Will calculate after all stocks are processed
            )
            
            stock_performances.append(stock_performance)
            detailed_performances.append(StockDetailedPerformance(
                **stock_performance.dict(),
                daily_performance=daily_performances
            ))
        
        # Calculate total gain/loss
        total_gain_loss = final_total_value - initial_total_value
        total_gain_loss_percentage = (total_gain_loss / initial_total_value) * 100 if initial_total_value > 0 else 0
        
        # Calculate contribution percentages
        for stock_performance in stock_performances:
            if total_gain_loss != 0:
                stock_performance.contribution_percentage = (stock_performance.gain_loss / total_gain_loss) * 100
            else:
                stock_performance.contribution_percentage = 0
        
        # Update detailed performances with contribution percentages
        for detailed_performance in detailed_performances:
            for stock_performance in stock_performances:
                if detailed_performance.symbol == stock_performance.symbol:
                    detailed_performance.contribution_percentage = stock_performance.contribution_percentage
        
        # Create response
        response = PerformanceRetreatResponse(
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            initial_total_value=initial_total_value,
            final_total_value=final_total_value,
            total_gain_loss=total_gain_loss,
            total_gain_loss_percentage=total_gain_loss_percentage,
            stock_performances=stock_performances,
            detailed_performances=detailed_performances
        )
        
        return PerformanceRetreatApiResponse(
            success=True,
            message="Successfully calculated portfolio performance",
            data=response
        )
    
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise
    
    except Exception as e:
        logger.error(f"Error in performance_retreat: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating portfolio performance: {str(e)}"
        )