from unittest.mock import MagicMock, Mock, patch

import pytest

from web_scraper.dependencies.items import HouseAdvertisement
from web_scraper.pipelines import ElasticSearchPipeline


@pytest.fixture
def pipeline():
    return ElasticSearchPipeline()


@pytest.fixture
def mock_spider():
    return Mock()


@pytest.fixture
def sample_item():
    return HouseAdvertisement(
        name="Sample House",
        price=120000.0,
        description="A sample house for testing",
        url="https://example.com/house/123",
        code_number=123,
        number_visit=42,
        publish_date="2023-01-15",
        last_update="2023-05-20",
    )


@patch("web_scraper.pipelines.elasticsearch.Elasticsearch")
@patch("web_scraper.pipelines.get_embedding_model")
@patch("web_scraper.pipelines.ElasticsearchStore")
def test_open_spider(mock_es_store, mock_get_embedding, mock_es, pipeline, mock_spider):
    """Test that open_spider initializes connections correctly"""
    # Setup mocks
    mock_es.return_value = Mock()
    mock_get_embedding.return_value = Mock()
    mock_es_store.return_value = Mock()

    # Call the method
    pipeline.open_spider(mock_spider)

    # Verify the expected calls
    mock_es.assert_called_once()
    mock_get_embedding.assert_called_once()
    mock_es_store.assert_called_once()
    assert pipeline.es_client is mock_es.return_value
    assert hasattr(pipeline, "vector_store")


@patch("web_scraper.pipelines.logger")
def test_process_item(mock_logger, pipeline, sample_item, mock_spider):
    """Test that process_item processes the item correctly"""
    # Setup mock vector store
    pipeline.vector_store = Mock()

    # Process the item
    result = pipeline.process_item(sample_item, mock_spider)

    # Verify the result and interactions
    assert isinstance(result, dict)
    assert result["name"] == "Sample House"
    assert result["price"] == 120000.0
    pipeline.vector_store.add_documents.assert_called_once()
    mock_logger.info.assert_called()


def test_close_spider(pipeline, mock_spider):
    """Test that close_spider cleans up connections"""
    # Setup mocks
    pipeline.es_client = Mock()
    pipeline.vector_store = Mock()

    # Close spider
    pipeline.close_spider(mock_spider)

    # Verify cleanup
    pipeline.es_client.close.assert_called_once()
    pipeline.vector_store.close.assert_called_once()
