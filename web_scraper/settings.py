import os

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0"
)
# Delay requests to avoid bot detection
DOWNLOAD_DELAY = 1  # Wait 2 seconds between requests
RANDOMIZE_DOWNLOAD_DELAY = True  # Randomize delay slightly
CONCURRENT_REQUESTS_PER_DOMAIN = 1  # Only 1 request at a time

SPIDER_MODULES = ["web_scraper.spiders"]
NEWSPIDER_MODULE = "web_scraper.spiders"

ITEM_PIPELINES = {
    "web_scraper.pipelines.ElasticSearchPipeline": 300,
}

# Elasticsearch settings (overridable from the environment, e.g. docker-compose)
ELASTIC_URL = os.getenv("ELASTIC_URL", "elasticsearch:9200")
ELASTIC_INDEX_NAME = os.getenv("ELASTIC_INDEX_NAME", "scrapy_items")

# Embedding settings
EMBEDDING_MODEL = "avsolatorio/GIST-small-Embedding-v0"
EMBEDDING_DIMENSION = 384

# Chat settings
CHAT_MODEL = "gpt-4o-mini"
