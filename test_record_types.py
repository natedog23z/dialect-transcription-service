import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app

client = TestClient(app)

@patch("app.services.supabase_service.SupabaseService.get_memo")
@patch("app.services.supabase_service.SupabaseService.update_memo_status")
@patch("app.services.supabase_service.SupabaseService.download_audio")
@patch("app.services.transcription_service.TranscriptionService.transcribe")
def test_transcribe_memo(mock_transcribe, mock_download, mock_update, mock_get):
    # Mock return values
    mock_get.return_value = AsyncMock(return_value={"id": "123", "status": "pending", "audio_url": "user_123.m4a"})()
    mock_update.return_value = AsyncMock(return_value=None)()
    mock_download.return_value = AsyncMock(return_value="/tmp/audio.m4a")()
    mock_transcribe.return_value = AsyncMock(return_value="Test transcript")()
    
    # Test with default record type (memos)
    response = client.post("/transcribe", json={"memoId": "123"})
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["memoId"] == "123"
    assert data["transcript"] == "Test transcript"
    assert data["recordType"] == "memos"
    
    # Verify mocks were called with correct parameters
    mock_get.assert_called_with("123", "memos")
    mock_update.assert_called_with("123", "completed", "Test transcript", record_type="memos")
    mock_download.assert_called_with("user_123.m4a", any_value(), record_type="memos")

@patch("app.services.supabase_service.SupabaseService.get_memo")
@patch("app.services.supabase_service.SupabaseService.update_memo_status")
@patch("app.services.supabase_service.SupabaseService.download_audio")
@patch("app.services.transcription_service.TranscriptionService.transcribe")
def test_transcribe_memo_reply(mock_transcribe, mock_download, mock_update, mock_get):
    # Mock return values for memo_replies
    mock_get.return_value = AsyncMock(return_value={"reply_id": "456", "status": "pending", "audio_url": "thread-replies/room_789/reply_456.m4a"})()
    mock_update.return_value = AsyncMock(return_value=None)()
    mock_download.return_value = AsyncMock(return_value="/tmp/audio_reply.m4a")()
    mock_transcribe.return_value = AsyncMock(return_value="Reply transcript")()
    
    # Test with memo_replies record type
    response = client.post("/transcribe", json={"memoId": "456", "recordType": "memo_replies"})
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["memoId"] == "456"
    assert data["transcript"] == "Reply transcript"
    assert data["recordType"] == "memo_replies"
    
    # Verify mocks were called with correct parameters
    mock_get.assert_called_with("456", "memo_replies")
    mock_update.assert_called_with("456", "completed", "Reply transcript", record_type="memo_replies")
    mock_download.assert_called_with("thread-replies/room_789/reply_456.m4a", any_value(), record_type="memo_replies")


def any_value():
    """Helper to ignore checking a specific parameter value"""
    class AnyValue:
        def __eq__(self, other):
            return True
    return AnyValue() 