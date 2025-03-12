"""
Mock test script to verify FastAPI application structure without real credentials.
"""
import sys
from unittest.mock import patch, MagicMock
from loguru import logger

logger.info("Python version: {}", sys.version)

# Create mocks for the external services
mock_supabase = MagicMock()
mock_transcription = MagicMock()

# Patch the service initialization
with patch("app.services.supabase_service.SupabaseService.__init__", return_value=None) as mock_supabase_init, \
     patch("app.services.supabase_service.SupabaseService.get_memo", return_value={"id": "mock-id", "status": "pending", "audio_url": "mock_url"}) as mock_get_memo, \
     patch("app.services.supabase_service.SupabaseService.download_audio", return_value="mock_file_path") as mock_download_audio, \
     patch("app.services.supabase_service.SupabaseService.update_memo_status", return_value=None) as mock_update_status, \
     patch("app.services.transcription_service.TranscriptionService.__init__", return_value=None) as mock_transcription_init, \
     patch("app.services.transcription_service.TranscriptionService.transcribe", return_value="Mock transcript") as mock_transcribe:
    
    try:
        # Now import the app with all services mocked
        from app.main import app
        logger.success("Successfully imported app with mocked services")
        
        # Print out app routes 
        logger.info("App routes:")
        for route in app.routes:
            logger.info(f"  {route.path} - {route.name} - {route.methods}")
        
        logger.success("Application structure is valid and can be imported successfully")
    except Exception as e:
        logger.error("Error importing app: {}", e)
        import traceback
        logger.error(traceback.format_exc()) 