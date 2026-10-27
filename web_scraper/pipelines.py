# Third party imports
import elasticsearch
from langchain_core.documents import Document
from langchain_elasticsearch import ElasticsearchStore

# Local imports
from web_scraper import settings
from web_scraper.dependencies import items
from web_scraper.dependencies.embedding import get_embedding_model, retrieval_strategies
from web_scraper.log import logger


class ElasticSearchPipeline:
    """Pipeline for storing scraped items in Elasticsearch with vector embeddings.

    This pipeline processes scraped house listings by:
    1. Converting the description text into vector embeddings
    2. Storing both the embeddings and metadata in Elasticsearch
    3. Enabling semantic search capabilities through the vector store

    Attributes:
        collection_name (str): Name of the collection in Elasticsearch
        vector_store (ElasticsearchStore): Vector store for document embeddings
        es_client (elasticsearch.Elasticsearch): Elasticsearch client connection

    Methods:
        open_spider: Initializes Elasticsearch and embedding model connections
        process_item: Processes each scraped item into a document with embeddings
        close_spider: Closes connections when spider finishes
    """

    collection_name = "scrapy_items"

    def open_spider(self, spider):
        self.es_client = elasticsearch.Elasticsearch(
            hosts=[f"http://{settings.ELASTIC_URL}"],
            max_retries=10,
        )

        embeddings = get_embedding_model(
            model=settings.EMBEDDING_MODEL, dimension=settings.EMBEDDING_DIMENSION
        )

        print(f"Embedding model: {settings.EMBEDDING_MODEL}")

        self.vector_store = ElasticsearchStore(
            es_connection=self.es_client,
            index_name=settings.ELASTIC_INDEX_NAME,
            embedding=embeddings,
            strategy=retrieval_strategies["semantic"],
        )

    def process_item(self, house_item: items.HouseAdvertisement, spider):
        logger.info(f"Processing item: {house_item}")

        document = Document(
            page_content=house_item.description,
            metadata=house_item.model_dump(exclude={"description", "code_number"}),
        )

        logger.info(f"Adding document id {house_item.code_number} to vector store")

        self.vector_store.add_documents([document], ids=[house_item.code_number])

        return house_item.model_dump()

    def close_spider(self, spider):
        self.es_client.close()
        self.vector_store.close()
        logger.info("Closed spider")
