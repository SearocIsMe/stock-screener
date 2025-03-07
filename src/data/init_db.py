"""
Database initialization script
"""
import os
import logging
from src.utils.logging_config import configure_logging
import yaml
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database
from .models import Base
from .database import get_db

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)

def init_db():
    """Initialize database tables"""
    try:
        # Load configuration
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "config.yaml")
        with open(config_path, "r") as config_file:
            config = yaml.safe_load(config_file)
        
        # Get database URL
        pg_config = config["database"]["postgres"]
        db_url = f"postgresql://{pg_config['username']}:{pg_config['password']}@{pg_config['host']}:{pg_config['port']}/{pg_config['database']}"
        
        # Create engine
        engine = create_engine(db_url)
        
        # Create database if it doesn't exist
        if not database_exists(engine.url):
            create_database(engine.url)
            logger.info(f"Created database: {pg_config['database']}")
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        return True
    
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False

if __name__ == "__main__":
    init_db()