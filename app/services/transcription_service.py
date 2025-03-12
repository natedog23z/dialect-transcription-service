import os
import time
from typing import Dict, Any, Optional
from loguru import logger
from openai import OpenAI
from openai.types.audio import Transcription

class TranscriptionService:
    """
    Service for transcribing audio files using OpenAI's Whisper API.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the OpenAI client for Whisper API.
        
        Args:
            api_key: OpenAI API Key
        """
        self.client = OpenAI(api_key=api_key)
        self.model = "whisper-1"  # Current recommended model
        logger.info(f"Transcription service initialized with model: {self.model}")
    
    async def transcribe(self, file_path: str, language: Optional[str] = None) -> str:
        """
        Transcribe an audio file using OpenAI's Whisper API.
        
        Args:
            file_path: Path to the audio file
            language: Optional ISO language code (e.g., 'en', 'es')
            
        Returns:
            Transcription text
            
        Raises:
            Exception: If transcription fails
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")
            
        try:
            start_time = time.time()
            logger.info(f"Starting transcription for file: {file_path}")
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # Size in MB
            logger.info(f"File size: {file_size:.2f} MB")
            
            # Prepare transcription parameters
            params = {
                "model": self.model,
                "response_format": "text",
                "temperature": 0.0,  # More deterministic results
            }
            
            # Add language if specified
            if language:
                params["language"] = language
                logger.info(f"Language specified: {language}")
            
            with open(file_path, "rb") as audio_file:
                # Use the OpenAI client to transcribe the audio
                try:
                    response = self.client.audio.transcriptions.create(
                        file=audio_file,
                        **params
                    )
                    
                    elapsed_time = time.time() - start_time
                    logger.info(f"Transcription completed in {elapsed_time:.2f} seconds")
                    
                    # Response is the transcription text
                    return response
                except Exception as e:
                    logger.error(f"OpenAI API error: {str(e)}")
                    # Re-raise to be handled by caller
                    raise
            
        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
            raise
        finally:
            # Clean up temporary file
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Removed temporary file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to remove temporary file {file_path}: {str(e)}")
    
    async def check_connection(self) -> bool:
        """
        Check connection to OpenAI API.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Simple API call to test connectivity
            models = self.client.models.list()
            # Verify the model we need is available
            available_models = [model.id for model in models.data]
            if self.model in available_models:
                logger.info(f"OpenAI connection successful. Model {self.model} is available.")
                return True
            else:
                logger.warning(f"OpenAI connection successful but model {self.model} not found")
                return False
        except Exception as e:
            logger.error(f"OpenAI API connection check failed: {str(e)}")
            return False 