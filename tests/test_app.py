from fastapi.testclient import TestClient
import unittest.mock as mock
from app import app

client = TestClient(app)


def test_healthz():
    with TestClient(app) as client:
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


@mock.patch("app.Agent")
def test_chat_endpoint(mock_agent_class):
    # Set up mock agent instance
    mock_agent_instance = mock.AsyncMock()

    # Mock the chat response
    mock_chat_response = mock.AsyncMock()
    mock_chat_response.text.return_value = "Here is a meal plan."
    mock_agent_instance.chat.return_value = mock_chat_response
    mock_agent_instance.conversation_id = "test-conv-id"

    # Configure the Agent context manager
    mock_agent_class.return_value.__aenter__.return_value = mock_agent_instance

    # Call the endpoint
    with TestClient(app) as client:
        response = client.post(
            "/chat", json={"message": "Suggest a dinner", "user_id": "user123"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "Here is a meal plan."
    assert data["conversation_id"] == "test-conv-id"

    # Verify Agent was initialized
    mock_agent_class.assert_called_once()
