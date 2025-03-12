from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from ai_bot_app.main import app
from ai_bot_app.routers.bot.ai_bot import get_react_agent


@pytest.fixture
def client():
    return TestClient(app)


@patch("ai_bot_app.routers.bot.ai_bot.get_react_agent")
@patch("ai_bot_app.log.logger")
def test_get_bot_response(mock_logger, mock_get_agent, client):
    """Test the get_bot_response endpoint"""
    # Setup mock agent
    mock_agent = Mock()
    mock_get_agent.return_value = mock_agent

    # Mock agent response
    mock_agent.invoke.return_value = {
        "messages": [Mock(content="I found a house that matches your criteria")]
    }

    # Request data
    request_data = {
        "question": "Find me a house with a pool",
        "thread_id": "test-thread-123",
    }

    # Make request
    response = client.post("/api/v1/bot/", json=request_data)

    # Verify response
    assert response.status_code == 200
    assert "ai_message" in response.json()
    mock_agent.invoke.assert_called_once()


@patch("ai_bot_app.routers.routers_dependencies.react_agent.get_llm_model")
@patch("langgraph.prebuilt.create_react_agent")
def test_get_react_agent(mock_create_agent, mock_get_llm):
    """Test the get_react_agent function"""
    # Setup mocks
    mock_llm = Mock()
    mock_get_llm.return_value = mock_llm
    mock_agent = Mock()
    mock_create_agent.return_value = mock_agent

    # Call the function
    agent = get_react_agent()

    # Verify the function returned the expected agent
    assert agent == mock_agent
    mock_get_llm.assert_called_once()
    mock_create_agent.assert_called_once()
