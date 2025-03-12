from fastapi.testclient import TestClient
import pytest
from unittest.mock import patch, MagicMock

from app.main import app

client = TestClient(app)

def test_root_endpoint():
    """Test the root endpoint returns a health check response."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "Dialect Transcription Service"}

def test_health_endpoint():
    """Test the health endpoint returns the expected format."""
    response = client.get("/health")
    assert response.status_code == 200
    health_data = response.json()
    assert "service" in health_data
    assert "supabase" in health_data
    assert "openai" in health_data

@patch("app.services.supabase_service.SupabaseService.get_memo")
@patch("app.services.supabase_service.SupabaseService.update_memo_status")
@patch("app.services.supabase_service.SupabaseService.download_audio")
@patch("app.services.transcription_service.TranscriptionService.transcribe")
def test_transcribe_endpoint(mock_transcribe, mock_download, mock_update, mock_get_memo):
    """Test the transcribe endpoint with mocked services."""
    # Mock the service calls
    mock_get_memo.return_value = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "audio_url": "https://example.com/audio.m4a",
        "status": "pending"
    }
    mock_download.return_value = "/tmp/audio.m4a"
    mock_transcribe.return_value = "This is a test transcription."
    
    # Call the endpoint
    response = client.post(
        "/transcribe",
        json={"memoId": "123e4567-e89b-12d3-a456-426614174000"}
    )
    
    # Check the response
    assert response.status_code == 200
    assert response.json()["success"] == True
    assert response.json()["memoId"] == "123e4567-e89b-12d3-a456-426614174000"

@patch("app.services.supabase_service.SupabaseService.get_memo")
def test_transcribe_endpoint_error(mock_get_memo):
    """Test the transcribe endpoint error handling."""
    # Mock a service error
    mock_get_memo.side_effect = Exception("Test error")
    
    # Call the endpoint
    response = client.post(
        "/transcribe",
        json={"memoId": "123e4567-e89b-12d3-a456-426614174000"}
    )
    
    # Check the response
    assert response.status_code == 500
    error_data = response.json()
    assert error_data["detail"]["success"] == False
    assert error_data["detail"]["error"] == "processing_error"
    assert "Test error" in error_data["detail"]["message"] 