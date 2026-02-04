import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import json

# Mock settings before importing main
with patch.dict('os.environ', {
    'GOOGLE_CLIENT_ID': 'test_client_id',
    'GOOGLE_CLIENT_SECRET': 'test_client_secret',
    'OPENAI_API_KEY': 'test_openai_key',
    'JWT_SECRET_KEY': 'test_jwt_secret',
    'FRONTEND_URL': 'http://localhost:3000'
}):
    from app.main import app
    from app.auth import create_jwt_token, verify_jwt_token, user_credentials_store
    from app.models import Email

client = TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_root_endpoint(self):
        """Test root endpoint returns healthy status."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
    
    def test_health_endpoint(self):
        """Test health endpoint returns detailed status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestAuthEndpoints:
    """Test authentication endpoints."""
    
    def test_login_endpoint_returns_auth_url(self):
        """Test login endpoint returns Google auth URL."""
        with patch('app.auth.create_oauth_flow') as mock_flow:
            mock_flow_instance = MagicMock()
            mock_flow_instance.authorization_url.return_value = (
                'https://accounts.google.com/o/oauth2/auth?test=1',
                'state123'
            )
            mock_flow.return_value = mock_flow_instance
            
            response = client.get("/auth/login")
            assert response.status_code == 200
            data = response.json()
            assert "auth_url" in data
            assert "google.com" in data["auth_url"]
    
    def test_me_endpoint_requires_auth(self):
        """Test /auth/me requires authentication."""
        response = client.get("/auth/me")
        assert response.status_code == 403  # No auth header


class TestJWTFunctions:
    """Test JWT token functions."""
    
    def test_create_and_verify_jwt_token(self):
        """Test JWT token creation and verification."""
        email = "test@example.com"
        name = "Test User"
        picture = "https://example.com/pic.jpg"
        
        token = create_jwt_token(email, name, picture)
        assert token is not None
        assert isinstance(token, str)
        
        # Verify token
        payload = verify_jwt_token(token)
        assert payload["sub"] == email
        assert payload["name"] == name
        assert payload["picture"] == picture
    
    def test_invalid_token_raises_exception(self):
        """Test that invalid token raises HTTPException."""
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            verify_jwt_token("invalid_token")
        
        assert exc_info.value.status_code == 401


class TestEmailParsing:
    """Test email parsing functionality."""
    
    def test_email_model_creation(self):
        """Test Email model can be created with required fields."""
        email = Email(
            id="msg123",
            thread_id="thread123",
            sender="John Doe",
            sender_email="john@example.com",
            subject="Test Subject",
            snippet="This is a test...",
            body="This is a test email body.",
            date="Mon, 1 Jan 2024 10:00:00 +0000"
        )
        
        assert email.id == "msg123"
        assert email.sender == "John Doe"
        assert email.sender_email == "john@example.com"
        assert email.summary is None  # Optional field
    
    def test_email_model_with_summary(self):
        """Test Email model with optional summary."""
        email = Email(
            id="msg123",
            thread_id="thread123",
            sender="John Doe",
            sender_email="john@example.com",
            subject="Test Subject",
            snippet="This is a test...",
            body="This is a test email body.",
            date="Mon, 1 Jan 2024 10:00:00 +0000",
            summary="AI generated summary",
            suggested_reply="Suggested reply text"
        )
        
        assert email.summary == "AI generated summary"
        assert email.suggested_reply == "Suggested reply text"


class TestGmailService:
    """Test Gmail service functions."""
    
    def test_parse_sender_with_name_and_email(self):
        """Test parsing sender from 'Name <email>' format."""
        from app.gmail_service import GmailService
        
        # Create mock credentials
        mock_creds = MagicMock()
        
        with patch('app.gmail_service.build'):
            service = GmailService(mock_creds)
            
            # Test various formats
            name, email = service._parse_sender('"John Doe" <john@example.com>')
            assert name == "John Doe"
            assert email == "john@example.com"
            
            name, email = service._parse_sender('John Doe <john@example.com>')
            assert name == "John Doe"
            assert email == "john@example.com"
            
            name, email = service._parse_sender('john@example.com')
            assert email == "john@example.com"


class TestAIService:
    """Test AI service functions."""
    
    def test_parse_action_from_response_with_json(self):
        """Test parsing action JSON from AI response."""
        from app.ai_service import parse_action_from_response
        
        response = 'Sure, I\'ll fetch your emails. {"action": "read_emails", "count": 5}'
        message, action = parse_action_from_response(response)
        
        assert action is not None
        assert action["action"] == "read_emails"
        assert action["count"] == 5
        assert "I'll fetch your emails" in message
    
    def test_parse_action_from_response_without_json(self):
        """Test parsing response without action JSON."""
        from app.ai_service import parse_action_from_response
        
        response = "Hello! How can I help you today?"
        message, action = parse_action_from_response(response)
        
        assert action is None
        assert message == response
    
    def test_parse_action_with_invalid_json(self):
        """Test parsing response with invalid JSON."""
        from app.ai_service import parse_action_from_response
        
        response = 'Here is some text {invalid json}'
        message, action = parse_action_from_response(response)
        
        assert action is None


class TestChatEndpoint:
    """Test chat endpoint."""
    
    def test_chat_requires_auth(self):
        """Test chat endpoint requires authentication."""
        response = client.post(
            "/chat",
            json={"message": "Hello"}
        )
        assert response.status_code == 403


class TestEmailEndpoints:
    """Test email endpoints."""
    
    def test_get_emails_requires_auth(self):
        """Test get emails requires authentication."""
        response = client.get("/emails")
        assert response.status_code == 403
    
    def test_delete_email_requires_auth(self):
        """Test delete email requires authentication."""
        response = client.delete("/emails/msg123")
        assert response.status_code == 403
    
    def test_send_email_requires_auth(self):
        """Test send email requires authentication."""
        response = client.post(
            "/emails/send",
            json={
                "to": "test@example.com",
                "subject": "Test",
                "body": "Test body"
            }
        )
        assert response.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
