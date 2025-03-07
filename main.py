#!/usr/bin/env python3
"""
Stock Screener Application Entry Point
"""
import os
import logging
from src.utils.logging_config import configure_logging
import uvicorn
import yaml
from fastapi import FastAPI
from src.api.routes import router as api_router

# Configure logging with file path, line number, and function name
configure_logging()
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
        # Load configuration
        config = load_config()
        logger.info("Configuration loaded successfully")
        
        # Create FastAPI app
        app = create_app()
        
        # Run the API server
        logger.info(f"Starting API server on {config['api']['host']}:{config['api']['port']}")
        uvicorn.run(
            "main:create_app",
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