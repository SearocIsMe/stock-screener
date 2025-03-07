"""
API routes for the stock screener application
"""
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from src.data.database import get_db
from src.data.acquisition import DataAcquisition
from src.filters.stock_filter import StockFilter

# Configure logging
logging.basicConfig(level=logging.INFO)
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

class RetrieveFilteredStocksRequest(BaseModel):
    """Retrieve filtered stocks request model"""
    timeFrame: List[str] = Field(..., description="List of time frames (daily, weekly, monthly)")
    recentDay: int = Field(1, description="Number of recent days to retrieve (0 for today)")

class ApiResponse(BaseModel):
    """API response model"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

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