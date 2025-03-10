"""
Centralized logging configuration for the stock screener application
"""
import logging

def configure_logging():
    """
    Configure logging with file path, line number, and function name
    
    This function sets up a standardized logging format across the application
    that includes the source code location (file, line, function) in the log output.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d:%(funcName)s] - %(message)s",
    )
    
    # Return the root logger in case it's needed
    return logging.getLogger()