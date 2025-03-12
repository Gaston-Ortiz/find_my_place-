# Third party imports
from unittest.mock import Mock, patch

import pytest

# Local imports
from web_scraper.dependencies.embedding import get_embedding_model, retrieval_strategies


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
