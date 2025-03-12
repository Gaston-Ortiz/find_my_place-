from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from ai_bot_app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@patch("elasticsearch.Elasticsearch")
def test_get_last_update(mock_es, client):
    """Test the get_last_update endpoint"""
    # Setup mock
    mock_es_instance = Mock()
    mock_es.return_value = mock_es_instance

    # Mock search response
    mock_es_instance.search.return_value = {
        "hits": {"hits": [{"_source": {"updated_db": "2023-03-15T12:30:45"}}]}
    }

    # Make request
    response = client.get("/api/v1/products/last_update")

    # Verify response
    assert response.status_code == 200
    assert response.json() == {"last_update": "2023-03-15T12:30:45"}


@patch("elasticsearch.Elasticsearch")
def test_get_houses_paginated(mock_es, client):
    """Test the get_houses endpoint with pagination"""
    # Setup mock
    mock_es_instance = Mock()
    mock_es.return_value = mock_es_instance

    # Mock search response for pagination
    mock_es_instance.search.return_value = {
        "hits": {
            "total": {"value": 100},
            "hits": [
                {"_source": {"text": "House 1", "metadata": {"name": "House 1"}}},
                {"_source": {"text": "House 2", "metadata": {"name": "House 2"}}},
            ],
        }
    }

    # Make request
    response = client.get("/api/v1/products/?skip=0&limit=2")

    # Verify response
    assert response.status_code == 200
    result = response.json()
    assert result["total_hits"] == 100
    assert result["hits_retrieved"] == 2
    assert len(result["hits"]) == 2


@patch("ai_bot_app.routers.products.crud.vector_store")
def test_get_houses_search(mock_vector_store, client):
    """Test the get_houses endpoint with search query"""
    # Setup mock
    mock_vector_store.similarity_search.return_value = [
        Mock(page_content="House with pool", metadata={"name": "Pool House"}),
        Mock(page_content="House near beach", metadata={"name": "Beach House"}),
    ]

    # Make request
    response = client.get("/api/v1/products/?search_query=pool")

    # Verify response
    assert response.status_code == 200
    mock_vector_store.similarity_search.assert_called_once_with("pool", k=10)


@patch("ai_bot_app.routers.products.crud.vector_store")
def test_create_house(mock_vector_store, client):
    """Test the create_house endpoint"""
    # Setup test data
    house_data = {
        "name": "New House",
        "price": 200000.0,
        "description": "Brand new house for sale",
        "url": "https://example.com/new",
        "code_number": 999,
        "number_visit": 0,
        "publish_date": "2023-03-20",
        "last_update": "2023-03-20",
    }

    # Make request
    response = client.post("/api/v1/products/", json=house_data)

    # Verify response
    assert response.status_code == 200
    assert response.json() == {"message": "House created successfully"}
    mock_vector_store.add_documents.assert_called_once()


@patch("elasticsearch.Elasticsearch")
def test_get_house(mock_es, client):
    """Test the get_house endpoint"""
    # Setup mock
    mock_es_instance = Mock()
    mock_es.return_value = mock_es_instance

    # Mock get response
    mock_es_instance.get.return_value = {
        "_source": {
            "text": "Nice house",
            "metadata": {"name": "Nice House", "price": 150000.0},
        }
    }

    # Make request
    response = client.get("/api/v1/products/123")

    # Verify response
    assert response.status_code == 200
    mock_es_instance.get.assert_called_once_with(
        index="scrapy_items", id=123, _source=["text", "metadata"]
    )


@patch("elasticsearch.Elasticsearch")
@patch("ai_bot_app.routers.products.crud.vector_store")
def test_update_house(mock_vector_store, mock_es, client):
    """Test the update_house endpoint"""
    # Setup mocks
    mock_es_instance = Mock()
    mock_es.return_value = mock_es_instance

    # Mock get response for existing document
    mock_es_instance.get.return_value = {
        "_source": {
            "text": "Original description",
            "metadata": {"name": "Original Name", "price": 150000.0},
        }
    }

    # Update data
    update_data = {"name": "Updated Name", "price": 160000.0}

    # Make request
    response = client.put("/api/v1/products/123", json=update_data)

    # Verify response
    assert response.status_code == 200
    assert response.json() == {"message": "House updated successfully"}
    mock_vector_store.add_documents.assert_called_once()


@patch("elasticsearch.Elasticsearch")
def test_delete_house(mock_es, client):
    """Test the delete_house endpoint"""
    # Setup mock
    mock_es_instance = Mock()
    mock_es.return_value = mock_es_instance

    # Make request
    response = client.delete("/api/v1/products/123")

    # Verify response
    assert response.status_code == 200
    assert response.json() == {"message": "House deleted successfully"}
    mock_es_instance.delete.assert_called_once_with(index="scrapy_items", id=123)
