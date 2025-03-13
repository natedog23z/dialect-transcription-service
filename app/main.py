import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal
from dotenv import load_dotenv
from loguru import logger

from app.services.supabase_service import SupabaseService
from app.services.transcription_service import TranscriptionService
from app.config import settings

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Dialect Transcription Service",
    description="A microservice to transcribe audio files for the Dialect Audio iOS app",
    version="0.1.0"
)

# Initialize services
supabase_service = SupabaseService(
    url_prod=settings.SUPABASE_URL_PROD,
    key_prod=settings.SUPABASE_SERVICE_KEY_PROD,
    url_local=settings.SUPABASE_URL_LOCAL,
    key_local=settings.SUPABASE_SERVICE_KEY_LOCAL
)

transcription_service = TranscriptionService(
    api_key=settings.WHISPER_API_KEY
)

# Configure logging
logger.add(
    "logs/app.log",
    rotation="500 MB",
    level=settings.LOG_LEVEL,
    format="{time} {level} {message}"
)

# Request and response models
class TranscriptionRequest(BaseModel):
    memoId: str
    environment: Optional[Literal["production", "local"]] = "production"

class TranscriptionResponse(BaseModel):
    success: bool
    memoId: str
    transcript: str = None
    environment: str = None

class ErrorResponse(BaseModel):
    success: bool
    memoId: str
    error: str
    message: str
    environment: str = None

class HealthCheckResponse(BaseModel):
    service: str
    supabase: dict
    openai: str

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Dialect Transcription Service"}

@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(request: TranscriptionRequest):
    """
    Transcribe an audio memo from Supabase Storage using Whisper API.
    
    Steps:
    1. Retrieve memo information from Supabase
    2. Update memo status to 'transcribing'
    3. Download audio file from storage
    4. Transcribe audio using Whisper API
    5. Update memo with transcription and status 'completed'
    """
    try:
        env = request.environment or "production"
        logger.info(f"Received transcription request for memo ID: {request.memoId} (Environment: {env})")
        
        # Step 1: Retrieve memo information
        memo = await supabase_service.get_memo(request.memoId, env)
        logger.info(f"Retrieved memo: {memo['id']}, status: {memo['status']} from {env} environment")
        
        # Step 2: Update memo status to 'transcribing'
        await supabase_service.update_memo_status(request.memoId, "transcribing", environment=env)
        
        try:
            # Step 3: Download audio file
            audio_file_path = await supabase_service.download_audio(
                memo['audio_url'], 
                settings.TEMP_DIR,
                environment=env
            )
            
            # Step 4: Transcribe audio
            transcript = await transcription_service.transcribe(audio_file_path)
            
            # Step 5: Update memo with transcription and status
            await supabase_service.update_memo_status(
                request.memoId, 
                "completed",
                transcript,
                environment=env
            )
            
            logger.info(f"Successfully transcribed memo {request.memoId} in {env} environment")
            
            return {
                "success": True,
                "memoId": request.memoId,
                "transcript": transcript,
                "environment": env
            }
            
        except Exception as e:
            # If there's an error during processing, update the memo status
            error_type = type(e).__name__
            await supabase_service.update_memo_status(request.memoId, "error", environment=env)
            raise Exception(f"{error_type}: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error transcribing memo {request.memoId} in {request.environment} environment: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "memoId": request.memoId,
                "error": "processing_error",
                "message": str(e),
                "environment": request.environment
            }
        )

@app.post("/retry-transcribe", response_model=TranscriptionResponse)
async def retry_transcription(request: TranscriptionRequest):
    """
    Retry transcription for a memo that previously failed.
    """
    try:
        env = request.environment or "production"
        logger.info(f"Received retry request for memo ID: {request.memoId} (Environment: {env})")
        
        # Get memo information
        memo = await supabase_service.get_memo(request.memoId, env)
        
        # Verify memo is in error state
        if memo['status'] != "error":
            logger.warning(f"Cannot retry memo {request.memoId} with status {memo['status']} in {env} environment")
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "memoId": request.memoId,
                    "error": "invalid_retry",
                    "message": f"Cannot retry a memo with status '{memo['status']}'. Only memos with 'error' status can be retried.",
                    "environment": env
                }
            )
        
        # Call the regular transcription endpoint logic
        return await transcribe_audio(request)
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error retrying transcription for memo {request.memoId} in {request.environment} environment: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "memoId": request.memoId,
                "error": "retry_error",
                "message": str(e),
                "environment": request.environment
            }
        )

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Health check endpoint for monitoring.
    Checks connection to Supabase (both environments) and OpenAI API.
    """
    health_status = {
        "service": "healthy",
        "supabase": {},
        "openai": "unknown"
    }
    
    # Check all Supabase connections
    try:
        supabase_connections = await supabase_service.check_all_connections()
        health_status["supabase"] = {
            env: "healthy" if status else "unhealthy" 
            for env, status in supabase_connections.items()
        }
    except Exception as e:
        logger.error(f"Supabase health check error: {str(e)}")
        health_status["supabase"] = {"error": str(e)}
    
    # Check OpenAI connection
    try:
        openai_healthy = await transcription_service.check_connection()
        health_status["openai"] = "healthy" if openai_healthy else "unhealthy"
    except Exception as e:
        logger.error(f"OpenAI health check error: {str(e)}")
        health_status["openai"] = "unhealthy"
    
    return health_status 