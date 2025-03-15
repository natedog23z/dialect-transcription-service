import os
import tempfile
from typing import Dict, Optional, Any, Literal, Tuple
from supabase import create_client, Client
from loguru import logger
import httpx

class SupabaseService:
    """
    Service for interacting with Supabase (database and storage).
    """
    
    def __init__(self, 
                url_prod: str, key_prod: str, branch_prod: str,
                url_staging: str, key_staging: str, branch_staging: str,
                url_local: str, key_local: str, branch_local: str):
        """
        Initialize the Supabase clients for production, staging, and local environments.
        
        Args:
            url_prod: Production Supabase project URL
            key_prod: Production Supabase service key
            branch_prod: Production Supabase branch name (not used in v1.0.4)
            url_staging: Staging Supabase project URL
            key_staging: Staging Supabase service key
            branch_staging: Staging Supabase branch name (not used in v1.0.4)
            url_local: Local Supabase project URL
            key_local: Local Supabase service key
            branch_local: Local Supabase branch name (not used in v1.0.4)
        """
        self.clients = {}
        self.branches = {}
        
        # Initialize production client if credentials are provided
        if url_prod and key_prod:
            # Initialize client
            self.clients['production'] = create_client(url_prod, key_prod)
            
            # Store branch name for logging purposes only (not used in v1.0.4)
            if branch_prod:
                self.branches['production'] = branch_prod
                logger.info(f"Production Supabase client initialized (branch {branch_prod} noted but not used in this version)")
            else:
                logger.info("Production Supabase client initialized")
        
        # Initialize staging client if credentials are provided
        if url_staging and key_staging:
            # Initialize client
            self.clients['staging'] = create_client(url_staging, key_staging)
            
            # Store branch name for logging purposes only (not used in v1.0.4)
            if branch_staging:
                self.branches['staging'] = branch_staging
                logger.info(f"Staging Supabase client initialized (branch {branch_staging} noted but not used in this version)")
            else:
                logger.info("Staging Supabase client initialized")
        
        # Initialize local client if credentials are provided
        if url_local and key_local:
            # Initialize client
            self.clients['local'] = create_client(url_local, key_local)
            
            # Store branch name for logging purposes only (not used in v1.0.4)
            if branch_local:
                self.branches['local'] = branch_local
                logger.info(f"Local Supabase client initialized (branch {branch_local} noted but not used in this version)")
            else:
                logger.info("Local Supabase client initialized")
            
        # Get system environment variable, but don't use it directly
        # This will only be used when no environment is specified in requests
        system_env = os.getenv("ENV", "production").lower()
        logger.info(f"System environment variable ENV is set to: {system_env}")
        
        # Default client is based on system ENV if available, otherwise production
        self.default_environment = system_env if system_env in self.clients else 'production'
        if self.default_environment not in self.clients:
            available_envs = list(self.clients.keys())
            if available_envs:
                self.default_environment = available_envs[0]
                logger.warning(f"Default environment {system_env} not found, using {self.default_environment} instead")
                
        # Storage bucket name (same across environments)
        self.storage_bucket = "audio_memos"
        
        logger.info(f"Supabase service initialized with environments: {', '.join(self.clients.keys())}")
        logger.info(f"Default environment (used when no environment is specified): {self.default_environment}")
        
        # Log branch info (for reference only, not used in v1.0.4)
        for env, branch in self.branches.items():
            logger.info(f"Branch for {env} environment: {branch} (noted but not used in this version)")
            
        # Log important note about branching
        logger.warning("NOTE: Supabase client v1.0.4 does not support branching via schema method. Branch names are stored for reference only.")
    
    def get_client(self, environment: Optional[str] = None) -> Tuple[Client, Optional[str]]:
        """
        Get the appropriate Supabase client for the specified environment.
        
        Args:
            environment: Optional environment (production, staging, local)
            
        Returns:
            Tuple of (Supabase client, branch name)
            
        Raises:
            ValueError: If no client is available for the specified environment
        """
        # If environment is None or empty, use the default
        env = environment if environment else self.default_environment
        env = env.lower()  # Convert to lowercase for consistency
        
        # Log which environment was requested vs which is being used
        if environment and environment != env:
            logger.info(f"Environment requested: {environment}, using normalized: {env}")
        
        # Check if we have a client for the requested environment
        if env not in self.clients:
            available_envs = list(self.clients.keys())
            err_msg = f"No Supabase client available for environment: {env}. Available environments: {', '.join(available_envs)}"
            logger.error(err_msg)
            raise ValueError(err_msg)
            
        branch = self.branches.get(env)
        logger.debug(f"Using Supabase client for environment: {env}, branch: {branch if branch else 'default'} (branch not used in this version)")
        
        return self.clients[env], branch
    
    async def get_memo(self, memo_id: str, environment: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieve a memo record from the database.
        
        Args:
            memo_id: UUID of the memo to retrieve
            environment: 'production', 'staging', or 'local' (optional)
            
        Returns:
            Dict containing the memo data
            
        Raises:
            Exception: If memo not found or other database error
        """
        try:
            # Get environment-specific client
            client, branch = self.get_client(environment)
            
            # More explicit logging about which environment is being used
            env_display = environment if environment else f"{self.default_environment} (default)"
            branch_display = f", branch: {branch}" if branch else ""
            logger.info(f"Retrieving memo {memo_id} from {env_display} environment{branch_display}")
            
            # In v1.0.4, we can't use schema method, so we just use the client directly
            response = client.table("memos").select("*").eq("id", memo_id).execute()
            
            if not response.data or len(response.data) == 0:
                raise Exception(f"Memo with ID {memo_id} not found")
                
            return response.data[0]
        except Exception as e:
            env_display = environment if environment else f"{self.default_environment} (default)"
            branch_display = f", branch: {branch}" if branch else ""
            logger.error(f"Error retrieving memo {memo_id} from {env_display} environment{branch_display}: {str(e)}")
            raise
    
    async def update_memo_status(self, memo_id: str, status: str, transcript: Optional[str] = None, environment: Optional[str] = None) -> None:
        """
        Update the status of a memo and optionally its transcript.
        
        Args:
            memo_id: UUID of the memo to update
            status: New status ('transcribing', 'completed', 'error')
            transcript: Optional transcript text
            environment: 'production', 'staging', or 'local' (optional)
            
        Raises:
            Exception: If update fails
        """
        try:
            # Get environment-specific client
            client, branch = self.get_client(environment)
            
            # More explicit logging about which environment is being used
            env_display = environment if environment else f"{self.default_environment} (default)"
            branch_display = f", branch: {branch}" if branch else ""
            logger.info(f"Updating memo {memo_id} status to {status} in {env_display} environment{branch_display}")
            
            update_data = {"status": status}
            
            if transcript is not None:
                update_data["transcript"] = transcript
            
            # In v1.0.4, we can't use schema method, so we just use the client directly
            client.table("memos").update(update_data).eq("id", memo_id).execute()
            
            logger.info(f"Successfully updated memo {memo_id} status to {status}")
        except Exception as e:
            env_display = environment if environment else f"{self.default_environment} (default)"
            branch_display = f", branch: {branch}" if branch else ""
            logger.error(f"Error updating memo {memo_id} in {env_display} environment{branch_display}: {str(e)}")
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
            client, branch = self.get_client(environment)
            
            # More explicit logging about which environment is being used
            env_display = environment if environment else f"{self.default_environment} (default)"
            branch_display = f", branch: {branch}" if branch else ""
            logger.info(f"Downloading audio from {env_display} environment{branch_display}: {audio_url}")
            
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
            branch_display = f", branch: {branch}" if branch else ""
            logger.error(f"Error downloading audio from {audio_url} in {env_display} environment{branch_display}: {str(e)}")
            raise
    
    async def check_connection(self, environment: Optional[str] = None) -> bool:
        """
        Check connection to Supabase.
        
        Args:
            environment: 'production', 'staging', or 'local' (optional)
            
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Get environment-specific client
            client, branch = self.get_client(environment)
            
            # More explicit logging about which environment is being used
            env_display = environment if environment else f"{self.default_environment} (default)"
            branch_display = f", branch: {branch}" if branch else ""
            logger.debug(f"Checking connection to {env_display} environment{branch_display}")
            
            # In v1.0.4, we can't use schema method, so we just use the client directly
            client.table("memos").select("id").limit(1).execute()
            
            logger.info(f"Supabase connection check successful for {env_display} environment{branch_display}")
            return True
        except Exception as e:
            env_display = environment if environment else f"{self.default_environment} (default)"
            branch_display = f", branch: {branch}" if branch else ""
            logger.error(f"Supabase connection check failed for {env_display} environment{branch_display}: {str(e)}")
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