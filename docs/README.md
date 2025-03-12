# Dialect Transcription Service

A Python FastAPI microservice for transcribing audio files for the Dialect Audio iOS app.

## Overview

This microservice integrates with a Supabase backend to process audio files created by the Dialect Audio iOS app. It downloads audio files from Supabase Storage, transcribes them using OpenAI's Whisper API, and updates the database record with the transcription.

## Features

- FastAPI REST API endpoints for audio transcription
- Integration with Supabase for database and storage access
- Integration with OpenAI's Whisper API for audio transcription
- Error handling and retry functionality
- Health check endpoint for monitoring
- Configurable via environment variables

## Requirements

- Python 3.9+
- OpenAI API key
- Supabase project URL and service key

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/your-username/dialect-transcription-service.git
   cd dialect-transcription-service
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file based on `.env.template`:
   ```
   cp .env.template .env
   ```

5. Edit the `.env` file with your credentials:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_KEY=your-service-key
   WHISPER_API_KEY=your-openai-api-key
   ```

## Usage

Start the service locally:

```
python run.py
```

The service will be available at `http://localhost:8000`.

### API Endpoints

- `GET /` - Root endpoint (health check)
- `POST /transcribe` - Transcribe a new audio memo
- `POST /retry-transcribe` - Retry a failed transcription
- `GET /health` - Check service health (Supabase and OpenAI connectivity)

## Deployment

This service is designed to be deployed on Render.com. Create a new Web Service with the following configuration:

- Build Command: `pip install -r requirements.txt`
- Start Command: `python run.py`
- Environment Variables: Add the variables from your `.env` file

## Development

For local development, set `ENV=development` in your `.env` file to enable auto-reload when files change.

## Testing

Run the tests with pytest:

```
pytest
```

## License

[MIT License](LICENSE) 