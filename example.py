#!/usr/bin/env python3
"""
Example script demonstrating how to use the stock screening tool
"""
import logging
import time
from sqlalchemy.orm import Session
from src.data.database import get_db, SessionLocal
from src.data.init_db import init_db
from src.data.acquisition import DataAcquisition
from src.filters.stock_filter import StockFilter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def main():
    """Main function demonstrating the stock screening workflow"""
    # Initialize database
    logger.info("Initializing database...")
    init_db()
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Step 1: Fetch stock symbols
        logger.info("Fetching stock symbols...")
        data_acquisition = DataAcquisition(db)
        symbols = data_acquisition.fetch_stock_symbols("SP500")
        logger.info(f"Fetched {len(symbols)} symbols from SP500")
        
        # For demonstration, use only a few symbols
        demo_symbols = symbols[:5]  # First 5 symbols
        logger.info(f"Using demo symbols: {demo_symbols}")
        
        # Step 2: Fetch historical data for the symbols
        logger.info("Fetching historical data...")
        data_acquisition.fetch_stock_history(
            symbols=demo_symbols,
            time_frame="daily"
        )
        logger.info("Historical data fetched successfully")
        
        # Step 3: Filter stocks based on technical indicators
        logger.info("Filtering stocks...")
        stock_filter = StockFilter(db)
        filtered_stocks = stock_filter.filter_stocks(
            symbols=demo_symbols,
            time_frames=["daily"]
        )
        
        # Step 4: Display filtered stocks
        if filtered_stocks:
            logger.info(f"Found {len(filtered_stocks)} filtered stocks:")
            for symbol, data in filtered_stocks.items():
                logger.info(f"Symbol: {symbol}")
                for time_frame, indicators in data.items():
                    if time_frame != "metaData":
                        logger.info(f"  Time Frame: {time_frame}")
                        logger.info(f"    BIAS: {indicators['BIAS']['bias']:.2f}")
                        logger.info(f"    RSI: {indicators['RSI']['value']:.2f}")
                        logger.info(f"    MACD: {indicators['MACD']['value']:.2f}")
        else:
            logger.info("No stocks matched the filtering criteria")
        
        # Step 5: Retrieve filtered stocks from Redis
        logger.info("Retrieving filtered stocks from Redis...")
        time.sleep(1)  # Wait for Redis to update
        retrieved_stocks = stock_filter.get_filtered_stocks(
            time_frames=["daily"],
            recent_days=0
        )
        
        logger.info(f"Retrieved {len(retrieved_stocks)} filtered stocks from Redis")
    
    except Exception as e:
        logger.error(f"Error in example script: {e}")
    
    finally:
        db.close()

if __name__ == "__main__":
    main()