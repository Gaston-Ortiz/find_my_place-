# Third party imports
import boto3
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_aws import BedrockEmbeddings
from langchain_elasticsearch import (
    ElasticsearchStore,
    DenseVectorStrategy,
    SparseVectorStrategy,
    DenseVectorScriptScoreStrategy,
)
from langchain_core.vectorstores import VectorStoreRetriever
from elasticsearch import Elasticsearch

# Internal dependencies
from ai_bot_app import settings

es_client = Elasticsearch(
    hosts=[f"http://{settings.ELASTIC_URL}"],
    max_retries=10,
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
        model (str): The name of the embedding model to use. Defaults to the value specified in settings.EMBEDDING_MODE.
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


def get_retrieval(
    strategy: str = "semantic",
    embedding_model: str = settings.EMBEDDING_MODEL,
    index_name: str = "udp_search",
) -> ElasticsearchStore | VectorStoreRetriever:
    """
    Function to get a retriever based on the given parameters.

    Parameters
    ----------
    index: str
        The index to be used for the retriever.

    strategy: str
        The strategy to be used for the retriever. The default value is semantic. Can be semantic, hybrid and keyword.

    embedding_model: str
        The hugging face model to load

    retriever_params: dict
        The parameters to be used for the retriever.

    Returns
    -------
    retriever: VectorStoreRetriever
        The retriever based on the given parameters.
    """
    embeddings = get_embedding_model(model=embedding_model)

    print(f"Embedding model: {embedding_model}")

    elastic_vector_search = ElasticsearchStore(
        es_connection=es_client,
        index_name=index_name,
        embedding=embeddings,
        strategy=retrieval_strategies[strategy],
    )

    return elastic_vector_search
