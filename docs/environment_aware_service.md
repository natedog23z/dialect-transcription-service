# Environment-Aware FastAPI Transcription Service

This document explains how the FastAPI transcription service has been updated to be environment-aware, allowing it to connect to different Supabase instances (local vs. production) based on the request it receives.

## Overview

The FastAPI service now supports dynamic connection to either a local or production Supabase instance based on the environment specified in each incoming request. This allows the Edge Function to determine which environment it's running in and ensure the FastAPI service connects to the correct database.

## Configuration

### Environment Variables

The following environment variables are now required:

```
# Production Supabase Configuration
SUPABASE_URL_PROD=https://your-production-project.supabase.co
SUPABASE_SERVICE_KEY_PROD=your-production-service-key

# Local Supabase Configuration
SUPABASE_URL_LOCAL=http://localhost:54321
SUPABASE_SERVICE_KEY_LOCAL=your-local-service-key
```

For backward compatibility, if `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` are defined but the production-specific variables are not, these will be used for the production environment.

## API Changes

### Request Format

The `/transcribe` and `/retry-transcribe` endpoints now accept an optional `environment` field in the request body:

```json
{
  "memoId": "uuid-of-memo",
  "environment": "local" // or "production" (default)
}
```

If the `environment` field is not provided, it defaults to "production" for backward compatibility.

### Response Format

The response from both endpoints now includes the environment that was used:

```json
{
  "success": true,
  "memoId": "uuid-of-memo",
  "transcript": "Transcription text...",
  "environment": "local" // or "production"
}
```

### Health Check

The `/health` endpoint now checks connectivity to both Supabase environments:

```json
{
  "service": "healthy",
  "supabase": {
    "production": "healthy",
    "local": "healthy"
  },
  "openai": "healthy"
}
```

## Edge Function Integration

The Edge Function should:

1. Determine whether it's running in a local or production environment
2. Include the correct `environment` value in the request to the FastAPI service

Example:

```javascript
// Determine environment
const isLocalEnvironment = SUPABASE_URL.includes('localhost');

// Include environment in request
const requestBody = JSON.stringify({
  memoId,
  environment: isLocalEnvironment ? 'local' : 'production'
});

// Send request
await fetch(`${transcriptionServiceUrl}/transcribe`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: requestBody
});
```

## Error Handling

If the specified environment is invalid or not initialized:

1. The service will log a warning
2. It will automatically fall back to the default environment (production if available, otherwise local)
3. Processing will continue without interruption

## Testing

To verify that the environment-aware functionality is working:

1. Set up both local and production Supabase instances
2. Configure the FastAPI service with credentials for both
3. Create test memos in both environments
4. Send requests with explicit environment values
5. Check that the correct Supabase instance is used for each request

For local testing, verify in the logs that the FastAPI service connects to the local Supabase instance. 