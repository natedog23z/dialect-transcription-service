"""
Simple test script to verify the application can be imported correctly.
"""
import sys
from loguru import logger

logger.info("Python version: {}", sys.version)

try:
    from app.main import app
    logger.info("Successfully imported app")
    logger.info("App routes: {}", app.routes)
except Exception as e:
    logger.error("Error importing app: {}", e)
    import traceback
    logger.error(traceback.format_exc()) 