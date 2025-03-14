import os
import tempfile
from typing import Dict, Optional, Any, Literal
from supabase import create_client, Client
from loguru import logger
import httpx

class SupabaseService:
    """
    Service for interacting with Supabase (database and storage).
    """
    
    def __init__(self, url_prod: str, key_prod: str, url_local: str, key_local: str):
        """
        Initialize the Supabase clients for both production and local environments.
        
        Args:
            url_prod: Production Supabase project URL
            key_prod: Production Supabase service key
            url_local: Local Supabase project URL
            key_local: Local Supabase service key
        """
        self.clients = {}
        
        # Initialize production client if credentials are provided
        if url_prod and key_prod:
            self.clients['production'] = create_client(url_prod, key_prod)
            logger.info("Production Supabase client initialized")
        
        # Initialize local client if credentials are provided
        if url_local and key_local:
            self.clients['local'] = create_client(url_local, key_local)
            logger.info("Local Supabase client initialized")
            
        # Get system environment variable, but don't use it directly
        # This will only be used when no environment is specified in requests
        system_env = os.getenv("ENV", "production").lower()
        logger.info(f"System environment variable ENV is set to: {system_env}")
        
        # Default client is based on system ENV if available, otherwise production
        self.default_environment = system_env if system_env in self.clients else 'production'
        if self.default_environment not in self.clients and 'local' in self.clients:
            self.default_environment = 'local'
        
        # Storage bucket name (same across environments)
        self.storage_bucket = "audio_memos"
        
        logger.info(f"Supabase service initialized with environments: {', '.join(self.clients.keys())}")
        logger.info(f"Default environment (used when no environment is specified): {self.default_environment}")
    
    def get_client(self, environment: Optional[str] = None) -> Client:
        """
        Get the appropriate Supabase client based on the environment.
        
        Args:
            environment: 'production' or 'local' (defaults to self.default_environment)
            
        Returns:
            Supabase Client instance
            
        Raises:
            Exception: If the requested environment client is not initialized
        """
        # If environment is explicitly provided, use it (priority over system ENV)
        if environment:
            # Log the explicitly requested environment
            logger.debug(f"Environment explicitly requested in function call: {environment}")
            
            # Normalize environment value
            env = environment.lower()
            
            # Validate environment
            if env not in ['production', 'local']:
                logger.warning(f"Invalid environment '{env}', falling back to {self.default_environment}")
                env = self.default_environment
            
            # Get the client for the requested environment
            if env in self.clients:
                logger.info(f"Using {env} Supabase client (from explicit request parameter)")
                return self.clients[env]
            
            # If requested environment is not available, warn and fall back to default
            logger.warning(f"Requested environment '{env}' not initialized, falling back to {self.default_environment}")
            
        # Use default environment if no environment was explicitly provided or if requested env is not available
        if self.default_environment in self.clients:
            # If we're here because no environment was provided, log that we're using the default
            if not environment:
                logger.info(f"No environment specified, using default: {self.default_environment}")
            return self.clients[self.default_environment]
        
        # If no clients are available, raise an exception
        available_envs = list(self.clients.keys())
        raise Exception(f"No Supabase client available for environment. Available environments: {available_envs}")
    
    async def get_memo(self, memo_id: str, environment: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieve a memo record from the database.
        
        Args:
            memo_id: UUID of the memo to retrieve
            environment: 'production' or 'local' (optional)
            
        Returns:
            Dict containing the memo data
            
        Raises:
            Exception: If memo not found or other database error
        """
        try:
            # Get environment-specific client
            client = self.get_client(environment)
            
            # More explicit logging about which environment is being used
            env_display = environment if environment else f"{self.default_environment} (default)"
            logger.info(f"Retrieving memo {memo_id} from {env_display} environment")
            
            response = client.table("memos").select("*").eq("id", memo_id).execute()
            
            if not response.data or len(response.data) == 0:
                raise Exception(f"Memo with ID {memo_id} not found")
                
            return response.data[0]
        except Exception as e:
            env_display = environment if environment else f"{self.default_environment} (default)"
            logger.error(f"Error retrieving memo {memo_id} from {env_display} environment: {str(e)}")
            raise
    
    async def update_memo_status(self, memo_id: str, status: str, transcript: Optional[str] = None, environment: Optional[str] = None) -> None:
        """
        Update the status of a memo and optionally its transcript.
        
        Args:
            memo_id: UUID of the memo to update
            status: New status ('transcribing', 'completed', 'error')
            transcript: Optional transcript text
            environment: 'production' or 'local' (optional)
            
        Raises:
            Exception: If update fails
        """
        try:
            # Get environment-specific client
            client = self.get_client(environment)
            
            # More explicit logging about which environment is being used
            env_display = environment if environment else f"{self.default_environment} (default)"
            logger.info(f"Updating memo {memo_id} status to {status} in {env_display} environment")
            
            update_data = {"status": status}
            
            if transcript is not None:
                update_data["transcript"] = transcript
                
            client.table("memos").update(update_data).eq("id", memo_id).execute()
            
            logger.info(f"Successfully updated memo {memo_id} status to {status}")
        except Exception as e:
            env_display = environment if environment else f"{self.default_environment} (default)"
            logger.error(f"Error updating memo {memo_id} in {env_display} environment: {str(e)}")
            raise
    
    async def download_audio(self, audio_url: str, temp_dir: str, environment: Optional[str] = None) -> str:
        """
        Download an audio file from Supabase Storage.
        
        Args:
            audio_url: URL of the audio file in storage
            temp_dir: Directory to save the downloaded file
            environment: 'production' or 'local' (optional)
            
        Returns:
            Path to the downloaded file
            
        Raises:
            Exception: If download fails
        """
        try:
            # Get environment-specific client
            client = self.get_client(environment)
            
            # More explicit logging about which environment is being used
            env_display = environment if environment else f"{self.default_environment} (default)"
            logger.info(f"Downloading audio from {env_display} environment: {audio_url}")
            
            # Handle both formats:
            # 1. Full path including bucket name: "audio_memos/filename.m4a"
            # 2. Just the filename: "filename.m4a"
            
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
                response = client.storage.from_(self.storage_bucket).download(file_path)
                f.write(response)
            
            logger.info(f"Downloaded audio file to {temp_file_path}")
            return temp_file_path
        except Exception as e:
            env_display = environment if environment else f"{self.default_environment} (default)"
            logger.error(f"Error downloading audio from {audio_url} in {env_display} environment: {str(e)}")
            raise
    
    async def check_connection(self, environment: Optional[str] = None) -> bool:
        """
        Check connection to Supabase.
        
        Args:
            environment: 'production' or 'local' (optional)
            
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Get environment-specific client
            client = self.get_client(environment)
            
            # More explicit logging about which environment is being used
            env_display = environment if environment else f"{self.default_environment} (default)"
            logger.debug(f"Checking connection to {env_display} environment")
            
            # Simple query to check if we can connect
            client.table("memos").select("id").limit(1).execute()
            logger.info(f"Supabase connection check successful for {env_display} environment")
            return True
        except Exception as e:
            env_display = environment if environment else f"{self.default_environment} (default)"
            logger.error(f"Supabase connection check failed for {env_display} environment: {str(e)}")
            return False
            
    async def check_all_connections(self) -> Dict[str, bool]:
        """
        Check connections to all configured Supabase environments.
        
        Returns:
            Dictionary mapping environment names to connection status
        """
        results = {}
        for env in self.clients.keys():
            results[env] = await self.check_connection(env)
        return results 