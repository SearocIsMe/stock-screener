#!/usr/bin/env python3
"""
Script to initialize the database and run the API server
"""
import os
import logging
import uvicorn
import yaml
from fastapi import FastAPI
from src.api.routes import router as api_router
from src.data.init_db import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from YAML file"""
    config_path = os.path.join(os.path.dirname(__file__), "config", "config.yaml")
    with open(config_path, "r") as config_file:
        return yaml.safe_load(config_file)

def create_app():
    """Create and configure the FastAPI application"""
    app = FastAPI(
        title="Stock Screener API",
        description="API for screening stocks based on technical indicators",
        version="1.0.0",
    )
    
    # Include API routes
    app.include_router(api_router, prefix="/api")
    
    return app

def main():
    """Main entry point for the application"""
    try:
        # Initialize database
        logger.info("Initializing database...")
        init_db()
        
        # Load configuration
        config = load_config()
        logger.info("Configuration loaded successfully")
        
        # Create FastAPI app
        app = create_app()
        
        # Run the API server
        logger.info(f"Starting API server on {config['api']['host']}:{config['api']['port']}")
        uvicorn.run(
            "run:create_app",
            host=config["api"]["host"],
            port=config["api"]["port"],
            reload=config["api"]["debug"],
            factory=True,
        )
    except Exception as e:
        logger.error(f"Error starting application: {e}")
        raise

if __name__ == "__main__":
    main()