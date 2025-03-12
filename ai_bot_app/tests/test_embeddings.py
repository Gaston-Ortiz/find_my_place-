from unittest.mock import Mock, patch

import pytest

from ai_bot_app.routers.routers_dependencies.embeddings import (
    get_embedding_model,
    get_retrieval,
    retrieval_strategies,
)


def test_retrieval_strategies():
    """Test that retrieval_strategies contains the expected strategies"""
    assert "semantic" in retrieval_strategies
    assert "hybrid" in retrieval_strategies
    assert "keyword" in retrieval_strategies
    assert "sparse" in retrieval_strategies


@patch("langchain_openai.OpenAIEmbeddings")
def test_get_embedding_model_openai(mock_openai):
    """Test get_embedding_model with an OpenAI model"""
    mock_openai.return_value = Mock()

    model = get_embedding_model(model="text-embedding-3-large")

    mock_openai.assert_called_once()


@patch("langchain_huggingface.HuggingFaceEmbeddings")
def test_get_embedding_model_huggingface(mock_hf):
    """Test get_embedding_model with a HuggingFace model"""
    mock_hf.return_value = Mock()

    model = get_embedding_model(model="avsolatorio/GIST-small-Embedding-v0")

    mock_hf.assert_called_once_with(model_name="avsolatorio/GIST-small-Embedding-v0")


@patch("boto3.client")
@patch("langchain_aws.BedrockEmbeddings")
def test_get_embedding_model_bedrock(mock_bedrock, mock_boto):
    """Test get_embedding_model with an Amazon Bedrock model"""
    mock_boto.return_value = Mock()
    mock_bedrock.return_value = Mock()

    model = get_embedding_model(model="amazon.titan-embed-text-v1")

    mock_boto.assert_called_once()
    mock_bedrock.assert_called_once()


@patch("elasticsearch.Elasticsearch")
@patch("ai_bot_app.routers.routers_dependencies.embeddings.get_embedding_model")
@patch("langchain_elasticsearch.ElasticsearchStore")
def test_get_retrieval(mock_es_store, mock_get_embedding, mock_es):
    """Test the get_retrieval function"""
    # Setup mocks
    mock_es.return_value = Mock()
    mock_embedding = Mock()
    mock_get_embedding.return_value = mock_embedding
    mock_es_store.return_value = Mock()

    # Call the function
    retriever = get_retrieval(strategy="semantic", index_name="test_index")

    # Verify expected calls
    mock_get_embedding.assert_called_once()
    mock_es_store.assert_called_once_with(
        es_connection=mock_es.return_value,
        index_name="test_index",
        embedding=mock_embedding,
        strategy=retrieval_strategies["semantic"],
    )
