import boto3
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_aws import BedrockEmbeddings
from web_scraper import settings
from langchain_elasticsearch import (
    DenseVectorStrategy,
    SparseVectorStrategy,
    DenseVectorScriptScoreStrategy,
)

retrieval_strategies = {
    "semantic": DenseVectorStrategy(),
    "hybrid": DenseVectorStrategy(hybrid=True),
    "keyword": DenseVectorScriptScoreStrategy(),
    "sparse": SparseVectorStrategy(model_id=".elser_model_2"),
}


def get_embedding_model(
    model: str = settings.EMBEDDING_MODEL,
    dimension: int = settings.EMBEDDING_DIMENSION,
):
    """
    Returns an embedding model based on the specified model name.

    Args:
        model (str): The name of the embedding model to use. Defaults to the value specified in settings.EMBEDDING_MODEL_DESCRIPTION.
    Returns:
        An instance of the embedding model. If the model name contains "openai", an instance of OpenAIEmbeddings is returned.
        Otherwise, an instance of HuggingFaceEmbeddings is returned with the specified model name.
    """
    if "openai" in model:
        embedding = OpenAIEmbeddings()
    elif "amazon" in model:
        bedrock_client = boto3.client(
            service_name="bedrock-runtime",
            region_name=settings.region_name,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )

        # Create embeddings instance using Amazon Titan Embeddings model
        embedding = BedrockEmbeddings(
            client=bedrock_client,
            model_id=model,
            model_kwargs={"dimensions": int(dimension)},
        )
    else:
        embedding = HuggingFaceEmbeddings(model_name=model)

    return embedding
