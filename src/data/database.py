"""
Database connection and session management
"""
import os
import yaml
import redis
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Load configuration
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "config.yaml")
with open(config_path, "r") as config_file:
    config = yaml.safe_load(config_file)

# PostgreSQL connection
pg_config = config["database"]["postgres"]
SQLALCHEMY_DATABASE_URL = f"postgresql://{pg_config['username']}:{pg_config['password']}@{pg_config['host']}:{pg_config['port']}/{pg_config['database']}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis connection
redis_config = config["database"]["redis"]
redis_client = redis.Redis(
    host=redis_config["host"],
    port=redis_config["port"],
    password=redis_config["password"],
    db=redis_config["db"],
    decode_responses=True,
)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_redis():
    """Get Redis client"""
    return redis_client