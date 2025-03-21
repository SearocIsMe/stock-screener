"""
Utility functions for handling asynchronous jobs
"""
import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Any, Callable, Optional

from src.data.database import get_redis
from src.utils.hash_utils import generate_hash_code
from src.utils.logging_config import configure_logging

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)


class AsyncJob:
    """Class for handling asynchronous jobs"""

    @staticmethod
    def create_job(job_type: str, request_data: Dict[str, Any]) -> str:
        """
        Create a new asynchronous job
        
        Args:
            job_type: Type of job (filtering or retreat)
            request_data: Request data
            
        Returns:
            Job ID (hash code)
        """
        # Generate hash code from request data
        job_id = generate_hash_code(request_data)
        
        # Create Redis key
        redis_key = f"{job_type}_job_{job_id}"
        
        # Create job data
        job_data = {
            "status": "processing",
            "request": request_data,
            "timestamp": datetime.now().isoformat(),
            "result": None
        }
        
        # Store in Redis
        redis_client = get_redis()
        redis_client.set(redis_key, json.dumps(job_data))
        
        return job_id

    @staticmethod
    def update_job_status(job_type: str, job_id: str, status: str, result: Optional[Dict[str, Any]] = None) -> None:
        """
        Update job status
        
        Args:
            job_type: Type of job (filtering or retreat)
            job_id: Job ID (hash code)
            status: Job status (processing or done)
            result: Job result (optional)
        """
        # Create Redis key
        redis_key = f"{job_type}_job_{job_id}"
        
        # Get Redis client
        redis_client = get_redis()
        
        # Get existing job data
        job_data_json = redis_client.get(redis_key)
        if not job_data_json:
            logger.error(f"Job {job_id} not found in Redis")
            return
        
        # Parse job data
        job_data = json.loads(job_data_json)
        
        # Update job data
        job_data["status"] = status
        if result is not None:
            job_data["result"] = result
        
        # Store in Redis
        redis_client.set(redis_key, json.dumps(job_data))

    @staticmethod
    def get_job_status(job_type: str, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job status
        
        Args:
            job_type: Type of job (filtering or retreat)
            job_id: Job ID (hash code)
            
        Returns:
            Job data or None if not found
        """
        # Create Redis key
        redis_key = f"{job_type}_job_{job_id}"
        
        # Get Redis client
        redis_client = get_redis()
        
        # Get job data
        job_data_json = redis_client.get(redis_key)
        if not job_data_json:
            return None
        
        # Parse job data
        return json.loads(job_data_json)

    @staticmethod
    def run_async(job_type: str, job_id: str, func: Callable, *args, **kwargs) -> None:
        """
        Run a function asynchronously
        
        Args:
            job_type: Type of job (filtering or retreat)
            job_id: Job ID (hash code)
            func: Function to run
            *args: Function arguments
            **kwargs: Function keyword arguments
        """
        def worker():
            try:
                # Run function
                result = func(*args, **kwargs)
                
                # Update job status
                AsyncJob.update_job_status(job_type, job_id, "done", result)
                
                logger.info(f"Async job {job_id} completed successfully")
            except Exception as e:
                logger.error(f"Error in async job {job_id}: {e}")
                
                # Update job status with error
                AsyncJob.update_job_status(job_type, job_id, "error", {"error": str(e)})
        
        # Start thread
        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()
        
        logger.info(f"Started async job {job_id}")