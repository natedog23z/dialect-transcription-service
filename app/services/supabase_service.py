import os
import tempfile
from typing import Dict, Optional, Any
from supabase import create_client, Client
from loguru import logger
import httpx

class SupabaseService:
    """
    Service for interacting with Supabase (database and storage).
    """
    
    def __init__(self, url: str, key: str):
        """
        Initialize the Supabase client.
        
        Args:
            url: Supabase project URL
            key: Supabase service key
        """
        self.client: Client = create_client(url, key)
        self.storage_bucket = "audio_memos"
        logger.info("Supabase service initialized")
    
    async def get_memo(self, memo_id: str, record_type: str = "memos") -> Dict[str, Any]:
        """
        Retrieve a memo record from the database.
        
        Args:
            memo_id: UUID of the memo to retrieve
            record_type: Type of record ('memos' or 'memo_replies')
            
        Returns:
            Dict containing the memo data
            
        Raises:
            Exception: If memo not found or other database error
        """
        try:
            logger.info(f"Getting {record_type} record with ID {memo_id}")
            
            if record_type == "memos":
                response = self.client.table("memos").select("*").eq("id", memo_id).execute()
                id_field = "id"
            elif record_type == "memo_replies":
                response = self.client.table("memo_replies").select("*").eq("reply_id", memo_id).execute()
                id_field = "reply_id"
            else:
                raise ValueError(f"Invalid record type: {record_type}")
                
            if not response.data or len(response.data) == 0:
                raise Exception(f"{record_type.rstrip('s')} with {id_field} {memo_id} not found")
                
            return response.data[0]
        except Exception as e:
            logger.error(f"Error retrieving {record_type} {memo_id}: {str(e)}")
            raise
    
    async def update_memo_status(self, memo_id: str, status: str, transcript: Optional[str] = None, record_type: str = "memos") -> None:
        """
        Update the status of a memo and optionally its transcript.
        
        Args:
            memo_id: UUID of the memo to update
            status: New status ('transcribing', 'completed', 'error')
            transcript: Optional transcript text
            record_type: Type of record ('memos' or 'memo_replies')
            
        Raises:
            Exception: If update fails
        """
        try:
            update_data = {"status": status}
            
            if transcript is not None:
                update_data["transcript"] = transcript
            
            if record_type == "memos":
                self.client.table("memos").update(update_data).eq("id", memo_id).execute()
                id_field = "id"
            elif record_type == "memo_replies":
                self.client.table("memo_replies").update(update_data).eq("reply_id", memo_id).execute()
                id_field = "reply_id"
            else:
                raise ValueError(f"Invalid record type: {record_type}")
            
            logger.info(f"Updated {record_type.rstrip('s')} {memo_id} status to {status}")
        except Exception as e:
            logger.error(f"Error updating {record_type.rstrip('s')} {memo_id}: {str(e)}")
            raise
    
    async def download_audio(self, audio_url: str, temp_dir: str, record_type: str = "memos") -> str:
        """
        Download an audio file from Supabase Storage.
        
        Args:
            audio_url: URL of the audio file in storage
            temp_dir: Directory to save the downloaded file
            record_type: Type of record ('memos' or 'memo_replies')
            
        Returns:
            Path to the downloaded file
            
        Raises:
            Exception: If download fails
        """
        try:
            # Handle both formats:
            # 1. Full path including bucket name: "audio_memos/filename.m4a"
            # 2. Just the filename: "filename.m4a" 
            # 3. Thread reply path: "thread-replies/[room_id]/[timestamp].m4a"
            
            logger.info(f"Downloading audio from {audio_url} (record type: {record_type})")
            
            if f"{self.storage_bucket}/" in audio_url:
                # Extract the path from the URL that contains the bucket name
                path_parts = audio_url.split(f"{self.storage_bucket}/")
                if len(path_parts) < 2:
                    raise Exception(f"Invalid audio URL format: {audio_url}")
                file_path = path_parts[1]
            else:
                # If URL doesn't contain the bucket name, use it directly as the file path
                file_path = audio_url
                logger.info(f"Using filename directly as path: {file_path}")
            
            # Ensure temp directory exists
            os.makedirs(temp_dir, exist_ok=True)
            
            # Create a temporary file with the correct extension
            file_extension = os.path.splitext(file_path)[1]
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension, dir=temp_dir)
            temp_file_path = temp_file.name
            temp_file.close()
            
            # Download the file
            with open(temp_file_path, "wb") as f:
                response = self.client.storage.from_(self.storage_bucket).download(file_path)
                f.write(response)
            
            logger.info(f"Downloaded audio file to {temp_file_path}")
            return temp_file_path
        except Exception as e:
            logger.error(f"Error downloading audio from {audio_url}: {str(e)}")
            raise
    
    async def check_connection(self) -> bool:
        """
        Check connection to Supabase.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Check connectivity by querying both tables
            self.client.table("memos").select("id").limit(1).execute()
            self.client.table("memo_replies").select("reply_id").limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"Supabase connection check failed: {str(e)}")
            return False 