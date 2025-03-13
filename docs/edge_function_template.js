// Edge Function template for calling the environment-aware FastAPI transcription service
// This is a reference implementation, not a complete Edge Function

// Supabase Edge Function
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'

serve(async (req) => {
  try {
    // Parse the request body
    const { memoId } = await req.json()
    
    if (!memoId) {
      return new Response(
        JSON.stringify({ error: 'Missing memoId in request body' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      )
    }
    
    // Get environment variables
    const SUPABASE_URL = Deno.env.get('SUPABASE_URL') || '';
    const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') || '';
    const FASTAPI_URL = Deno.env.get('FASTAPI_URL') || '';
    
    // Define production and local FastAPI URLs
    const FASTAPI_PROD_URL = 'https://dialect-transcription-service.onrender.com';
    const FASTAPI_LOCAL_URL = 'http://host.docker.internal:8000'; // Special Docker address to reach host machine
    
    // Determine if we're in a local development environment
    const isLocalEnvironment = SUPABASE_URL.includes('localhost') || 
                              SUPABASE_URL.includes('127.0.0.1') ||
                              SUPABASE_URL.includes('10.0.4.190');
    
    // Choose the appropriate FastAPI endpoint
    const transcriptionServiceUrl = FASTAPI_URL || (isLocalEnvironment ? FASTAPI_LOCAL_URL : FASTAPI_PROD_URL);
    
    console.log(`DEBUG: Using environment: ${isLocalEnvironment ? 'local' : 'production'}`);
    console.log(`DEBUG: Full URL being called: ${transcriptionServiceUrl}/transcribe`);
    
    // Prepare the request to the FastAPI service with environment information
    const requestBody = JSON.stringify({
      memoId,
      environment: isLocalEnvironment ? 'local' : 'production'
    });
    
    console.log(`Sending request to FastAPI service with body: ${requestBody}`);
    
    // Make request to FastAPI service
    const response = await fetch(`${transcriptionServiceUrl}/transcribe`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: requestBody
    });
    
    // Handle the response
    const data = await response.json();
    
    // Return the response from the FastAPI service
    return new Response(
      JSON.stringify(data),
      { status: response.status, headers: { 'Content-Type': 'application/json' } }
    );
    
  } catch (error) {
    console.error(`Error in Edge Function: ${error.message}`);
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}) 