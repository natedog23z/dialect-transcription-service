import os
from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Literal, Dict, Union, List, Any
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

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
supabase_service = SupabaseService(
    url_prod=settings.SUPABASE_URL_PROD,
    key_prod=settings.SUPABASE_SERVICE_KEY_PROD,
    branch_prod=settings.SUPABASE_BRANCH_PROD,
    url_staging=settings.SUPABASE_URL_STAGING,
    key_staging=settings.SUPABASE_SERVICE_KEY_STAGING,
    branch_staging=settings.SUPABASE_BRANCH_STAGING,
    url_local=settings.SUPABASE_URL_LOCAL,
    key_local=settings.SUPABASE_SERVICE_KEY_LOCAL,
    branch_local=settings.SUPABASE_BRANCH_LOCAL
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
    environment: Optional[Literal["production", "staging", "local"]] = "production"

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
    status: str
    service: str

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
        # Clear environment selection logging
        env = request.environment
        
        if env:
            logger.info(f"Environment explicitly provided in request: {env}")
        else:
            env = "production"  # Default fallback if not specified in request
            logger.info(f"No environment specified in request, defaulting to: {env}")
        
        logger.info(f"Processing transcription request for memo ID: {request.memoId} using {env} environment")
        
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
        # Clear environment selection logging
        env = request.environment
        
        if env:
            logger.info(f"Environment explicitly provided in retry request: {env}")
        else:
            env = "production"  # Default fallback if not specified in request
            logger.info(f"No environment specified in retry request, defaulting to: {env}")
        
        logger.info(f"Processing retry request for memo ID: {request.memoId} using {env} environment")
        
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

@app.post("/transcribe_url", response_model=TranscriptionResponse)
async def transcribe_from_url(request: Dict[str, Any], x_environment: Optional[str] = Header(None, alias="X-Environment")):
    """
    Transcribe audio from a URL.
    
    Args:
        request: JSON object containing memoId and audioUrl
        x_environment: Environment header (production, staging, local)
        
    Returns:
        Transcription response
    """
    try:
        memo_id = request.get("memoId")
        audio_url = request.get("audioUrl")
        
        # Use header environment if provided, otherwise use the one in the request body
        environment = x_environment or request.get("environment", "production")
        
        if not memo_id:
            raise HTTPException(status_code=400, detail="memoId is required")
        if not audio_url:
            raise HTTPException(status_code=400, detail="audioUrl is required")
            
        logger.info(f"Transcribing URL audio for memo {memo_id} in {environment} environment")
        
        # Download audio to a temp file
        temp_file_path = await supabase_service.download_audio(
            audio_url=audio_url, 
            temp_dir=settings.TEMP_DIR,
            environment=environment
        )
        
        # Get the transcription
        transcript = await transcription_service.transcribe_audio_file(temp_file_path)
        
        # Update the memo record with the transcript
        await supabase_service.update_memo_status(
            memo_id=memo_id,
            status="completed",
            transcript=transcript,
            environment=environment
        )
        
        # Delete the temp file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
        logger.info(f"Successfully transcribed URL audio for memo {memo_id} in {environment} environment")
        
        return {
            "success": True,
            "memoId": memo_id,
            "transcript": transcript,
            "environment": environment
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error transcribing URL audio for memo {memo_id} in {environment} environment: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "memoId": memo_id,
                "error": "transcription_url_error",
                "message": str(e),
                "environment": environment
            }
        )

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Health check endpoint for monitoring.
    Returns a simplified health status of the service.
    """
    return {
        "status": "healthy",
        "service": "Dialect Transcription Service"
    } 